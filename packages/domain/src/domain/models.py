"""Canonical building model — spec A6/S2. SI units internally, Z-up, stable UUIDs."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from .enums import InputBasis

SCHEMA_VERSION = "0.1.0"
FT2_TO_M2 = 0.09290304


def new_id() -> str:
    return str(uuid.uuid4())


class Assumption(BaseModel):
    id: str = Field(default_factory=new_id)
    field: str
    value: object
    rationale: str
    input_basis: InputBasis = InputBasis.DEMONSTRATION_ASSUMPTION
    review_status: str = "unreviewed"


class Level(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str  # basement | ground | upper | roof
    label: str
    elevation_m: float


class Space(BaseModel):
    id: str = Field(default_factory=new_id)
    level_id: str
    name: str
    use: str
    classification: str  # principal | support
    # polygon: list of [x_m, y_m] in canonical local coords (Z-up, plan XY)
    polygon: list[list[float]]
    target_area_m2: Optional[float] = None

    @model_validator(mode="after")
    def _valid_polygon(self):
        if len(self.polygon) < 4:
            raise ValueError("space polygon needs >=4 points (closed ring)")
        return self


class PoolSystem(BaseModel):
    id: str = Field(default_factory=new_id)
    level_id: str
    # water geometry (editable demonstration assumptions, spec A3.2)
    water_length_m: float = 8.0
    water_width_m: float = 3.5
    water_depth_m: float = 1.4
    # water rectangle origin in canonical coords
    origin_x_m: float = 2.0
    origin_y_m: float = 2.0
    input_basis: InputBasis = InputBasis.DEMONSTRATION_ASSUMPTION


class Brief(BaseModel):
    location_status: str = "demo_site"
    use: str = "single_family_residence"
    floors_above_ground: int = 2
    principal_rooms_per_floor: int = 6
    target_floor_area_m2: float = 3000 * FT2_TO_M2
    basement_area_m2: float = 3000 * FT2_TO_M2
    roof_terrace_target_m2: float = 900 * FT2_TO_M2
    materials: str = "steel primary, timber secondary, reinforced-concrete substructure/pool"
    pool: bool = True
    terrace: bool = True


class SiteContext(BaseModel):
    mode: str = "synthetic_demo"  # synthetic_demo | sourced_parcel
    name: str = "Demo Villa NYC-01"
    real_address: Optional[str] = None
    bbl: Optional[str] = None
    context_width_m: float = 30.0
    context_depth_m: float = 45.0
    input_basis: InputBasis = InputBasis.DEMONSTRATION_ASSUMPTION


class ProjectSnapshot(BaseModel):
    schema_version: str = SCHEMA_VERSION
    project_id: str
    revision_id: str = Field(default_factory=new_id)
    parent_revision_id: Optional[str] = None
    revision_number: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    title: str = "NodeSnap Villa — NYC demonstration"
    jurisdiction: str = "NYC"
    brief: Brief = Field(default_factory=Brief)
    site: SiteContext = Field(default_factory=SiteContext)
    levels: list[Level] = []
    spaces: list[Space] = []
    pool: Optional[PoolSystem] = None
    roof_terrace_area_m2: Optional[float] = None
    assumptions: list[Assumption] = []
    content_hash: str = ""

    def compute_hash(self) -> str:
        data = self.model_dump(mode="json", exclude={"content_hash", "created_at"})
        canon = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(canon.encode()).hexdigest()

    def with_hash(self) -> "ProjectSnapshot":
        self.content_hash = self.compute_hash()
        return self
