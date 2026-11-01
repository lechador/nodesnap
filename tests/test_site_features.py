"""Independent geometry and immutable-history evidence for private-home sites."""
from copy import deepcopy
import hashlib
import json

import pytest
from pydantic import ValidationError
from shapely.geometry import LineString, Polygon

from domain.building import BuildingGenerationError, build_building
from domain.commands import CommandError, apply_commands
from domain.models import BuildingProgram, GarageProgram, PoolProgram, ProjectSnapshot, YardProgram, new_id
from domain.seed import build_seed
from geometry.validate import validate_snapshot
from test_building_generation import small_program


def private_home(**overrides):
    program = small_program()
    program.update(yard={"width_m":12,"depth_m":8},garage={"width_m":3.6,"depth_m":6},
                   pool={"location":"outdoor","level":"ground","water_length_m":8,"water_width_m":3.5,"water_depth_m":1.4})
    program.update(overrides)
    return build_building(new_id(),program)


def water_polygon(pool):
    x,y,length,width = pool.origin_x_m,pool.origin_y_m,pool.water_length_m,pool.water_width_m
    return Polygon([(x,y),(x+length,y),(x+length,y+width),(x,y+width),(x,y)])


def assert_site_valid(snapshot):
    assert validate_snapshot(snapshot) == []
    assert snapshot.site_layout.revision_id == snapshot.revision_id
    assert snapshot.content_hash == snapshot.compute_hash()


def test_private_home_keeps_enclosed_plan_and_exact_site_quantities_separate():
    snapshot = private_home()
    assert_site_valid(snapshot)
    layout = snapshot.site_layout
    envelope = Polygon(snapshot.envelope_polygon)
    yard = Polygon(layout.yard.polygon)
    lawn = Polygon(layout.yard.polygon,layout.yard.holes)
    deck_extent = Polygon(layout.pool_deck.polygon)
    deck = Polygon(layout.pool_deck.polygon,layout.pool_deck.holes)
    water = water_polygon(snapshot.pool)
    garage = Polygon(layout.garage.polygon)
    assert envelope.area == 120
    assert yard.area == 96
    assert water.area == 28
    assert garage.area == pytest.approx(21.6)
    assert lawn.area + deck.area + water.area == pytest.approx(yard.area)
    assert yard.covers(deck_extent) and deck_extent.covers(water)
    assert lawn.intersection(deck).area == 0
    assert lawn.intersection(water).area == 0
    assert deck.intersection(water).area == 0
    assert envelope.intersection(yard).area == 0
    assert envelope.intersection(garage).area == 0
    assert yard.intersection(garage).area == 0
    assert not any(room.use in {"pool_hall","garage","yard"} for room in snapshot.spaces)
    ground = next(level for level in snapshot.levels if level.name == "ground")
    slab = next(slab for slab in snapshot.architecture.slabs if slab.level_id == ground.id)
    assert slab.holes == []
    assert snapshot.pool.level_id == ground.id and snapshot.pool.location == "outdoor"


@pytest.mark.parametrize("side",["left","right"])
def test_vehicle_opening_and_driveway_are_connected_with_true_clear_geometry(side):
    snapshot = private_home(garage={"width_m":6.4,"depth_m":7,"height_m":3.2,"side":side,"vehicle_door_width_m":5.2})
    assert_site_valid(snapshot)
    garage = snapshot.site_layout.garage
    shape = Polygon(garage.polygon)
    approach = Polygon(snapshot.site_layout.driveway.polygon)
    door = LineString([garage.vehicle_door_start,garage.vehicle_door_end])
    assert door.length == pytest.approx(5.2)
    assert shape.boundary.covers(door)
    assert approach.boundary.covers(door)
    assert shape.intersection(approach).area == 0
    assert shape.buffer(-garage.wall_thickness_m,join_style=2).area == pytest.approx(6*6.6)
    assert garage.slab_thickness_m == .16 and garage.roof_thickness_m == .18
    assert garage.height_m + garage.roof_thickness_m == pytest.approx(3.38)


def test_large_yard_and_deep_garage_remain_disjoint():
    snapshot = private_home(yard={"width_m":40,"depth_m":12},garage={"width_m":8,"depth_m":20,"vehicle_door_width_m":5})
    assert_site_valid(snapshot)
    assert Polygon(snapshot.site_layout.garage.polygon).intersection(Polygon(snapshot.site_layout.yard.polygon)).area == 0
    context = Polygon(snapshot.site_layout.context_polygon)
    assert context.covers(Polygon(snapshot.site_layout.yard.polygon))
    assert context.covers(Polygon(snapshot.site_layout.garage.polygon))
    assert snapshot.site.mode == "synthetic_demo"
    assert "not a surveyed property boundary" in next(a.rationale for a in snapshot.assumptions if a.field == "site.layout")


