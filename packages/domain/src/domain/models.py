"""Canonical building model — spec A6/S2. SI units internally, Z-up, stable UUIDs."""
from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

from .enums import InputBasis

SCHEMA_VERSION = "0.2.0"
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
    name: str  # stable lookup name: basement, ground, upper, level_3, …, roof
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
        if any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in self.polygon):
            raise ValueError("space coordinates must be finite XY pairs in metres")
        if self.polygon[0] != self.polygon[-1]:
            raise ValueError("space polygon must be explicitly closed")
        return self


class ArchitecturalEntity(BaseModel):
    """Concept geometry, not structural sizing or a code-compliance result."""
    model_config = ConfigDict(allow_inf_nan=False)
    id: str
    input_basis: InputBasis = InputBasis.DEMONSTRATION_ASSUMPTION


class WallAssembly(ArchitecturalEntity):
    name: str
    thickness_m: float = Field(gt=0)
    material: Literal["stone", "plaster", "concrete", "glass"]
    structural_role: str = "not_determined"


class Wall(ArchitecturalEntity):
    level_id: str
    start: list[float]
    end: list[float]
    thickness_m: float = Field(gt=0)
    height_m: float = Field(gt=0)
    exterior: bool
    role: Literal["enclosure", "partition", "guard"]
    material: Literal["stone", "plaster", "concrete", "glass"]
    assembly_id: str
    space_ids: list[str]


class Opening(ArchitecturalEntity):
    wall_id: str
    kind: Literal["door", "window", "passage"]
    offset_m: float = Field(ge=0)
    width_m: float = Field(gt=0)
    height_m: float = Field(gt=0)
    sill_height_m: float = Field(ge=0)
    space_ids: list[str]
    hinge: Literal["start", "end"] = "start"


class Slab(ArchitecturalEntity):
    level_id: str
    elevation_m: float | None = None  # top elevation; null means level datum
    polygon: list[list[float]]
    holes: list[list[list[float]]] = Field(default_factory=list)
    thickness_m: float = Field(gt=0)
    kind: Literal["floor", "roof"]
    material: str = "concrete"


class Stair(ArchitecturalEntity):
    lower_level_id: str
    upper_level_id: str
    lower_space_id: str
    upper_space_id: str
    polygon: list[list[float]]
    width_m: float = Field(gt=0)
    riser_count: int = Field(ge=2)
    riser_height_m: float = Field(gt=0)
    tread_depth_m: float = Field(gt=0)
    flight_run_m: float = Field(gt=0)
    landing_depth_m: float = Field(gt=0)
    orientation: Literal["north", "south"] = "south"
    form: Literal["dogleg"] = "dogleg"


class SpaceMetrics(BaseModel):
    space_id: str
    clear_polygon: list[list[float]]
    zone_area_m2: float
    net_area_m2: float
    clear_width_m: float
    clear_depth_m: float


class Architecture(BaseModel):
    revision_id: str
    generator_version: str = "orthogonal-architecture-1.0"
    coordinate_basis: str = "local_xy_z_up"
    dimension_basis: str = "Exterior faces define the envelope; internal zone edges are wall centerlines. Clear polygons subtract actual wall thickness."
    assemblies: list[WallAssembly] = Field(default_factory=list)
    walls: list[Wall] = Field(default_factory=list)
    openings: list[Opening] = Field(default_factory=list)
    slabs: list[Slab] = Field(default_factory=list)
    stairs: list[Stair] = Field(default_factory=list)
    space_metrics: list[SpaceMetrics] = Field(default_factory=list)
    issues: list[dict] = Field(default_factory=list)
    input_basis: InputBasis = InputBasis.DERIVED
    review_status: str = "unreviewed"


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


class ProgramModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class RoomProgram(ProgramModel):
    name: str = Field(min_length=1, max_length=120)
    use: str = Field(min_length=1, max_length=60)
    target_area_m2: float = Field(gt=0, le=3000)
    area_basis: Literal["user_supplied", "demonstration_assumption"] = "demonstration_assumption"
    count: int = Field(default=1, ge=1, le=12)
    classification: Literal["principal", "support"] = "principal"

    @model_validator(mode="after")
    def validate_use(self):
        if self.use in {"circulation", "stairs_service", "roof_access", "roof_terrace"}:
            raise ValueError("Circulation, stair reserves and roof access are generated from the building program, not requested as rooms.")
        if not self.name.strip() or not self.use.strip():
            raise ValueError("Room names and uses must contain text.")
        return self


class FloorProgram(ProgramModel):
    label: str = Field(min_length=1, max_length=80)
    height_m: float = Field(default=3.2, ge=2.6, le=4.5)
    rooms: list[RoomProgram] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_rooms(self):
        names = [room.name if room.count == 1 else f"{room.name} {index + 1}"
                 for room in self.rooms for index in range(room.count)]
        if len(names) > 20:
            raise ValueError("Each floor supports at most 20 requested room instances.")
        if len({name.casefold() for name in names}) != len(names):
            raise ValueError("Expanded room names must be unique within each floor.")
        return self


class PoolProgram(ProgramModel):
    water_length_m: float = Field(gt=0, le=40)
    water_width_m: float = Field(gt=0, le=25)
    water_depth_m: float = Field(default=1.4, gt=0, le=5)
    level: Literal["basement", "ground"] = "basement"


class BuildingProgram(ProgramModel):
    title: str = Field(min_length=1, max_length=160)
    building_use: str = Field(default="single_family_residence", min_length=1, max_length=80)
    footprint_basis: Literal["user_supplied", "demonstration_assumption"] = "demonstration_assumption"
    width_m: float = Field(ge=8, le=60)
    depth_m: float = Field(ge=8, le=60)
    floors: list[FloorProgram] = Field(min_length=1, max_length=12)
    basement: FloorProgram | None = None
    pool: PoolProgram | None = None
    roof_terrace_area_m2: float = Field(default=0, ge=0, le=3000)
    material_palette: Literal["limestone_oak", "warm_concrete", "white_stucco"] = "limestone_oak"
    design_notes: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_program(self):
        if self.pool and self.pool.level == "basement" and self.basement is None:
            raise ValueError("A basement pool requires a basement floor program.")
        if any(not any(room.classification == "principal" for room in floor.rooms) for floor in self.floors):
            raise ValueError("Each occupied above-ground floor needs at least one principal room.")
        if self.roof_terrace_area_m2 and self.roof_terrace_area_m2 > (self.width_m - 3.0) * self.depth_m:
            raise ValueError("The requested roof terrace leaves insufficient area for its stair enclosure and connected access.")
        return self


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
    architecture: Optional[Architecture] = None
    material_palette: Literal["limestone_oak", "warm_concrete", "white_stucco"] = "limestone_oak"
    building_program: BuildingProgram | None = None
    envelope_polygon: list[list[float]] | None = None
    content_hash: str = ""

    @model_serializer(mode="wrap")
    def serialize_compatible(self, handler):
        data = handler(self)
        for key in ("building_program", "envelope_polygon"):
            if data.get(key) is None:
                data.pop(key, None)
        return data

    def compute_hash(self) -> str:
        excluded = {"content_hash", "created_at"}
        # Optional full-building fields must not rewrite existing 0.2 hashes.
        if self.building_program is None:
            excluded.add("building_program")
        if self.envelope_polygon is None:
            excluded.add("envelope_polygon")
        # Loading a deployed 0.1 snapshot must not change its historical hash
        # just because this version knows additional optional schema fields.
        if self.schema_version == "0.1.0" and self.architecture is None:
            excluded.update({"architecture", "material_palette"})
        data = self.model_dump(mode="json", exclude=excluded)
        canon = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(canon.encode()).hexdigest()

    def with_hash(self) -> "ProjectSnapshot":
        self.content_hash = self.compute_hash()
        return self
