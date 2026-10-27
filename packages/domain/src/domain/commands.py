"""Typed edit commands — spec S3. Chat and drag use the same path."""
from __future__ import annotations

import copy
from typing import Optional

from pydantic import BaseModel, Field

from .models import ProjectSnapshot, new_id


class Command(BaseModel):
    command_id: str = Field(default_factory=new_id)
    type: str  # set_pool_dimensions | ...


class SetPoolDimensions(Command):
    type: str = "set_pool_dimensions"
    water_length_m: Optional[float] = None
    water_width_m: Optional[float] = None
    water_depth_m: Optional[float] = None


class CommandBatch(BaseModel):
    base_revision_id: str
    commands: list[dict]  # parsed per type below


class CommandError(ValueError):
    pass


def apply_commands(snapshot: ProjectSnapshot, raw_commands: list[dict]) -> ProjectSnapshot:
    """Validate the complete proposed result; return a new revision or raise."""
    snap = copy.deepcopy(snapshot)
    for raw in raw_commands:
        ctype = raw.get("type")
        if ctype == "set_pool_dimensions":
            cmd = SetPoolDimensions(**raw)
            if snap.pool is None:
                raise CommandError("project has no pool system")
            for field in ("water_length_m", "water_width_m", "water_depth_m"):
                v = getattr(cmd, field)
                if v is not None:
                    if not (0 < v <= 50):
                        raise CommandError(f"{field} out of supported range: {v}")
                    setattr(snap.pool, field, v)
        else:
            raise CommandError(f"unsupported command type: {ctype}")
    snap.parent_revision_id = snapshot.revision_id
    snap.revision_id = new_id()
    snap.revision_number = snapshot.revision_number + 1
    from datetime import datetime, timezone
    snap.created_at = datetime.now(timezone.utc)
    return snap.with_hash()
