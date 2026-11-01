"""NodeSnap studio API. Immutable model revisions, isolated sessions, real outputs.

Deployment entry point remains ``app.main:app``. SQLite is the local default;
PostgreSQL, reverse proxy paths and artifact volume configuration are unchanged.
Long calculations still run in-process: no fictional queue or worker is claimed.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import ipaddress
import io
import json
import os
import secrets
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Generic, Literal, TypeVar
from urllib.parse import urlsplit

from fastapi import Cookie, Depends, FastAPI, File, Header, HTTPException, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from domain.commands import CommandError, apply_commands
from domain.models import BuildingProgram, FT2_TO_M2, ProjectSnapshot, new_id
from domain.building import build_building
from domain.seed import build_seed
from engineering.registry import methods_for_snapshot
from engineering.pool import pool_quantities
from geometry.generate import generate_floor
from geometry.validate import area_schedule, validate_snapshot
from reports.pdf import build_review_package

from . import budget
from .analysis import compute_results, with_freshness
from .database import (ActorRow, AnalysisRow, ArtifactRow, ConversationLeaseRow, ConversationRow, EventRow,
                       JobRow, MutationRow, ProjectRow, RevisionRow, append_event,
                       canonical_json, commit_snapshot, connect, digest, ensure_head,
                       load_snapshot, now, own_project, receipt, save_receipt)
from .meta import meta_status, transcribe
from .orchestrate import propose, propose_design


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    @model_validator(mode="after")
    def finite_payload(self):
        if len(canonical_json(self.model_dump()).encode()) > 128_000:
            raise ValueError("Request exceeds the supported command size.")
        return self


T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    request_id: str
    data: T


class CreateProject(StrictBody):
    seed: bool = True
    title: str | None = Field(default=None, max_length=120)


class CommandsBody(StrictBody):
    base_revision_id: str
    commands: list[dict] = Field(min_length=1, max_length=24)


class AnalysisBody(StrictBody):
    revision_id: str
    disciplines: list[str] = Field(default_factory=list, max_length=12)


class ExportBody(StrictBody):
    revision_id: str


class RestoreBody(StrictBody):
    base_revision_id: str
    target_revision_id: str


class RoomRequest(StrictBody):
    name: str = Field(min_length=1, max_length=100)
    use: str = Field(min_length=1, max_length=60)
    target_area_m2: float = Field(gt=0, le=1000)


class GenerateBody(StrictBody):
    base_revision_id: str
    level: str = Field(min_length=1, max_length=80)
    rooms: list[RoomRequest] = Field(min_length=1, max_length=20)


class ConversationBody(StrictBody):
    text: str = Field(min_length=1, max_length=8000)
    base_revision_id: str


class BriefMessage(StrictBody):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=8000)


class DesignBody(StrictBody):
    text: str | None = Field(default=None, min_length=1, max_length=8000)
    brief_history: list[BriefMessage] = Field(default_factory=list, max_length=12)
    program: BuildingProgram | None = None

    @model_validator(mode="after")
    def one_input(self):
        if (self.text is None) == (self.program is None):
            raise ValueError("Supply either a written brief or a complete building program.")
        if self.text is not None and not self.text.strip():
            raise ValueError("Describe the building you want to design.")
        return self


class DesignResult(BaseModel):
    execution_status: Literal["completed", "blocked", "error", "unsupported"]
    explanation: str
    project_id: str | None = None
    committed_revision_id: str | None = None
    revision_number: int | None = None
    committed_revision_number: int | None = None
    content_hash: str | None = None
    title: str | None = None
    program: BuildingProgram | None = None
    assumptions: list[str] = Field(default_factory=list)
    issue: dict | None = None
    spend_total_est_usd: float | None = None


def repair_requirements(program):
    """Only inferred dimensions/areas and explanatory notes may change in repair."""
    protected = program.model_dump(mode="json")
    protected.pop("design_notes", None)
    if protected.get("footprint_basis") == "demonstration_assumption":
        protected.pop("width_m", None)
        protected.pop("depth_m", None)
    floors = [*protected["floors"]]
    if protected.get("basement"):
        floors.append(protected["basement"])
    for floor in floors:
        for room in floor["rooms"]:
            if room.get("area_basis") == "demonstration_assumption":
                room.pop("target_area_m2", None)
    return protected


async def planned_building(factory, text, history=None, context=""):
    """At most three programs, with geometry feedback and protected explicit inputs."""
    status = meta_status()
    if not status["configured"]:
        return {"execution_status": "blocked", "issue": status["issue"], "proposal": None}
    feedback = ""
    previous_program = None
    protected = None
    geometry_message = None
    attempts = min(3, max(1, int(os.environ.get("MAX_LAYOUT_CANDIDATES", "3"))))
    for attempt in range(attempts):
        output = {}
        budget.reserve(factory, 1_000_000)
        try:
            planning_context = context if not feedback else canonical_json({
                "current_design": context, "planning_feedback": feedback, "previous_program": previous_program})
            output = await propose_design(text, history, planning_context)
        finally:
            budget.settle(factory, 1_000_000, "building_design", status["reasoning_model"], output.get("usage"),
                          billing_rejected=(output.get("issue") or {}).get("code") == "PROVIDER_BILLING_REQUIRED")
        proposal = output.get("proposal")
        if not proposal:
            if output.get("issue", {}).get("code") != "MALFORMED_OUTPUT":
                return output
            feedback = "Return exactly a complete schema-constrained program; the previous response could not be validated."
            continue
        if proposal["intent"] != "design_building":
            return output
        program = BuildingProgram.model_validate(proposal["program"])
        if protected is None:
            protected = repair_requirements(program)
        elif repair_requirements(program) != protected:
            feedback = ("The repair changed protected requirements. Restore the previous program's exact title, floor/room identities, counts, uses, heights, "
                        "optional features and all user_supplied dimensions/areas. You may change only demonstration_assumption footprint dimensions and room areas, "
                        "and design_notes. Do not drop rooms or reclassify supplied values as assumptions.")
            continue
        previous_program = program.model_dump(mode="json")
        try:
            candidate = await run_in_threadpool(build_building, new_id(), program)
            issues = validate_snapshot(candidate)
            if issues:
                raise ValueError("; ".join(issue["message"] for issue in issues[:5]))
            return output
        except ValueError as exc:
            geometry_message = str(exc)
            feedback = (f"The deterministic geometry check rejected this candidate: {geometry_message} "
                        "Return a revised complete program that fits. Preserve the exact requested floor and room counts, uses, labels, pool/basement/terrace choices, "
                        "all user_supplied footprint/room areas, yard/garage settings, pool location and all other protected requirements. Adjust only demonstration_assumption room areas/footprint. "
                        "For an explicit footprint, leave generous circulation and service capacity (usually room targets total 55–65% of gross footprint). "
                        "An undersized room may need a larger area or redistribution, even when the total area is small. "
                        "Do not repeat the identical failed candidate. If these explicit requirements conflict, ask one relevant clarification.")
    return {**output, "execution_status": "blocked" if geometry_message else "error", "proposal": None,
            "issue": {"code": "INFEASIBLE_LAYOUT" if geometry_message else "MALFORMED_OUTPUT",
                      "message": geometry_message or "The building program could not be interpreted. Please clarify the rooms and floors."}}


def site_feature_descriptions(snapshot: ProjectSnapshot) -> dict[str, str]:
    """Describe committed SI geometry, never a provider's claimed additions."""
    layout = snapshot.site_layout
    features = {}
    for field, label in (("yard", "rear yard"), ("garage", "detached garage")):
        item = getattr(layout, field, None) if layout else None
        if item:
            xs, ys = [point[0] for point in item.polygon], [point[1] for point in item.polygon]
            features[field] = f"{max(xs) - min(xs):g} × {max(ys) - min(ys):g} m {label}"
    if snapshot.pool:
        pool = snapshot.pool
        features["pool"] = f"{pool.water_length_m:g} × {pool.water_width_m:g} m {pool.location} pool"
    return features


