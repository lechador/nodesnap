"""Validated typed changes shared by conversation and direct manipulation."""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from .architecture import bounds, enrich_snapshot, rect, stable_id
from .models import Assumption, BuildingProgram, Level, ProjectSnapshot, new_id

# An execution bound for the current concept generator, not a planning,
# zoning, fire-safety or structural allowance.
MAX_LIVING_LEVELS = 12


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    command_id: str = Field(default_factory=new_id)


class SetPoolDimensions(Command):
    type: Literal["set_pool_dimensions"] = "set_pool_dimensions"
    water_length_m: float | None = Field(default=None, gt=0, le=50)
    water_width_m: float | None = Field(default=None, gt=0, le=50)
    water_depth_m: float | None = Field(default=None, gt=0, le=5)


class MoveSpace(Command):
    type: Literal["move_space"] = "move_space"
    element_id: str
    dx_m: float = Field(default=0, ge=-30, le=30)
    dy_m: float = Field(default=0, ge=-30, le=30)


class MoveWall(Command):
    type: Literal["move_wall"] = "move_wall"
    element_id: str
    offset_m: float = Field(ge=-5, le=5)


class SetTerraceArea(Command):
    type: Literal["set_terrace_area"] = "set_terrace_area"
    area_m2: float = Field(ge=0, le=3000)


class SetLevelHeight(Command):
    type: Literal["set_level_height"] = "set_level_height"
    level_id: str
    height_m: float = Field(ge=2.6, le=4.5)


class SetMaterialPalette(Command):
    type: Literal["set_material_palette"] = "set_material_palette"
    palette: Literal["limestone_oak", "warm_concrete", "white_stucco"]


class AddLevel(Command):
    type: Literal["add_level"] = "add_level"
    source_level_id: str | None = None
    height_m: float | None = Field(default=None, ge=2.6, le=4.5)


class RemoveLevel(Command):
    type: Literal["remove_level"] = "remove_level"
    level_id: str | None = None


class DesignBuilding(Command):
    type: Literal["design_building"] = "design_building"
    program: BuildingProgram


TypedCommand = Annotated[SetPoolDimensions | MoveSpace | MoveWall | SetTerraceArea | SetLevelHeight | SetMaterialPalette | AddLevel | RemoveLevel | DesignBuilding,
                         Field(discriminator="type")]
COMMAND_ADAPTER = TypeAdapter(TypedCommand)


class CommandBatch(BaseModel):
    base_revision_id: str
    commands: list[dict] = Field(min_length=1, max_length=30)


class CommandError(ValueError):
    pass


def _level_stack(snapshot: ProjectSnapshot):
    """Validate the canonical level stack before a storey topology edit."""
    levels = sorted(snapshot.levels, key=lambda level: level.elevation_m)
    if (len({level.id for level in levels}) != len(levels)
            or len({level.name for level in levels}) != len(levels)
            or len({space.id for space in snapshot.spaces}) != len(snapshot.spaces)
            or any(not math.isfinite(level.elevation_m) for level in levels)
            or any(upper.elevation_m - lower.elevation_m <= .25
                   for lower, upper in zip(levels, levels[1:]))):
        raise CommandError("Changing levels requires unique level/space identities and distinct, finite level elevations.")
    roof = next((level for level in levels if level.name == "roof"), None)
    ground = next((level for level in levels if level.name == "ground"), None)
    if roof is None or ground is None or roof != levels[-1]:
        raise CommandError("Changing levels requires one ground datum and a roof above every occupied level.")
    principal_levels = {space.level_id for space in snapshot.spaces if space.classification == "principal"}
    living = [level for level in levels if level.id in principal_levels
              and ground.elevation_m <= level.elevation_m < roof.elevation_m
              and level.name != "basement"]
    if not living or ground not in living or living[-1] != levels[-2]:
        raise CommandError("Changing levels requires an occupied ground floor and an occupied floor directly below the roof.")
    return levels, living


