"""Independent geometry and revision fixtures for the architectural rewrite."""
import math
import pytest
from shapely.geometry import Polygon

from domain.architecture import enrich_snapshot
from domain.commands import CommandError, apply_commands
from domain.models import FT2_TO_M2, ProjectSnapshot, Space, new_id
from domain.seed import GROUND_PRINCIPAL, build_seed
from geometry.generate import generate_floor
from geometry.layout import solve_floor
from geometry.validate import area_schedule, validate_snapshot


def test_seed_connects_all_levels_and_preserves_program():
    snap = build_seed(new_id())
    assert validate_snapshot(snap) == []
    assert len(snap.architecture.stairs) == 3
    for name in ('ground', 'upper'):
        level = next(l for l in snap.levels if l.name == name)
        spaces = [s for s in snap.spaces if s.level_id == level.id]
        assert sum(s.classification == 'principal' for s in spaces) == 6
        assert math.isclose(sum(Polygon(s.polygon).area for s in spaces), 18 * 15.5)
    assert sum(s.use == 'bedroom' for s in snap.spaces) == 5
    for stair in snap.architecture.stairs:
        levels = {l.id: l for l in snap.levels}
        assert math.isclose(stair.riser_count * stair.riser_height_m,
                            levels[stair.upper_level_id].elevation_m - levels[stair.lower_level_id].elevation_m)


def test_net_area_is_independent_of_zone_and_targets():
    snap = build_seed(new_id())
    living = next(s for s in snap.spaces if s.use == 'living')
    xs, ys = zip(*living.polygon)
    # Living touches west/north envelope: full300mm exterior + half150mm
    # shared partitions on east/south. This reference is not the production helper.
    expected = (max(xs)-min(xs)-.3-.075) * (max(ys)-min(ys)-.3-.075)
    row = next(r for r in area_schedule(snap) if r['space_id'] == living.id)
    assert math.isclose(row['actual_area_m2'], expected, abs_tol=.0001)
    assert row['zone_area_m2'] > row['actual_area_m2']
    assert row['revision_id'] == snap.revision_id


def test_openings_really_fit_hosts_and_ids_survive_pool_change():
    snap = build_seed(new_id())
    walls = {w.id: w for w in snap.architecture.walls}
    for opening in snap.architecture.openings:
        host = walls[opening.wall_id]
        assert opening.offset_m + opening.width_m <= math.dist(host.start, host.end)
        assert opening.sill_height_m + opening.height_m <= host.height_m
        assert set(opening.space_ids) <= set(host.space_ids)
    edited = apply_commands(snap, [{'type': 'set_pool_dimensions', 'water_length_m': 10}])
    assert set(walls) == {w.id for w in edited.architecture.walls}
    assert edited.architecture.revision_id == edited.revision_id
    assert snap.architecture.revision_id == snap.revision_id
    assert snap.pool.water_length_m == 8
    assert validate_snapshot(edited) == []


def test_partition_move_preserves_adjacent_room_area_sum():
    snap = build_seed(new_id())
    by_id = {s.id: s for s in snap.spaces}
    wall = next(w for w in snap.architecture.walls if not w.exterior and len(w.space_ids) == 2
                and all(by_id[k].classification == 'principal' for k in w.space_ids))
    before = sum(Polygon(by_id[k].polygon).area for k in wall.space_ids)
    moved = apply_commands(snap, [{'type': 'move_wall', 'element_id': wall.id, 'offset_m': .2}])
    after = sum(Polygon(s.polygon).area for s in moved.spaces if s.id in wall.space_ids)
    assert math.isclose(before, after)
    assert validate_snapshot(moved) == []
    assert wall.id in {w.id for w in moved.architecture.walls}