def design_summary(snapshot, *, redesign=False):
    floors = [level for level in snapshot.levels if level.name not in {"basement", "roof"}]
    bedrooms = sum(space.use == "bedroom" for space in snapshot.spaces)
    program = snapshot.building_program
    rooms = sum(room.count for floor in program.floors for room in floor.rooms)
    if program.basement:
        rooms += sum(room.count for room in program.basement.rooms)
    verb = "Redesigned" if redesign else "Created"
    description = f"{verb} {snapshot.title}: {len(floors)} above-ground {'floor' if len(floors) == 1 else 'floors'}, {rooms} requested rooms"
    if bedrooms:
        description += f" including {bedrooms} {'bedroom' if bedrooms == 1 else 'bedrooms'}"
    description += f", in a {program.width_m:g} × {program.depth_m:g} m building footprint. "
    features = site_feature_descriptions(snapshot)
    if features:
        description += "Includes: " + ", ".join(features.values()) + ". "
    return (description + f"The model and plans share revision {snapshot.revision_number}; concept assumptions are recorded with the design.")


def revision_info(snapshot):
    return {"project_id": snapshot.project_id, "revision_id": snapshot.revision_id,
            "revision_number": snapshot.revision_number, "content_hash": snapshot.content_hash,
            "title": snapshot.title, "created_at": snapshot.created_at.isoformat()}


def validate_proposed(snapshot):
    issues = validate_snapshot(snapshot)
    if issues:
        raise HTTPException(422, {"code": "INVALID_GEOMETRY", "message": "The proposed design has invalid geometry.", "issues": issues})


def living_level(snapshot: ProjectSnapshot, name: str):
    """Resolve a current occupied floor; never trust a model-supplied name."""
    level = next((level for level in snapshot.levels if level.name == name), None)
    if level is None:
        raise CommandError(f"Level '{name}' does not exist in this revision. Choose an existing living floor.")
    if level.name in {"basement", "roof"} or level.elevation_m < 0:
        raise CommandError("Choose a living floor; basement and roof layouts cannot be regenerated or copied as a new storey.")
    principal = [space for space in snapshot.spaces if space.level_id == level.id and space.classification == "principal"]
    if not 1 <= len(principal) <= 20:
        raise CommandError("Choose a living floor containing between one and twenty principal rooms.")
    return level


def regenerated(snapshot, level, rooms):
    living_level(snapshot, level)
    output = generate_floor(snapshot, level, rooms)
    if output["spaces"] is None:
        return None, output["solver_status"]
    proposed = snapshot.model_copy(deep=True)
    proposed.spaces = output["spaces"]
    if "pool" in output:
        proposed.pool = output["pool"]
    if "building_program" in output:
        proposed.building_program = output["building_program"]
    proposed.parent_revision_id = snapshot.revision_id
    proposed.revision_id = new_id()
    proposed.revision_number = snapshot.revision_number + 1
    proposed.created_at = datetime.now(timezone.utc)
    from domain.architecture import enrich_snapshot
    enrich_snapshot(proposed)
    validate_proposed(proposed)
    return proposed.with_hash(), output["solver_status"]


def restored_snapshot(current, target):
    proposed = target.model_copy(deep=True)
    if proposed.architecture is None and proposed.schema_version == "0.1.0":
        from domain.legacy import upgrade_legacy_architecture
        try:
            upgrade_legacy_architecture(proposed)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
    proposed.parent_revision_id = current.revision_id
    proposed.revision_id = new_id()
    proposed.revision_number = current.revision_number + 1
    proposed.created_at = datetime.now(timezone.utc)
    from domain.architecture import enrich_snapshot
    enrich_snapshot(proposed)
    validate_proposed(proposed)
    return proposed.with_hash()


def normalized_origin(value: str) -> tuple[str, str, int] | None:
    """An Origin is a serialized origin, not a URL with credentials or a path."""
    if not value or any(character.isspace() or ord(character) < 32 for character in value):
        return None
    if any(character in value for character in (",", "\\", "\x7f", "?", "#")):
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.path or parsed.query or parsed.fragment or parsed.netloc.endswith(":")):
            return None
        port = parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
        if not 1 <= port <= 65535:
            return None
        return parsed.scheme, parsed.hostname.lower(), port
    except ValueError:
        return None


def internal_proxy_peer(request: Request) -> bool:
    """The existing deployment publishes Caddy only; Next reaches the API on
    its private Docker network. Local Next reaches it over loopback. Do not
    accept forwarded-host assertions from a directly connected public peer.
    Next's rewrite proxy overwrites forwarded-host from its actual Host header.
    """
    try:
        peer = ipaddress.ip_address(request.client.host) if request.client else None
    except ValueError:
        return False
    if isinstance(peer, ipaddress.IPv6Address) and peer.ipv4_mapped:
        peer = peer.ipv4_mapped
    networks = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7")
    return bool(peer and (peer.is_loopback or any(peer in ipaddress.ip_network(network) for network in networks)))


def mutation_origin_allowed(request: Request) -> bool:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return True
    fetch_site = request.headers.get("sec-fetch-site", "").lower()
    if fetch_site not in {"", "same-origin", "same-site", "none"}:
        return False
    origins = request.headers.getlist("origin")
    if not origins:
        return True  # CLI and server clients still require the ordinary actor authorization.
    if len(origins) != 1:
        return False
    origin = normalized_origin(origins[0])
    if origin is None:
        return False
    allowed = {normalized_origin(f"{request.url.scheme}://{request.headers.get('host', '')}")}
    if internal_proxy_peer(request) and request.headers.get("x-forwarded-host"):
        hosts = request.headers.getlist("x-forwarded-host")
        schemes = request.headers.getlist("x-forwarded-proto")
        if len(hosts) != 1 or len(schemes) > 1:
            return False
        scheme = schemes[0] if schemes else request.url.scheme
        public_origin = normalized_origin(f"{scheme}://{hosts[0]}")
        if public_origin is None:
            return False
        allowed.add(public_origin)
    return origin in allowed


