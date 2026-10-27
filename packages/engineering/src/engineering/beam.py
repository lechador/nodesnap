"""PyNiteFEA beam adapter — spec E5/E14.

Planar (XZ) Euler-Bernoulli beams: prismatic, linear elastic, no self-weight
(material density 0), no shear deformation claim beyond the solver's own
formulation. Sign convention verified against fixtures: PyNite reports
sagging moment as negative My in this setup; the adapter returns the signed
value plus its magnitude, and reactions positive upward (+Z).
Instability or non-finite results raise AdapterError — never silently fixed
with fictitious restraints (spec E5).
"""
from __future__ import annotations

from Pynite import FEModel3D


class AdapterError(RuntimeError):
    pass


def solve_beam(length_m: float, E_pa: float, I_m4: float, *,
               support: str,  # "simply_supported" | "cantilever"
               dist_load_n_m: float = 0.0,
               point_loads: list[dict] | None = None) -> dict:  # [{x_m, force_n}] (force_n signed, -Z down)
    if length_m <= 0 or E_pa <= 0 or I_m4 <= 0:
        raise AdapterError("length, E and I must be positive finite values")
    point_loads = point_loads or []
    # nodes at supports, load points, and quarter points for deflection sampling
    xs = {0.0, length_m, length_m / 2}
    for pl in point_loads:
        if not (0 <= pl["x_m"] <= length_m):
            raise AdapterError("point load must lie within the span")
        xs.add(float(pl["x_m"]))
    xs = sorted(xs)
    m = FEModel3D()
    for i, x in enumerate(xs):
        m.add_node(f"N{i}", x, 0, 0)
    m.add_material("MAT", E_pa, E_pa / (2 * 1.3), 0.3, 0.0)  # rho=0: no self-weight
    m.add_section("SEC", A=0.01, Iy=I_m4, Iz=I_m4, J=1e-7)
    for i in range(len(xs) - 1):
        m.add_member(f"M{i}", f"N{i}", f"N{i+1}", "MAT", "SEC")
    if support == "simply_supported":
        m.def_support("N0", True, True, True, True, False, False)
        m.def_support(f"N{len(xs)-1}", False, True, True, True, False, False)
    elif support == "cantilever":
        m.def_support("N0", True, True, True, True, True, True)
    else:
        raise AdapterError(f"unsupported support condition: {support}")
    if dist_load_n_m:
        for i in range(len(xs) - 1):
            m.add_member_dist_load(f"M{i}", "Fz", dist_load_n_m, dist_load_n_m, case="Case 1")
    for pl in point_loads:
        i = xs.index(float(pl["x_m"]))
        # point load applied as a nodal load at the interior node
        m.add_node_load(f"N{i}", "FZ", pl["force_n"], case="Case 1")
    m.add_load_combo("Combo 1", {"Case 1": 1.0})
    try:
        m.analyze_linear(check_stability=True)
    except Exception as e:
        raise AdapterError(f"analysis failed (unstable or singular): {e}") from e

    def disp(x_target: float) -> float:
        i = min(range(len(xs)), key=lambda k: abs(xs[k] - x_target))
        if abs(xs[i] - x_target) > 1e-9:
            raise AdapterError("deflection sample point is not a node")
        return float(m.nodes[f"N{i}"].DZ["Combo 1"])

    reactions = {}
    for name in ("N0", f"N{len(xs)-1}"):
        node = m.nodes[name]
        reactions[name] = {"FZ_n": float(node.RxnFZ["Combo 1"]),
                           "MY_nm": float(node.RxnMY["Combo 1"]) if node.RxnMY else 0.0}
    max_abs_moment = 0.0
    for i in range(len(xs) - 1):
        arr = m.members[f"M{i}"].moment_array("My", n_points=21)
        max_abs_moment = max(max_abs_moment, float(abs(arr).max()))
    results = {
        "reactions": reactions,
        "max_abs_moment_nm": max_abs_moment,
        "midspan_deflection_m": disp(length_m / 2) if support == "simply_supported" else None,
        "tip_deflection_m": disp(length_m) if support == "cantilever" else None,
        "support_rotation_rad": float(m.nodes["N0"].RY["Combo 1"]),
        "tip_rotation_rad": float(m.nodes[f"N{len(xs)-1}"].RY["Combo 1"]) if support == "cantilever" else None,
        "sign_convention": "reactions +Z up; PyNite My negative in sagging (magnitudes compared in fixtures)",
        "solver": "PyniteFEA FEModel3D.analyze_linear",
    }
    for v in [results["max_abs_moment_nm"]] + [r["FZ_n"] for r in reactions.values()]:
        if v != v or v in (float("inf"), float("-inf")):
            raise AdapterError("non-finite solver result")
    return results
