"""Risk-based API acceptance: isolation, replay, races, exports and Meta boundary."""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import threading
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app import main
from app.database import BudgetRow, RevisionRow
from app.meta import meta_status
from app.orchestrate import Proposal


@pytest.fixture
def studio(tmp_path, monkeypatch):
    monkeypatch.delenv("META_API_KEY", raising=False)
    application = main.create_app(f"sqlite:///{tmp_path / 'studio.db'}", tmp_path / "artifacts")
    with TestClient(application) as client:
        client.post("/api/v1/demo/sessions")
        project = client.post("/api/v1/projects", json={"seed": True}).json()["data"]
        yield client, project, application
    application.state.engine.dispose()


def mutation_headers(revision, key=None):
    return {"If-Match": f'"{revision}"', "Idempotency-Key": key or str(uuid.uuid4())}


def pool_body(project, length=9, command_id=None):
    return {"base_revision_id": project["revision_id"], "commands": [{"type": "set_pool_dimensions", "water_length_m": length, "command_id": command_id or str(uuid.uuid4())}]}


def test_session_resume_and_private_project_list(studio):
    client, project, application = studio
    token = client.cookies.get("nodesnap_session")
    response = client.post("/api/v1/demo/sessions")
    assert response.json()["data"]["resumed"] is True
    assert client.cookies.get("nodesnap_session") == token
    assert client.get("/api/v1/projects").json()["data"][0]["project_id"] == project["project_id"]
    with TestClient(application) as other:
        other.post("/api/v1/demo/sessions")
        assert other.get("/api/v1/projects").json()["data"] == []
        assert other.get(f"/api/v1/projects/{project['project_id']}").status_code == 403


def test_idempotency_precedes_stale_check_and_rejects_changed_payload(studio):
    client, project, _ = studio
    path = f"/api/v1/projects/{project['project_id']}/commands"
    headers = mutation_headers(project["revision_id"], "pool-edit-1")
    payload = pool_body(project)
    first = client.post(path, json=payload, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["data"]["revision_number"] == 2
    repeat = client.post(path, json=payload, headers=headers)
    assert repeat.status_code == 200
    assert repeat.json()["data"] == first.json()["data"]
    payload["commands"][0]["water_length_m"] = 10
    assert client.post(path, json=payload, headers=headers).status_code == 409
    assert client.post(path, json=payload, headers=mutation_headers(project["revision_id"])).status_code == 412
    historic = client.get(f"/api/v1/projects/{project['project_id']}/revisions/{project['revision_id']}").json()["data"]
    assert historic["pool"]["water_length_m"] == 8


def test_command_id_cannot_be_applied_twice_under_new_request_key(studio):
    client, project, _ = studio
    path = f"/api/v1/projects/{project['project_id']}/commands"
    payload = pool_body(project)
    committed = client.post(path, json=payload, headers=mutation_headers(project["revision_id"])).json()["data"]
    payload["base_revision_id"] = committed["revision_id"]
    response = client.post(path, json=payload, headers=mutation_headers(committed["revision_id"]))
    assert response.status_code == 409


def test_mutations_require_agreeing_preconditions_and_nonempty_commands(studio):
    client, project, _ = studio
    path = f"/api/v1/projects/{project['project_id']}/commands"
    assert client.post(path, json=pool_body(project)).status_code == 428
    assert client.post(path, json=pool_body(project), headers=mutation_headers(str(uuid.uuid4()))).status_code == 422
    payload = {"base_revision_id": project["revision_id"], "commands": []}
    assert client.post(path, json=payload, headers=mutation_headers(project["revision_id"])).status_code == 422


def test_two_concurrent_edits_cannot_overwrite_the_head(studio):
    client, project, application = studio
    cookies = dict(client.cookies)
    barrier = threading.Barrier(2)
    def edit(length):
        with TestClient(application) as worker:
            worker.cookies.update(cookies)
            barrier.wait()
            return worker.post(f"/api/v1/projects/{project['project_id']}/commands", json=pool_body(project, length), headers=mutation_headers(project["revision_id"]))
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(edit, [9, 10]))
    assert sorted(response.status_code for response in responses) == [200, 412]
    history = client.get(f"/api/v1/projects/{project['project_id']}/revisions").json()["data"]
    assert len(history) == 2
    assert history[0]["revision_number"] == 2


