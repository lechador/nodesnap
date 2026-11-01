"""Upstream failures are diagnosable without exposing credentials or brief data."""
import asyncio
import io
import json
import logging
import wave

import httpx
import pytest
from fastapi.testclient import TestClient

from app import meta


@pytest.fixture
def provider(monkeypatch, caplog):
    monkeypatch.setenv("META_API_KEY", "private-configured-test-key")
    monkeypatch.setenv("META_BASE_URL", meta.BASE)
    monkeypatch.setenv("META_REASONING_MODEL", "muse-wonder-1.0")
    monkeypatch.setenv("META_TRANSCRIPTION_MODEL", "muse-voice-transcribe-1.0")
    monkeypatch.setattr(meta, "_verified", {})
    caplog.set_level(logging.WARNING, logger=meta.__name__)
    client_class = httpx.AsyncClient

    def install(handler):
        monkeypatch.setattr(meta.httpx, "AsyncClient", lambda **kwargs: client_class(
            transport=httpx.MockTransport(handler), **kwargs))
    return install


def request():
    return asyncio.run(meta.response({"model": "muse-wonder-1.0", "input": "private homeowner brief"}))


def diagnostic(caplog):
    records = [record for record in caplog.records if record.name == meta.__name__]
    assert len(records) == 1
    return json.loads(records[0].getMessage().split(": ", 1)[1])


def models():
    return httpx.Response(200, json={"data": [{"id": "muse-wonder-1.0"}]})


def test_schema_http_error_logs_allowlisted_sanitized_details(provider, caplog):
    def handle(req):
        if req.url.path.endswith("/models"):
            return models()
        return httpx.Response(400, headers={"x-request-id": "provider-request-1"}, json={"error": {
            "code": "invalid_json_schema", "type": "invalid_request_error", "param": "text.format.schema",
            "message": "Invalid schema at properties.garage: private-configured-test-key\n"
                       "LLM_another_credential_0123456789 sk-anothersecret Bearer confidential-token "
                       "api_key=another-secret 0123456789abcdef0123456789abcdef " + "x" * 600,
            "request": "private homeowner brief", "authorization": "do-not-log",
        }, "input": "private homeowner brief"})
    provider(handle)
    result = request()
    assert result == {"execution_status": "error", "issue": {"code": "PROVIDER_ERROR", "message":
        "The Meta connection could not complete this request. Your design is preserved."}}
    logged = diagnostic(caplog)
    assert logged["stage"] == "responses"
    assert logged["http_status"] == 400
    assert logged["request_id"] == "provider-request-1"
    assert logged["provider_code"] == "invalid_json_schema"
    assert logged["provider_type"] == "invalid_request_error"
    assert logged["provider_param"] == "text.format.schema"
    assert logged["provider_message"].startswith("Invalid schema at properties.garage:")
    assert len(logged["provider_message"]) == 480
    for secret in ("private-configured-test-key", "LLM_another_credential_0123456789", "sk-anothersecret",
                   "confidential-token", "another-secret", "0123456789abcdef0123456789abcdef",
                   "private homeowner brief", "do-not-log"):
        assert secret not in caplog.text
        assert secret not in json.dumps(result)


def test_model_lookup_failure_identifies_stage_without_posting(provider, caplog):
    paths = []
    def handle(req):
        paths.append(req.url.path)
        return httpx.Response(403, headers={"x-request-id": "model-request-1"}, json={
            "error": {"code": "access_denied", "message": "Account cannot list models"}})
    provider(handle)
    assert request()["issue"]["code"] == "PROVIDER_ERROR"
    assert paths == ["/v1/models"]
    logged = diagnostic(caplog)
    assert logged["stage"] == "model_lookup"
    assert logged["http_status"] == 403
    assert logged["provider_code"] == "access_denied"


@pytest.mark.parametrize("error,code", [(httpx.ConnectError, "PROVIDER_ERROR"), (httpx.ReadTimeout, "PROVIDER_TIMEOUT")])
def test_network_exception_does_not_log_sensitive_exception_message(provider, caplog, error, code):
    def handle(req):
        if req.url.path.endswith("/models"):
            return models()
        raise error("private-configured-test-key private homeowner brief https://secret-url/", request=req)
    provider(handle)
    assert request()["issue"]["code"] == code
    assert diagnostic(caplog) == {"stage": "responses", "exception": error.__name__}
    assert "private" not in caplog.text
    assert "secret-url" not in caplog.text


