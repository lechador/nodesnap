"""Storey-addition invariants, independent quantities and revision evidence."""
import math

import pytest
from shapely.geometry import Polygon

from domain.architecture import enrich_snapshot
from domain.commands import CommandError, MAX_LIVING_LEVELS, apply_commands
from domain.models import new_id
from domain.seed import build_seed
from geometry.generate import generate_floor
from geometry.validate import area_schedule, validate_snapshot


def named(snapshot, name):
    return next(level for level in snapshot.levels if level.name == name)


def rooms(snapshot, level):
    return [space for space in snapshot.spaces if space.level_id == level.id]


def test_add_level_preserves_history_and_existing_entity_identities():
    seed = build_seed(new_id())
    original = seed.model_dump_json()
    added = apply_commands(seed, [{"type": "add_level"}])
    assert seed.model_dump_json() == original
    assert seed.content_hash == seed.compute_hash()
    assert added.content_hash == added.compute_hash() != seed.content_hash
    assert added.parent_revision_id == seed.revision_id
    assert added.revision_number == seed.revision_number + 1
    assert added.architecture.revision_id == added.revision_id
    assert added.brief.floors_above_ground == 3
    assert [level.name for level in added.levels] == ["basement", "ground", "upper", "level_3", "roof"]
    assert [level.elevation_m for level in added.levels] == pytest.approx([-3.2, 0, 3.4, 6.8, 10.2])
    assert named(added, "level_3").label == "Level 3"
    assert {level.id for level in seed.levels} < {level.id for level in added.levels}
    previous_spaces = {space.id: space.model_dump() for space in seed.spaces}
    assert previous_spaces == {space.id: space.model_dump() for space in added.spaces if space.id in previous_spaces}
    for kind in ("walls", "openings", "slabs"):
        assert {item.id for item in getattr(seed.architecture, kind)} < {item.id for item in getattr(added.architecture, kind)}
    # The former upper-to-roof stair is replaced by two actual connections.
    unchanged_stairs = [stair for stair in seed.architecture.stairs if stair.upper_level_id != named(seed, "roof").id]
    assert all(stair in added.architecture.stairs for stair in unchanged_stairs)
    assert validate_snapshot(added) == []


def test_new_level_has_independently_identified_rooms_real_slabs_openings_and_access():
    seed = build_seed(new_id())
    added = apply_commands(seed, [{"type": "add_level"}])
    source = rooms(seed, named(seed, "upper"))
    new_level = named(added, "level_3")
    copied = rooms(added, new_level)
    assert len(copied) == 10
    assert sum(space.classification == "principal" for space in copied) == 6
    assert sum(Polygon(space.polygon).area for space in copied) == pytest.approx(18 * 15.5)
    assert {space.id for space in copied}.isdisjoint(space.id for space in seed.spaces)
    assert [space.model_dump(exclude={"id", "level_id"}) for space in copied] == [space.model_dump(exclude={"id", "level_id"}) for space in source]
    core = next(space for space in copied if space.use == "stairs_service")
    slab = next(slab for slab in added.architecture.slabs if slab.level_id == new_level.id)
    assert slab.kind == "floor"
    assert Polygon(slab.polygon).area == 279
    assert len(slab.holes) == 1
    assert Polygon(core.polygon).covers(Polygon(slab.holes[0]))
    assert Polygon(slab.holes[0]).area == pytest.approx((3 - .075 - .30) * (4.15 - .15))
    endpoints = {(stair.lower_level_id, stair.upper_level_id) for stair in added.architecture.stairs}
    ordered = sorted(added.levels, key=lambda level: level.elevation_m)
    assert endpoints == {(lower.id, upper.id) for lower, upper in zip(ordered, ordered[1:])}
    for stair in added.architecture.stairs:
        by_id = {level.id: level for level in added.levels}
        assert stair.riser_height_m * stair.riser_count == pytest.approx(by_id[stair.upper_level_id].elevation_m - by_id[stair.lower_level_id].elevation_m)
    hosts = {wall.id: wall for wall in added.architecture.walls if wall.level_id == new_level.id}
    openings = [opening for opening in added.architecture.openings if opening.wall_id in hosts]
    assert any(opening.kind == "window" for opening in openings)
    assert any(opening.kind == "door" for opening in openings)
    for opening in openings:
        wall = hosts[opening.wall_id]
        assert opening.offset_m + opening.width_m <= math.dist(wall.start, wall.end)
        assert opening.sill_height_m + opening.height_m <= wall.height_m
    assert all(row["revision_id"] == added.revision_id for row in area_schedule(added))
    assert validate_snapshot(added) == []


