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


@app.post("/api/v1/projects/{project_id}/analyses")
def post_analysis(project_id: str, body: AnalysisBody, request: Request,
                  nodesnap_session: str | None = Cookie(default=None)):
    actor = get_actor(nodesnap_session)
    db = Session(); own_project(db, actor, project_id)
    snap = load_snapshot(db, project_id, body.revision_id)
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
    pdf = build_review_pdf(snap)
    artifact_id = new_id()
    path = ARTIFACT_ROOT / f"{artifact_id}.pdf"
    path.write_bytes(pdf)
    manifest = {"artifact_id": artifact_id, "project_id": project_id,
                "revision_id": snap.revision_id, "revision_number": snap.revision_number,
                "content_hash": snap.content_hash,
                "file_sha256": hashlib.sha256(pdf).hexdigest(),
                "document_presence": "generated", "review_status": "unreviewed",
                "authority_process": "not_submitted"}
    (ARTIFACT_ROOT / f"{artifact_id}.json").write_text(str(manifest))
    return envelope(manifest, request)


@app.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str, nodesnap_session: str | None = Cookie(default=None)):
    get_actor(nodesnap_session)
    path = ARTIFACT_ROOT / f"{artifact_id}.pdf"
    if not path.exists():
        raise HTTPException(404, "artifact not found")
    return FileResponse(path, media_type="application/pdf",
                        filename=f"nodesnap-{artifact_id}.pdf")


class ConversationBody(BaseModel):
    text: str
    base_revision_id: str


@app.post("/api/v1/projects/{project_id}/conversations")
async def conversation(project_id: str, body: ConversationBody, request: Request,
                       nodesnap_session: str | None = Cookie(default=None)):
    actor = get_actor(nodesnap_session)
    db = Session(); own_project(db, actor, project_id); db.close()
    result = await interpret_brief(body.text)
    return envelope({"base_revision_id": body.base_revision_id, **result}, request)
