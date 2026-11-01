"""One bounded Meta-only HTTP adapter. No configurable arbitrary upstreams."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time

import httpx

BASE = "https://api.meta.ai/v1"
REASONING_MODELS = {"muse-wonder-1.0", "muse-spark-1.3"}
TRANSCRIPTION_MODELS = {"muse-voice-transcribe-1.0"}
ALLOWED = REASONING_MODELS | TRANSCRIPTION_MODELS
_verified: dict[str, tuple[float, set[str]]] = {}
_logger = logging.getLogger(__name__)


def _billing_rejection(exc: Exception) -> dict | None:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 402:
        return {"execution_status": "blocked", "issue": {"code": "PROVIDER_BILLING_REQUIRED", "message":
            "This studio's Meta account needs billing attention before AI design and voice can continue. "
            "Your existing buildings, direct edits and exports are still available."}}
    return None


def _safe_diagnostic(value, limit: int = 480) -> str | None:
    """Keep useful schema errors, without logging credentials or whole objects."""
    if not isinstance(value, (str, int, float)):
        return None
    text = str(value)
    key = os.environ.get("META_API_KEY", "")
    if key:
        text = text.replace(key, "[REDACTED]")
    text = re.sub(r"(?i)\b(?:bearer|basic)\s+\S+", "[REDACTED_AUTH]", text)
    text = re.sub(r"(?i)\b(?:api[_-]?key|authorization|access[_-]?token|secret|password|token)\b[\"']?\s*[:=]\s*[\"']?[^\s\"',;}]+", "[REDACTED_CREDENTIAL]", text)
    text = re.sub(r"\b(?:LLM_|sk-|gh[pousr]_)[A-Za-z0-9_-]+", "[REDACTED_KEY]", text)
    text = re.sub(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[REDACTED_TOKEN]", text)
    text = re.sub(r"\b[0-9a-fA-F]{32,}\b", "[REDACTED_TOKEN]", text)
    return " ".join(text.split())[:limit]


def _log_provider_failure(stage: str, exc: Exception, result: httpx.Response | None = None):
    """Server-only, allowlisted diagnostics; never log request data or headers."""
    upstream = exc.response if isinstance(exc, httpx.HTTPStatusError) else result
    diagnostic = {"stage": stage, "exception": type(exc).__name__}
    if upstream is not None:
        diagnostic["http_status"] = upstream.status_code
        diagnostic["request_id"] = _safe_diagnostic(upstream.headers.get("x-request-id"), 160)
        try:
            body = upstream.json()
        except ValueError:
            body = None
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            for field in ("code", "type", "param", "message"):
                value = _safe_diagnostic(error.get(field), 480 if field == "message" else 160)
                if value is not None:
                    diagnostic[f"provider_{field}"] = value
    # Exception text can contain URLs, request bodies or credentials. Do not log it.
    _logger.warning("Meta request failed: %s", json.dumps(diagnostic, ensure_ascii=True))


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
        if not isinstance(body, dict):
            raise ValueError("Invalid Meta model list envelope")
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
    stage = "model_lookup"
    result = None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=15), follow_redirects=False) as client:
            await verify_access(client, payload["model"])
            stage = "responses"
            result = await client.post(f"{BASE}/responses", headers=headers(), json=payload)
            result.raise_for_status()
            raw = result.json()
            if not isinstance(raw, dict):
                raise ValueError("Invalid Meta response envelope")
            return {"execution_status": "completed", "model": payload["model"], "request_id": result.headers.get("x-request-id"), "raw": raw, "usage": raw.get("usage")}
    except httpx.TimeoutException as exc:
        _log_provider_failure(stage, exc, result)
        return {"execution_status": "error", "issue": {"code": "PROVIDER_TIMEOUT", "message": "Meta took too long to respond. Your design has not changed; try again."}}
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        _log_provider_failure(stage, exc, result)
        if rejected := _billing_rejection(exc):
            return rejected
        return {"execution_status": "error", "issue": {"code": "PROVIDER_ERROR", "message": "The Meta connection could not complete this request. Your design is preserved."}}


async def transcribe(data: bytes) -> dict:
    status = meta_status()
    if not status["configured"]:
        return {"execution_status": "blocked", "issue": status["issue"], "text": None}
    files = {"request": (None, json.dumps({"model": status["transcription_model"], "audioEncoding": "WAV", "mode": "PUSH_TO_TALK"}), "application/json"), "audio": ("recording.wav", data, "audio/wav")}
    stage = "model_lookup"
    result = None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=15), follow_redirects=False) as client:
            await verify_access(client, status["transcription_model"])
            stage = "transcription"
            result = await client.post(f"{BASE}/asr/transcribe", headers=headers(), files=files)
            result.raise_for_status()
            raw = result.json()
            if not isinstance(raw, dict) or not isinstance(raw.get("transcript"), str):
                raise ValueError("Missing transcript")
            return {"execution_status": "completed", "model": status["transcription_model"], "text": raw["transcript"], "audio_duration_ms": raw.get("audioDurationMs"), "session_id": raw.get("sessionId")}
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        _log_provider_failure(stage, exc, result)
        if rejected := _billing_rejection(exc):
            return {**rejected, "text": None}
        return {"execution_status": "error", "text": None, "issue": {"code": "PROVIDER_ERROR", "message": "Transcription was unavailable. Type your request or record it again."}}
