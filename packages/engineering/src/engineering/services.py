"""Revision-bound services inventories and transparent component scenarios.

Geometry comes from the canonical architecture, never fixed template dimensions.
U-values, temperature difference, electrical allowances, equipment inputs and
rainfall remain explicit demonstration assumptions, not code or product values.
These components do not establish discipline completion or regulatory checks.
"""
from __future__ import annotations

import math

from shapely.geometry import Polygon
from shapely.ops import unary_union


def _finite(*values):
    if any(not math.isfinite(value) for value in values):
        raise ValueError("All quantities must be finite.")


def conduction_w(area_m2: float, u_w_m2k: float, delta_t_k: float) -> float:
    """Steady planar component Q = U*A*ΔT; negative ΔT retains its sign."""
    _finite(area_m2, u_w_m2k, delta_t_k)
    if area_m2 < 0 or u_w_m2k < 0:
        raise ValueError("Area and U must be non-negative.")
    return u_w_m2k * area_m2 * delta_t_k


def roof_runoff_l_s(area_m2: float, rainfall_mm_h: float, runoff_coefficient: float) -> float:
    """Q = C*i*A: 1 mm over 1 m² is 1 litre; divide hourly rate by 3600."""
    _finite(area_m2, rainfall_mm_h, runoff_coefficient)
    if area_m2 < 0 or rainfall_mm_h < 0 or not 0 <= runoff_coefficient <= 1:
        raise ValueError("Area/rainfall must be non-negative and runoff coefficient in [0, 1].")
    return runoff_coefficient * rainfall_mm_h * area_m2 / 3600.0


def electrical_totals(items: list[dict], voltage_v: float = 240.0) -> dict:
    """Single-phase unity-power-factor connected allowance, I=P/V; not sizing."""
    _finite(voltage_v)
    if voltage_v <= 0:
        raise ValueError("Declared voltage must be positive.")
    for item in items:
        _finite(item["power_w"], item.get("count", 1))
        if item["power_w"] < 0 or item.get("count", 1) < 0:
            raise ValueError("Power and equipment count must be non-negative.")
    total_w = sum(item["power_w"] * item.get("count", 1) for item in items)
    return {"items": items, "connected_load_w": total_w,
            "declared_voltage_v": voltage_v,
            "current_at_connected_load_a": total_w / voltage_v,
            "circuit_model": "Assumed single phase, 240 V and unity power factor; not a motor/appliance sizing calculation.",
            "demand_load_w": None,
            "note": "Connected allowances only; actual equipment input, power factor, demand factors, ampacity, protection and service sizing remain unresolved."}


def plumbing_totals(fixtures: list[dict]) -> dict:
    for fixture in fixtures:
        _finite(fixture["flow_l_min"], fixture.get("count", 1))
        if fixture["flow_l_min"] < 0 or fixture.get("count", 1) < 0:
            raise ValueError("Fixture flow and count must be non-negative.")
    return {"fixtures": fixtures,
            "sum_of_fixture_flows_l_min": sum(fixture["flow_l_min"] * fixture.get("count", 1) for fixture in fixtures),
            "note": "Arithmetic sum of declared fixture-flow assumptions; fixture-unit/simultaneity sizing is research_required."}


FIXTURES_PER_BATHROOM = [
    {"name": "WC", "flow_l_min": 6.0}, {"name": "Basin", "flow_l_min": 5.0},
    {"name": "Shower", "flow_l_min": 9.0},
]
EQUIPMENT = [
    {"name": "Pool circulation pump (assumed)", "power_w": 750, "count": 1},
    {"name": "Pool heater, electric (assumed input)", "power_w": 9000, "count": 1},
    {"name": "Heat-pump system (assumed input)", "power_w": 5000, "count": 1},
    {"name": "Electric water heating (assumed)", "power_w": 4500, "count": 1},
]
# Demonstration scenario inputs, retained separately from geometry-derived area.
THERMAL_INPUTS = {"opaque_wall_u_w_m2k": .30, "window_u_w_m2k": 1.60,
                  "door_u_w_m2k": 1.80, "roof_u_w_m2k": .20,
                  "basement_floor_u_w_m2k": .35, "delta_t_k": 22.0}
RAIN_INPUTS = {"rainfall_mm_h": 100.0, "runoff_coefficient": .95}


def _slab_region(slab):
    return Polygon(slab.polygon, holes=slab.holes)


