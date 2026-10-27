"""NodeSnap API — spec S4. Python owns all business rules and DB writes.
Dev default DB is SQLite (DATABASE_URL overrides, e.g. Postgres in Compose);
recorded in docs/decisions.md. Jobs execute in-process for M1; RQ worker
lands in M6 without changing these contracts."""
from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Cookie, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from domain.commands import CommandError, apply_commands
from domain.models import ProjectSnapshot, new_id
from domain.seed import build_seed
from engineering.pool import pool_quantities
from engineering.registry import METHODS
from geometry.validate import area_schedule, validate_spaces
from reports.pdf import build_review_pdf

from .meta import interpret_brief, meta_status

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./nodesnap.db")
if DB_URL.startswith("postgresql"):
    DB_URL = DB_URL.replace("postgresql+psycopg://", "postgresql+psycopg://")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
Base = declarative_base()
Session = sessionmaker(bind=engine)
ARTIFACT_ROOT = Path(os.environ.get("ARTIFACT_ROOT", "./artifacts"))


class ActorRow(Base):
    __tablename__ = "actors"
    id = Column(String, primary_key=True)
    token_hash = Column(String, index=True)


class ProjectRow(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True)
    actor_id = Column(String, index=True)
    current_revision_id = Column(String)


class RevisionRow(Base):
    __tablename__ = "revisions"
    revision_id = Column(String, primary_key=True)
    project_id = Column(String, index=True)
    revision_number = Column(Integer)
    snapshot_json = Column(Text)


class JobRow(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True)
    project_id = Column(String, index=True)
    revision_id = Column(String)
    kind = Column(String)
    status = Column(String)
    result_json = Column(Text, default="")


class AnalysisRow(Base):
    __tablename__ = "analyses"
    id = Column(String, primary_key=True)
    project_id = Column(String, index=True)
    revision_id = Column(String, index=True)
    result_json = Column(Text)


Base.metadata.create_all(engine)
ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="NodeSnap API", version="0.1.0")


def envelope(data, request: Request):
    return {"request_id": str(uuid.uuid4()), "data": data}


def get_actor(session_token: str | None):
    if not session_token:
        raise HTTPException(401, "demo session required")
    h = hashlib.sha256(session_token.encode()).hexdigest()
    db = Session()
    row = db.query(ActorRow).filter_by(token_hash=h).first()
    db.close()
    if not row:
        raise HTTPException(401, "invalid session")
    return row.id


def load_snapshot(db, project_id: str, revision_id: str) -> ProjectSnapshot:
    row = db.query(RevisionRow).filter_by(project_id=project_id, revision_id=revision_id).first()
    if not row:
        raise HTTPException(404, "revision not found")
    return ProjectSnapshot.model_validate_json(row.snapshot_json)


def own_project(db, actor_id: str, project_id: str) -> ProjectRow:
    row = db.query(ProjectRow).filter_by(id=project_id).first()
    if not row:
        raise HTTPException(404, "project not found")
    if row.actor_id != actor_id:
        raise HTTPException(403, "project belongs to another session")
    return row


@app.get("/health")
def health(request: Request):
    return envelope({"status": "ok", "meta": meta_status()}, request)


@app.post("/api/v1/demo/sessions")
def create_session(request: Request, response: Response):
    token = uuid.uuid4().hex + uuid.uuid4().hex
    db = Session()
    actor = ActorRow(id=new_id(), token_hash=hashlib.sha256(token.encode()).hexdigest())
    db.add(actor); db.commit(); aid = actor.id; db.close()
    response.set_cookie("nodesnap_session", token, httponly=True, samesite="lax")
    return envelope({"actor_id": aid}, request)


class CreateProject(BaseModel):
    seed: bool = True