def test_coverage_rejects_revision_from_other_project(studio):
    client, project, _ = studio
    response = client.get(f"/api/v1/projects/{project['project_id']}/coverage", params={"revision_id": str(uuid.uuid4())})
    assert response.status_code == 404


def test_export_hashes_are_actual_bytes_and_artifacts_are_owner_bound(studio):
    client, project, application = studio
    response = client.post(f"/api/v1/projects/{project['project_id']}/exports", json={"revision_id": project["revision_id"]})
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    pdf = client.get(f"/artifacts/{result['artifact_id']}")
    manifest = client.get(f"/artifacts/{result['manifest_artifact_id']}")
    model = client.get(f"/artifacts/{result['model_artifact_id']}")
    assert pdf.content.startswith(b"%PDF")
    assert pdf.headers["content-disposition"].startswith("inline;")
    assert model.headers["content-disposition"].startswith("attachment;")
    assert manifest.headers["content-disposition"].startswith("attachment;")
    assert hashlib.sha256(pdf.content).hexdigest() == result["file_sha256"]
    assert hashlib.sha256(model.content).hexdigest() == result["model_sha256"]
    assert hashlib.sha256(manifest.content).hexdigest() == result["manifest_sha256_stored_externally"]
    stored_manifest = manifest.json()
    assert "manifest_sha256_stored_externally" not in stored_manifest
    assert stored_manifest["revision_id"] == project["revision_id"]
    assert all(item["revision_id"] == project["revision_id"] for item in stored_manifest["results"])
    with TestClient(application) as other:
        other.post("/api/v1/demo/sessions")
        for identifier in [result['artifact_id'], result['model_artifact_id'], result['manifest_artifact_id']]:
            assert other.get(f"/artifacts/{identifier}").status_code == 403


def test_historical_analysis_is_stale_not_current(studio):
    client, project, _ = studio
    client.post(f"/api/v1/projects/{project['project_id']}/commands", json=pool_body(project), headers=mutation_headers(project["revision_id"]))
    response = client.post(f"/api/v1/projects/{project['project_id']}/analyses", json={"revision_id": project["revision_id"]})
    assert response.status_code == 200, response.text
    assert all(result["freshness_status"] == "stale" for result in response.json()["data"]["results"])


def test_missing_meta_is_persisted_as_blocked_without_fabricated_answer(studio):
    client, project, _ = studio
    path = f"/api/v1/projects/{project['project_id']}/conversations"
    response = client.post(path, json={"text": "Make the pool 10 metres long", "base_revision_id": project["revision_id"]}, headers=mutation_headers(project["revision_id"]))
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["execution_status"] == "blocked"
    assert result["committed_revision_id"] is None
    assert result["issue"]["code"] == "MISSING_INPUT"
    assert len(client.get(path).json()["data"]) == 1


def test_stale_model_proposal_cannot_overwrite_newer_direct_edit(studio, monkeypatch):
    client, project, application = studio
    monkeypatch.setenv("META_API_KEY", "synthetic-test-only")
    async def proposal(text, context):
        response = await asyncio.to_thread(client.post, f"/api/v1/projects/{project['project_id']}/commands", json=pool_body(project, 10), headers=mutation_headers(project["revision_id"]))
        assert response.status_code == 200
        return {"execution_status": "completed", "model": "muse-wonder-1.0", "usage": {"input_tokens": 100, "output_tokens": 20}, "proposal": Proposal(intent="set_pool_dimensions", pool_length_m=9, explanation="Resize the pool.").model_dump()}
    monkeypatch.setattr(main, "propose", proposal)
    response = client.post(f"/api/v1/projects/{project['project_id']}/conversations", json={"text": "Make pool 9m", "base_revision_id": project["revision_id"]}, headers=mutation_headers(project["revision_id"]))
    result = response.json()["data"]
    assert result["execution_status"] == "blocked"
    assert result["issue"]["code"] == "STALE_REVISION"
    current = client.get(f"/api/v1/projects/{project['project_id']}").json()["data"]
    snapshot = client.get(f"/api/v1/projects/{project['project_id']}/revisions/{current['revision_id']}").json()["data"]
    assert snapshot["pool"]["water_length_m"] == 10


