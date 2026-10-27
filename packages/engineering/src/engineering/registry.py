"""Engineering method registry — spec E2. A method is verified_for_scope only
after its reference tests pass; implemented-but-unverified checks stay
not_evaluated."""
from __future__ import annotations

from pydantic import BaseModel

from domain.enums import MethodState

RHO_WATER_KG_M3 = 1000.0   # physical property input, documented basis (fresh water ~20C)
G_M_S2 = 9.80665           # standard gravity, exact defined value


class EngineeringMethod(BaseModel):
    id: str
    version: str = "0.1.0"
    discipline: str
    purpose: str
    method_state: MethodState = MethodState.RESEARCH_REQUIRED
    source: str
    exclusions: str = ""


METHODS: list[EngineeringMethod] = [
    EngineeringMethod(
        id="pool_quantities", discipline="pool",
        purpose="Water surface area, volume, mass, weight, hydrostatic pressure for a declared flat-bottom basin.",
        method_state=MethodState.IMPLEMENTED,
        source="Explicit physical definitions (rho, g as declared inputs); spec E7. Not a pool-shell design method.",
        exclusions="Sloped/complex basins, shell thickness, reinforcement, founding."),
    EngineeringMethod(
        id="area_schedule", discipline="architecture",
        purpose="Net space areas from canonical polygons vs program targets.",
        method_state=MethodState.IMPLEMENTED,
        source="Shapely planar area on canonical geometry; spec E4.",
        exclusions="Zoning floor area and code area definitions are separate quantities."),
    EngineeringMethod(
        id="pool_environment", discipline="pool",
        purpose="Evaporation / latent load / pool heat balance.",
        method_state=MethodState.RESEARCH_REQUIRED,
        source="ASHRAE indoor-pool guidance — exact method transcription still gated (spec E7/E16).",
        exclusions="No residential pool factor may be invented."),
    EngineeringMethod(
        id="beam_analysis", discipline="structure",
        purpose="Planar Euler-Bernoulli beam analysis (PyNiteFEA adapter) for declared support/load cases.",
        method_state=MethodState.VERIFIED_FOR_SCOPE,
        source="Spec E14 Fixtures A-C closed-form references; tests/test_m3_fixtures.py passes at rel_tol=1e-6.",
        exclusions="Prismatic linear-elastic beams only; no shear-deformation, nonlinear or code design checks."),
    EngineeringMethod(
        id="structural_frame_analysis", discipline="structure",
        purpose="Elastic frame analysis via PyNiteFEA adapter.",
        method_state=MethodState.IMPLEMENTED,
        source="Beam adapter verified (Fixtures A-C); whole-frame idealization not yet independently reviewed.",
        exclusions="Nonlinear/second-order behaviour, connections, diaphragms, lateral systems not covered."),
    EngineeringMethod(
        id="foundation_bearing_review", discipline="foundations",
        purpose="Reaction-based preliminary bearing scenario.",
        method_state=MethodState.IMPLEMENTED,
        source="Uniform average-pressure scenario over the footprint with an explicitly assumed allowable bearing input (spec E6).",
        exclusions="Settlement, uplift, reinforcement, excavation support; no geotechnical evidence in demo."),
    EngineeringMethod(
        id="services_inventories", discipline="hvac/plumbing/electrical/energy/drainage",
        purpose="Fixture/equipment inventories with transparent component quantities: envelope conduction U*A*dT, connected electrical load, fixture-flow sums, roof runoff scenario.",
        method_state=MethodState.IMPLEMENTED,
        source="Spec E8-E12 component definitions with explicitly assumed inputs; hand-checked in tests/test_m4_services.py.",
        exclusions="Code sizing (fixture units, demand factors, ampacity, ventilation rates, energy pathway, hydraulics) and pool latent/environment methods remain research_required."),
]


def get_method(method_id: str) -> EngineeringMethod | None:
    return next((m for m in METHODS if m.id == method_id), None)