def create_app(database_url: str | None = None, artifact_root: str | Path | None = None):
    app = FastAPI(title="NodeSnap Studio API", version="0.2.0")
    engine, factory = connect(database_url or os.environ.get("DATABASE_URL", "sqlite:///./nodesnap.db"))
    root = Path(artifact_root or os.environ.get("ARTIFACT_ROOT", "./artifacts"))
    root.mkdir(parents=True, exist_ok=True)
    app.state.session_factory = factory
    app.state.engine = engine
    app.state.artifact_root = root

    @app.middleware("http")
    async def request_identity(request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        if mutation_origin_allowed(request):
            response = await call_next(request)
        else:
            response = JSONResponse({"request_id": request.state.request_id,
                "error": {"code": "ORIGIN_REJECTED", "message": "Open NodeSnap directly to make this change. Cross-origin browser mutations are not allowed."},
                "detail": "Cross-origin browser mutations are not allowed."}, status_code=403)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith(("/api/", "/artifacts/")):
            response.headers["Cache-Control"] = "private, no-store"
        return response

    def envelope(data, request):
        return {"request_id": request.state.request_id, "data": data}

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        codes = {401: "SESSION_REQUIRED", 403: "FORBIDDEN", 404: "NOT_FOUND", 409: "CONFLICT", 412: "STALE_REVISION", 422: "DOMAIN_VALIDATION", 429: "RATE_LIMITED"}
        error = exc.detail if isinstance(exc.detail, dict) else {"code": codes.get(exc.status_code, "REQUEST_FAILED"), "message": str(exc.detail)}
        return JSONResponse({"request_id": request.state.request_id, "error": error, "detail": error["message"]}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        fields = [{"field": ".".join(str(part) for part in err["loc"]), "message": err["msg"]} for err in exc.errors()]
        return JSONResponse({"request_id": request.state.request_id, "error": {"code": "INVALID_REQUEST", "message": "Check the highlighted input fields.", "fields": fields}, "detail": "Invalid request fields."}, status_code=422)

    @app.exception_handler(CommandError)
    async def invalid_command(request, exc):
        return await http_error(request, HTTPException(422, str(exc)))

    @app.exception_handler(IntegrityError)
    async def duplicate(request, exc):
        return await http_error(request, HTTPException(409, "A matching request was accepted concurrently. Reload the design before retrying."))

    def actor(nodesnap_session: str | None = Cookie(default=None)):
        if not nodesnap_session or len(nodesnap_session) > 128:
            raise HTTPException(401, "Start a demonstration session to continue.")
        with factory() as db:
            row = db.query(ActorRow).filter_by(token_hash=hashlib.sha256(nodesnap_session.encode()).hexdigest()).first()
            if row is None:
                raise HTTPException(401, "Your session is unavailable. Start a new demonstration session.")
            return row.id

    def check_header(if_match, base, idempotency_key):
        if not if_match or not idempotency_key:
            raise HTTPException(428, "Edits require If-Match and Idempotency-Key headers.")
        if if_match and if_match.strip('"') != base:
            raise HTTPException(422, "If-Match must identify the same revision as base_revision_id.")

    @app.get("/health")
    def health(request: Request):
        with factory() as db:
            return envelope({"status": "ok", "meta": meta_status(), "spend": budget.summary(db), "execution_mode": "in_process"}, request)

    @app.post("/api/v1/demo/sessions")
    def create_session(request: Request, response: Response, nodesnap_session: str | None = Cookie(default=None)):
        # Reloading a tab does not silently abandon its existing project ownership.
        if nodesnap_session:
            try:
                return envelope({"actor_id": actor(nodesnap_session), "resumed": True}, request)
            except HTTPException:
                pass
        token = secrets.token_hex(32)
        identifier = new_id()
        with factory.begin() as db:
            db.add(ActorRow(id=identifier, token_hash=hashlib.sha256(token.encode()).hexdigest()))
        secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        response.set_cookie("nodesnap_session", token, httponly=True, samesite="lax", secure=secure, max_age=30 * 24 * 3600, path="/")
        return envelope({"actor_id": identifier, "resumed": False}, request)

    @app.get("/api/v1/projects")
    def list_projects(request: Request, actor_id: str = Depends(actor)):
        with factory() as db:
            projects = [revision_info(load_snapshot(db, row.id, row.current_revision_id)) for row in db.query(ProjectRow).filter_by(actor_id=actor_id).all()]
        return envelope(sorted(projects, key=lambda item: item["created_at"], reverse=True), request)

    @app.post("/api/v1/projects")
    def create_project(body: CreateProject, request: Request, actor_id: str = Depends(actor)):
        if not body.seed:
            raise HTTPException(422, "Describe a new building through /api/v1/designs, or explicitly open the demonstration example.")
        snapshot = build_seed(new_id())
        if body.title and body.title.strip():
            snapshot.title = body.title.strip()
            snapshot.with_hash()
        with factory.begin() as db:
            db.add(ProjectRow(id=snapshot.project_id, actor_id=actor_id, current_revision_id=snapshot.revision_id))
            db.add(RevisionRow(revision_id=snapshot.revision_id, project_id=snapshot.project_id, revision_number=1, snapshot_json=snapshot.model_dump_json()))
            append_event(db, snapshot, "project.created", revision_info(snapshot))
        return envelope(revision_info(snapshot), request)

    @app.post("/api/v1/designs", response_model=Envelope[DesignResult])
    async def create_design(body: DesignBody, request: Request, actor_id: str = Depends(actor), idempotency_key: str | None = Header(default=None)):
        if not idempotency_key:
            raise HTTPException(428, "New designs require an Idempotency-Key header.")
        payload = body.model_dump(mode="json")
        with factory.begin() as db:
            rid, previous = receipt(db, actor_id, request.url.path, idempotency_key, payload)
            if previous is not None:
                return envelope(previous, request)
            db.add(MutationRow(id=rid, request_hash=digest(payload), response_json=""))
        result = {"execution_status": "blocked", "explanation": "The building brief needs another detail.",
                  "project_id": None, "committed_revision_id": None, "assumptions": []}
        try:
            proposal = None
            if body.program is not None:
                program = body.program
            else:
                output = await planned_building(factory, body.text, [message.model_dump() for message in body.brief_history])
                proposal = output.get("proposal")
                if proposal:
                    result["explanation"] = proposal["explanation"]
                    if proposal["intent"] == "unsupported":
                        result["execution_status"] = "unsupported"
                    elif proposal["intent"] == "clarify":
                        result["issue"] = {"code": "MISSING_INPUT", "message": proposal["explanation"]}
                    program = BuildingProgram.model_validate(proposal["program"]) if proposal["intent"] == "design_building" else None
                else:
                    result.update(execution_status=output["execution_status"], issue=output.get("issue"),
                                  explanation=output.get("issue", {}).get("message", "The building brief could not be interpreted. Try describing the rooms and floors."))
                    program = None
            if program is not None:
                snapshot = await run_in_threadpool(build_building, new_id(), program)
                validate_proposed(snapshot)
                result.update(execution_status="completed", project_id=snapshot.project_id,
                              committed_revision_id=snapshot.revision_id, revision_number=snapshot.revision_number,
                              committed_revision_number=snapshot.revision_number,
                              content_hash=snapshot.content_hash, title=snapshot.title,
                              program=program.model_dump(mode="json"), explanation=design_summary(snapshot),
                              assumptions=list(dict.fromkeys([*program.design_notes, *[assumption.rationale for assumption in snapshot.assumptions if not assumption.field.startswith("design_notes.")]])))
                with factory.begin() as db:
                    db.add(ProjectRow(id=snapshot.project_id, actor_id=actor_id, current_revision_id=snapshot.revision_id))
                    db.add(RevisionRow(revision_id=snapshot.revision_id, project_id=snapshot.project_id,
                                       revision_number=snapshot.revision_number, snapshot_json=snapshot.model_dump_json()))
                    append_event(db, snapshot, "project.created", {**revision_info(snapshot), "source": "building_program"})
                    # Existing storage requires a revision anchor. Pre-model turns
                    # are anchored to the created revision but explicitly marked
                    # as preceding creation in their public conversation data.
                    pending = []
                    for message in body.brief_history:
                        if message.role == "user":
                            pending.append(message.text)
                        elif pending:
                            db.add(ConversationRow(id=new_id(), project_id=snapshot.project_id, base_revision_id=snapshot.revision_id,
                                created_at=now(), user_text="\n".join(pending), response_json=canonical_json({
                                    "execution_status": "blocked", "explanation": message.text, "committed_revision_id": None,
                                    "base_revision_id": None, "brief_phase": "before_project_creation"})))
                            pending = []
                    if pending:
                        db.add(ConversationRow(id=new_id(), project_id=snapshot.project_id, base_revision_id=snapshot.revision_id,
                            created_at=now(), user_text="\n".join(pending), response_json=canonical_json({
                                "execution_status": "blocked", "explanation": "Included in the building brief.", "committed_revision_id": None,
                                "base_revision_id": None, "brief_phase": "before_project_creation"})))
                    db.add(ConversationRow(id=new_id(), project_id=snapshot.project_id, base_revision_id=snapshot.revision_id,
                        created_at=now(), user_text=body.text or "Create a building from this architectural program.", response_json=canonical_json({**result,
                            "base_revision_id": None, "brief_phase": "before_project_creation"})))
                    save_receipt(db, rid, payload, result)
        except (CommandError, ValueError) as exc:
            result.update(execution_status="blocked", issue={"code": "DOMAIN_VALIDATION", "message": str(exc)}, explanation=str(exc))
        except HTTPException as exc:
            message = exc.detail if isinstance(exc.detail, str) else exc.detail["message"]
            code = exc.detail.get("code", "REQUEST_FAILED") if isinstance(exc.detail, dict) else "REQUEST_FAILED"
            result.update(execution_status="blocked", issue={"code": code, "message": message}, explanation=message)
        with factory.begin() as db:
            result["spend_total_est_usd"] = budget.summary(db)["est_total_usd"]
            save_receipt(db, rid, payload, result)
        return envelope(result, request)

    @app.get("/api/v1/projects/{project_id}")
    def get_project(project_id: str, request: Request, actor_id: str = Depends(actor)):
        with factory() as db:
            project = own_project(db, actor_id, project_id)
            snapshot = load_snapshot(db, project_id, project.current_revision_id)
        return envelope({**revision_info(snapshot), "permissions": {"read": True, "edit": True, "export": True}}, request)

    @app.get("/api/v1/projects/{project_id}/revisions")
    def revisions(project_id: str, request: Request, actor_id: str = Depends(actor)):
        with factory() as db:
            project = own_project(db, actor_id, project_id)
            rows = db.query(RevisionRow).filter_by(project_id=project_id).order_by(RevisionRow.revision_number.desc()).all()
            result = [{**revision_info(ProjectSnapshot.model_validate_json(row.snapshot_json)), "is_current": row.revision_id == project.current_revision_id} for row in rows]
        return envelope(result, request)

    @app.get("/api/v1/projects/{project_id}/revisions/{revision_id}", response_model=Envelope[ProjectSnapshot])
    def revision(project_id: str, revision_id: str, request: Request, response: Response, actor_id: str = Depends(actor)):
        with factory() as db:
            own_project(db, actor_id, project_id)
            snapshot = load_snapshot(db, project_id, revision_id)
        response.headers["ETag"] = f'"{snapshot.revision_id}"'
        return envelope(snapshot.model_dump(mode="json"), request)

    @app.post("/api/v1/projects/{project_id}/commands")
    def commands(project_id: str, body: CommandsBody, request: Request, actor_id: str = Depends(actor), if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None)):
        check_header(if_match, body.base_revision_id, idempotency_key)
        payload = body.model_dump()
        with factory.begin() as db:
            project = own_project(db, actor_id, project_id)
            rid, previous = receipt(db, actor_id, request.url.path, idempotency_key, payload)
            if previous is not None:
                return envelope(previous, request)
            ensure_head(project, body.base_revision_id)
            snapshot = load_snapshot(db, project_id, body.base_revision_id)
            proposed = apply_commands(snapshot, body.commands)
            validate_proposed(proposed)
            result = commit_snapshot(db, actor_id, snapshot, proposed, commands=body.commands)
            save_receipt(db, rid, payload, result)
        return envelope(result, request)

    @app.post("/api/v1/projects/{project_id}/generate")
    def generate(project_id: str, body: GenerateBody, request: Request, actor_id: str = Depends(actor), if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None)):
        check_header(if_match, body.base_revision_id, idempotency_key)
        payload = body.model_dump()
        with factory.begin() as db:
            project = own_project(db, actor_id, project_id)
            rid, previous = receipt(db, actor_id, request.url.path, idempotency_key, payload)
            if previous is not None:
                return envelope(previous, request)
            ensure_head(project, body.base_revision_id)
            snapshot = load_snapshot(db, project_id, body.base_revision_id)
            proposed, solver_status = regenerated(snapshot, body.level, [room.model_dump() for room in body.rooms])
            if proposed is None:
                result = {"solver_status": solver_status, "execution_status": "blocked", "issue": {"code": "INFEASIBLE" if solver_status == "INFEASIBLE" else "SOLVER_UNRESOLVED", "message": "No valid candidate was returned within the supported layout family and search budget."}}
            else:
                result = {**commit_snapshot(db, actor_id, snapshot, proposed), "solver_status": solver_status, "execution_status": "completed"}
            save_receipt(db, rid, payload, result)
        return envelope(result, request)

    @app.post("/api/v1/projects/{project_id}/restore")
    def restore(project_id: str, body: RestoreBody, request: Request, actor_id: str = Depends(actor), if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None)):
        check_header(if_match, body.base_revision_id, idempotency_key)
        payload = body.model_dump()
        with factory.begin() as db:
            project = own_project(db, actor_id, project_id)
            rid, previous = receipt(db, actor_id, request.url.path, idempotency_key, payload)
            if previous is not None:
                return envelope(previous, request)
            ensure_head(project, body.base_revision_id)
            current = load_snapshot(db, project_id, body.base_revision_id)
            target = load_snapshot(db, project_id, body.target_revision_id)
            result = {**commit_snapshot(db, actor_id, current, restored_snapshot(current, target)), "restored_from_revision_number": target.revision_number}
            save_receipt(db, rid, payload, result)
        return envelope(result, request)

    @app.post("/api/v1/projects/{project_id}/undo")
    def undo(project_id: str, request: Request, actor_id: str = Depends(actor)):
        with factory() as db:
            project = own_project(db, actor_id, project_id)
            current = load_snapshot(db, project_id, project.current_revision_id)
            if not current.parent_revision_id:
                raise HTTPException(422, "There is no earlier revision to restore.")
        return restore(project_id, RestoreBody(base_revision_id=current.revision_id, target_revision_id=current.parent_revision_id), request, actor_id, current.revision_id, new_id())

    @app.post("/api/v1/projects/{project_id}/analyses")
    def analyses(project_id: str, body: AnalysisBody, request: Request, actor_id: str = Depends(actor)):
        with factory() as db:
            own_project(db, actor_id, project_id)
            snapshot = load_snapshot(db, project_id, body.revision_id)
        results = compute_results(snapshot)
        job_id = new_id()
        with factory.begin() as db:
            project = own_project(db, actor_id, project_id)
            db.add(AnalysisRow(id=new_id(), project_id=project_id, revision_id=snapshot.revision_id, result_json=canonical_json(results)))
            db.add(JobRow(id=job_id, project_id=project_id, revision_id=snapshot.revision_id, kind="analysis", status="succeeded", result_json=canonical_json(results)))
            append_event(db, snapshot, "analysis.completed", {"job_id": job_id})
            current_id = project.current_revision_id
        return envelope({"job_id": job_id, "job_status": "succeeded", "execution_mode": "in_process", "revision_id": snapshot.revision_id, "results": with_freshness(results, current_id)}, request)

    @app.get("/api/v1/projects/{project_id}/analyses")
    def previous_analysis(project_id: str, revision_id: str, request: Request, actor_id: str = Depends(actor)):
        with factory() as db:
            project = own_project(db, actor_id, project_id)
            load_snapshot(db, project_id, revision_id)
            row = db.query(AnalysisRow).filter_by(project_id=project_id, revision_id=revision_id).first()
            return envelope({"revision_id": revision_id, "results": with_freshness(json.loads(row.result_json), project.current_revision_id) if row else []}, request)

    @app.get("/api/v1/projects/{project_id}/coverage")
    def coverage(project_id: str, revision_id: str, request: Request, actor_id: str = Depends(actor)):
        with factory() as db:
            project = own_project(db, actor_id, project_id)
            snapshot = load_snapshot(db, project_id, revision_id)
            has_analysis = db.query(AnalysisRow).filter_by(project_id=project_id, revision_id=revision_id).first() is not None
            has_export = db.query(ArtifactRow).filter_by(project_id=project_id, revision_id=revision_id, extension="pdf").first() is not None
        return envelope({"revision_id": revision_id, "freshness_status": "current" if project.current_revision_id == revision_id else "stale", "workflow_complete": has_analysis and has_export, "discipline_design_complete": False, "methods": [method.model_dump(mode="json") for method in methods_for_snapshot(snapshot)]}, request)

    @app.get("/api/v1/jobs/{job_id}")
    def job(job_id: str, request: Request, actor_id: str = Depends(actor)):
        with factory() as db:
            row = db.get(JobRow, job_id)
            if row is None:
                raise HTTPException(404, "Job not found.")
            project = own_project(db, actor_id, row.project_id)
            return envelope({"job_id": row.id, "project_id": row.project_id, "revision_id": row.revision_id, "job_status": row.status, "kind": row.kind, "execution_mode": "in_process", "freshness_status": "current" if row.revision_id == project.current_revision_id else "stale", "result": json.loads(row.result_json) if row.result_json else None}, request)

    @app.get("/api/v1/projects/{project_id}/events")
    async def events(project_id: str, request: Request, actor_id: str = Depends(actor), last_event_id: str | None = Header(default=None)):
        with factory() as db:
            own_project(db, actor_id, project_id)
        try:
            after = int(last_event_id or 0)
        except ValueError:
            raise HTTPException(422, "Last-Event-ID must be a sequence number.")
        async def stream():
            cursor = after
            for _ in range(30):
                if await request.is_disconnected():
                    return
                with factory() as db:
                    rows = db.query(EventRow).filter(EventRow.project_id == project_id, EventRow.sequence > cursor).order_by(EventRow.sequence).limit(100).all()
                for event in rows:
                    cursor = event.sequence
                    data = {"event_sequence": cursor, "type": event.type, "project_id": project_id, "revision_id": event.revision_id, "created_at": event.created_at, **json.loads(event.data_json)}
                    yield f"id: {cursor}\nevent: {event.type}\ndata: {canonical_json(data)}\n\n"
                yield ": keep-alive\n\n"
                await asyncio.sleep(1)
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    @app.post("/api/v1/projects/{project_id}/exports")
    def export(project_id: str, body: ExportBody, request: Request, actor_id: str = Depends(actor)):
        with factory() as db:
            own_project(db, actor_id, project_id)
            snapshot = load_snapshot(db, project_id, body.revision_id)
        results = compute_results(snapshot)
        export_id, pdf_id, model_id, manifest_id = (new_id() for _ in range(4))
        coverage_basis = {"discipline_design_complete": False, "methods": [method.model_dump(mode="json") for method in methods_for_snapshot(snapshot)]}
        basis = {"export_id": export_id, **revision_info(snapshot), "result_set_hash": digest(results), "coverage_hash": digest(coverage_basis), "report_template_version": "0.5.0"}
        pdf, sheet_index = build_review_package(snapshot, results)
        model_bytes = snapshot.model_dump_json(indent=2).encode()
        manifest = {**basis, "export_basis_hash": digest(basis), "artifact_id": pdf_id, "model_artifact_id": model_id, "manifest_artifact_id": manifest_id,
                    "file_sha256": hashlib.sha256(pdf).hexdigest(), "model_sha256": hashlib.sha256(model_bytes).hexdigest(),
                    "document_presence": "generated", "review_status": "unreviewed", "authority_process": "not_submitted",
                    "discipline_design_complete": False, "results": results, "coverage": coverage_basis,
                    "sheets": sheet_index}
        manifest_bytes = json.dumps(manifest, indent=2, allow_nan=False).encode()
        manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
        written = []
        try:
            with factory.begin() as db:
                own_project(db, actor_id, project_id)
                for identifier, extension, content in [(pdf_id, "pdf", pdf), (model_id, "json", model_bytes), (manifest_id, "json", manifest_bytes)]:
                    path = root / f"{identifier}.{extension}"
                    with path.open("xb") as handle:
                        handle.write(content)
                    written.append(path)
                    db.add(ArtifactRow(id=identifier, project_id=project_id, revision_id=snapshot.revision_id, export_id=export_id, extension=extension, sha256=hashlib.sha256(content).hexdigest()))
                db.add(JobRow(id=export_id, project_id=project_id, revision_id=snapshot.revision_id, kind="export", status="succeeded", result_json=canonical_json({"artifact_id": pdf_id, "manifest_artifact_id": manifest_id})))
                append_event(db, snapshot, "export.completed", {"export_id": export_id, "artifact_id": pdf_id})
        except Exception:
            for path in written:
                path.unlink(missing_ok=True)
            raise
        return envelope({**manifest, "manifest_sha256_stored_externally": manifest_hash}, request)

    def legacy_artifact(db, identifier):
        # Existing deployment exports predate artifact records. Recover ownership
        # from their immutable manifest; an unbound file is never made public.
        for path in root.glob("*.json"):
            try:
                manifest = json.loads(path.read_text())
            except (ValueError, OSError):
                continue
            if not isinstance(manifest, dict) or not all(key in manifest for key in ("artifact_id", "project_id", "revision_id", "export_id")):
                continue
            candidates = {manifest["artifact_id"]: "pdf", manifest.get("model_artifact_id"): "json", path.stem: "json"}
            if identifier not in candidates:
                continue
            load_snapshot(db, manifest["project_id"], manifest["revision_id"])
            content = root / f"{identifier}.{candidates[identifier]}"
            if content.is_file():
                row = ArtifactRow(id=identifier, project_id=manifest["project_id"], revision_id=manifest["revision_id"], export_id=manifest["export_id"], extension=candidates[identifier], sha256=hashlib.sha256(content.read_bytes()).hexdigest())
                db.add(row)
                return row
        return None

    @app.get("/artifacts/{artifact_id}")
    @app.get("/api/v1/artifacts/{artifact_id}")
    def artifact(artifact_id: str, actor_id: str = Depends(actor)):
        try:
            uuid.UUID(artifact_id)
        except ValueError:
            raise HTTPException(404, "Artifact not found.")
        with factory.begin() as db:
            row = db.get(ArtifactRow, artifact_id) or legacy_artifact(db, artifact_id)
            if row is None:
                raise HTTPException(404, "Artifact not found.")
            own_project(db, actor_id, row.project_id)
            path = root / f"{row.id}.{row.extension}"
            if not path.is_file():
                raise HTTPException(404, "The artifact file is unavailable.")
            if hashlib.sha256(path.read_bytes()).hexdigest() != row.sha256:
                raise HTTPException(409, "Artifact integrity check failed. Create a new export.")
            return FileResponse(path, media_type="application/pdf" if row.extension == "pdf" else "application/json", filename=f"nodesnap-{row.revision_id[:8]}-{row.id[:8]}.{row.extension}", content_disposition_type="inline" if row.extension == "pdf" else "attachment", headers={"ETag": f'"{row.sha256}"'})

    @app.get("/api/v1/projects/{project_id}/conversations")
    def conversations(project_id: str, request: Request, actor_id: str = Depends(actor)):
        with factory() as db:
            own_project(db, actor_id, project_id)
            rows = db.query(ConversationRow).filter_by(project_id=project_id).order_by(ConversationRow.created_at).all()
            result = [{"id": row.id, "base_revision_id": row.base_revision_id, "created_at": row.created_at, "text": row.user_text, **json.loads(row.response_json)} for row in rows]
        return envelope(result, request)

    @app.post("/api/v1/projects/{project_id}/conversations")
    async def conversation(project_id: str, body: ConversationBody, request: Request, actor_id: str = Depends(actor), if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None)):
        check_header(if_match, body.base_revision_id, idempotency_key)
        if not body.text.strip():
            raise HTTPException(422, "Describe a change or ask a question.")
        payload = body.model_dump()
        with factory.begin() as db:
            project = own_project(db, actor_id, project_id)
            rid, previous = receipt(db, actor_id, request.url.path, idempotency_key, payload)
            if previous is not None:
                return envelope(previous, request)
            ensure_head(project, body.base_revision_id)
            snapshot = load_snapshot(db, project_id, body.base_revision_id)
            history = db.query(ConversationRow).filter_by(project_id=project_id).order_by(ConversationRow.created_at.desc()).limit(4).all()
            lease = db.get(ConversationLeaseRow, project_id)
            if lease:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(lease.created_at)).total_seconds()
                if age < 600:
                    raise HTTPException(409, "Another chat request is still running for this design. Wait for it to finish.")
                db.delete(lease)
                db.flush()
            db.add(ConversationLeaseRow(project_id=project_id))
            if rid:
                db.add(MutationRow(id=rid, request_hash=digest(payload), response_json=""))
        ordered_levels = sorted(snapshot.levels, key=lambda level: level.elevation_m)
        levels = {level.id: level.name for level in ordered_levels}
        occupied_levels = [level for level in ordered_levels if level.name not in {"basement", "roof"} and level.elevation_m >= 0]
        clear_areas = {row["space_id"]: row["actual_area_m2"] for row in area_schedule(snapshot)}
        context = json.dumps({"revision_number": snapshot.revision_number, "title": snapshot.title,
            "living_floor_count": len(occupied_levels),
            "bedroom_count": sum(space.use == "bedroom" for space in snapshot.spaces),
            "building_program": snapshot.building_program.model_dump(mode="json") if snapshot.building_program else None,
            "default_new_level_source": occupied_levels[-1].name if occupied_levels else None,
            "living_floor_order": [level.name for level in occupied_levels],
            "removable_levels": [level.name for level in occupied_levels if level.name != "ground"],
            "has_prior_revision": snapshot.parent_revision_id is not None,
            "pool": {**snapshot.pool.model_dump(mode="json"), "location": snapshot.pool.location} if snapshot.pool else None,
            "terrace_area_m2": snapshot.roof_terrace_area_m2,
            "pool_quantities": pool_quantities(snapshot.pool.water_length_m, snapshot.pool.water_width_m, snapshot.pool.water_depth_m) if snapshot.pool else None,
            "levels": [{"name": level.name, "label": level.label, "elevation_m": level.elevation_m,
                        "floor_to_floor_height_m": round(ordered_levels[index + 1].elevation_m - level.elevation_m, 6) if index + 1 < len(ordered_levels) else None}
                       for index, level in enumerate(ordered_levels)],
            "site_layout": snapshot.site_layout.model_dump(mode="json") if snapshot.site_layout else None,
            "rooms": [{"name": space.name, "use": space.use, "level": levels[space.level_id],
                       "clear_area_m2": clear_areas.get(space.id),
                       "target_area_ft2": round(space.target_area_m2 / FT2_TO_M2, 2) if space.target_area_m2 else None}
                      for space in snapshot.spaces if space.classification == "principal"],
            "recent_requests": [row.user_text[:500] for row in reversed(history)]}, separators=(",", ":"))
        result = {"base_revision_id": body.base_revision_id, "execution_status": "blocked", "committed_revision_id": None}
        try:
            status = meta_status()
            if not status["configured"]:
                result.update(issue=status["issue"], explanation=status["issue"]["message"])
            else:
                feedback = ""
                output = {}
                for attempt in range(3):
                    output = {}
                    budget.reserve(factory, 500_000)
                    try:
                        output = await propose(body.text + feedback, context)
                    finally:
                        budget.settle(factory, 500_000, "conversation", status["reasoning_model"], output.get("usage"),
                                      billing_rejected=(output.get("issue") or {}).get("code") == "PROVIDER_BILLING_REQUIRED")
                    if output.get("proposal") or output.get("issue", {}).get("code") != "MALFORMED_OUTPUT":
                        break
                    feedback = "\nController feedback: return exactly the schema-constrained proposal; the previous response could not be validated."
                result.update({key: value for key, value in output.items() if key != "request_id"})
                proposal = output.get("proposal")
                if proposal and proposal["intent"] == "design_building":
                    brief_history = []
                    for entry in reversed(history):
                        brief_history.append({"role": "user", "text": entry.user_text[:8000]})
                        explanation = json.loads(entry.response_json).get("explanation")
                        if explanation:
                            brief_history.append({"role": "assistant", "text": explanation[:8000]})
                    output = await planned_building(factory, body.text, brief_history, context)
                    result.update({key: value for key, value in output.items() if key != "request_id"})
                    proposal = output.get("proposal")
                    if not proposal:
                        result["explanation"] = output.get("issue", {}).get("message", "The new building brief could not be interpreted.")
                    elif proposal["intent"] == "clarify":
                        result["execution_status"] = "blocked"
                        result["issue"] = {"code": "MISSING_INPUT", "message": proposal["explanation"]}
                if proposal:
                    result["explanation"] = proposal["explanation"]
                    commands = proposal_commands(proposal, snapshot)
                    new_snapshot = None
                    if commands:
                        for command in commands:
                            command["command_id"] = new_id()
                        new_snapshot = apply_commands(snapshot, commands)
                        validate_proposed(new_snapshot)
                    elif proposal["intent"] == "regenerate_floor":
                        level_name = proposal.get("level")
                        level = living_level(snapshot, level_name)
                        rooms = [{"name": space.name, "use": space.use, "target_area_m2": space.target_area_m2} for space in snapshot.spaces if space.level_id == level.id and space.classification == "principal"]
                        if proposal.get("room_name"):
                            room = next((room for room in rooms if room["name"].casefold() == proposal["room_name"].casefold()), None)
                            if room is None or proposal.get("room_target_area_ft2") is None:
                                raise CommandError("Name an existing room and its target area to resize it.")
                            room["target_area_m2"] = proposal["room_target_area_ft2"] * FT2_TO_M2
                        new_snapshot, solver_status = await run_in_threadpool(regenerated, snapshot, level_name, rooms)
                        result["solver_status"] = solver_status
                        if new_snapshot is None:
                            raise CommandError("No valid floor plan fits this area request within the supported layout family.")
                    elif proposal["intent"] == "unsupported":
                        result["execution_status"] = "unsupported"
                    if new_snapshot:
                        with factory.begin() as db:
                            own_project(db, actor_id, project_id)
                            committed = commit_snapshot(db, actor_id, snapshot, new_snapshot, commands=commands)
                            result.update(committed_revision_id=committed["revision_id"], committed_revision_number=committed["revision_number"], invalidated_result_groups=committed["invalidated_result_groups"])
                            result["explanation"] = committed_message(proposal, new_snapshot, snapshot)
                            result["spend_total_est_usd"] = budget.summary(db)["est_total_usd"]
                            save_receipt(db, rid, payload, result)
            with factory() as db:
                result["spend_total_est_usd"] = budget.summary(db)["est_total_usd"]
        except (CommandError, ValueError) as exc:
            result.update(execution_status="blocked", issue={"code": "DOMAIN_VALIDATION", "message": str(exc)}, explanation=str(exc))
        except HTTPException as exc:
            message = exc.detail if isinstance(exc.detail, str) else exc.detail["message"]
            code = "STALE_REVISION" if exc.status_code == 412 else (exc.detail.get("code", "REQUEST_FAILED") if isinstance(exc.detail, dict) else "REQUEST_FAILED")
            result.update(execution_status="blocked", issue={"code": code, "message": message}, explanation=message)
        with factory.begin() as db:
            own_project(db, actor_id, project_id)
            lease = db.get(ConversationLeaseRow, project_id)
            if lease:
                db.delete(lease)
            db.add(ConversationRow(id=new_id(), project_id=project_id, base_revision_id=body.base_revision_id, user_text=body.text, response_json=canonical_json(result)))
            save_receipt(db, rid, payload, result)
            append_event(db, snapshot, "conversation.completed", {"execution_status": result["execution_status"], "committed_revision_id": result.get("committed_revision_id")})
        return envelope(result, request)

    @app.post("/api/v1/projects/{project_id}/transcriptions")
    async def transcription(project_id: str, request: Request, audio: UploadFile = File(...), actor_id: str = Depends(actor)):
        with factory() as db:
            own_project(db, actor_id, project_id)
        return await transcribed_audio(audio, request)

    @app.post("/api/v1/transcriptions")
    async def brief_transcription(request: Request, audio: UploadFile = File(...), actor_id: str = Depends(actor)):
        return await transcribed_audio(audio, request)

    async def transcribed_audio(audio, request):
        data = await audio.read(4_000_001)
        if len(data) > 4_000_000:
            raise HTTPException(413, "Use a recording of 60 seconds or less.")
        try:
            with wave.open(io.BytesIO(data)) as recording:
                duration = recording.getnframes() / recording.getframerate()
                valid = recording.getnchannels() == 1 and recording.getsampwidth() == 2 and recording.getframerate() in (16000, 24000)
                if not valid or not 0 < duration <= min(60, float(os.environ.get("MAX_AUDIO_SECONDS", "60"))):
                    raise ValueError("format")
        except (wave.Error, EOFError, ValueError, ZeroDivisionError):
            raise HTTPException(422, "Record mono 16-bit WAV at 16 or 24 kHz, up to 60 seconds.")
        status = meta_status()
        if not status["configured"]:
            return envelope({"execution_status": "blocked", "issue": status["issue"], "text": None}, request)
        reservation = 3_000
        budget.reserve(factory, reservation)
        output = {}
        try:
            output = await transcribe(data)
        finally:
            budget.settle(factory, reservation, "transcription", status["transcription_model"], {} if output.get("execution_status") == "completed" else None, round(duration * 1000) if output.get("execution_status") == "completed" else 0,
                          billing_rejected=(output.get("issue") or {}).get("code") == "PROVIDER_BILLING_REQUIRED")
        return envelope(output, request)

    return app