def site_surface_quantities(snapshot) -> dict | None:
    """Measured concept-site areas; never legal lot, floor-area or setback checks.

    Gross yard includes the pool/deck reservation, while grass and deck subtract
    their canonical holes. The garage is a separate, unconditioned outbuilding.
    """
    layout = getattr(snapshot, "site_layout", None)
    if layout is None:
        return None
    def gross(surface):
        return Polygon(surface.polygon).area if surface else 0.0
    def net(surface):
        return Polygon(surface.polygon, holes=surface.holes).area if surface else 0.0
    garage = layout.garage
    return {
        "revision_id": snapshot.revision_id,
        "input_hash": snapshot.content_hash,
        "input_basis": "derived",
        "yard_gross_area_m2": gross(layout.yard),
        "yard_grass_area_m2": net(layout.yard),
        "garage_gross_floor_area_m2": gross(garage),
        "garage_clear_floor_area_m2": Polygon(garage.polygon).buffer(-garage.wall_thickness_m, join_style=2).area if garage else 0.0,
        "garage_roof_area_m2": gross(garage),
        "driveway_area_m2": net(layout.driveway),
        "pool_deck_area_m2": net(layout.pool_deck),
        "outdoor_pool_water_area_m2": snapshot.pool.water_length_m * snapshot.pool.water_width_m if snapshot.pool and getattr(snapshot.pool, "location", "indoor") == "outdoor" else 0.0,
        "area_basis": "Planar polygon area in metres; grass and deck subtract canonical holes. Garage clear floor is inside its wall faces, excluding door-reveal recesses. Garage is separate from house enclosed/conditioned area; outdoor surfaces are not enclosed floor area.",
        "note": "Concept geometry only. Synthetic context is not a surveyed boundary. Parcel fit, setbacks, garage structure/fire separation/ventilation, pool barriers and site drainage are not established.",
    }


