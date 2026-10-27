"""Discipline inventories + transparent component calculations — spec E8-E12.

Every number here is either (a) counted from the canonical model, or
(b) computed from inputs explicitly labelled demonstration_assumption.
None of these is a code sizing method: fixture-unit demand, ventilation
rates, demand factors, ampacity, energy-code pathways and hydraulic sizing
remain research_required in the registry, and every check stays
not_evaluated.
"""
from __future__ import annotations


def conduction_w(area_m2: float, u_w_m2k: float, delta_t_k: float) -> float:
    """Steady conduction component Q = U*A*dT (spec E8). One component only."""
    if area_m2 < 0 or u_w_m2k < 0:
        raise ValueError("area and U must be non-negative")
    return u_w_m2k * area_m2 * delta_t_k


def roof_runoff_l_s(area_m2: float, rainfall_mm_h: float, runoff_coefficient: float) -> float:
    """Scenario runoff Q = C*i*A with the conversion stated: 1 mm over 1 m2
    = 1 litre, so L/s = C * (mm/h) * m2 / 3600 (spec E12)."""
    if not (0 <= runoff_coefficient <= 1):
        raise ValueError("runoff coefficient must be in [0, 1]")
    return runoff_coefficient * rainfall_mm_h * area_m2 / 3600.0


def electrical_totals(items: list[dict], voltage_v: float = 240.0) -> dict:
    """Connected-load ledger. Current uses the declared single-phase circuit
    model I = P/V; no demand factors are applied (spec E10)."""
    total_w = sum(i["power_w"] * i.get("count", 1) for i in items)
    return {"items": items, "connected_load_w": total_w,
            "declared_voltage_v": voltage_v,
            "current_at_connected_load_a": total_w / voltage_v,
            "demand_load_w": None,
            "note": "Connected load only; demand factors, ampacity, protection and service sizing are research_required."}


def plumbing_totals(fixtures: list[dict]) -> dict:
    total = sum(f["flow_l_min"] * f.get("count", 1) for f in fixtures)
    return {"fixtures": fixtures, "sum_of_fixture_flows_l_min": total,
            "note": "Arithmetic sum of declared fixture flows; fixture-unit/simultaneity sizing is research_required."}


# Declared demonstration inventories (inputs, not code values)
FIXTURES_PER_BATHROOM = [
    {"name": "WC", "flow_l_min": 6.0}, {"name": "Basin", "flow_l_min": 5.0},
    {"name": "Shower", "flow_l_min": 9.0},
]
EQUIPMENT = [  # electrical input power, explicitly assumed for the demo ledger
    {"name": "Pool circulation pump (assumed)", "power_w": 750, "count": 1},
    {"name": "Pool heater, electric (assumed input)", "power_w": 9000, "count": 1},
    {"name": "Heat-pump system (assumed input)", "power_w": 5000, "count": 1},
    {"name": "Electric water heating (assumed)", "power_w": 4500, "count": 1},
]


def build_inventories(snapshot) -> dict:
    from geometry.validate import polygon_area_m2
    bathrooms = [s for s in snapshot.spaces if s.use in ("bathroom", "changing")]
    kitchens = [s for s in snapshot.spaces if s.use == "kitchen"]
    fixtures: list[dict] = []
    for b in bathrooms:
        for f in FIXTURES_PER_BATHROOM:
            fixtures.append({**f, "count": 1, "location": b.name})
    for k in kitchens:
        fixtures.append({"name": "Kitchen sink", "flow_l_min": 8.0, "count": 1, "location": k.name})
        fixtures.append({"name": "Dishwasher", "flow_l_min": 6.0, "count": 1, "location": k.name})

    lighting = []
    for s in snapshot.spaces:
        if s.classification == "principal":
            lighting.append({"name": f"Lighting+receptacle allowance — {s.name} (assumed 12 W/m2)",
                             "power_w": round(12.0 * polygon_area_m2(s.polygon), 1), "count": 1})
    electrical = electrical_totals(lighting + [dict(e) for e in EQUIPMENT])

    # Envelope conduction ledger: declared assembly U-values + design dT (assumptions)
    wall_area = 2 * (18.0 + 15.5) * 6.8
    roof_area = 18.0 * 15.5
    envelope = [
        {"element": "Above-grade walls", "area_m2": round(wall_area, 2), "u_w_m2k": 0.30},
        {"element": "Roof", "area_m2": roof_area, "u_w_m2k": 0.20},
        {"element": "Ground/basement envelope (simplified)", "area_m2": roof_area, "u_w_m2k": 0.35},
    ]
    delta_t = 22.0  # K, declared winter design difference (assumption)
    for e in envelope:
        e["heat_loss_w"] = round(conduction_w(e["area_m2"], e["u_w_m2k"], delta_t), 1)
    envelope_total = round(sum(e["heat_loss_w"] for e in envelope), 1)

    runoff = roof_runoff_l_s(roof_area, rainfall_mm_h=100.0, runoff_coefficient=0.95)
    return {
        "plumbing": plumbing_totals(fixtures),
        "electrical": electrical,
        "hvac_energy": {"envelope_conduction": envelope, "delta_t_k": delta_t,
                        "total_conduction_w": envelope_total,
                        "note": "Conduction component only (U*A*dT with assumed U/dT); solar, infiltration, ventilation, latent and pool loads are separate gated methods."},
        "drainage": {"roof_area_m2": roof_area, "rainfall_mm_h_assumed": 100.0,
                     "runoff_coefficient_assumed": 0.95, "runoff_l_s": runoff,
                     "note": "Scenario quantity only; gutter/downpipe/detention/connection sizing is research_required."},
        "input_basis": "demonstration_assumption",
    }