def _add_level(snapshot: ProjectSnapshot, cmd: AddLevel) -> None:
    """Append one concept storey beneath the roof on the mutable candidate."""
    levels, living = _level_stack(snapshot)
    roof = levels[-1]
    if len(living) >= MAX_LIVING_LEVELS:
        raise CommandError(f"This concept generator supports at most {MAX_LIVING_LEVELS} occupied above-ground levels; this is an execution limit, not a building approval.")
    source = next((level for level in living if level.id == cmd.source_level_id), None) if cmd.source_level_id is not None else living[-1]
    if source is None:
        raise CommandError("Choose an existing occupied above-ground floor as the source; basement and roof cannot be copied as living floors.")
    source_spaces = [space for space in snapshot.spaces if space.level_id == source.id]
    principal_count = sum(space.classification == "principal" for space in source_spaces)
    if (snapshot.building_program is None and principal_count != 6) or not 1 <= principal_count <= 20:
        raise CommandError("Choose a source floor with a supported complete room program.")
    core_levels = [source, living[-1]]
    if snapshot.building_program is None or snapshot.roof_terrace_area_m2:
        core_levels.append(roof)
    cores = [[space for space in snapshot.spaces if space.level_id == level.id and space.use == "stairs_service"]
             for level in core_levels]
    if any(len(core) != 1 for core in cores) or any(core[0].polygon != cores[0][0].polygon for core in cores[1:]):
        raise CommandError("The source, top living floor and roof require one aligned stair core before adding a level.")
    forbidden_uses={"roof_terrace","roof_access"} | ({"pool_hall"} if snapshot.building_program is None else set())
    if any(space.use in forbidden_uses for space in source_spaces):
        raise CommandError("The source must be an enclosed living floor, without roof or unsupported pool zones.")
    inherited_height = roof.elevation_m - living[-1].elevation_m
    height = cmd.height_m if cmd.height_m is not None else inherited_height
    if not 2.6 - 1e-8 <= height <= 4.5 + 1e-8:
        raise CommandError("The inherited floor-to-floor height is outside 2.6–4.5 m; supply a supported height_m for the new level.")
    number = len(living) + 1
    while any(level.name == f"level_{number}" for level in levels):
        number += 1
    new_level = Level(id=stable_id(snapshot.project_id, f"level:add:{cmd.command_id}"),
                      name=f"level_{number}", label=f"Level {number}", elevation_m=roof.elevation_m)
    if new_level.id in {level.id for level in levels}:
        raise CommandError("This add_level command has already been applied.")
    copied = []
    converted_pool_spaces = []
    for space in source_spaces:
        copy = space.model_copy(deep=True)
        copy.id = stable_id(snapshot.project_id, f"space:{new_level.id}:copy:{space.id}")
        copy.level_id = new_level.id
        if copy.use=="pool_hall":
            copy.name="Flexible room above pool"
            copy.use="flexible"
            converted_pool_spaces.append(copy.id)
        copied.append(copy)
    roof.elevation_m += height
    snapshot.levels = sorted([*snapshot.levels, new_level], key=lambda level: level.elevation_m)
    snapshot.spaces.extend(copied)
    snapshot.brief.floors_above_ground = len(living) + 1
    if snapshot.building_program is not None:
        from .models import RoomProgram
        source_program=snapshot.building_program.floors[living.index(source)].model_copy(deep=True)
        source_program.label=new_level.label
        source_program.height_m=height
        if converted_pool_spaces:
            source_program.rooms=[r for r in source_program.rooms if r.use!="pool_hall"]
            source_program.rooms.extend(RoomProgram(name=s.name,use=s.use,target_area_m2=s.target_area_m2,
                                                    classification=s.classification)
                                        for s in copied if s.id in converted_pool_spaces)
        snapshot.building_program.floors.append(source_program)
    snapshot.assumptions.append(Assumption(
        id=stable_id(snapshot.project_id, f"assumption:add-level:{cmd.command_id}"),
        field=f"levels.{new_level.id}.concept_storey",
        value={"command_id": cmd.command_id, "base_revision_id": snapshot.revision_id,
               "source_state": "candidate_after_prior_commands",
               "source_level_id": source.id, "source_space_ids": [space.id for space in source_spaces],
               "copied_space_ids": [space.id for space in copied],
               "pool_halls_reused_as_flexible_room_ids": converted_pool_spaces,
               "floor_to_floor_height_m": height,
               "height_basis": "user_supplied" if cmd.height_m is not None else "inherited_top_storey",
               "height_source_level_id": living[-1].id if cmd.height_m is None else None},
        rationale=f"{new_level.label} copies the current zones and room targets from {source.label}; "
                  "the connected roof and terrace move upward. Layout, assemblies and inherited height are "
                  "concept assumptions. Added loads, structural capacity, zoning, fire safety, egress and "
                  "services require project-specific assessment; no approval is established."
                  + (" A pool hall in the source becomes a dry flexible room on the new floor; the existing pool is retained only at its original level." if converted_pool_spaces else "")))


