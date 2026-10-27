"""Pool quantities — spec E7. Pure function, explicit physical inputs.
Physics only: this does not design the pool shell."""
from __future__ import annotations

from .registry import G_M_S2, RHO_WATER_KG_M3


def pool_quantities(water_length_m: float, water_width_m: float,
                    water_depth_m: float,
                    rho_kg_m3: float = RHO_WATER_KG_M3,
                    g_m_s2: float = G_M_S2) -> dict:
    for name, v in [("water_length_m", water_length_m),
                    ("water_width_m", water_width_m),
                    ("water_depth_m", water_depth_m)]:
        if not (v > 0) or v != v or v in (float("inf"), float("-inf")):
            raise ValueError(f"{name} must be a positive finite number")
    surface = water_length_m * water_width_m
    volume = surface * water_depth_m  # flat-bottom declared basin only
    mass = rho_kg_m3 * volume
    return {
        "method_id": "pool_quantities",
        "inputs": {"water_length_m": water_length_m, "water_width_m": water_width_m,
                   "water_depth_m": water_depth_m, "rho_water_kg_m3": rho_kg_m3,
                   "g_m_s2": g_m_s2},
        "surface_area_m2": surface,
        "volume_m3": volume,
        "mass_kg": mass,
        "weight_n": mass * g_m_s2,
        "max_hydrostatic_pressure_pa": rho_kg_m3 * g_m_s2 * water_depth_m,
        "unit_conventions": "SI; mass from rho*V, weight = mass*g, p = rho*g*depth",
    }
