"""Independent geometry/quantity fixtures for services, not code design checks."""
import math

import pytest

from domain.architecture import rect
from domain.commands import apply_commands
from domain.models import Architecture, Level, Opening, ProjectSnapshot, Slab, Space, SpaceMetrics, Wall, new_id
from domain.seed import build_seed
from engineering.services import build_inventories, conduction_w, electrical_totals, envelope_components, roof_runoff_l_s


def rectangular_fixture():
    """10×8×3 m shell, 3 m² glazing + 2 m² door, an independently declared fixture.

    Main roof has a 2×2 opening filled by a higher headhouse cover: total
    catchment is 80 m², never 84. This is not a villa design fixture.
    """
    ground = Level(name="ground", label="Ground", elevation_m=0)
    roof = Level(name="roof", label="Roof", elevation_m=3)
    rid = new_id()
    room = Space(level_id=ground.id, name="Fixture room", use="living", classification="principal", polygon=rect(0, 0, 10, 8))
    terrace = Space(level_id=roof.id, name="Fixture terrace", use="roof_terrace", classification="support", polygon=rect(0, 0, 5, 4))
    corners = [(0, 0), (10, 0), (10, 8), (0, 8), (0, 0)]
    walls = [Wall(id=new_id(), level_id=ground.id, start=list(a), end=list(b), thickness_m=.3, height_m=3, exterior=True, role="enclosure", material="stone", assembly_id="fixture", space_ids=[room.id]) for a, b in zip(corners, corners[1:])]
    opening = rect(6, 2, 2, 2)
    architecture = Architecture(revision_id=rid, walls=walls,
        openings=[Opening(id=new_id(), wall_id=walls[0].id, kind="window", offset_m=1, width_m=2, height_m=1.5, sill_height_m=.7, space_ids=[room.id]),
                  Opening(id=new_id(), wall_id=walls[1].id, kind="door", offset_m=1, width_m=1, height_m=2, sill_height_m=0, space_ids=[room.id])],
        slabs=[Slab(id=new_id(), level_id=ground.id, polygon=rect(0, 0, 10, 8), thickness_m=.25, kind="floor"),
               Slab(id=new_id(), level_id=roof.id, polygon=rect(0, 0, 10, 8), holes=[opening], thickness_m=.25, kind="roof"),
               Slab(id=new_id(), level_id=roof.id, elevation_m=5, polygon=opening, thickness_m=.18, kind="roof")],
        space_metrics=[SpaceMetrics(space_id=room.id, clear_polygon=rect(.5, .5, 9, 7), zone_area_m2=80, net_area_m2=63, clear_width_m=9, clear_depth_m=7)])
    return ProjectSnapshot(project_id=new_id(), revision_id=rid, levels=[ground, roof], spaces=[room, terrace], architecture=architecture, roof_terrace_area_m2=20).with_hash()


def test_independent_shell_areas_openings_and_conduction():
    snapshot = rectangular_fixture()
    thermal, runoff = envelope_components(snapshot)
    areas = thermal["area_reconciliation"]
    assert areas["gross_wall_area_m2"] == 108
    assert areas["opaque_wall_area_m2"] == 103
    assert areas["window_area_m2"] == 3
    assert areas["door_area_m2"] == 2
    assert areas["opaque_wall_area_m2"] + areas["window_area_m2"] + areas["door_area_m2"] == areas["gross_wall_area_m2"]
    # 22 K × (103*.30 + 3*1.60 + 2*1.80 + 80*.20 + 80*.35) = 1832.6 W.
    assert math.isclose(thermal["total_conduction_w"], 1832.6, abs_tol=1e-9)
    assert all(row["revision_id"] == snapshot.revision_id for row in thermal["envelope_conduction"])
    assert all(row["u_input_basis"] == "demonstration_assumption" for row in thermal["envelope_conduction"])