def _remove_level(snapshot: ProjectSnapshot, cmd: RemoveLevel) -> None:
    """Remove a living storey and close its vertical interval on the candidate."""
    levels, living = _level_stack(snapshot)
    target = (next((level for level in living if level.id == cmd.level_id), None)
              if cmd.level_id is not None else living[-1])
    if target is None or target.name == "ground":
        raise CommandError("Choose an occupied above-ground floor above ground to remove; ground, basement and roof must remain.")
    if len(living) <= 1:
        raise CommandError("Keep at least the occupied ground floor.")
    assumption_id = stable_id(snapshot.project_id, f"assumption:remove-level:{cmd.command_id}")
    if any(assumption.id == assumption_id for assumption in snapshot.assumptions):
        raise CommandError("This remove_level command has already been applied.")
    index = levels.index(target)
    lower, upper = levels[index - 1], levels[index + 1]
    core_levels = [lower,target]
    if upper.name != "roof" or snapshot.building_program is None or snapshot.roof_terrace_area_m2:
        core_levels.append(upper)
    cores = [[space for space in snapshot.spaces if space.level_id == level.id and space.use == "stairs_service"]
             for level in core_levels]
    if any(len(core) != 1 for core in cores) or any(core[0].polygon != cores[0][0].polygon for core in cores[1:]):
        raise CommandError("The removed floor and both neighboring levels require one aligned stair core.")
    if snapshot.pool and snapshot.pool.level_id == target.id:
        raise CommandError("A floor hosting the pool cannot be removed through the living-floor command.")
    removed_spaces = [space for space in snapshot.spaces if space.level_id == target.id]
    if any(space.use in {"roof_terrace", "roof_access", "pool_hall"} for space in removed_spaces):
        raise CommandError("Only an enclosed living floor can be removed; roof and pool zones must remain.")
    height = upper.elevation_m - target.elevation_m
    shifted_ids = [level.id for level in levels[index + 1:]]
    for level in levels[index + 1:]:
        level.elevation_m -= height
    snapshot.levels = [level for level in levels if level.id != target.id]
    snapshot.spaces = [space for space in snapshot.spaces if space.level_id != target.id]
    snapshot.brief.floors_above_ground = len(living) - 1
    if snapshot.building_program is not None:
        snapshot.building_program.floors.pop(living.index(target))
    snapshot.assumptions.append(Assumption(
        id=assumption_id,
        field=f"levels.{target.id}.removed_concept_storey",
        value={"command_id": cmd.command_id, "base_revision_id": snapshot.revision_id,
               "source_state": "candidate_after_prior_commands",
               "removed_level_id": target.id, "removed_level_name": target.name,
               "removed_space_ids": [space.id for space in removed_spaces],
               "removed_floor_to_floor_height_m": height, "shifted_level_ids": shifted_ids},
        rationale=f"{target.label} and its zones are removed from this concept revision; higher floors, "
                  "the roof and terrace descend by its floor-to-floor height. Surviving room layouts and "
                  "identities are retained, and the aligned stair route is rebuilt. This is a concept edit, "
                  "not a demolition or structural design. Capacity, zoning, fire safety, egress and services "
                  "require project-specific assessment; no approval is established."))


