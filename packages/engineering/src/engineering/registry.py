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
        id="structural_frame_analysis", discipline="structure",
        purpose="Elastic frame analysis via PyNiteFEA adapter.",
        method_state=MethodState.RESEARCH_REQUIRED,
        source="Fixtures A-C must pass before integration (spec E14).",
        exclusions="Nonlinear/second-order behaviour not covered by linear adapter."),
    EngineeringMethod(
        id="foundation_bearing_review", discipline="foundations",
        purpose="Reaction-based preliminary bearing scenario.",
        method_state=MethodState.RESEARCH_REQUIRED,
        source="Requires project geotechnical basis or explicit demo scenario (spec E6).",
        exclusions="Settlement, uplift, reinforcement, excavation support."),
]


def get_method(method_id: str) -> EngineeringMethod | None:
    return next((m for m in METHODS if m.id == method_id), None)