def envelope_components(snapshot) -> tuple[dict, dict]:
    """Exposed wall areas and projected roof catchment from hosted geometry.

    This is a planar component ledger. Slab-edge thermal bridges, soil coupling,
    infiltration, solar and pool moisture remain explicitly outside its domain.
    Roof projections are unioned so the headhouse cover is not counted twice.
    """
    architecture = snapshot.architecture
    if not architecture:
        issue = {"code": "MISSING_INPUT", "field": "architecture", "message": "This historical revision predates architectural assemblies. Create a new coordinated revision to calculate envelope components."}
        return ({"execution_status": "blocked", "envelope_conduction": [], "total_conduction_w": None, "delta_t_k": THERMAL_INPUTS["delta_t_k"], "issues": [issue]},
                {"execution_status": "blocked", "roof_area_m2": None, "runoff_l_s": None, "issues": [issue]})
    levels = {level.id: level for level in snapshot.levels}
    reference = next((level.elevation_m for level in snapshot.levels if level.name == "ground"), None)
    if reference is None:
        raise ValueError("A declared local ground-level datum is required; actual site grade remains unknown.")
    openings = {}
    for opening in architecture.openings:
        openings.setdefault(opening.wall_id, []).append(opening)
    eligible_walls = [wall for wall in architecture.walls if wall.exterior and wall.role == "enclosure" and levels[wall.level_id].elevation_m >= reference]
    ledger = []
    totals = {"gross_wall_area_m2": 0.0, "opaque_wall_area_m2": 0.0, "window_area_m2": 0.0, "door_area_m2": 0.0, "unfilled_opening_area_m2": 0.0}
    for wall in eligible_walls:
        gross = math.dist(wall.start, wall.end) * wall.height_m
        grouped = {kind: sum(opening.width_m * opening.height_m for opening in openings.get(wall.id, []) if opening.kind == kind) for kind in ("window", "door", "passage")}
        net = gross - sum(grouped.values())
        if net < -1e-6:
            raise ValueError(f"Openings exceed host wall area: {wall.id}")
        ledger.append({"wall_id": wall.id, "level_id": wall.level_id, "gross_area_m2": gross,
                       "opaque_area_m2": max(0.0, net), "window_area_m2": grouped["window"],
                       "door_area_m2": grouped["door"], "unfilled_opening_area_m2": grouped["passage"]})
        for key, value in [("gross_wall_area_m2", gross), ("opaque_wall_area_m2", max(0.0, net)), ("window_area_m2", grouped["window"]), ("door_area_m2", grouped["door"]), ("unfilled_opening_area_m2", grouped["passage"])]:
            totals[key] += value
    roofs = [slab for slab in architecture.slabs if slab.kind == "roof"]
    roof_region = unary_union([_slab_region(slab) for slab in roofs])
    roof_area = roof_region.area
    terrace_region = unary_union([Polygon(space.polygon) for space in snapshot.spaces if space.use == "roof_terrace"]).intersection(roof_region)
    terrace_area = terrace_region.area
    ground_floors = [slab for slab in architecture.slabs if slab.kind == "floor"]
    lowest = min((levels[slab.level_id].elevation_m for slab in ground_floors), default=reference)
    basement_slabs = [slab for slab in ground_floors if levels[slab.level_id].elevation_m == lowest]
    basement_region = unary_union([_slab_region(slab) for slab in basement_slabs])
    definitions = [
        ("Opaque above-reference enclosure walls", totals["opaque_wall_area_m2"], "opaque_wall_u_w_m2k", [wall.id for wall in eligible_walls]),
        ("Glazing in above-reference enclosure walls", totals["window_area_m2"], "window_u_w_m2k", [opening.id for wall in eligible_walls for opening in openings.get(wall.id, []) if opening.kind == "window"]),
        ("Exterior door panels (assumed infill)", totals["door_area_m2"], "door_u_w_m2k", [opening.id for wall in eligible_walls for opening in openings.get(wall.id, []) if opening.kind == "door"]),
        ("Roof assembly projected exposed area", roof_area, "roof_u_w_m2k", [slab.id for slab in roofs]),
        ("Lowest floor, excluding pool/stair openings (simplified scenario)", basement_region.area, "basement_floor_u_w_m2k", [slab.id for slab in basement_slabs]),
    ]
    delta_t = THERMAL_INPUTS["delta_t_k"]
    envelope = [{"element": label, "area_m2": area, "u_w_m2k": THERMAL_INPUTS[key],
                 "heat_loss_w": conduction_w(area, THERMAL_INPUTS[key], delta_t), "object_ids": identifiers,
                 "area_input_basis": "derived", "u_input_basis": "demonstration_assumption",
                 "delta_t_input_basis": "demonstration_assumption", "revision_id": snapshot.revision_id}
                for label, area, key, identifiers in definitions]
    hvac = {"execution_status": "completed", "envelope_conduction": envelope, "delta_t_k": delta_t,
            "total_conduction_w": sum(row["heat_loss_w"] for row in envelope),
            "surface_ledger": ledger, "area_reconciliation": totals,
            "scenario_inputs": {**THERMAL_INPUTS, "input_basis": "demonstration_assumption"},
            "datum_basis": "Local ground level, not measured grade or a legal basement classification.",
            "note": "Planar U*A*ΔT scenario only. U-values and temperature difference are demonstration assumptions. Excludes below-grade walls/ground coupling, slab-edge bridges, unfilled openings, solar, infiltration, ventilation, latent and pool loads; not equipment sizing or energy compliance."}
    if totals["unfilled_opening_area_m2"] > 0:
        hvac["issues"] = [{"code": "MISSING_INPUT", "field": "exterior_opening_infill", "message": "Unfilled exterior passages are excluded from conduction. Infiltration and infill require design inputs."}]
    catchments = [{"zone": "occupied_terrace", "area_m2": terrace_area},
                  {"zone": "remaining_roof_and_headhouse", "area_m2": max(0.0, roof_area - terrace_area)}]
    layout = getattr(snapshot, "site_layout", None)
    garage = layout.garage if layout else None
    garage_roof_area = Polygon(garage.polygon).area if garage else 0.0
    if garage:
        catchments.append({"zone": "detached_garage_roof", "area_m2": garage_roof_area,
                           "object_ids": [garage.id]})
        hvac["excluded_site_buildings"] = [{"object_id": garage.id, "use": "garage", "conditioning": "unconditioned", "area_m2": garage_roof_area}]
        hvac["note"] += " Detached garage is unconditioned and excluded from this house-envelope allowance; its ventilation and services require separate design."
    for catchment in catchments:
        catchment.update({"runoff_l_s": roof_runoff_l_s(catchment["area_m2"], **RAIN_INPUTS), "input_basis": "derived", "revision_id": snapshot.revision_id})
    drainage = {"execution_status": "completed", "roof_area_m2": roof_area + garage_roof_area, "terrace_area_m2": terrace_area,
                "other_roof_area_m2": roof_area + garage_roof_area - terrace_area, "catchments": catchments,
                "roof_object_ids": [slab.id for slab in roofs] + ([garage.id] if garage else []),
                "rainfall_mm_h_assumed": RAIN_INPUTS["rainfall_mm_h"],
                "runoff_coefficient_assumed": RAIN_INPUTS["runoff_coefficient"],
                "runoff_l_s": sum(catchment["runoff_l_s"] for catchment in catchments),
                "area_basis": "Union of canonical roof slab projections, excluding unroofed openings; headhouse counted once. Occupied terrace is a subset, not added roof area.",
                "note": "Scenario rainfall and runoff coefficient only. No drain positions, falls, overflow, pipe/detention capacity or receiving-system connection is established."}
    if layout:
        drainage["house_roof_area_m2"] = roof_area
        drainage["garage_roof_area_m2"] = garage_roof_area
        drainage["area_basis"] += " Detached-garage roof is a separate nonoverlapping catchment."
        drainage["note"] += " Yard, paving and pool-deck runoff are excluded; their permeability, grading and drainage connections are unknown."
    return hvac, drainage