@app.post("/api/v1/projects")
def create_project(body: CreateProject, request: Request,
                   nodesnap_session: str | None = Cookie(default=None)):
    actor = get_actor(nodesnap_session)
    project_id = new_id()
    snap = build_seed(project_id)
    db = Session()
    db.add(ProjectRow(id=project_id, actor_id=actor, current_revision_id=snap.revision_id))
    db.add(RevisionRow(revision_id=snap.revision_id, project_id=project_id,
                       revision_number=snap.revision_number,
                       snapshot_json=snap.model_dump_json()))
    db.commit(); db.close()
    return envelope({"project_id": project_id, "revision_id": snap.revision_id,
                     "revision_number": snap.revision_number,
                     "content_hash": snap.content_hash}, request)


@app.get("/api/v1/projects/{project_id}")
def get_project(project_id: str, request: Request,
                nodesnap_session: str | None = Cookie(default=None)):
    actor = get_actor(nodesnap_session)
    db = Session(); proj = own_project(db, actor, project_id)
    snap = load_snapshot(db, project_id, proj.current_revision_id); db.close()
    return envelope({"project_id": project_id, "revision_id": snap.revision_id,
                     "revision_number": snap.revision_number,
                     "content_hash": snap.content_hash, "title": snap.title}, request)


@app.get("/api/v1/projects/{project_id}/revisions/{revision_id}")
def get_revision(project_id: str, revision_id: str, request: Request,
                 nodesnap_session: str | None = Cookie(default=None)):
    actor = get_actor(nodesnap_session)
    db = Session(); own_project(db, actor, project_id)
    snap = load_snapshot(db, project_id, revision_id); db.close()
    return envelope(snap.model_dump(mode="json"), request)


class CommandsBody(BaseModel):
    base_revision_id: str
    commands: list[dict]


@app.post("/api/v1/projects/{project_id}/commands")
def post_commands(project_id: str, body: CommandsBody, request: Request,
                  if_match: str | None = Header(default=None),
                  idempotency_key: str | None = Header(default=None),
                  nodesnap_session: str | None = Cookie(default=None)):
    actor = get_actor(nodesnap_session)
    if if_match and if_match.strip('"') != body.base_revision_id:
        raise HTTPException(422, "If-Match and base_revision_id disagree")
    db = Session(); proj = own_project(db, actor, project_id)
    if proj.current_revision_id != body.base_revision_id:
        db.close(); raise HTTPException(412, "stale base revision; reload current revision")
    snap = load_snapshot(db, project_id, body.base_revision_id)
    try:
        new_snap = apply_commands(snap, body.commands)
    except CommandError as e:
        db.close(); raise HTTPException(422, str(e))
    issues = validate_spaces(new_snap.spaces)
    if issues:
        db.close(); raise HTTPException(422, f"invalid geometry: {issues}")
    db.add(RevisionRow(revision_id=new_snap.revision_id, project_id=project_id,
                       revision_number=new_snap.revision_number,
                       snapshot_json=new_snap.model_dump_json()))
    proj.current_revision_id = new_snap.revision_id
    db.commit(); db.close()
    return envelope({"revision_id": new_snap.revision_id,
                     "revision_number": new_snap.revision_number,
                     "content_hash": new_snap.content_hash,
                     "invalidated_result_groups": ["pool", "architecture"]}, request)


class AnalysisBody(BaseModel):
    revision_id: str
    disciplines: list[str] = ["pool", "architecture"]