def test_copies_current_edited_zones_and_terrace_stays_on_the_same_lifted_roof():
    seed = build_seed(new_id())
    upper = named(seed, "upper")
    by_id = {space.id: space for space in seed.spaces}
    partition = next(wall for wall in seed.architecture.walls if wall.level_id == upper.id
                     and not wall.exterior and len(wall.space_ids) == 2
                     and all(by_id[key].classification == "principal" for key in wall.space_ids)
                     and wall.start[0] == wall.end[0])
    edited = apply_commands(seed, [{"type": "move_wall", "element_id": partition.id, "offset_m": .2},
                                   {"type": "set_level_height", "level_id": upper.id, "height_m": 4},
                                   {"type": "set_terrace_area", "area_m2": 100}])
    before = edited.model_dump_json()
    added = apply_commands(edited, [{"type": "add_level"}])
    assert edited.model_dump_json() == before
    assert named(added, "level_3").elevation_m == pytest.approx(7.4)
    assert named(added, "roof").elevation_m == pytest.approx(11.4)
    copied = rooms(added, named(added, "level_3"))
    assert [space.polygon for space in copied] == [space.polygon for space in rooms(edited, upper)]
    assert any(copy.polygon != original.polygon for copy, original in zip(copied, rooms(seed, upper)))
    terrace = next(space for space in added.spaces if space.use == "roof_terrace")
    assert terrace.id == next(space.id for space in seed.spaces if space.use == "roof_terrace")
    assert terrace.level_id == named(seed, "roof").id
    assert Polygon(terrace.polygon).area == pytest.approx(100)
    assert added.roof_terrace_area_m2 == 100
    provenance = added.assumptions[-1]
    assert provenance.value["base_revision_id"] == edited.revision_id
    assert provenance.value["source_state"] == "candidate_after_prior_commands"
    assert provenance.value["source_level_id"] == upper.id
    assert provenance.value["floor_to_floor_height_m"] == pytest.approx(4)
    assert provenance.value["height_basis"] == "inherited_top_storey"
    assert provenance.review_status == "unreviewed"
    assert "no approval" in provenance.rationale
    assert validate_snapshot(added) == []


def test_explicit_source_and_height_do_not_resize_previous_storeys():
    seed = build_seed(new_id())
    added = apply_commands(seed, [{"type": "add_level", "source_level_id": named(seed, "ground").id, "height_m": 2.6}])
    assert [level.elevation_m for level in added.levels] == pytest.approx([-3.2, 0, 3.4, 6.8, 9.4])
    assert [space.use for space in rooms(added, named(added, "level_3"))] == [space.use for space in rooms(seed, named(seed, "ground"))]
    assert added.assumptions[-1].value["height_basis"] == "user_supplied"
    assert validate_snapshot(added) == []


def test_repeated_additions_copy_the_current_top_and_reach_runtime_bound():
    seed = build_seed(new_id())
    third = apply_commands(seed, [{"type": "add_level", "height_m": 4.5}])
    fourth = apply_commands(third, [{"type": "add_level"}])
    assert named(fourth, "level_4").elevation_m == pytest.approx(11.3)
    assert named(fourth, "roof").elevation_m == pytest.approx(15.8)
    assert fourth.assumptions[-1].value["source_level_id"] == named(third, "level_3").id
    assert validate_snapshot(fourth) == []
    maximum = apply_commands(fourth, [{"type": "add_level"} for _ in range(MAX_LIVING_LEVELS - 4)])
    assert maximum.brief.floors_above_ground == MAX_LIVING_LEVELS
    assert len(maximum.architecture.stairs) == MAX_LIVING_LEVELS + 1
    assert len({space.id for space in maximum.spaces}) == len(maximum.spaces)
    assert validate_snapshot(maximum) == []
    before = maximum.model_dump_json()
    with pytest.raises(CommandError, match="execution limit"):
        apply_commands(maximum, [{"type": "add_level"}])
    assert maximum.model_dump_json() == before


