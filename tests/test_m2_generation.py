"""M2 verification: CP-SAT generation, drag command, distinct briefs."""
from domain.commands import apply_commands
from domain.models import FT2_TO_M2, new_id
from domain.seed import GROUND_PRINCIPAL, build_seed
from geometry.generate import generate_floor
from geometry.validate import validate_spaces


def _rooms(scale=1.0):
    return [{"name": n, "use": u, "target_area_m2": round(ft2 * FT2_TO_M2 * scale, 3)}
            for n, u, ft2 in GROUND_PRINCIPAL]


def test_solver_generates_valid_floor():
    snap = build_seed(new_id())
    out = generate_floor(snap, "ground", _rooms())
    assert out["solver_status"] in ("OPTIMAL", "FEASIBLE")
    assert validate_spaces(out["spaces"]) == []
    principal = [s for s in out["spaces"]
                 if s.classification == "principal"
                 and any(l.name == "ground" and l.id == s.level_id for l in snap.levels)]
    assert len(principal) == 6


def test_different_program_gives_different_geometry():
    snap = build_seed(new_id())
    a = generate_floor(snap, "ground", _rooms())
    bigger_living = _rooms()
    bigger_living[0]["target_area_m2"] = round(900 * FT2_TO_M2, 3)
    bigger_living[1]["target_area_m2"] = round(200 * FT2_TO_M2, 3)
    b = generate_floor(snap, "ground", bigger_living)
    pa = {s.name: s.polygon for s in a["spaces"]}
    pb = {s.name: s.polygon for s in b["spaces"]}
    assert pa["Main living room"] != pb["Main living room"]


def test_impossible_program_is_infeasible_not_fake():
    snap = build_seed(new_id())
    huge = [{"name": f"Room {i}", "use": "living", "target_area_m2": 200.0} for i in range(6)]
    out = generate_floor(snap, "ground", huge)
    assert out["spaces"] is None
    assert out["solver_status"] == "INFEASIBLE"


def test_move_space_command_snaps_and_revalidates():
    snap = build_seed(new_id())
    target = next(s for s in snap.spaces if s.name == "Kitchen")
    moved = apply_commands(snap, [{"type": "move_space", "element_id": target.id,
                                   "dx_m": 0.24, "dy_m": 0.0}])
    sp = next(s for s in moved.spaces if s.id == target.id)
    # 0.24 snapped to 0.2 on the 0.1 m planning grid (coords stored to 0.1 mm)
    assert abs((sp.polygon[0][0] - target.polygon[0][0]) - 0.2) < 1e-3
    assert moved.revision_number == snap.revision_number + 1