def compute_results(snap) -> list[dict]:
    results = []
    if snap.pool:
        q = pool_quantities(snap.pool.water_length_m, snap.pool.water_width_m, snap.pool.water_depth_m)
        results.append({"discipline": "pool", "method_id": "pool_quantities",
                        "method_state": "implemented", "execution_status": "completed",
                        "check_outcome": "not_evaluated", "freshness_status": "current",
                        "review_status": "unreviewed", "revision_id": snap.revision_id,
                        "input_bases": ["demonstration_assumption"], "quantities": q})
    results.append({"discipline": "architecture", "method_id": "area_schedule",
                    "method_state": "implemented", "execution_status": "completed",
                    "check_outcome": "not_evaluated", "freshness_status": "current",
                    "review_status": "unreviewed", "revision_id": snap.revision_id,
                    "input_bases": ["derived"], "schedule": area_schedule(snap),
                    "geometry_issues": validate_spaces(snap.spaces)})
    # Structure + foundations: real solver output, checks stay not_evaluated
    # (implemented methods, unverified member/code checks — spec A6.3).
    try:
        from engineering.frame import build_villa_frame, foundation_bearing
        frame = build_villa_frame()
        results.append({"discipline": "structure", "method_id": "structural_frame_analysis",
                        "method_state": "implemented", "execution_status": "completed",
                        "check_outcome": "not_evaluated", "freshness_status": "current",
                        "review_status": "unreviewed", "revision_id": snap.revision_id,
                        "input_bases": ["demonstration_assumption"], "quantities": frame,
                        "issues": [{"code": "UNVERIFIED_SOURCE", "field": "member_design_checks",
                                    "message": "Elastic responses only; steel/timber member, connection and lateral checks require sourced methods."}]})
        bearing = foundation_bearing(frame["sum_base_reactions_n"], 18.0 * 15.5, 100_000.0)
        results.append({"discipline": "foundations", "method_id": "foundation_bearing_review",
                        "method_state": "implemented", "execution_status": "completed",
                        "check_outcome": "not_evaluated", "freshness_status": "current",
                        "review_status": "unreviewed", "revision_id": snap.revision_id,
                        "input_bases": ["demonstration_assumption"], "quantities": bearing,
                        "issues": [{"code": "MISSING_INPUT", "field": "geotechnical_design_basis",
                                    "message": "No project geotechnical basis; scenario uses an assumed 100 kPa allowable bearing."}]})
    except Exception as e:
        results.append({"discipline": "structure", "method_id": "structural_frame_analysis",                        "method_state": "implemented", "execution_status": "error",
                        "check_outcome": "not_evaluated", "freshness_status": "current",
                        "review_status": "unreviewed", "revision_id": snap.revision_id,
                        "input_bases": ["demonstration_assumption"],
                        "issues": [{"code": "UNSTABLE_MODEL", "message": f"frame analysis failed: {type(e).__name__}"}]})
    from engineering.services import build_inventories
    results.append({"discipline": "hvac/plumbing/electrical/energy/drainage",
                    "method_id": "services_inventories",
                    "method_state": "implemented", "execution_status": "completed",
                    "check_outcome": "not_evaluated", "freshness_status": "current",
                    "review_status": "unreviewed", "revision_id": snap.revision_id,
                    "input_bases": ["demonstration_assumption", "derived"],
                    "quantities": build_inventories(snap),
                    "issues": [{"code": "UNVERIFIED_SOURCE", "field": "code_sizing_methods",
                                "message": "Inventories and component quantities only; code sizing/ventilation/energy-pathway/hydraulic methods remain research_required."}]})
    return results


@app.post("/api/v1/projects/{project_id}/analyses")
def post_analysis(project_id: str, body: AnalysisBody, request: Request,
                  nodesnap_session: str | None = Cookie(default=None)):
    actor = get_actor(nodesnap_session)
    db = Session(); own_project(db, actor, project_id)
    snap = load_snapshot(db, project_id, body.revision_id)
    results = compute_results(snap)
    job_id = new_id()
    import json as _json
    db.add(JobRow(id=job_id, project_id=project_id, revision_id=snap.revision_id,
                  kind="analysis", status="succeeded", result_json=_json.dumps(results)))
    db.add(AnalysisRow(id=new_id(), project_id=project_id, revision_id=snap.revision_id,
                       result_json=_json.dumps(results)))
    db.commit(); db.close()
    return JSONResponse(status_code=202, content=envelope(
        {"job_id": job_id, "job_status": "succeeded", "results": results}, request))


