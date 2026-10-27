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
            if cmd.water_length_m is None and cmd.water_width_m is None and cmd.water_depth_m is None:
                raise CommandError("set_pool_dimensions stated no dimension")
            if snap.pool is None:
                raise CommandError("project has no pool system")
            for field in ("water_length_m", "water_width_m", "water_depth_m"):
                v = getattr(cmd, field)
                if v is not None:
                    if not (0 < v <= 50):
                        raise CommandError(f"{field} out of supported range: {v}")
                    setattr(snap.pool, field, v)
            # Keep the water inside the pool hall: re-centre on resize instead
            # of silently overflowing the hall wall.
            hall = next((s for s in snap.spaces if s.use == "pool_hall"), None)
            if hall is not None:
                xs = [pt[0] for pt in hall.polygon]; ys = [pt[1] for pt in hall.polygon]
                hw, hd = max(xs) - min(xs), max(ys) - min(ys)
                if snap.pool.water_length_m > hw or snap.pool.water_width_m > hd:
                    raise CommandError(
                        f"pool {snap.pool.water_length_m} x {snap.pool.water_width_m} m does not fit "
                        f"the pool hall ({hw} x {hd} m)")
                snap.pool.origin_x_m = round(min(xs) + (hw - snap.pool.water_length_m) / 2, 4)
                snap.pool.origin_y_m = round(min(ys) + (hd - snap.pool.water_width_m) / 2, 4)
        elif ctype == "move_space":
            sid = raw.get("element_id")
            dx, dy = float(raw.get("dx_m", 0)), float(raw.get("dy_m", 0))
            sp = next((s for s in snap.spaces if s.id == sid), None)
            if sp is None:
                raise CommandError(f"space not found: {sid}")
            # snap translation to the 0.1 m planning grid
            dx, dy = round(dx * 10) / 10, round(dy * 10) / 10
            sp.polygon = [[round(x + dx, 4), round(y + dy, 4)] for x, y in sp.polygon]
        else:
            raise CommandError(f"unsupported command type: {ctype}")
    snap.parent_revision_id = snapshot.revision_id
    snap.revision_id = new_id()
    snap.revision_number = snapshot.revision_number + 1
    from datetime import datetime, timezone
    snap.created_at = datetime.now(timezone.utc)
    return snap.with_hash()