@pytest.mark.parametrize("status", [200, 502])
def test_non_json_response_keeps_status_but_never_logs_raw_body(provider, caplog, status):
    def handle(req):
        if req.url.path.endswith("/models"):
            return models()
        return httpx.Response(status, text="<html>private homeowner brief private-configured-test-key</html>")
    provider(handle)
    assert request()["issue"]["code"] == "PROVIDER_ERROR"
    logged = diagnostic(caplog)
    assert logged["http_status"] == status
    assert logged["stage"] == "responses"
    assert "provider_message" not in logged
    assert "private" not in caplog.text


def test_nested_error_data_is_not_serialized(provider, caplog):
    def handle(req):
        if req.url.path.endswith("/models"):
            return models()
        return httpx.Response(400, json={"error": {"message": {"input": "private homeowner brief"},
            "code": ["private-configured-test-key"], "param": "Authorization: private-configured-test-key"}})
    provider(handle)
    assert request()["issue"]["code"] == "PROVIDER_ERROR"
    logged = diagnostic(caplog)
    assert "provider_message" not in logged
    assert "provider_code" not in logged
    assert "private" not in caplog.text


@pytest.mark.parametrize("kind", ["building_design", "conversation", "transcription"])
def test_billing_rejection_blocks_without_spend_and_preserves_prior_unknown_receipt(provider, tmp_path, kind):
    from app import budget, main
    from app.database import BudgetRow, MetaUsageRow

    calls = []
    def handle(req):
        if req.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "muse-wonder-1.0"}, {"id": "muse-voice-transcribe-1.0"}]})
        calls.append(req.url.path)
        return httpx.Response(402, json={"error": {"code": "billing_not_configured", "type": "billing_error",
            "message": "Private team needs billing attention: https://billing.example/private-team-id"}})
    provider(handle)
    application = main.create_app(f"sqlite:///{tmp_path / 'billing.db'}", tmp_path / "artifacts")
    factory = application.state.session_factory
    budget.reserve(factory, 250_000)
    budget.settle(factory, 250_000, "building_design", "muse-wonder-1.0", None)
    with factory() as db:
        old = db.query(MetaUsageRow).one()
        old_id, old_json = old.id, {column.name: getattr(old, column.name) for column in old.__table__.columns}
    with TestClient(application) as client:
        client.post("/api/v1/demo/sessions")
        headers = {"Idempotency-Key": "one-billing-rejection"}
        if kind == "building_design":
            path, kwargs = "/api/v1/designs", {"json": {"text": "Design a private house with a yard"}, "headers": headers}
        elif kind == "conversation":
            project = client.post("/api/v1/projects", json={"seed": True}).json()["data"]
            path = f"/api/v1/projects/{project['project_id']}/conversations"
            kwargs = {"json": {"text": "Add a yard", "base_revision_id": project["revision_id"]},
                      "headers": {**headers, "If-Match": project["revision_id"]}}
        else:
            recording = io.BytesIO()
            with wave.open(recording, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(b"\x00\x00" * 16000)
            path, kwargs = "/api/v1/transcriptions", {"files": {"audio": ("recording.wav", recording.getvalue(), "audio/wav")}}
        reply = client.post(path, **kwargs)
        assert reply.status_code == 200, reply.text
        result = reply.json()["data"]
        assert result["execution_status"] == "blocked"
        assert result["issue"]["code"] == "PROVIDER_BILLING_REQUIRED"
        assert "Meta account needs billing attention" in result["issue"]["message"]
        assert "direct edits and exports are still available" in result["issue"]["message"]
        for private in ("private-team-id", "billing.example", "billing_not_configured", "billing_error"):
            assert private not in reply.text
        if kind != "transcription":
            assert client.post(path, **kwargs).json()["data"] == result
        assert len(calls) == 1
        projects = client.get("/api/v1/projects").json()["data"]
        if kind == "conversation":
            assert len(projects) == 1
            assert projects[0]["revision_id"] == project["revision_id"]
        else:
            assert projects == []
    with factory() as db:
        balance = db.get(BudgetRow, "application")
        assert balance.reserved_microusd == 0
        assert balance.spent_microusd == 250_000
        old = db.get(MetaUsageRow, old_id)
        assert {column.name: getattr(old, column.name) for column in old.__table__.columns} == old_json
        receipt = db.query(MetaUsageRow).filter(MetaUsageRow.id != old_id).one()
        assert receipt.kind == f"{kind}_billing_rejected"
        assert receipt.est_cost_usd == "0.000000"
        assert receipt.input_tokens == receipt.output_tokens == receipt.audio_ms == 0
    application.state.engine.dispose()