@app.get("/api/v1/projects/{project_id}/coverage")
def coverage(project_id: str, revision_id: str, request: Request,
             nodesnap_session: str | None = Cookie(default=None)):
    actor = get_actor(nodesnap_session)
    db = Session(); own_project(db, actor, project_id); db.close()
    return envelope({"revision_id": revision_id,
                     "workflow_complete": False, "discipline_design_complete": False,
                     "methods": [m.model_dump(mode="json") for m in METHODS]}, request)


class ExportBody(BaseModel):
    revision_id: str


@app.post("/api/v1/projects/{project_id}/exports")
def post_export(project_id: str, body: ExportBody, request: Request,
                nodesnap_session: str | None = Cookie(default=None)):
    actor = get_actor(nodesnap_session)
    db = Session(); own_project(db, actor, project_id)
    snap = load_snapshot(db, project_id, body.revision_id); db.close()
    # Freeze the export basis: every file below derives from THIS revision and
    # THIS result set, computed once (spec S8). Basis hash is computed before
    # file hashes exist; the manifest hash itself is stored externally.
    import json as _json
    results = compute_results(snap)
    export_id = new_id()
    basis = {"export_id": export_id, "project_id": project_id,
             "revision_id": snap.revision_id, "content_hash": snap.content_hash,
             "result_method_ids": [r["method_id"] for r in results],
             "report_template_version": "0.2.0"}
    basis_hash = hashlib.sha256(_json.dumps(basis, sort_keys=True).encode()).hexdigest()
    pdf = build_review_pdf(snap, results)
    artifact_id = new_id()
    (ARTIFACT_ROOT / f"{artifact_id}.pdf").write_bytes(pdf)
    model_id = new_id()
    (ARTIFACT_ROOT / f"{model_id}.json").write_text(snap.model_dump_json(indent=1))
    manifest = {"artifact_id": artifact_id, "model_artifact_id": model_id,
                **basis, "export_basis_hash": basis_hash,
                "file_sha256": hashlib.sha256(pdf).hexdigest(),
                "model_sha256": hashlib.sha256(snap.model_dump_json(indent=1).encode()).hexdigest(),
                "document_presence": "generated", "review_status": "unreviewed",
                "authority_process": "not_submitted",
                "sheets": ["COVER", "C-101", "A-101 basement", "A-102 ground", "A-103 upper",
                           "A-104 roof", "CALC-101", "S-101", "F-101", "MPE-101", "REG-101"]}
    manifest_id = new_id()
    (ARTIFACT_ROOT / f"{manifest_id}.json").write_text(_json.dumps(manifest, indent=1))
    manifest["manifest_artifact_id"] = manifest_id
    manifest["manifest_sha256_stored_externally"] = hashlib.sha256(
        _json.dumps(manifest, indent=1).encode()).hexdigest()
    return envelope(manifest, request)


@app.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str, nodesnap_session: str | None = Cookie(default=None)):
    get_actor(nodesnap_session)
    for ext, media in (("pdf", "application/pdf"), ("json", "application/json")):
        path = ARTIFACT_ROOT / f"{artifact_id}.{ext}"
        if path.exists():
            return FileResponse(path, media_type=media,
                                filename=f"nodesnap-{artifact_id}.{ext}")
    raise HTTPException(404, "artifact not found")


class GenerateBody(BaseModel):
    base_revision_id: str
    level: str  # ground | upper
    rooms: list[dict]  # [{name, use, target_area_m2}]