def test_added_floor_can_regenerate_while_preserving_its_ids_and_other_levels():
    added = apply_commands(build_seed(new_id()), [{"type": "add_level"}])
    level = named(added, "level_3")
    program = [{"name": space.name, "use": space.use, "target_area_m2": space.target_area_m2}
               for space in rooms(added, level) if space.classification == "principal"]
    program[0]["target_area_m2"] *= 1.1
    generated = generate_floor(added, level.name, program)
    assert generated["solver_status"] in {"OPTIMAL", "FEASIBLE"}
    candidate = added.model_copy(deep=True)
    candidate.spaces = generated["spaces"]
    enrich_snapshot(candidate)
    old = {space.id for space in rooms(added, level) if space.classification == "principal"}
    assert old == {space.id for space in rooms(candidate, level) if space.classification == "principal"}
    assert [space.model_dump() for space in added.spaces if space.level_id != level.id] == [space.model_dump() for space in candidate.spaces if space.level_id != level.id]
    assert any(a.polygon != b.polygon for a, b in zip(rooms(added, level), rooms(candidate, level)))
    assert validate_snapshot(candidate) == []


def test_command_identity_gives_stable_new_entities_and_cannot_be_applied_again():
    seed = build_seed(new_id())
    command = {"type": "add_level", "command_id": new_id()}
    first, retry = apply_commands(seed, [command]), apply_commands(seed, [command])
    assert {space.id for space in first.spaces} == {space.id for space in retry.spaces}
    assert {level.id for level in first.levels} == {level.id for level in retry.levels}
    with pytest.raises(CommandError, match="already been applied"):
        apply_commands(first, [command])


@pytest.mark.parametrize("payload", [
    {"height_m": 2.59}, {"height_m": 4.51}, {"height_m": float("nan")}, {"height_m": float("inf")},
    {"source_level_id": "missing"}, {"count": 3},
])
def test_invalid_parameters_are_rejected_without_mutation(payload):
    seed = build_seed(new_id())
    before = seed.model_dump_json()
    with pytest.raises(CommandError):
        apply_commands(seed, [{"type": "add_level", **payload}])
    assert seed.model_dump_json() == before


@pytest.mark.parametrize("source", ["basement", "roof"])
def test_nonliving_source_is_rejected(source):
    seed = build_seed(new_id())
    with pytest.raises(CommandError, match="occupied above-ground"):
        apply_commands(seed, [{"type": "add_level", "source_level_id": named(seed, source).id}])


@pytest.mark.parametrize("fault", ["duplicate_id", "duplicate_name", "equal_elevation", "roof_below_top", "nonfinite"])
def test_invalid_level_topology_is_detected_without_crashing(fault):
    seed = build_seed(new_id())
    if fault == "duplicate_id":
        seed.levels[0].id = seed.levels[1].id
    elif fault == "duplicate_name":
        seed.levels[0].name = seed.levels[1].name
    elif fault == "equal_elevation":
        seed.levels[1].elevation_m = seed.levels[2].elevation_m
    elif fault == "roof_below_top":
        named(seed, "roof").elevation_m = 2
    else:
        seed.levels[0].elevation_m = float("nan")
    assert validate_snapshot(seed)
    with pytest.raises(CommandError):
        apply_commands(seed, [{"type": "add_level"}])


def test_missing_or_misaligned_stair_core_cannot_be_copied():
    seed = build_seed(new_id())
    core = next(space for space in rooms(seed, named(seed, "upper")) if space.use == "stairs_service")
    core.polygon = [[x + .1, y] for x, y in core.polygon]
    with pytest.raises(CommandError, match="aligned stair core"):
        apply_commands(seed, [{"type": "add_level"}])
