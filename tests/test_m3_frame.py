"""M3 frame: equilibrium, load accounting, bearing scenario."""
from engineering.frame import build_villa_frame, foundation_bearing


def test_frame_equilibrium_and_load_total():
    out = build_villa_frame()
    # 18 x 15.5 m plate: floor 5000 Pa + roof 6000 Pa over 279 m2
    expected = 279.0 * (5000 + 6000)
    assert abs(out["total_applied_load_n"] - expected) < 1.0
    assert out["equilibrium_relative_residual"] < 1e-6
    assert abs(out["sum_base_reactions_n"] - expected) / expected < 1e-6
    assert out["max_floor_deflection_m"] > 0
    assert out["max_beam_abs_moment_nm"] > 0
    # interior columns carry more than corners under uniform gravity
    r = out["base_reactions_n"]
    assert r["(6.0,5.1667)"] > r["(0.0,0.0)"]


def test_span_change_changes_result():
    base = build_villa_frame(beam_I_m4=1.5e-5)
    stiffer = build_villa_frame(beam_I_m4=3.0e-5)
    assert stiffer["max_floor_deflection_m"] < base["max_floor_deflection_m"]


def test_bearing_scenario_math():
    b = foundation_bearing(3_069_000.0, 279.0, 100_000.0)
    assert abs(b["average_pressure_pa"] - 11000.0) < 1e-6
    assert abs(b["utilization"] - 0.11) < 1e-9