@app.post("/api/v1/projects/{project_id}/generate")
def post_generate(project_id: str, body: GenerateBody, request: Request,
                  nodesnap_session: str | None = Cookie(default=None)):
    from geometry.generate import generate_floor
    actor = get_actor(nodesnap_session)
    db = Session(); proj = own_project(db, actor, project_id)
    if proj.current_revision_id != body.base_revision_id:
        db.close(); raise HTTPException(412, "stale base revision; reload current revision")
    snap = load_snapshot(db, project_id, body.base_revision_id)
    out = generate_floor(snap, body.level, body.rooms)
    if out["spaces"] is None:
        db.close()
        return envelope({"solver_status": out["solver_status"], "execution_status": "blocked",
                         "issue": {"code": "INFEASIBLE",
                                   "message": "No solution within the encoded supported family (strip grammar, +/-15% area)."}}, request)
    import copy as _copy
    new_snap = _copy.deepcopy(snap)
    new_snap.spaces = out["spaces"]
    issues = validate_spaces(new_snap.spaces)
    if issues:
        db.close(); raise HTTPException(422, f"generated geometry invalid: {issues}")
    new_snap.parent_revision_id = snap.revision_id
    new_snap.revision_id = new_id()
    new_snap.revision_number = snap.revision_number + 1
    new_snap = new_snap.with_hash()
    db.add(RevisionRow(revision_id=new_snap.revision_id, project_id=project_id,
                       revision_number=new_snap.revision_number,
                       snapshot_json=new_snap.model_dump_json()))
    proj.current_revision_id = new_snap.revision_id
    db.commit(); db.close()
    return envelope({"revision_id": new_snap.revision_id,
                     "revision_number": new_snap.revision_number,
                     "content_hash": new_snap.content_hash,
                     "solver_status": out["solver_status"],
                     "invalidated_result_groups": ["architecture", "pool"]}, request)


@app.post("/api/v1/projects/{project_id}/undo")
def post_undo(project_id: str, request: Request,
              nodesnap_session: str | None = Cookie(default=None)):
    """Undo = a NEW revision restoring the parent state. History is never rewritten."""
    actor = get_actor(nodesnap_session)
    db = Session(); proj = own_project(db, actor, project_id)
    cur = load_snapshot(db, project_id, proj.current_revision_id)
    if not cur.parent_revision_id:
        db.close(); raise HTTPException(422, "nothing to undo")
    parent = load_snapshot(db, project_id, cur.parent_revision_id)
    import copy as _copy
    restored = _copy.deepcopy(parent)
    restored.parent_revision_id = cur.revision_id
    restored.revision_id = new_id()
    restored.revision_number = cur.revision_number + 1
    restored = restored.with_hash()
    db.add(RevisionRow(revision_id=restored.revision_id, project_id=project_id,
                       revision_number=restored.revision_number,
                       snapshot_json=restored.model_dump_json()))
    proj.current_revision_id = restored.revision_id
    db.commit(); db.close()
    return envelope({"revision_id": restored.revision_id,
                     "revision_number": restored.revision_number,
                     "restored_from_revision_number": parent.revision_number}, request)


class ConversationBody(BaseModel):
    text: str
    base_revision_id: str


