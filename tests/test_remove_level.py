"""Removal topology, immutable history, identity and regeneration evidence."""
import pytest

from domain.architecture import enrich_snapshot
from domain.commands import CommandError, apply_commands
from domain.models import new_id
from domain.seed import build_seed
from geometry.generate import generate_floor
from geometry.validate import validate_snapshot


def level(snapshot, name):
    return next(item for item in snapshot.levels if item.name == name)


def assert_connected(snapshot):
    assert validate_snapshot(snapshot) == []
    levels = sorted(snapshot.levels, key=lambda item: item.elevation_m)
    assert len(snapshot.architecture.stairs) == len(levels) - 1
    assert {(stair.lower_level_id, stair.upper_level_id) for stair in snapshot.architecture.stairs} == {
        (lower.id, upper.id) for lower, upper in zip(levels, levels[1:])}
    assert len(snapshot.architecture.slabs) == len(levels) + 1  # One cover over the roof headhouse.
    by_id = {item.id: item for item in levels}
    for stair in snapshot.architecture.stairs:
        assert stair.riser_count * stair.riser_height_m == pytest.approx(
            by_id[stair.upper_level_id].elevation_m - by_id[stair.lower_level_id].elevation_m)
    assert {metric.space_id for metric in snapshot.architecture.space_metrics} == {space.id for space in snapshot.spaces}
    assert snapshot.architecture.revision_id == snapshot.revision_id


def test_remove_last_added_floor_returns_seed_geometry_with_new_revision():
    seed = build_seed(new_id())
    added = apply_commands(seed, [{"type": "add_level", "height_m": 4.1}])
    previous = added.model_dump_json()
    removed_id = level(added, "level_3").id
    removed_spaces = {space.id for space in added.spaces if space.level_id == removed_id}
    removed = apply_commands(added, [{"type": "remove_level"}])
    assert added.model_dump_json() == previous
    assert added.content_hash == added.compute_hash()
    assert removed.parent_revision_id == added.revision_id
    assert removed.revision_number == added.revision_number + 1
    assert removed.content_hash == removed.compute_hash() != added.content_hash
    assert [item.model_dump() for item in removed.levels] == [item.model_dump() for item in seed.levels]
    assert [space.model_dump() for space in removed.spaces] == [space.model_dump() for space in seed.spaces]
    assert removed.brief.floors_above_ground == 2
    for kind in ("walls", "openings", "slabs", "stairs", "space_metrics"):
        assert getattr(removed.architecture, kind) == getattr(seed.architecture, kind)
    assumption = removed.assumptions[-1]
    assert assumption.value["removed_level_id"] == removed_id
    assert set(assumption.value["removed_space_ids"]) == removed_spaces
    assert assumption.value["removed_floor_to_floor_height_m"] == pytest.approx(4.1)
    assert assumption.value["base_revision_id"] == added.revision_id
    assert assumption.value["source_state"] == "candidate_after_prior_commands"
    assert "no approval" in assumption.rationale
    assert assumption.review_status == "unreviewed"
    assert_connected(removed)


def test_remove_original_upper_preserves_ground_basement_and_roof():
    seed = build_seed(new_id())
    upper_id = level(seed, "upper").id
    removed = apply_commands(seed, [{"type": "remove_level", "level_id": upper_id}])
    assert [item.name for item in removed.levels] == ["basement", "ground", "roof"]
    assert [item.elevation_m for item in removed.levels] == pytest.approx([-3.2, 0, 3.4])
    assert removed.brief.floors_above_ground == 1
    assert len(removed.spaces) == 20
    assert removed.pool == seed.pool
    assert removed.roof_terrace_area_m2 == seed.roof_terrace_area_m2
    assert {space.id for space in removed.spaces} == {space.id for space in seed.spaces if space.level_id != upper_id}
    assert level(removed, "roof").id == level(seed, "roof").id
    assert_connected(removed)


def test_explicit_middle_removal_closes_only_its_height_interval():
    seed = build_seed(new_id())
    added = apply_commands(seed, [{"type": "add_level", "height_m": 4.1}, {"type": "add_level", "height_m": 2.8}])
    target = level(added, "level_3")
    before = added.model_dump_json()
    removed = apply_commands(added, [{"type": "remove_level", "level_id": target.id}])
    assert added.model_dump_json() == before
    assert [item.name for item in removed.levels] == ["basement", "ground", "upper", "level_4", "roof"]
    assert [item.elevation_m for item in removed.levels] == pytest.approx([-3.2, 0, 3.4, 6.8, 9.6])
    assert {item.id for item in removed.levels} == {item.id for item in added.levels if item.id != target.id}
    assert [space.model_dump() for space in removed.spaces] == [space.model_dump() for space in added.spaces if space.level_id != target.id]
    assert level(removed, "level_4").label == level(added, "level_4").label
    assert removed.brief.floors_above_ground == 3
    assert_connected(removed)
    # Regeneration follows actual surviving floors, even when their names have gaps.
    surviving = level(removed, "level_4")
    program = [{"name": space.name, "use": space.use, "target_area_m2": space.target_area_m2}
               for space in removed.spaces if space.level_id == surviving.id and space.classification == "principal"]
    generated = generate_floor(removed, surviving.name, program)
    assert generated["solver_status"] in {"OPTIMAL", "FEASIBLE"}
    candidate = removed.model_copy(deep=True)
    candidate.spaces = generated["spaces"]
    enrich_snapshot(candidate)
    assert_connected(candidate)