def committed_message(proposal: dict, snapshot: ProjectSnapshot, previous: ProjectSnapshot | None = None) -> str:
    intent = proposal["intent"]
    if intent == "design_building":
        return design_summary(snapshot, redesign=True)
    if intent == "set_site_features":
        actual = site_feature_descriptions(snapshot)
        before = site_feature_descriptions(previous) if previous else {}
        changes = []
        fields = {"set_yard": "yard", "set_garage": "garage", "set_outdoor_pool": "pool"}
        for edit in proposal["site_edits"]:
            field = fields[edit["type"]]
            if edit.get(field) is None:
                changes.append(f"Removed the {'outdoor pool' if field == 'pool' else field}.")
            elif field in actual:
                verb = "Updated" if field in before else "Added"
                changes.append(f"{verb} the {actual[field]}." + (" Its vehicle door and driveway are included." if field == "garage" else ""))
        if previous and previous.pool and previous.pool.location == "indoor" and snapshot.pool and snapshot.pool.location == "outdoor":
            changes.append("The former indoor pool hall remains in the house layout and can be redesigned separately.")
        if "yard" in actual and "yard" not in before and not any(edit["type"] == "set_yard" for edit in proposal["site_edits"]):
            changes.append("A fitting rear yard was added as a siting assumption.")
        return (" ".join(changes) + f" Model and plans now share revision {snapshot.revision_number}. "
                "Siting is a concept assumption; parcel boundaries, setbacks and safety requirements still need review.")
    if intent == "remove_level" and previous:
        current_ids = {level.id for level in snapshot.levels}
        removed = next(level for level in previous.levels if level.id not in current_ids)
        previous_roof = next(level for level in previous.levels if level.name == "roof")
        roof = next(level for level in snapshot.levels if level.name == "roof")
        drop = previous_roof.elevation_m - roof.elevation_m
        return (f"Removed {removed.label} and its rooms. Lowered the roof and terrace by {drop:g} m and rebuilt the connected stairs. "
                f"Plans and model now share revision {snapshot.revision_number}; the previous design remains in history. "
                "Engineering checks still need review.")
    if intent == "add_level" and previous:
        previous_ids = {level.id for level in previous.levels}
        added = next(level for level in snapshot.levels if level.id not in previous_ids)
        source = next((level for level in previous.levels if level.name == proposal.get("level")), None)
        if source is None:
            source = max((level for level in previous.levels if level.name not in {"basement", "roof"} and level.elevation_m >= 0), key=lambda level: level.elevation_m)
        roof = next(level for level in snapshot.levels if level.name == "roof")
        height = roof.elevation_m - added.elevation_m
        height_basis = "requested" if proposal.get("level_height_m") is not None else "inherited"
        return (f"Added {added.label}, copying the {source.label} room layout with the {height_basis} {height:g} m storey height. "
                f"Raised the roof and terrace by {height:g} m and connected the stairs. Plans and model now share revision {snapshot.revision_number}. "
                "This is a design concept; structural capacity and code compliance still need review.")
    if intent == "set_pool_dimensions" and snapshot.pool:
        pool = snapshot.pool
        quantities = pool_quantities(pool.water_length_m, pool.water_width_m, pool.water_depth_m)
        return f"Updated the pool to {pool.water_length_m:g} × {pool.water_width_m:g} m, with {pool.water_depth_m:g} m water depth. Water volume is {quantities['volume_m3']:.2f} m³. The plans and model now share revision {snapshot.revision_number}."
    if intent == "set_material_palette":
        name = {"limestone_oak": "limestone and oak", "warm_concrete": "warm concrete", "white_stucco": "white stucco"}[proposal["material_palette"]]
        return f"Applied the {name} finish concept in revision {snapshot.revision_number}."
    if intent == "set_terrace_area":
        return f"Updated the occupied roof terrace to {snapshot.roof_terrace_area_m2:.2f} m² in revision {snapshot.revision_number}. Guard, drainage and waterproofing design remain review items."
    if intent == "set_level_height":
        return f"Set the {proposal['level']} floor-to-floor height to {proposal['level_height_m']:g} m and coordinated the levels above it. Saved revision {snapshot.revision_number}."
    return f"Generated a valid {proposal.get('level', 'ground')}-floor layout in revision {snapshot.revision_number}. Room areas and openings now reflect that layout; affected calculations need to be rerun."