@app.post("/api/v1/projects/{project_id}/conversations")
async def conversation(project_id: str, body: ConversationBody, request: Request,
                       nodesnap_session: str | None = Cookie(default=None)):
    """Bounded Meta orchestration: propose -> domain-validate -> commit typed
    commands through the same path as direct edits. Explain/unsupported
    proposals never mutate the model."""
    from domain.models import FT2_TO_M2
    from geometry.generate import generate_floor
    from .orchestrate import propose

    actor = get_actor(nodesnap_session)
    db = Session(); proj = own_project(db, actor, project_id)
    snap = load_snapshot(db, project_id, body.base_revision_id)
    lvl_label = {l.id: l.name for l in snap.levels}
    rooms_ctx = "; ".join(
        f"{lvl_label[s.level_id]}: {s.name} ({s.target_area_m2 and round(s.target_area_m2 / FT2_TO_M2)} ft2 target)"
        for s in snap.spaces if s.classification == "principal")
    pool_ctx = (f"pool water {snap.pool.water_length_m} x {snap.pool.water_width_m} x "
                f"{snap.pool.water_depth_m} m" if snap.pool else "no pool")
    context = f"Revision {snap.revision_number}. {pool_ctx}. Principal rooms: {rooms_ctx}."
    out = await propose(body.text, context)
    if out.get("execution_status") != "completed" or not out.get("proposal"):
        db.close()
        return envelope({"base_revision_id": body.base_revision_id, **out}, request)
    p = out["proposal"]
    # Bounded repair (spec S6: two proposal repairs max): if the model answered
    # explain/unsupported but the homeowner plainly stated a change with a
    # number, re-ask once with corrective feedback instead of silently no-oping.
    import re as _re
    change_like = bool(_re.search(r"\d", body.text)) and bool(
        _re.search(r"(make|set|change|longer|bigger|larger|smaller|resize|extend|metres?|meters?|feet|ft)\b",
                   body.text, _re.I))
    if p["intent"] in ("explain", "unsupported") and change_like:
        out2 = await propose(
            body.text + "\n\n[Controller feedback: your previous proposal changed nothing, "
            "but the homeowner stated an explicit change with a dimension. Re-propose "
            "capturing that change.]", context)
        if out2.get("execution_status") == "completed" and out2.get("proposal"):
            out = out2
            p = out["proposal"]
    result = {"base_revision_id": body.base_revision_id, "execution_status": "completed",
              "model": out.get("model"), "usage": out.get("usage"),
              "proposal": p, "explanation": p.get("explanation", ""),
              "committed_revision_id": None}

    def commit(new_snap, groups):
        db.add(RevisionRow(revision_id=new_snap.revision_id, project_id=project_id,
                           revision_number=new_snap.revision_number,
                           snapshot_json=new_snap.model_dump_json()))
        proj.current_revision_id = new_snap.revision_id
        db.commit()
        result["committed_revision_id"] = new_snap.revision_id
        result["committed_revision_number"] = new_snap.revision_number
        result["invalidated_result_groups"] = groups

    try:
        if p["intent"] == "set_pool_dimensions":
            cmd = {"type": "set_pool_dimensions",
                   "water_length_m": p.get("pool_length_m"),
                   "water_width_m": p.get("pool_width_m"),
                   "water_depth_m": p.get("pool_depth_m")}
            if all(cmd[k] is None for k in ("water_length_m", "water_width_m", "water_depth_m")):
                raise CommandError("proposal stated no pool dimension")
            commit(apply_commands(snap, [cmd]), ["pool", "architecture"])
        elif p["intent"] == "regenerate_floor":
            level = p.get("level") or "ground"
            lvl = next((l for l in snap.levels if l.name == level), None)
            if lvl is None:
                raise CommandError(f"unsupported level: {level}")
            rooms = [{"name": s.name, "use": s.use, "target_area_m2": s.target_area_m2}
                     for s in snap.spaces if s.level_id == lvl.id and s.classification == "principal"]
            if p.get("room_name") and p.get("room_target_area_ft2"):
                hit = [r for r in rooms if r["name"].lower() == p["room_name"].lower()]
                if not hit:
                    raise CommandError(f"room not found on {level}: {p['room_name']}")
                hit[0]["target_area_m2"] = round(p["room_target_area_ft2"] * FT2_TO_M2, 3)
            gen = generate_floor(snap, level, rooms)
            if gen["spaces"] is None:
                result["execution_status"] = "blocked"
                result["issue"] = {"code": "INFEASIBLE",
                                   "message": "No layout within the supported grammar for that program."}
                db.close(); return envelope(result, request)
            import copy as _copy
            new_snap = _copy.deepcopy(snap)
            new_snap.spaces = gen["spaces"]
            issues = validate_spaces(new_snap.spaces)
            if issues:
                raise CommandError(f"generated geometry invalid: {issues}")
            new_snap.parent_revision_id = snap.revision_id
            new_snap.revision_id = new_id()
            new_snap.revision_number = snap.revision_number + 1
            commit(new_snap.with_hash(), ["architecture"])
            result["solver_status"] = gen["solver_status"]
        # explain / unsupported: no mutation by design
    except CommandError as e:
        db.close()
        result["execution_status"] = "blocked"
        result["issue"] = {"code": "DOMAIN_VALIDATION", "message": str(e)}
        return envelope(result, request)
    db.close()
    return envelope(result, request)