def test_surviving_room_edits_and_ids_are_not_reset_on_removal():
    seed = build_seed(new_id())
    added = apply_commands(seed, [{"type": "add_level"}])
    upper = level(added, "upper")
    spaces = {space.id: space for space in added.spaces}
    wall = next(wall for wall in added.architecture.walls if wall.level_id == upper.id
                and not wall.exterior and len(wall.space_ids) == 2 and wall.start[0] == wall.end[0]
                and all(spaces[key].classification == "principal" for key in wall.space_ids))
    edited = apply_commands(added, [{"type": "move_wall", "element_id": wall.id, "offset_m": .1}])
    removed = apply_commands(edited, [{"type": "remove_level"}])
    assert [space.model_dump() for space in removed.spaces if space.level_id == upper.id] == [
        space.model_dump() for space in edited.spaces if space.level_id == upper.id]
    assert wall.id in {wall.id for wall in removed.architecture.walls}
    assert_connected(removed)


def test_repeated_add_remove_keeps_connected_ground_and_fresh_entity_ids():
    seed = build_seed(new_id())
    current = seed
    seen = {item.id for item in seed.levels}
    for _ in range(3):
        added = apply_commands(current, [{"type": "add_level"}])
        created = {item.id for item in added.levels} - {item.id for item in current.levels}
        assert created.isdisjoint(seen)
        seen |= created
        current = apply_commands(added, [{"type": "remove_level"}])
        assert current.brief.floors_above_ground == 2
        assert_connected(current)
    current = apply_commands(current, [{"type": "remove_level"}])
    before = current.model_dump_json()
    with pytest.raises(CommandError, match="ground"):
        apply_commands(current, [{"type": "remove_level"}])
    assert current.model_dump_json() == before
    rebuilt = apply_commands(current, [{"type": "add_level"}])
    assert rebuilt.brief.floors_above_ground == 2
    assert_connected(rebuilt)


def test_failed_later_removal_keeps_entire_batch_atomic_and_command_replay_is_rejected():
    seed = build_seed(new_id())
    before = seed.model_dump_json()
    with pytest.raises(CommandError):
        apply_commands(seed, [{"type": "remove_level"}, {"type": "remove_level"}])
    assert seed.model_dump_json() == before
    taller = apply_commands(seed, [{"type": "add_level"}])
    command = {"type": "remove_level", "command_id": new_id()}
    removed = apply_commands(taller, [command])
    with pytest.raises(CommandError, match="already been applied"):
        apply_commands(removed, [command])


@pytest.mark.parametrize("name", ["ground", "basement", "roof", "missing"])
def test_protected_or_unknown_level_is_rejected_without_mutation(name):
    seed = build_seed(new_id())
    before = seed.model_dump_json()
    identity = "missing" if name == "missing" else level(seed, name).id
    with pytest.raises(CommandError, match="ground"):
        apply_commands(seed, [{"type": "remove_level", "level_id": identity}])
    assert seed.model_dump_json() == before


@pytest.mark.parametrize("fault", ["duplicate_level", "duplicate_name", "equal_elevation", "roof_below", "nonfinite", "missing_core", "misaligned_core"])
def test_invalid_stack_or_core_is_rejected(fault):
    seed = build_seed(new_id())
    if fault == "duplicate_level":
        level(seed, "ground").id = level(seed, "basement").id
    elif fault == "duplicate_name":
        level(seed, "basement").name = "ground"
    elif fault == "equal_elevation":
        level(seed, "upper").elevation_m = 0
    elif fault == "roof_below":
        level(seed, "roof").elevation_m = 2
    elif fault == "nonfinite":
        level(seed, "roof").elevation_m = float("inf")
    else:
        core = next(space for space in seed.spaces if space.level_id == level(seed, "roof").id and space.use == "stairs_service")
        if fault == "missing_core":
            seed.spaces.remove(core)
        else:
            core.polygon = [[x + .1, y] for x, y in core.polygon]
    before = seed.model_dump_json()
    with pytest.raises(CommandError):
        apply_commands(seed, [{"type": "remove_level"}])
    assert seed.model_dump_json() == before