def test_roof_headhouse_is_counted_once_and_terrace_is_subset():
    _, runoff = envelope_components(rectangular_fixture())
    assert runoff["roof_area_m2"] == 80
    assert runoff["terrace_area_m2"] == 20
    assert runoff["other_roof_area_m2"] == 60
    assert sum(zone["area_m2"] for zone in runoff["catchments"]) == 80
    assert math.isclose(runoff["runoff_l_s"], 19 / 9, abs_tol=1e-12)


def test_clear_area_drives_lighting_instead_of_zone_area():
    snapshot = rectangular_fixture()
    electrical = build_inventories(snapshot)["electrical"]
    allowance = next(item for item in electrical["items"] if "space_id" in item)
    assert allowance["clear_area_m2"] == 63
    assert allowance["power_w"] == 756  # 63*12, not the gross-zone allowance 80*12.
    assert math.isclose(electrical["connected_load_w"], 10256)
    assert electrical["revision_id"] == snapshot.revision_id
    assert electrical["input_hash"] == snapshot.content_hash


def test_accepted_floor_height_changes_real_envelope_quantity():
    snapshot = build_seed(new_id())
    ground = next(level for level in snapshot.levels if level.name == "ground")
    taller = apply_commands(snapshot, [{"type": "set_level_height", "level_id": ground.id, "height_m": 4.0}])
    before = build_inventories(snapshot)["hvac_energy"]
    after = build_inventories(taller)["hvac_energy"]
    # Ground enclosure perimeter 2*(18+15.5)=67 m; height increases from3.4 to4m.
    # Windows and doors keep their modeled areas; 40.2m² extra opaque wall.
    assert math.isclose(after["area_reconciliation"]["gross_wall_area_m2"] - before["area_reconciliation"]["gross_wall_area_m2"], 40.2, abs_tol=1e-9)
    assert math.isclose(after["total_conduction_w"] - before["total_conduction_w"], 265.32, abs_tol=1e-8)
    assert after["revision_id"] == taller.revision_id
    assert after["input_hash"] != before["input_hash"]


def test_terrace_edit_redistributes_catchments_without_inventing_roof_area():
    snapshot = build_seed(new_id())
    revised = apply_commands(snapshot, [{"type": "set_terrace_area", "area_m2": 100}])
    before = build_inventories(snapshot)["drainage"]
    after = build_inventories(revised)["drainage"]
    assert math.isclose(after["terrace_area_m2"], 100)
    assert math.isclose(after["roof_area_m2"], before["roof_area_m2"])
    assert math.isclose(after["other_roof_area_m2"], after["roof_area_m2"] - 100)
    assert after["revision_id"] == revised.revision_id


def test_pool_edit_changes_lowest_slab_component_not_air_conditioner_capacity():
    snapshot = build_seed(new_id())
    revised = apply_commands(snapshot, [{"type": "set_pool_dimensions", "water_length_m": 9}])
    before = build_inventories(snapshot)
    after = build_inventories(revised)
    # Extra water opening (9-8)*3.5 =3.5m² removed from the lowest slab.
    delta = after["hvac_energy"]["total_conduction_w"] - before["hvac_energy"]["total_conduction_w"]
    assert math.isclose(delta, -3.5 * .35 * 22, abs_tol=1e-9)
    assert after["electrical"]["connected_load_w"] == before["electrical"]["connected_load_w"]
    assert all(item.get("selection_status") == "unselected" for item in after["electrical"]["items"] if "space_id" not in item)


def test_legacy_missing_architecture_is_unknown_not_template_numbers():
    snapshot = rectangular_fixture()
    snapshot.architecture = None
    result = build_inventories(snapshot)
    assert result["hvac_energy"]["execution_status"] == "blocked"
    assert result["hvac_energy"]["total_conduction_w"] is None
    assert result["drainage"]["roof_area_m2"] is None


@pytest.mark.parametrize("run", [lambda: conduction_w(float("nan"), .3, 22), lambda: roof_runoff_l_s(-1, 100, .95), lambda: electrical_totals([], voltage_v=0)])
def test_invalid_component_inputs_rejected(run):
    with pytest.raises(ValueError):
        run()