def apply_commands(snapshot: ProjectSnapshot, raw_commands: list[dict]) -> ProjectSnapshot:
    """Produce a candidate without mutating its source; validate geometry before commit."""
    if not raw_commands or len(raw_commands) > 30:
        raise CommandError("A change must contain between 1 and 30 commands.")
    try:
        commands = [COMMAND_ADAPTER.validate_python(raw) for raw in raw_commands]
    except ValidationError as exc:
        raise CommandError(str(exc)) from exc
    if len({cmd.command_id for cmd in commands}) != len(commands):
        raise CommandError("A command ID cannot occur twice in one batch.")
    snap = snapshot.model_copy(deep=True)
    for cmd in commands:
        if isinstance(cmd, SetPoolDimensions):
            if all(getattr(cmd, field) is None for field in ("water_length_m", "water_width_m", "water_depth_m")):
                raise CommandError("set_pool_dimensions stated no dimension")
            if snap.pool is None:
                raise CommandError("project has no pool system")
            for field in ("water_length_m", "water_width_m", "water_depth_m"):
                value = getattr(cmd, field)
                if value is not None:
                    setattr(snap.pool, field, value)
            hall = next((s for s in snap.spaces if s.use == "pool_hall" and s.level_id == snap.pool.level_id), None)
            if hall is None:
                raise CommandError("The pool requires a host pool hall.")
            x0, y0, x1, y1 = bounds(hall)
            if snap.pool.water_length_m > x1 - x0 or snap.pool.water_width_m > y1 - y0:
                raise CommandError(f"Pool {snap.pool.water_length_m:g} × {snap.pool.water_width_m:g} m does not fit the pool hall ({x1-x0:g} × {y1-y0:g} m).")
            snap.pool.origin_x_m = x0 + (x1 - x0 - snap.pool.water_length_m) / 2
            snap.pool.origin_y_m = y0 + (y1 - y0 - snap.pool.water_width_m) / 2
        elif isinstance(cmd, MoveSpace):
            space = next((s for s in snap.spaces if s.id == cmd.element_id), None)
            if space is None:
                raise CommandError(f"Space not found: {cmd.element_id}")
            if space.use in {"stairs_service", "circulation", "roof_access"}:
                raise CommandError("The circulation/core is fixed in this layout family; moving it would break access.")
            dx, dy = round(cmd.dx_m * 10) / 10, round(cmd.dy_m * 10) / 10
            if dx == 0 and dy == 0:
                raise CommandError("The move is smaller than the 0.1 m planning grid.")
            space.polygon = [[x + dx, y + dy] for x, y in space.polygon]
        elif isinstance(cmd, MoveWall):
            enrich_snapshot(snap)
            wall = next((w for w in snap.architecture.walls if w.id == cmd.element_id), None)
            if wall is None or wall.exterior or len(wall.space_ids) != 2:
                raise CommandError("Only shared interior partitions can move.")
            owners = [next(s for s in snap.spaces if s.id == key) for key in wall.space_ids]
            a, b = [bounds(s) for s in owners]
            if (any(s.classification != "principal" for s in owners) or abs(wall.start[0] - wall.end[0]) > 1e-7
                    or abs(a[1] - b[1]) > 1e-7 or abs(a[3] - b[3]) > 1e-7):
                raise CommandError("This handle supports vertical partitions between principal rooms in the same strip; the core and corridor stay fixed.")
            offset = round(cmd.offset_m * 10) / 10
            if offset == 0:
                raise CommandError("The move is smaller than the 0.1 m planning grid.")
            position = wall.start[0]
            for space in owners:
                space.polygon = [[x + offset if abs(x - position) < 1e-7 else x, y] for x, y in space.polygon]
                x0, _, x1, _ = bounds(space)
                if x1 - x0 < 1.5:
                    raise CommandError("The move leaves a room narrower than the supported 1.5 m zone width.")
        elif isinstance(cmd, SetTerraceArea) and snap.building_program is not None:
            from .building import _roof_spaces, envelope_bounds
            roof = next(l for l in snap.levels if l.name == "roof")
            x0,y0,x1,y1 = envelope_bounds(snap)
            old_by_use = {space.use:space.id for space in snap.spaces if space.level_id == roof.id}
            try:
                roof_spaces = _roof_spaces(snap.project_id,"building",roof,x1-x0,y1-y0,cmd.area_m2)
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
            for space in roof_spaces:
                if space.use in old_by_use:
                    space.id = old_by_use[space.use]
            snap.spaces = [space for space in snap.spaces if space.level_id != roof.id]+roof_spaces
            snap.roof_terrace_area_m2=cmd.area_m2
            snap.brief.roof_terrace_target_m2=cmd.area_m2
            snap.brief.terrace=cmd.area_m2>0
        elif isinstance(cmd, SetTerraceArea):
            if not 40 <= cmd.area_m2 <= 130:
                raise CommandError("This legacy terrace supports 40–130 m²; design a new building for another envelope.")
            terrace = next((s for s in snap.spaces if s.use == "roof_terrace"), None)
            access = next((s for s in snap.spaces if s.use == "roof_access"), None)
            if not terrace or not access:
                raise CommandError("This revision has no connected terrace; generate the current villa template first.")
            width = cmd.area_m2 / 9.29
            terrace.polygon = rect(0, 0, width, 9.29)
            access.polygon = rect(width, 6.95, 18 - width, 1.6)
            terrace.target_area_m2 = cmd.area_m2
            snap.roof_terrace_area_m2 = cmd.area_m2
            snap.brief.roof_terrace_target_m2 = cmd.area_m2
        elif isinstance(cmd, SetLevelHeight):
            levels = sorted(snap.levels, key=lambda level: level.elevation_m)
            index = next((i for i, level in enumerate(levels) if level.id == cmd.level_id), None)
            if index is None or index == len(levels) - 1:
                raise CommandError("Choose a level with a level above it to edit floor-to-floor height.")
            delta = cmd.height_m - (levels[index + 1].elevation_m - levels[index].elevation_m)
            for level in levels[index + 1:]:
                level.elevation_m += delta
        elif isinstance(cmd, SetMaterialPalette):
            snap.material_palette = cmd.palette
        elif isinstance(cmd, AddLevel):
            _add_level(snap, cmd)
        elif isinstance(cmd, RemoveLevel):
            _remove_level(snap, cmd)
        elif isinstance(cmd, DesignBuilding):
            from .building import build_building
            try:
                snap = build_building(snapshot.project_id,cmd.program,namespace=f"design:{cmd.command_id}")
                snap.revision_id=snapshot.revision_id
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
    if snap.building_program is not None:
        from .building import synchronize_program
        try:
            synchronize_program(snap)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
    snap.parent_revision_id = snapshot.revision_id
    snap.revision_id = new_id()
    snap.revision_number = snapshot.revision_number + 1
    snap.created_at = datetime.now(timezone.utc)
    return enrich_snapshot(snap).with_hash()