def proposal_commands(proposal: dict, snapshot: ProjectSnapshot) -> list[dict]:
    if proposal["intent"] == "set_site_features":
        edits = proposal.get("site_edits") or []
        if not edits or len(edits) > 3 or len({edit["type"] for edit in edits}) != len(edits):
            raise CommandError("Specify each yard, garage or outdoor-pool change once.")
        fields = {"set_yard": "yard", "set_garage": "garage", "set_outdoor_pool": "pool"}
        commands = []
        for edit in edits:
            field = fields.get(edit.get("type"))
            if field is None or field not in edit:
                raise CommandError("This site feature change is not supported.")
            commands.append({"type": edit["type"], field: edit[field]})
        # Place/remove the pool before removing a yard; additions place the yard
        # before the pool. Each case is applied atomically to one revision.
        commands.sort(key=lambda cmd: (2 if cmd["type"] == "set_yard" and cmd["yard"] is None else
                                      0 if cmd["type"] == "set_yard" else 1))
        return commands
    command = proposal_command(proposal, snapshot)
    return [command] if command else []


def proposal_command(proposal: dict, snapshot: ProjectSnapshot):
    intent = proposal["intent"]
    if intent == "design_building":
        return {"type": intent, "program": proposal["program"]}
    if intent == "remove_level":
        command = {"type": intent}
        if proposal.get("level") is not None:
            level = next((level for level in snapshot.levels if level.name == proposal["level"]), None)
            if level is None:
                raise CommandError(f"Level '{proposal['level']}' does not exist in this revision. Choose an existing living floor above ground.")
            command["level_id"] = level.id
        return command
    if intent == "add_level":
        command = {"type": intent}
        if proposal.get("level") is not None:
            command["source_level_id"] = living_level(snapshot, proposal["level"]).id
        if proposal.get("level_height_m") is not None:
            command["height_m"] = proposal["level_height_m"]
        return command
    if intent == "set_pool_dimensions":
        return {"type": intent, "water_length_m": proposal.get("pool_length_m"), "water_width_m": proposal.get("pool_width_m"), "water_depth_m": proposal.get("pool_depth_m")}
    if intent == "set_terrace_area":
        return {"type": intent, "area_m2": proposal.get("terrace_area_m2")}
    if intent == "set_material_palette":
        return {"type": intent, "palette": proposal.get("material_palette")}
    if intent == "set_level_height":
        level = next((level for level in snapshot.levels if level.name == proposal.get("level")), None)
        if level is None:
            raise CommandError("Choose an existing level to change its floor-to-floor height.")
        return {"type": intent, "level_id": level.id, "height_m": proposal.get("level_height_m")}
    return None


app = create_app()
