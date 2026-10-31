"""One bounded Meta-only HTTP adapter. No configurable arbitrary upstreams."""
from __future__ import annotations

import hashlib
import json
import os
import time

import httpx

BASE = "https://api.meta.ai/v1"
REASONING_MODELS = {"muse-wonder-1.0", "muse-spark-1.3"}
TRANSCRIPTION_MODELS = {"muse-voice-transcribe-1.0"}
ALLOWED = REASONING_MODELS | TRANSCRIPTION_MODELS
_verified: dict[str, tuple[float, set[str]]] = {}


def meta_status() -> dict:
    base = os.environ.get("META_BASE_URL", BASE).rstrip("/")
    reasoning = os.environ.get("META_REASONING_MODEL", "muse-wonder-1.0")
    transcription = os.environ.get("META_TRANSCRIPTION_MODEL", "muse-voice-transcribe-1.0")
    issue = None
    if base != BASE:
        issue = {"code": "UNSUPPORTED", "field": "META_BASE_URL", "message": "NodeSnap only permits the official Meta Model API endpoint."}
    elif reasoning not in REASONING_MODELS or transcription not in TRANSCRIPTION_MODELS:
        issue = {"code": "UNSUPPORTED", "field": "model", "message": "Select a verified Meta reasoning/transcription model in server configuration."}
    elif not os.environ.get("META_API_KEY", "").strip():
        issue = {"code": "MISSING_INPUT", "field": "META_API_KEY", "message": "Chat needs the server's Meta connection. You can still explore the villa, edit dimensions, run calculations and export drawings."}
    return {"configured": issue is None, "base_url": BASE, "reasoning_model": reasoning,
            "transcription_model": transcription, "execution_status": "blocked" if issue else "completed", "issue": issue}


def headers():
    return {"Authorization": f"Bearer {os.environ['META_API_KEY']}", "Accept": "application/json"}


async def verify_access(client: httpx.AsyncClient, model: str):
    key_id = hashlib.sha256(os.environ.get("META_API_KEY", "").encode()).hexdigest()
    cached = _verified.get(key_id)
    if cached is None or time.monotonic() - cached[0] > 600:
        response = await client.get(f"{BASE}/models", headers=headers())
        response.raise_for_status()
        body = response.json()
        models = {item["id"] for item in body.get("data", body.get("models", [])) if isinstance(item, dict) and "id" in item}
        _verified[key_id] = (time.monotonic(), models)
    if model not in _verified[key_id][1]:
        raise ValueError("The configured Meta model is not available to this account.")


async def response(payload: dict) -> dict:
    status = meta_status()
    if not status["configured"]:
        return {"execution_status": "blocked", "issue": status["issue"]}
    if payload.get("model") not in REASONING_MODELS:
        return {"execution_status": "blocked", "issue": {"code": "UNSUPPORTED", "message": "This reasoning model is not permitted."}}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=15), follow_redirects=False) as client:
            await verify_access(client, payload["model"])
            result = await client.post(f"{BASE}/responses", headers=headers(), json=payload)
            result.raise_for_status()
            raw = result.json()
            if not isinstance(raw, dict):
                raise ValueError("Invalid Meta response envelope")
            return {"execution_status": "completed", "model": payload["model"], "request_id": result.headers.get("x-request-id"), "raw": raw, "usage": raw.get("usage")}
    except httpx.TimeoutException:
        return {"execution_status": "error", "issue": {"code": "PROVIDER_TIMEOUT", "message": "Meta took too long to respond. Your design has not changed; try again."}}
    except (httpx.HTTPError, ValueError, KeyError):
        return {"execution_status": "error", "issue": {"code": "PROVIDER_ERROR", "message": "The Meta connection could not complete this request. Your design is preserved."}}


async def transcribe(data: bytes) -> dict:
    status = meta_status()
    if not status["configured"]:
        return {"execution_status": "blocked", "issue": status["issue"], "text": None}
    files = {"request": (None, json.dumps({"model": status["transcription_model"], "audioEncoding": "WAV", "mode": "PUSH_TO_TALK"}), "application/json"), "audio": ("recording.wav", data, "audio/wav")}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=15), follow_redirects=False) as client:
            await verify_access(client, status["transcription_model"])
            result = await client.post(f"{BASE}/asr/transcribe", headers=headers(), files=files)
            result.raise_for_status()
            raw = result.json()
            if not isinstance(raw.get("transcript"), str):
                raise ValueError("Missing transcript")
            return {"execution_status": "completed", "model": status["transcription_model"], "text": raw["transcript"], "audio_duration_ms": raw.get("audioDurationMs"), "session_id": raw.get("sessionId")}
    except (httpx.HTTPError, ValueError, KeyError):
        return {"execution_status": "error", "text": None, "issue": {"code": "PROVIDER_ERROR", "message": "Transcription was unavailable. Type your request or record it again."}}