def test_terrace_and_floor_height_rebuild_revision_bound_geometry():
    snap = build_seed(new_id())
    ground = next(l for l in snap.levels if l.name == 'ground')
    edited = apply_commands(snap, [{'type': 'set_terrace_area', 'area_m2': 100},
                                  {'type': 'set_level_height', 'level_id': ground.id, 'height_m': 4}])
    terrace = next(s for s in edited.spaces if s.use == 'roof_terrace')
    assert math.isclose(Polygon(terrace.polygon).area, 100)
    assert edited.roof_terrace_area_m2 == 100
    assert next(l for l in edited.levels if l.name == 'upper').elevation_m == 4
    assert math.isclose(next(l for l in edited.levels if l.name == 'roof').elevation_m, 7.4)
    assert validate_snapshot(edited) == []


def test_disconnected_room_is_detected_not_passing():
    snap = build_seed(new_id())
    living = next(s for s in snap.spaces if s.use == 'living')
    snap.architecture.openings = [o for o in snap.architecture.openings if living.id not in o.space_ids]
    assert any(i['code'] == 'DISCONNECTED_SPACE' and i['object_id'] == living.id for i in validate_snapshot(snap))


@pytest.mark.parametrize('commands', [[], [{'type':'set_pool_dimensions','water_length_m':float('nan')}],
    [{'type':'move_space','element_id':'missing','dx_m':float('inf')}],
    [{'type':'set_material_palette','palette':'fake','arbitrary':'script'}],
    [{'type':'set_terrace_area','area_m2':1000}]])
def test_invalid_commands_fail_without_mutation(commands):
    snap = build_seed(new_id())
    before = snap.model_dump_json()
    with pytest.raises(CommandError):
        apply_commands(snap, commands)
    assert snap.model_dump_json() == before


def test_generated_layout_preserves_ids_and_access():
    snap = build_seed(new_id())
    rooms = [{'name':n,'use':u,'target_area_m2':ft*FT2_TO_M2} for n,u,ft in GROUND_PRINCIPAL]
    generated = generate_floor(snap, 'ground', rooms)
    candidate = snap.model_copy(deep=True)
    candidate.spaces = generated['spaces']
    enrich_snapshot(candidate)
    assert validate_snapshot(candidate) == []
    before = {s.name:s.id for s in snap.spaces if s.classification == 'principal'}
    after = {s.name:s.id for s in candidate.spaces if s.classification == 'principal'}
    assert before == after
    assert generated['settings']['num_search_workers'] == 1
    assert solve_floor(rooms, time_limit_s=0)['solver_status'] == 'UNKNOWN'
    assert solve_floor([{'name':'bad','target_area_m2':float('nan')}])['solver_status'] == 'MODEL_INVALID'


def test_legacy_model_hash_remains_stable():
    import hashlib, json
    snap = build_seed(new_id()).model_dump(mode='json')
    snap['schema_version'] = '0.1.0'
    snap.pop('architecture'); snap.pop('material_palette')
    basis = {k:v for k,v in snap.items() if k not in {'content_hash','created_at'}}
    digest = hashlib.sha256(json.dumps(basis,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    loaded = ProjectSnapshot.model_validate(snap)
    assert loaded.architecture is None
    assert loaded.compute_hash() == digest


def test_pool_cannot_occupy_physical_wall_thickness():
    snap = build_seed(new_id())
    candidate = apply_commands(snap, [{'type': 'set_pool_dimensions', 'water_length_m': 12}])
    assert any(issue['code'] == 'POOL_WALL_INTERSECTION' for issue in validate_snapshot(candidate))


def test_every_pdf_page_carries_same_revision_and_architecture_matches():
    import pymupdf
    from reports.pdf import build_review_pdf
    snap = build_seed(new_id())
    document = pymupdf.open(stream=build_review_pdf(snap), filetype='pdf')
    assert all(snap.revision_id in page.get_text() for page in document)
    plan = document[3].get_text()
    assert '1:75' in plan and 'ROOM / AREA REGISTER' in plan and '18.000 m' in plan
    assert '300 mm envelope' in plan
