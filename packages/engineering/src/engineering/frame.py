"""Baseline villa gravity frame — spec E5. Declared concept idealization:
regular steel gravity frame on an 18.0 x 15.5 m plate, columns at a 3x3-bay
grid, fixed bases at ground level, rigid beam-column joints (the adapter's
default member behaviour). Load inputs and section properties are explicit
demonstration assumptions passed in by the caller — they are NOT code
factors, selected members, or a qualified lateral system. No lateral,
seismic, connection, diaphragm or member-design check is claimed here.
"""
from __future__ import annotations

from Pynite import FEModel3D

GRID_X = [0.0, 6.0, 12.0, 18.0]
GRID_Y = [0.0, 5.1667, 10.3333, 15.5]
FLOOR_Z = [3.4, 6.8]  # upper floor diaphragm, roof
E_STEEL_PA = 200e9


def build_villa_frame(floor_load_pa: float = 5000.0,
                      roof_load_pa: float = 6000.0,
                      column_I_m4: float = 2.0e-5,
                      beam_I_m4: float = 1.5e-5) -> dict:
    """Gravity scenario only. Returns equilibrium-verified solver results."""
    m = FEModel3D()
    m.add_material("STEEL", E_STEEL_PA, E_STEEL_PA / (2 * 1.3), 0.3, 0.0)  # rho 0: self-weight excluded, tracked in ledger by caller
    m.add_section("COL", A=0.02, Iy=column_I_m4, Iz=column_I_m4, J=1e-5)
    m.add_section("BEAM", A=0.015, Iy=beam_I_m4, Iz=beam_I_m4, J=1e-5)

    def nid(x, y, z):
        return f"N_{x}_{y}_{z}"

    for z in [0.0] + FLOOR_Z:
        for x in GRID_X:
            for y in GRID_Y:
                m.add_node(nid(x, y, z), x, y, z)
    # columns
    zs = [0.0] + FLOOR_Z
    for x in GRID_X:
        for y in GRID_Y:
            for a, b in zip(zs[:-1], zs[1:]):
                m.add_member(f"C_{x}_{y}_{a}", nid(x, y, a), nid(x, y, b), "STEEL", "COL")
            m.def_support(nid(x, y, 0.0), True, True, True, True, True, True)
    # beams both directions at each elevated level + tributary line loads
    total_applied_n = 0.0
    bays_y = [GRID_Y[i + 1] - GRID_Y[i] for i in range(len(GRID_Y) - 1)]
    bays_x = [GRID_X[i + 1] - GRID_X[i] for i in range(len(GRID_X) - 1)]
    for li, z in enumerate(FLOOR_Z):
        load_pa = floor_load_pa if li == 0 else roof_load_pa
        # beams along X at each Y grid line: tributary width = half bays either side
        for j, y in enumerate(GRID_Y):
            trib = (bays_y[j - 1] / 2 if j > 0 else 0) + (bays_y[j] / 2 if j < len(bays_y) else 0)
            w = load_pa * trib  # N/m
            for i in range(len(GRID_X) - 1):
                name = f"BX_{z}_{y}_{i}"
                m.add_member(name, nid(GRID_X[i], y, z), nid(GRID_X[i + 1], y, z), "STEEL", "BEAM")
                m.add_member_dist_load(name, "Fz", -w, -w, case="G")
                total_applied_n += w * (GRID_X[i + 1] - GRID_X[i])
        # beams along Y at each X grid line (no area load: X-beams own the slab transfer, recorded to avoid double counting)
        for x in GRID_X:
            for j in range(len(GRID_Y) - 1):
                m.add_member(f"BY_{z}_{x}_{j}", nid(x, GRID_Y[j], z), nid(x, GRID_Y[j + 1], z), "STEEL", "BEAM")
    m.add_load_combo("Gravity (declared scenario)", {"G": 1.0})
    m.analyze_linear(check_stability=True)

    combo = "Gravity (declared scenario)"
    reaction_sum = 0.0
    base_reactions = {}
    for x in GRID_X:
        for y in GRID_Y:
            r = float(m.nodes[nid(x, y, 0.0)].RxnFZ[combo])
            base_reactions[f"({x},{y})"] = round(r, 2)
            reaction_sum += r
    max_disp = 0.0
    max_beam_moment = 0.0
    for name, mem in m.members.items():
        if name.startswith("BX_"):
            darr = mem.deflection_array("dz", n_points=11, combo_name=combo)
            if darr.ndim == 2:  # PyNite returns [x, deflection] rows
                darr = darr[1]
            max_disp = max(max_disp, float(abs(darr).max()))
            arr = mem.moment_array("My", n_points=11, combo_name=combo)
            max_beam_moment = max(max_beam_moment, float(abs(arr).max()))
    equilibrium_residual = abs(reaction_sum - total_applied_n) / total_applied_n if total_applied_n else 0.0
    return {
        "method_id": "structural_frame_analysis",
        "idealization": "3-bay x 3-bay steel gravity frame, fixed bases at z=0, rigid joints, "
                        "slab load transferred to X-beams by tributary width (Y-beams carry no area load)",
        "inputs": {"floor_load_pa": floor_load_pa, "roof_load_pa": roof_load_pa,
                   "column_I_m4": column_I_m4, "beam_I_m4": beam_I_m4,
                   "E_steel_pa": E_STEEL_PA, "input_basis": "demonstration_assumption",
                   "self_weight": "excluded (material density 0 in adapter); not double counted"},
        "total_applied_load_n": round(total_applied_n, 2),
        "sum_base_reactions_n": round(reaction_sum, 2),
        "equilibrium_relative_residual": equilibrium_residual,
        "base_reactions_n": base_reactions,
        "max_floor_deflection_m": max_disp,
        "max_beam_abs_moment_nm": round(max_beam_moment, 2),
    }


def foundation_bearing(total_reaction_n: float, footprint_area_m2: float,
                       assumed_allowable_bearing_pa: float) -> dict:
    """Reaction-based preliminary bearing scenario — spec E6. States its
    pressure assumption; does not imply settlement or reinforcement adequacy."""
    if footprint_area_m2 <= 0 or assumed_allowable_bearing_pa <= 0:
        raise ValueError("footprint area and allowable bearing must be positive")
    pressure = total_reaction_n / footprint_area_m2  # uniform-pressure assumption
    return {"method_id": "foundation_bearing_review",
            "pressure_assumption": "uniform average pressure = total base reaction / footprint area",
            "average_pressure_pa": pressure,
            "assumed_allowable_bearing_pa": assumed_allowable_bearing_pa,
            "utilization": pressure / assumed_allowable_bearing_pa,
            "input_basis": "demonstration_assumption",
            "exclusions": "settlement, uplift, sliding, overturning, punching, reinforcement, excavation"}
