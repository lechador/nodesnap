"""M1 verification: seed -> geometry -> pool quantities -> PDF -> revision edit."""
import math

from domain.commands import apply_commands
from domain.models import new_id
from domain.seed import build_seed
from engineering.pool import pool_quantities
from geometry.validate import area_schedule, validate_spaces
from reports.pdf import build_review_pdf

FT2 = 0.09290304


def test_seed_program():
    snap = build_seed(new_id())
    assert validate_spaces(snap.spaces) == []
    principal = {}
    for lvl in snap.levels:
        principal[lvl.name] = [s for s in snap.spaces
                               if s.level_id == lvl.id and s.classification == "principal"]
    assert len(principal["ground"]) == 6
    assert len(principal["upper"]) == 6
    bedrooms = [s for s in snap.spaces if s.use == "bedroom"]
    assert len(bedrooms) == 5  # guest downstairs + primary + 3 upstairs
    assert snap.pool.water_length_m == 8.0 and snap.pool.water_depth_m == 1.4
    assert abs(snap.roof_terrace_area_m2 - 900 * FT2) < 0.1
    assert snap.content_hash == snap.compute_hash()


def test_pool_quantities_exact():
    q = pool_quantities(8.0, 3.5, 1.4)
    assert q["surface_area_m2"] == 28.0
    assert math.isclose(q["volume_m3"], 39.2)
    assert math.isclose(q["mass_kg"], 39200.0)
    assert math.isclose(q["weight_n"], 39200.0 * 9.80665)
    assert math.isclose(q["max_hydrostatic_pressure_pa"], 1000 * 9.80665 * 1.4)


def test_pool_edit_creates_new_revision_and_changes_quantities():
    snap = build_seed(new_id())
    new = apply_commands(snap, [{"type": "set_pool_dimensions",
                                 "water_length_m": 10.0}])
    assert new.revision_number == snap.revision_number + 1
    assert new.parent_revision_id == snap.revision_id
    assert new.content_hash != snap.content_hash
    q = pool_quantities(new.pool.water_length_m, new.pool.water_width_m,
                        new.pool.water_depth_m)
    assert q["surface_area_m2"] == 35.0


def test_area_schedule_reports_actual_not_target():
    snap = build_seed(new_id())
    rows = area_schedule(snap)
    assert len(rows) == len(snap.spaces)
    assert all(r["actual_area_m2"] > 0 for r in rows)


def test_pdf_is_real_and_revision_bound():
    snap = build_seed(new_id())
    pdf = build_review_pdf(snap)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 5000
