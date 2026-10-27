"""Meta Model API adapter — spec A7/S6. Server-side only, allowlisted models.
No silent non-Meta fallback. Without META_API_KEY this returns an explicit
blocked status; nothing is faked."""
from __future__ import annotations

import os

import httpx

BASE = os.environ.get("META_BASE_URL", "https://api.meta.ai/v1")
ALLOWED = {"muse-wonder-1.0", "muse-spark-1.3", "muse-voice-transcribe-1.0"}


def meta_status() -> dict:
    key = os.environ.get("META_API_KEY", "")
    return {
        "configured": bool(key),
        "base_url": BASE,
        "reasoning_model": os.environ.get("META_REASONING_MODEL", "muse-wonder-1.0"),
        "transcription_model": os.environ.get("META_TRANSCRIPTION_MODEL", "muse-voice-transcribe-1.0"),
        "execution_status": "blocked" if not key else "completed",
        "issue": None if key else {
            "code": "MISSING_INPUT", "field": "META_API_KEY",
            "message": "META_API_KEY is not configured; Meta calls are blocked, deterministic features remain available."},
    }


async def interpret_brief(text: str) -> dict:
    st = meta_status()
    if not st["configured"]:
        return {"execution_status": "blocked", "issue": st["issue"], "proposal": None}
    model = st["reasoning_model"]
    if model not in ALLOWED:
        return {"execution_status": "blocked", "proposal": None,
                "issue": {"code": "UNSUPPORTED", "field": "model",
                          "message": f"model {model} not in allowlist"}}
    # Responses API per spec A7.2; structured output validated server-side by caller.
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{BASE}/responses",
            headers={"Authorization": f"Bearer {os.environ['META_API_KEY']}",
                     "Content-Type": "application/json"},
            json={"model": model, "input": text,
                  "max_output_tokens": 800})
        r.raise_for_status()
        return {"execution_status": "completed", "model": model,
                "request_id": r.headers.get("x-request-id"), "raw": r.json()}
