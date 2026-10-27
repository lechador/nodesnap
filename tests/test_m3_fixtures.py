"""Fixture verification of the PyNite adapter — spec E14 tolerances:
rel_tol=1e-6; displacement abs_tol=1e-9 m; rotation 1e-9 rad; force/moment 1e-4."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))

import pytest
from beam_references import fixture_a, fixture_b, fixture_c

from engineering.beam import AdapterError, solve_beam

REL = 1e-6


def close(actual, expected, abs_tol):
    assert abs(actual - expected) <= abs_tol + REL * abs(expected), \
        f"{actual} != {expected}"


def test_fixture_a_simply_supported_udl():
    ref = fixture_a()
    out = solve_beam(4.0, 200e9, 8e-6, support="simply_supported", dist_load_n_m=-5000.0)
    close(out["reactions"]["N0"]["FZ_n"], ref["reaction_n"], 1e-4)
    close(out["reactions"]["N2"]["FZ_n"], ref["reaction_n"], 1e-4)
    close(out["max_abs_moment_nm"], ref["max_moment_nm"], 1e-4)
    close(abs(out["midspan_deflection_m"]), ref["midspan_deflection_m"], 1e-9)
    close(abs(out["support_rotation_rad"]), ref["end_slope_rad"], 1e-9)


def test_fixture_b_midpoint_point_load():
    ref = fixture_b()
    out = solve_beam(3.0, 200e9, 6e-6, support="simply_supported",
                     point_loads=[{"x_m": 1.5, "force_n": -12000.0}])
    close(out["reactions"]["N0"]["FZ_n"], ref["reaction_n"], 1e-4)
    close(out["max_abs_moment_nm"], ref["max_moment_nm"], 1e-4)
    close(abs(out["midspan_deflection_m"]), ref["midspan_deflection_m"], 1e-9)


def test_fixture_c_cantilever_tip_load():
    ref = fixture_c()
    out = solve_beam(2.0, 200e9, 1e-5, support="cantilever",
                     point_loads=[{"x_m": 2.0, "force_n": -1000.0}])
    close(abs(out["tip_deflection_m"]), ref["tip_deflection_m"], 1e-9)
    close(abs(out["reactions"]["N0"]["FZ_n"]), ref["reaction_n"], 1e-4)
    close(abs(out["reactions"]["N0"]["MY_nm"]), ref["fixed_moment_nm"], 1e-4)
    close(abs(out["tip_rotation_rad"]), ref["tip_rotation_rad"], 1e-9)


def test_linear_scaling_and_sign_reversal():
    a = solve_beam(4.0, 200e9, 8e-6, support="simply_supported", dist_load_n_m=-5000.0)
    b = solve_beam(4.0, 200e9, 8e-6, support="simply_supported", dist_load_n_m=-10000.0)
    close(b["midspan_deflection_m"], 2 * a["midspan_deflection_m"], 1e-9)
    c = solve_beam(4.0, 400e9, 8e-6, support="simply_supported", dist_load_n_m=-5000.0)
    close(c["midspan_deflection_m"], a["midspan_deflection_m"] / 2, 1e-9)
    d = solve_beam(4.0, 200e9, 8e-6, support="simply_supported", dist_load_n_m=5000.0)
    close(d["midspan_deflection_m"], -a["midspan_deflection_m"], 1e-9)


def test_invalid_inputs_rejected():
    with pytest.raises(AdapterError):
        solve_beam(4.0, -200e9, 8e-6, support="simply_supported", dist_load_n_m=-5000.0)
    with pytest.raises(AdapterError):
        solve_beam(4.0, 200e9, 8e-6, support="floating", dist_load_n_m=-5000.0)
