"""Persistence for the studio. Existing deployment tables remain compatible.

New tables are additive; no snapshot or existing revision is rewritten at startup.
Revision writes use a compare-and-swap UPDATE in the same transaction as their
audit/idempotency records, on both PostgreSQL and the local SQLite database.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import Column, Integer, String, Text, create_engine, update
from sqlalchemy.orm import declarative_base, sessionmaker

from domain.models import ProjectSnapshot, new_id

Base = declarative_base()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(data) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(data) -> str:
    return hashlib.sha256(canonical_json(data).encode()).hexdigest()


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


class MetaUsageRow(Base):
    __tablename__ = "meta_usage"
    id = Column(String, primary_key=True)
    created_at = Column(String)
    kind = Column(String)
    model = Column(String)
    input_tokens = Column(Integer, default=0)
    cached_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    audio_ms = Column(Integer, default=0)
    est_cost_usd = Column(String, default="0")


class MutationRow(Base):
    __tablename__ = "mutation_receipts"
    id = Column(String, primary_key=True)
    request_hash = Column(String, nullable=False)
    response_json = Column(Text, nullable=False, default="")
    created_at = Column(String, default=now)


class CommandReceiptRow(Base):
    __tablename__ = "command_receipts"
    id = Column(String, primary_key=True)  # project:command UUID
    revision_id = Column(String, nullable=False)


class EventRow(Base):
    __tablename__ = "project_events"
    sequence = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, index=True, nullable=False)
    revision_id = Column(String, nullable=False)
    type = Column(String, nullable=False)
    created_at = Column(String, default=now)
    data_json = Column(Text, nullable=False)


class ArtifactRow(Base):
    __tablename__ = "artifact_records"
    id = Column(String, primary_key=True)
    project_id = Column(String, index=True, nullable=False)
    revision_id = Column(String, nullable=False)
    export_id = Column(String, nullable=False)
    extension = Column(String, nullable=False)
    sha256 = Column(String, nullable=False)
    created_at = Column(String, default=now)


class ConversationRow(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True)
    project_id = Column(String, index=True, nullable=False)
    base_revision_id = Column(String, nullable=False)
    created_at = Column(String, default=now)
    user_text = Column(Text, nullable=False)
    response_json = Column(Text, nullable=False)


class ConversationLeaseRow(Base):
    __tablename__ = "conversation_leases"
    project_id = Column(String, primary_key=True)
    created_at = Column(String, nullable=False, default=now)


class BudgetRow(Base):
    __tablename__ = "meta_budget"
    id = Column(String, primary_key=True)
    spent_microusd = Column(Integer, nullable=False, default=0)
    reserved_microusd = Column(Integer, nullable=False, default=0)


def connect(database_url: str):
    options = {"check_same_thread": False, "timeout": 30} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=options, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as db:
        if db.get(BudgetRow, "application") is None:
            historic = sum(float(r.est_cost_usd) for r in db.query(MetaUsageRow).all())
            db.add(BudgetRow(id="application", spent_microusd=round(historic * 1_000_000), reserved_microusd=0))
    return engine, factory


def own_project(db, actor_id: str, project_id: str) -> ProjectRow:
    row = db.get(ProjectRow, project_id)
    if row is None:
        raise HTTPException(404, "Project not found.")
    if row.actor_id != actor_id:
        raise HTTPException(403, "This project belongs to another session.")
    return row


def load_snapshot(db, project_id: str, revision_id: str) -> ProjectSnapshot:
    row = db.get(RevisionRow, revision_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(404, "Revision not found in this project.")
    return ProjectSnapshot.model_validate_json(row.snapshot_json)


def ensure_head(project: ProjectRow, base_revision_id: str):
    if project.current_revision_id != base_revision_id:
        raise HTTPException(412, "The design changed. Reload the latest revision before applying this edit.")


def receipt_key(actor: str, scope: str, key: str) -> str:
    return digest([actor, scope, key])


def receipt(db, actor: str, scope: str, key: str | None, body: dict) -> tuple[str | None, dict | None]:
    if not key:
        return None, None
    if len(key) > 160:
        raise HTTPException(422, "Idempotency-Key must be at most 160 characters.")
    rid = receipt_key(actor, scope, key)
    previous = db.get(MutationRow, rid)
    if previous:
        if previous.request_hash != digest(body):
            raise HTTPException(409, "This idempotency key was already used with different content.")
        if not previous.response_json:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(previous.created_at)).total_seconds()
            if age < 600:
                raise HTTPException(409, "This request is already running. Wait for its result before retrying.")
            # A committed mutation stores its receipt in the same transaction.
            # An expired unfinished receipt therefore cannot hide an accepted edit.
            db.delete(previous)
            db.flush()
            return rid, None
        return rid, json.loads(previous.response_json)
    return rid, None


def save_receipt(db, rid: str | None, body: dict, result: dict):
    if rid:
        row = db.get(MutationRow, rid)
        if row is None:
            row = MutationRow(id=rid, request_hash=digest(body))
            db.add(row)
        row.response_json = canonical_json(result)


def append_event(db, snapshot: ProjectSnapshot, kind: str, data: dict):
    db.add(EventRow(project_id=snapshot.project_id, revision_id=snapshot.revision_id,
                    type=kind, data_json=canonical_json(data)))


INVALIDATED_GROUPS = ["architecture", "pool", "structure", "foundations", "hvac", "plumbing", "electrical", "energy", "drainage", "documents"]


def commit_snapshot(db, actor: str, base: ProjectSnapshot, proposed: ProjectSnapshot, *, commands: list[dict] | None = None) -> dict:
    """Only transaction boundary for all direct, chat, generate and restore edits."""
    if proposed.project_id != base.project_id or proposed.parent_revision_id != base.revision_id:
        raise HTTPException(422, "Invalid revision lineage.")
    for command in commands or []:
        command_id = command.get("command_id")
        if command_id:
            identity = f"{base.project_id}:{command_id}"
            if db.get(CommandReceiptRow, identity):
                raise HTTPException(409, "This command was already applied. Reload the current revision.")
            db.add(CommandReceiptRow(id=identity, revision_id=proposed.revision_id))
    # UPDATE is the lock and precondition; the loser cannot overwrite a winner.
    changed = db.execute(update(ProjectRow).where(
        ProjectRow.id == base.project_id, ProjectRow.actor_id == actor,
        ProjectRow.current_revision_id == base.revision_id,
    ).values(current_revision_id=proposed.revision_id), execution_options={"synchronize_session": False})
    if changed.rowcount != 1:
        raise HTTPException(412, "The design changed while this request was running. Reload and retry.")
    db.add(RevisionRow(revision_id=proposed.revision_id, project_id=proposed.project_id,
                       revision_number=base.revision_number + 1, snapshot_json=proposed.model_dump_json()))
    result = {"revision_id": proposed.revision_id, "revision_number": proposed.revision_number,
              "content_hash": proposed.content_hash, "invalidated_result_groups": INVALIDATED_GROUPS}
    append_event(db, proposed, "revision.committed", result)
    return result