def build_inventories(snapshot) -> dict:
    bathrooms = [space for space in snapshot.spaces if space.use in ("bathroom", "changing")]
    kitchens = [space for space in snapshot.spaces if space.use == "kitchen"]
    fixtures = [{**fixture, "count": 1, "location": space.name, "space_id": space.id, "input_basis": "demonstration_assumption"}
                for space in bathrooms for fixture in FIXTURES_PER_BATHROOM]
    for kitchen in kitchens:
        fixtures.extend({"name": name, "flow_l_min": flow, "count": 1, "location": kitchen.name, "space_id": kitchen.id, "input_basis": "demonstration_assumption"} for name, flow in [("Kitchen sink", 8.0), ("Dishwasher", 6.0)])
    metrics = {metric.space_id: metric for metric in snapshot.architecture.space_metrics} if snapshot.architecture else {}
    lighting = [{"name": f"Lighting+receptacle allowance — {space.name} (assumed 12 W/m²)",
                 "power_w": 12.0 * metrics[space.id].net_area_m2, "count": 1,
                 "space_id": space.id, "clear_area_m2": metrics[space.id].net_area_m2,
                 "allowance_w_m2": 12.0, "area_input_basis": "derived", "input_basis": "demonstration_assumption"}
                for space in snapshot.spaces if space.classification == "principal" and space.id in metrics]
    equipment = [{**item, "input_basis": "demonstration_assumption", "selection_status": "unselected"} for item in EQUIPMENT if snapshot.pool or not item["name"].startswith("Pool")]
    electrical = electrical_totals(lighting + equipment)
    electrical["area_basis"] = "Canonical clear room areas; allowance applies only to modeled principal spaces, not a whole-house code demand calculation."
    if not metrics:
        electrical["issues"] = [{"code": "MISSING_INPUT", "field": "clear_room_areas", "message": "Only equipment allowances are counted; clear-area lighting awaits a coordinated architectural revision."}]
    hvac, drainage = envelope_components(snapshot)
    if snapshot.pool and getattr(snapshot.pool, "location", "indoor") == "outdoor":
        hvac["pool_environment"] = {
            "location": "outdoor", "method_state": "research_required",
            "execution_status": "blocked", "check_outcome": "not_evaluated",
            "indoor_dehumidification_applicable": False,
            "note": "Open-air pool: indoor dehumidification is not applicable. Outdoor evaporation/heat balance awaits sourced methods and project inputs.",
        }
    for component in (electrical, hvac, drainage):
        component["revision_id"] = snapshot.revision_id
        component["input_hash"] = snapshot.content_hash
    plumbing = {**plumbing_totals(fixtures), "revision_id": snapshot.revision_id, "input_hash": snapshot.content_hash}
    result = {"plumbing": plumbing, "electrical": electrical, "hvac_energy": hvac, "drainage": drainage,
            "revision_id": snapshot.revision_id, "input_hash": snapshot.content_hash,
            "input_basis": "demonstration_assumption", "input_bases": ["demonstration_assumption", "derived"]}
    site = site_surface_quantities(snapshot)
    if site is not None:
        result["site_features"] = site
        electrical["note"] += " Detached-garage and yard electrical services are excluded; no EV charger or landscape-lighting allowance is assumed. Listed pool equipment remains an explicit demonstration allowance."
    return result
