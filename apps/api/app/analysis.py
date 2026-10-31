"""Deterministic, revision-bound analysis composition; no provider calls."""
from __future__ import annotations

import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import engineering
import geometry.validate

from engineering.pool import pool_quantities
from engineering.registry import METHODS
from geometry.validate import area_schedule, validate_snapshot
from .database import now


def implementation_hash() -> str:
    files = [Path(__file__), Path(geometry.validate.__file__)]
    files.extend(sorted(Path(engineering.__file__).parent.glob("*.py")))
    return hashlib.sha256(b"".join(path.read_bytes() for path in files)).hexdigest()

def _compute_results(snap) -> list[dict]:
    results = []
    if snap.pool:
        q = pool_quantities(snap.pool.water_length_m, snap.pool.water_width_m, snap.pool.water_depth_m)
        results.append({"discipline": "pool", "method_id": "pool_quantities",
                        "method_state": "implemented", "execution_status": "completed",
                        "check_outcome": "not_evaluated", "freshness_status": "current",
                        "review_status": "unreviewed", "revision_id": snap.revision_id,
                        "input_bases": ["demonstration_assumption"], "quantities": q})
    results.append({"discipline": "architecture", "method_id": "area_schedule",
                    "method_state": "implemented", "execution_status": "completed",
                    "check_outcome": "not_evaluated", "freshness_status": "current",
                    "review_status": "unreviewed", "revision_id": snap.revision_id,
                    "input_bases": ["derived"], "schedule": area_schedule(snap),
                    "geometry_issues": validate_snapshot(snap)})
    # Structure + foundations: real solver output, checks stay not_evaluated
    # (implemented methods, unverified member/code checks — spec A6.3).
    try:
        from engineering.frame import build_villa_frame, foundation_bearing
        frame = build_villa_frame()
        results.append({"discipline": "structure", "method_id": "structural_frame_analysis",
                        "method_state": "implemented", "execution_status": "completed",
                        "check_outcome": "not_evaluated", "freshness_status": "current",
                        "review_status": "unreviewed", "revision_id": snap.revision_id,
                        "input_bases": ["demonstration_assumption"], "quantities": frame,
                        "issues": [{"code": "UNVERIFIED_SOURCE", "field": "member_design_checks",
                                    "message": "Elastic responses only; steel/timber member, connection and lateral checks require sourced methods."}]})
        bearing = foundation_bearing(frame["sum_base_reactions_n"], 18.0 * 15.5, 100_000.0)
        results.append({"discipline": "foundations", "method_id": "foundation_bearing_review",
                        "method_state": "implemented", "execution_status": "completed",
                        "check_outcome": "not_evaluated", "freshness_status": "current",
                        "review_status": "unreviewed", "revision_id": snap.revision_id,
                        "input_bases": ["demonstration_assumption"], "quantities": bearing,
                        "issues": [{"code": "MISSING_INPUT", "field": "geotechnical_design_basis",
                                    "message": "No project geotechnical basis; scenario uses an assumed 100 kPa allowable bearing."}]})
    except Exception as e:
        results.append({"discipline": "structure", "method_id": "structural_frame_analysis",                        "method_state": "implemented", "execution_status": "error",
                        "check_outcome": "not_evaluated", "freshness_status": "current",
                        "review_status": "unreviewed", "revision_id": snap.revision_id,
                        "input_bases": ["demonstration_assumption"],
                        "issues": [{"code": "UNSTABLE_MODEL", "message": f"frame analysis failed: {type(e).__name__}"}]})
    from engineering.services import build_inventories
    results.append({"discipline": "hvac/plumbing/electrical/energy/drainage",
                    "method_id": "services_inventories",
                    "method_state": "implemented", "execution_status": "completed",
                    "check_outcome": "not_evaluated", "freshness_status": "current",
                    "review_status": "unreviewed", "revision_id": snap.revision_id,
                    "input_bases": ["demonstration_assumption", "derived"],
                    "quantities": build_inventories(snap),
                    "issues": [{"code": "UNVERIFIED_SOURCE", "field": "code_sizing_methods",
                                "message": "Inventories and component quantities only; code sizing/ventilation/energy-pathway/hydraulic methods remain research_required."}]})
    return results



def compute_results(snapshot) -> list[dict]:
    results = _compute_results(snapshot)
    registry = {method.id: method for method in METHODS}
    engine_versions = {name: version(name) for name in ("nodesnap-engineering", "shapely", "PyniteFEA")}
    method_hash = implementation_hash()
    for result in results:
        method = registry[result["method_id"]]
        result.update({
            "project_id": snapshot.project_id,
            "revision_number": snapshot.revision_number,
            "input_hash": snapshot.content_hash,
            "method_version": method.version,
            "source": method.source,
            "exclusions": method.exclusions,
            "engine_versions": engine_versions,
            "implementation_hash": method_hash,
            "scenario_id": "demonstration_baseline",
            "created_at": now(),
        })
        if result["discipline"] in ("structure", "foundations"):
            result.setdefault("issues", []).append({
                "code": "OUTSIDE_METHOD_DOMAIN", "field": "model_coupling",
                "message": "Independent 18 × 15.5 m baseline gravity-frame scenario. Pool, facade and room changes do not alter its fixed loads or members; it is not a structural design of this revision.",
            })
        if result["discipline"] == "architecture" and getattr(snapshot, "architecture", None):
            result["architecture"] = snapshot.architecture.model_dump(mode="json")
        # Serialization is also a finite-number gate; reject NaN/Infinity before persistence.
        result["result_id"] = hashlib.sha256(json.dumps(result, sort_keys=True, allow_nan=False).encode()).hexdigest()
    return results


def with_freshness(results: list[dict], current_revision_id: str) -> list[dict]:
    current_implementation = implementation_hash()
    return [{**result, "freshness_status": "current" if result["revision_id"] == current_revision_id and result.get("implementation_hash") == current_implementation else "stale"} for result in results]