def test_meta_configuration_rejects_foreign_provider_and_wrong_model(monkeypatch):
    monkeypatch.setenv("META_API_KEY", "synthetic-test-only")
    monkeypatch.setenv("META_BASE_URL", "https://untrusted.example/v1")
    assert meta_status()["configured"] is False
    monkeypatch.setenv("META_BASE_URL", "https://api.meta.ai/v1")
    monkeypatch.setenv("META_REASONING_MODEL", "muse-voice-transcribe-1.0")
    assert meta_status()["configured"] is False
    with pytest.raises(ValueError):
        Proposal(intent="delete_everything", explanation="No.")
    with pytest.raises(ValueError):
        Proposal(intent="set_pool_dimensions", pool_length_m=float("nan"), explanation="No.")


def test_concurrent_budget_reservations_stop_before_ceiling(studio, monkeypatch):
    _, _, application = studio
    monkeypatch.setenv("APP_SPEND_CEILING_USD", "0.15")
    from app import budget
    def reserve(_):
        try:
            budget.reserve(application.state.session_factory, 100_000)
            return True
        except main.HTTPException:
            return False
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(reserve, [1, 2])) == [False, True]
    with application.state.session_factory() as db:
        assert db.get(BudgetRow, "application").reserved_microusd == 100_000


def test_invalid_audio_rejected_before_provider_work(studio):
    client, project, _ = studio
    response = client.post(f"/api/v1/projects/{project['project_id']}/transcriptions", files={"audio": ("recording.wav", b"not wav", "audio/wav")})
    assert response.status_code == 422


def test_chat_commit_and_replay_share_one_persisted_revision(studio, monkeypatch):
    client, project, application = studio
    monkeypatch.setenv("META_API_KEY", "synthetic-test-only")
    calls = []
    async def proposal(text, context):
        calls.append(text)
        return {"execution_status": "completed", "model": "muse-wonder-1.0", "usage": {"input_tokens": 100, "output_tokens": 20}, "proposal": Proposal(intent="set_pool_dimensions", pool_length_m=9, explanation="Resize the pool.").model_dump()}
    monkeypatch.setattr(main, "propose", proposal)
    path = f"/api/v1/projects/{project['project_id']}/conversations"
    body = {"text": "Make pool 9 metres long", "base_revision_id": project["revision_id"]}
    headers = mutation_headers(project["revision_id"], "chat-once")
    first = client.post(path, json=body, headers=headers)
    assert first.status_code == 200, first.text
    result = first.json()["data"]
    assert result["committed_revision_number"] == 2
    assert "44.10 m³" in result["explanation"]
    replay = client.post(path, json=body, headers=headers)
    assert replay.json()["data"] == result
    assert len(calls) == 1
    assert len(client.get(path).json()["data"]) == 1
    with application.state.session_factory() as db:
        assert db.get(BudgetRow, "application").reserved_microusd == 0


def test_restore_creates_revision_without_rewriting_history(studio):
    client, project, _ = studio
    pid = project["project_id"]
    edited = client.post(f"/api/v1/projects/{pid}/commands", json=pool_body(project), headers=mutation_headers(project["revision_id"])).json()["data"]
    response = client.post(f"/api/v1/projects/{pid}/restore", json={"base_revision_id": edited["revision_id"], "target_revision_id": project["revision_id"]}, headers=mutation_headers(edited["revision_id"]))
    assert response.status_code == 200, response.text
    restored = response.json()["data"]
    assert restored["revision_number"] == 3
    current = client.get(f"/api/v1/projects/{pid}/revisions/{restored['revision_id']}").json()["data"]
    assert current["pool"]["water_length_m"] == 8
    assert current["parent_revision_id"] == edited["revision_id"]
    assert current["architecture"]["revision_id"] == restored["revision_id"]
    assert len(client.get(f"/api/v1/projects/{pid}/revisions").json()["data"]) == 3


