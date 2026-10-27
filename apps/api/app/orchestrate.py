"""Meta orchestration — spec A7/S6. Bounded controller: the model proposes a
small typed proposal; deterministic server code validates and commits it.
One model call per conversation in this stage (cap MAX_MODEL_TURNS_PER_JOB=8
applies to the job loop when it lands). No silent non-Meta fallback."""
from __future__ import annotations

import os
from typing import Optional

import httpx
from pydantic import BaseModel, Field

from .meta import meta_status

BASE = os.environ.get("META_BASE_URL", "https://api.meta.ai/v1")

PROPOSAL_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "intent": {"type": "string",
                   "enum": ["set_pool_dimensions", "regenerate_floor", "explain", "unsupported"]},
        "pool_length_m": {"type": ["number", "null"]},
        "pool_width_m": {"type": ["number", "null"]},
        "pool_depth_m": {"type": ["number", "null"]},
        "level": {"type": ["string", "null"], "enum": ["ground", "upper", None]},
        "room_name": {"type": ["string", "null"]},
        "room_target_area_ft2": {"type": ["number", "null"]},
        "explanation": {"type": "string"},
    },
    "required": ["intent", "pool_length_m", "pool_width_m", "pool_depth_m",
                 "level", "room_name", "room_target_area_ft2", "explanation"],
}

SYSTEM = (
    "You are NodeSnap's proposal translator. Convert the homeowner request into "
    "exactly one proposal object. Supported actions: set_pool_dimensions (pool "
    "water length/width/depth in metres), regenerate_floor (change one named "
    "room's target area in square feet on the ground or upper floor, which "
    "re-runs the layout solver), explain (answer a question, change nothing), "
    "unsupported (anything else). Fill only fields relevant to the intent; "
    "leave others null. Never invent dimensions the user did not state. "
    "If the user states a pool dimension in metres, that is always "
    "set_pool_dimensions, even if it equals the current value. "
    "The explanation must be one short plain sentence addressed to the "
    "homeowner describing the action; include no internal reasoning."
)


class Proposal(BaseModel):
    intent: str
    pool_length_m: Optional[float] = None
    pool_width_m: Optional[float] = None
    pool_depth_m: Optional[float] = None
    level: Optional[str] = None
    room_name: Optional[str] = None
    room_target_area_ft2: Optional[float] = None
    explanation: str = ""


async def propose(text: str, context: str) -> dict:
    st = meta_status()
    if not st["configured"]:
        return {"execution_status": "blocked", "issue": st["issue"], "proposal": None}
    payload = {
        "model": st["reasoning_model"],
        "input": f"{SYSTEM}\n\nCurrent project (bounded summary):\n{context}\n\nHomeowner request: {text}",
        "text": {"format": {"type": "json_schema", "name": "nodesnap_proposal",
                            "schema": PROPOSAL_SCHEMA, "strict": True}},
        "max_output_tokens": 3000,
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{BASE}/responses",
                headers={"Authorization": f"Bearer {os.environ['META_API_KEY']}",
                         "Content-Type": "application/json"},
                json=payload)
            r.raise_for_status()
            j = r.json()
    except Exception as e:  # transport/provider failure: explicit, no fallback
        return {"execution_status": "error", "proposal": None,
                "issue": {"code": "PROVIDER_ERROR", "message": f"Meta call failed: {type(e).__name__}"}}
    texts = []
    for item in j.get("output", []):
        for c in item.get("content", []):
            if c.get("text"):
                texts.append(c["text"])
    if not texts:
        return {"execution_status": "error", "proposal": None,
                "issue": {"code": "MALFORMED_OUTPUT",
                          "message": "Model returned no structured proposal text."},
                "usage": j.get("usage")}
    try:
        proposal = Proposal.model_validate_json("".join(texts))
    except Exception as e:
        return {"execution_status": "error", "proposal": None,
                "issue": {"code": "MALFORMED_OUTPUT", "message": f"Proposal failed schema validation: {e}"},
                "usage": j.get("usage")}
    return {"execution_status": "completed", "model": st["reasoning_model"],
            "proposal": proposal.model_dump(), "usage": j.get("usage"),
            "request_id": r.headers.get("x-request-id")}
