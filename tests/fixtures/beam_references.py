"""Independent closed-form references for Fixtures A-C — spec E14.
Euler-Bernoulli, prismatic, linear elasticity, no self-weight.
These formulas are the test oracle; they share no code with the adapter.
"""


def fixture_a(L=4.0, w=5000.0, E=200e9, I=8e-6):
    return {"reaction_n": w * L / 2, "max_moment_nm": w * L**2 / 8,
            "midspan_deflection_m": 5 * w * L**4 / (384 * E * I),
            "end_slope_rad": w * L**3 / (24 * E * I)}


def fixture_b(L=3.0, P=12000.0, E=200e9, I=6e-6):
    return {"reaction_n": P / 2, "max_moment_nm": P * L / 4,
            "midspan_deflection_m": P * L**3 / (48 * E * I)}


def fixture_c(L=2.0, P=1000.0, E=200e9, I=1e-5):
    return {"reaction_n": P, "fixed_moment_nm": P * L,
            "tip_deflection_m": P * L**3 / (3 * E * I),
            "tip_rotation_rad": P * L**2 / (2 * E * I)}