def test_nonfinite_nested_command_is_a_validation_error(studio):
    client, project, _ = studio
    body = pool_body(project, float("nan"))
    response = client.post(f"/api/v1/projects/{project['project_id']}/commands", content=json.dumps(body), headers={**mutation_headers(project["revision_id"]), "Content-Type": "application/json"})
    assert response.status_code == 422


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_cross_origin_browser_mutations_are_rejected_before_routes(studio, method):
    client, project, _ = studio
    path = f"/api/v1/projects/{project['project_id']}/commands"
    response = client.request(method, path, json=pool_body(project), headers={**mutation_headers(project["revision_id"]), "Origin": "https://hostile.example", "Sec-Fetch-Site": "cross-site"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORIGIN_REJECTED"
    assert response.headers["x-request-id"] == response.json()["request_id"]
    assert client.get(f"/api/v1/projects/{project['project_id']}").json()["data"]["revision_id"] == project["revision_id"]


def test_same_origin_browser_edit_and_origin_absent_cli_are_allowed(studio):
    client, project, _ = studio
    response = client.post(f"/api/v1/projects/{project['project_id']}/commands", json=pool_body(project), headers={**mutation_headers(project["revision_id"]), "Origin": "http://testserver:80", "Sec-Fetch-Site": "same-origin"})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["revision_number"] == 2
    assert client.post("/api/v1/demo/sessions").status_code == 200


@pytest.mark.parametrize("origin", ["null", "", "https://testserver", "http://testserver:3000", "http://testserver/", "http://testserver?", "http://testserver#", "http://user@testserver", "http://testserver:", "http://testserver:0", "http://testserver:99999", "http://testserver, https://hostile.example", "https://hostile.example"])
def test_null_malformed_or_different_origin_is_rejected(studio, origin):
    client, _, _ = studio
    response = client.post("/api/v1/demo/sessions", headers={"Origin": origin})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORIGIN_REJECTED"


def test_multiple_origin_headers_and_cross_site_without_origin_are_rejected(studio):
    client, _, _ = studio
    duplicate = client.post("/api/v1/demo/sessions", headers=[("Origin", "http://testserver"), ("Origin", "https://hostile.example")])
    assert duplicate.status_code == 403
    assert client.post("/api/v1/demo/sessions", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403


def test_private_next_proxy_accepts_public_https_origin(studio):
    client, project, application = studio
    token = client.cookies.get("nodesnap_session")
    with TestClient(application, base_url="http://api:8000", client=("172.22.0.10", 40000)) as proxy:
        response = proxy.post(f"/api/v1/projects/{project['project_id']}/commands", json=pool_body(project), headers={
            **mutation_headers(project["revision_id"]), "Cookie": f"nodesnap_session={token}",
            "Origin": "https://nodesnap.tech", "X-Forwarded-Host": "nodesnap.tech",
            "X-Forwarded-Proto": "https", "Sec-Fetch-Site": "same-origin",
        })
        assert response.status_code == 200, response.text
        assert response.json()["data"]["revision_number"] == 2


def test_loopback_next_proxy_accepts_local_frontend_port(studio):
    _, _, application = studio
    with TestClient(application, base_url="http://localhost:8000", client=("127.0.0.1", 40000)) as proxy:
        response = proxy.post("/api/v1/demo/sessions", headers={"Origin": "http://localhost:3000", "X-Forwarded-Host": "localhost:3000", "X-Forwarded-Proto": "http", "Sec-Fetch-Site": "same-origin"})
        assert response.status_code == 200, response.text


def test_public_peer_cannot_supply_trusted_forwarded_host(studio):
    _, _, application = studio
    with TestClient(application, base_url="http://api:8000", client=("8.8.8.8", 40000)) as direct:
        response = direct.post("/api/v1/demo/sessions", headers={"Origin": "https://hostile.example", "X-Forwarded-Host": "hostile.example", "X-Forwarded-Proto": "https"})
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "ORIGIN_REJECTED"