def test_default_outdoor_pool_adds_recorded_yard_without_indoor_basement():
    snapshot = private_home(yard=None,garage=None)
    assert_site_valid(snapshot)
    assert snapshot.site_layout.yard and not snapshot.site_layout.garage
    assert not any(level.name == "basement" for level in snapshot.levels)
    assert snapshot.building_program.yard is not None
    assert any(a.field == "site.layout" for a in snapshot.assumptions)


def test_adding_site_features_never_changes_existing_room_geometry_or_ids():
    original = build_building(new_id(),small_program())
    before = original.model_dump_json()
    edited = apply_commands(original,[{"type":"set_yard","yard":{"depth_m":6}},
                                     {"type":"set_garage","garage":{"width_m":3.8,"depth_m":6.4}}])
    assert_site_valid(edited)
    assert original.model_dump_json() == before
    assert [s.model_dump() for s in edited.spaces] == [s.model_dump() for s in original.spaces]
    assert [level.model_dump() for level in edited.levels] == [level.model_dump() for level in original.levels]
    assert edited.parent_revision_id == original.revision_id
    assert edited.revision_number == original.revision_number+1
    assert [wall.id for wall in edited.architecture.walls] == [wall.id for wall in original.architecture.walls]


def test_site_resize_retains_feature_ids_and_source_bytes():
    original = private_home()
    before = original.model_dump_json()
    changed = apply_commands(original,[{"type":"set_yard","yard":{"width_m":16,"depth_m":10}},
                                      {"type":"set_garage","garage":{"width_m":6,"depth_m":7,"vehicle_door_width_m":5}},
                                      {"type":"set_pool_dimensions","water_length_m":10}])
    assert_site_valid(changed)
    assert original.model_dump_json() == before
    for field in ("yard","garage","driveway","pool_deck"):
        assert getattr(original.site_layout,field).id == getattr(changed.site_layout,field).id
    assert original.pool.id == changed.pool.id
    assert water_polygon(changed.pool).area == 35


def test_combined_removal_validates_final_state_independent_of_command_order():
    original = private_home()
    changed = apply_commands(original,[{"type":"set_yard","yard":None},
                                      {"type":"set_garage","garage":None},
                                      {"type":"set_outdoor_pool","pool":None}])
    assert validate_snapshot(changed) == []
    assert changed.site_layout is None and changed.pool is None
    assert changed.building_program.yard is None and changed.building_program.garage is None
    assert changed.spaces == original.spaces
    assert original.pool is not None and original.site_layout is not None


@pytest.mark.parametrize("commands",[
    [{"type":"set_yard","yard":None}],
    [{"type":"set_yard","yard":{"width_m":4,"depth_m":4}}],
    [{"type":"set_pool_dimensions","water_length_m":25}],
    [{"type":"set_garage","garage":{"width_m":3,"vehicle_door_width_m":6}}],
    [{"type":"set_garage","garage":{"width_m":3.6,"attachment":"attached"}}],
])
def test_invalid_site_edit_is_atomic(commands):
    original = private_home()
    before = original.model_dump_json()
    with pytest.raises(CommandError):
        apply_commands(original,commands)
    assert original.model_dump_json() == before


def test_indoor_to_outdoor_conversion_preserves_hall_and_pool_identity():
    original = build_seed(new_id())
    before = original.model_dump_json()
    changed = apply_commands(original,[{"type":"set_outdoor_pool","pool":{
        "location":"outdoor","level":"ground","water_length_m":8,"water_width_m":3.5}}])
    assert_site_valid(changed)
    assert changed.pool.id == original.pool.id
    assert changed.spaces == original.spaces
    assert changed.pool.level_id != original.pool.level_id
    hall = next(space for space in original.spaces if space.use == "pool_hall")
    assert hall.id in next(a.value for a in changed.assumptions if a.field == "site.pool_conversion")["retained_former_hall_ids"]
    assert original.model_dump_json() == before
    for slab in changed.architecture.slabs:
        assert water_polygon(changed.pool).intersection(Polygon(slab.polygon)).area == 0


def test_unrelated_edits_rebind_site_revision_without_relocating_features():
    original = private_home()
    changed = apply_commands(original,[{"type":"set_material_palette","palette":"white_stucco"}])
    assert_site_valid(changed)
    a,b = original.site_layout.model_dump(),changed.site_layout.model_dump()
    a.pop("revision_id"); b.pop("revision_id")
    assert a == b
    assert original.pool == changed.pool


def test_legacy_hashes_do_not_acquire_new_optional_fields():
    for original in (build_seed(new_id()),build_building(new_id(),small_program())):
        payload = original.model_dump(mode="json")
        assert "site_layout" not in payload
        if payload.get("pool"):
            assert "location" not in payload["pool"]
        if payload.get("building_program"):
            assert "yard" not in payload["building_program"] and "garage" not in payload["building_program"]
        canon = {key:value for key,value in payload.items() if key not in {"content_hash","created_at"}}
        old_hash = hashlib.sha256(json.dumps(canon,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
        loaded = ProjectSnapshot.model_validate(deepcopy(payload))
        assert loaded.compute_hash() == old_hash == payload["content_hash"]
        assert loaded.model_dump(mode="json") == payload
    legacy_pool = PoolProgram(water_length_m=8,water_width_m=3,level="ground")
    assert "location" not in legacy_pool.model_dump()


def test_new_design_cannot_hide_a_garage_or_yard_as_an_indoor_room():
    for use in ("garage","yard","garden","outdoor_pool"):
        program = small_program()
        program["floors"][0]["rooms"][0]["use"] = use
        # Existing serialized programs remain parseable; new generation enforces the contract.
        BuildingProgram.model_validate(program)
        with pytest.raises(BuildingGenerationError,match="typed yard/garage"):
            build_building(new_id(),program)


@pytest.mark.parametrize("model,kwargs",[
    (YardProgram,{"depth_m":float("nan")}),
    (GarageProgram,{"width_m":float("inf")}),
    (PoolProgram,{"water_length_m":8,"water_width_m":3,"location":"outdoor","level":"basement"}),
])
def test_nonfinite_or_conflicting_feature_inputs_are_rejected(model,kwargs):
    with pytest.raises(ValidationError):
        model(**kwargs)


def test_geometric_validator_detects_site_drift_independently_of_generator():
    cases=[]
    stale=private_home(); stale.site_layout.revision_id=new_id(); cases.append((stale,"STALE_REVISION"))
    door=private_home(); door.site_layout.garage.vehicle_door_width_m+=1; cases.append((door,"INVALID_OPENING_HOST"))
    deck=private_home(); deck.site_layout.pool_deck.holes=[]; cases.append((deck,"INVALID_POOL_DECK"))
    lawn=private_home(); lawn.site_layout.yard.holes=[]; cases.append((lawn,"SITE_OVERLAP"))
    overlap=private_home(); overlap.site_layout.garage.polygon=deepcopy(overlap.envelope_polygon); cases.append((overlap,"SITE_BUILDING_INTERSECTION"))
    outside=private_home(); outside.pool.origin_y_m=-5; cases.append((outside,"OUTSIDE_YARD"))
    for snapshot,code in cases:
        assert code in {issue["code"] for issue in validate_snapshot(snapshot)}


def test_synthetic_context_and_its_register_match_saved_geometry():
    snapshot = private_home()
    x0,y0,x1,y1 = Polygon(snapshot.site_layout.context_polygon).bounds
    assert snapshot.site.context_width_m == pytest.approx(x1-x0)
    assert snapshot.site.context_depth_m == pytest.approx(y1-y0)
    note = next(a for a in snapshot.assumptions if a.field == "site.context_m")
    assert note.value == pytest.approx([x1-x0,y1-y0])
    assert "3 m display margin" in note.rationale


def test_sourced_context_dimensions_are_never_fabricated_or_resized():
    original = build_building(new_id(),small_program())
    original.site.mode = "sourced_parcel"
    original.site.context_width_m = 27
    original.site.context_depth_m = 32
    changed = apply_commands(original,[{"type":"set_yard","yard":{"width_m":40,"depth_m":20}}])
    assert_site_valid(changed)
    assert changed.site.context_width_m == 27
    assert changed.site.context_depth_m == 32
    assert Polygon(changed.site_layout.context_polygon).bounds[2]-Polygon(changed.site_layout.context_polygon).bounds[0] > 27
    assert "Parcel fit" in next(a.rationale for a in changed.assumptions if a.field == "site.layout")


def test_add_remove_floor_keeps_site_and_outdoor_water_on_ground():
    original = private_home()
    added = apply_commands(original,[{"type":"add_level"}])
    removed = apply_commands(added,[{"type":"remove_level"}])
    for snapshot in (added,removed):
        assert_site_valid(snapshot)
        assert snapshot.site_layout.yard.polygon == original.site_layout.yard.polygon
        assert snapshot.site_layout.garage.polygon == original.site_layout.garage.polygon
        assert snapshot.pool == original.pool
        assert not any(space.use == "pool_hall" for space in snapshot.spaces)


def test_invalid_deck_hole_returns_issue_instead_of_crashing_validator():
    snapshot = private_home()
    snapshot.site_layout.pool_deck.holes = [[[0,0],[1,0]]]
    assert "INVALID_GEOMETRY" in {issue["code"] for issue in validate_snapshot(snapshot)}
