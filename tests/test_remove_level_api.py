"""Removing a storey preserves real geometry, revision history and export identity."""
from __future__ import annotations

import asyncio
import json
import uuid

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app import main, orchestrate
from app.database import CommandReceiptRow
from app.orchestrate import Proposal
from domain.models import ProjectSnapshot
from geometry.validate import validate_snapshot


@pytest.fixture
def studio(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "meta_status", lambda: {"configured": True, "reasoning_model": "muse-wonder-1.0"})
    application = main.create_app(f"sqlite:///{tmp_path / 'studio.db'}", tmp_path / "artifacts")
    with TestClient(application) as client:
        client.post("/api/v1/demo/sessions")
        project = client.post("/api/v1/projects", json={"seed": True}).json()["data"]
        yield client, project, application
    application.state.engine.dispose()


def headers(revision_id, key=None):
    return {"If-Match": f'"{revision_id}"', "Idempotency-Key": key or str(uuid.uuid4())}


def snapshot(client, pid, rid):
    response = client.get(f"/api/v1/projects/{pid}/revisions/{rid}")
    assert response.status_code == 200, response.text
    return ProjectSnapshot.model_validate(response.json()["data"])


def add(client, pid, rid):
    response = client.post(f"/api/v1/projects/{pid}/commands", json={"base_revision_id": rid,
        "commands": [{"type": "add_level", "command_id": str(uuid.uuid4())}]}, headers=headers(rid))
    assert response.status_code == 200, response.text
    return response.json()["data"]["revision_id"]


def mock_proposal(monkeypatch, intent="remove_level", level=None, contexts=None):
    async def propose(text, context):
        if contexts is not None:
            contexts.append(json.loads(context))
        return {"execution_status": "completed", "model": "muse-wonder-1.0",
                "usage": {"input_tokens": 100, "output_tokens": 20},
                "proposal": Proposal(intent=intent, level=level, explanation="Update the requested floor.").model_dump()}
    monkeypatch.setattr(main, "propose", propose)


def chat(client, pid, rid, key=None, text="remove last level"):
    response = client.post(f"/api/v1/projects/{pid}/conversations", json={"text": text,
        "base_revision_id": rid}, headers=headers(rid, key))
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_remove_last_level_commits_once_and_preserves_history(studio, monkeypatch):
    client, project, application = studio
    pid = project["project_id"]
    initial = snapshot(client, pid, project["revision_id"])
    added_id = add(client, pid, initial.revision_id)
    added = snapshot(client, pid, added_id)
    removed_level = next(level for level in added.levels if level.name == "level_3")
    removed_space_ids = {space.id for space in added.spaces if space.level_id == removed_level.id}
    client.post(f"/api/v1/projects/{pid}/analyses", json={"revision_id": added_id})
    contexts = []
    mock_proposal(monkeypatch, contexts=contexts)
    result = chat(client, pid, added_id, key="remove-once")
    assert result["execution_status"] == "completed"
    assert result["committed_revision_number"] == 3
    assert "Removed Level 3" in result["explanation"]
    assert "Lowered the roof and terrace by 3.4 m" in result["explanation"]
    assert {"architecture", "structure", "documents"} <= set(result["invalidated_result_groups"])
    current = snapshot(client, pid, result["committed_revision_id"])
    assert current.levels == initial.levels
    assert current.spaces == initial.spaces
    assert current.brief.floors_above_ground == 2
    assert len(current.architecture.stairs) == 3
    assert validate_snapshot(current) == []
    assert removed_space_ids.isdisjoint(space.id for space in current.spaces)
    assert current.parent_revision_id == added_id
    assert snapshot(client, pid, added_id) == added
    assert snapshot(client, pid, initial.revision_id) == initial
    assert chat(client, pid, added_id, key="remove-once") == result
    assert len(contexts) == 1
    assert contexts[0]["removable_levels"] == ["upper", "level_3"]
    assert contexts[0]["has_prior_revision"] is True
    assert len(client.get(f"/api/v1/projects/{pid}/revisions").json()["data"]) == 3
    results = client.get(f"/api/v1/projects/{pid}/analyses", params={"revision_id": added_id}).json()["data"]["results"]
    assert all(row["freshness_status"] == "stale" for row in results)
    with application.state.session_factory() as db:
        assert db.query(CommandReceiptRow).count() == 2


def test_remove_named_middle_level_moves_survivors_without_renaming_them(studio, monkeypatch):
    client, project, _ = studio
    pid = project["project_id"]
    first = add(client, pid, project["revision_id"])
    second = add(client, pid, first)
    prior = snapshot(client, pid, second)
    upper = next(level for level in prior.levels if level.name == "upper")
    mock_proposal(monkeypatch, level="upper")
    result = chat(client, pid, second, text="remove the upper floor")
    assert result["execution_status"] == "completed"
    current = snapshot(client, pid, result["committed_revision_id"])
    assert current.brief.floors_above_ground == 3
    assert all(level.id != upper.id for level in current.levels)
    for level in prior.levels:
        if level.id == upper.id:
            continue
        survivor = next(item for item in current.levels if item.id == level.id)
        assert survivor.name == level.name
        assert survivor.elevation_m == pytest.approx(level.elevation_m - (3.4 if level.elevation_m > upper.elevation_m else 0))
    assert validate_snapshot(current) == []
    contexts = []
    mock_proposal(monkeypatch, intent="explain", contexts=contexts)
    chat(client, pid, current.revision_id, text="Which floors remain?")
    assert contexts[0]["living_floor_order"] == ["ground", "level_3", "level_4"]
    assert contexts[0]["removable_levels"] == ["level_3", "level_4"]
    assert contexts[0]["living_floor_count"] == 3
    assert contexts[0]["bedroom_count"] == 9


@pytest.mark.parametrize("level_name", ["ground", "basement", "roof", "level_99"])
def test_protected_or_unknown_level_removal_is_atomic(studio, monkeypatch, level_name):
    client, project, application = studio
    mock_proposal(monkeypatch, level=level_name)
    result = chat(client, project["project_id"], project["revision_id"], key="rejected-remove")
    assert result["execution_status"] == "blocked"
    assert result["issue"]["code"] == "DOMAIN_VALIDATION"
    assert result["committed_revision_id"] is None
    assert chat(client, project["project_id"], project["revision_id"], key="rejected-remove") == result
    assert client.get(f"/api/v1/projects/{project['project_id']}").json()["data"]["revision_id"] == project["revision_id"]
    assert len(client.get(f"/api/v1/projects/{project['project_id']}/revisions").json()["data"]) == 1
    with application.state.session_factory() as db:
        assert db.query(CommandReceiptRow).count() == 0


def test_removal_stops_at_ground_and_removed_floor_cannot_be_regenerated(studio, monkeypatch):
    client, project, _ = studio
    pid = project["project_id"]
    mock_proposal(monkeypatch)
    removed = chat(client, pid, project["revision_id"])
    current = snapshot(client, pid, removed["committed_revision_id"])
    assert current.brief.floors_above_ground == 1
    assert len(current.architecture.stairs) == 2
    assert validate_snapshot(current) == []
    second = chat(client, pid, current.revision_id)
    assert second["execution_status"] == "blocked"
    assert second["committed_revision_id"] is None
    mock_proposal(monkeypatch, intent="regenerate_floor", level="upper")
    replan = chat(client, pid, current.revision_id, text="regenerate the upper floor")
    assert replan["execution_status"] == "blocked"
    assert "does not exist" in replan["issue"]["message"]
    assert len(client.get(f"/api/v1/projects/{pid}/revisions").json()["data"]) == 2


def test_restore_after_removal_recovers_exact_level_and_space_ids(studio, monkeypatch):
    client, project, _ = studio
    pid = project["project_id"]
    added_id = add(client, pid, project["revision_id"])
    added = snapshot(client, pid, added_id)
    mock_proposal(monkeypatch)
    removed = chat(client, pid, added_id)
    response = client.post(f"/api/v1/projects/{pid}/restore", json={
        "base_revision_id": removed["committed_revision_id"], "target_revision_id": added_id,
    }, headers=headers(removed["committed_revision_id"]))
    assert response.status_code == 200, response.text
    restored = snapshot(client, pid, response.json()["data"]["revision_id"])
    assert restored.revision_number == 4
    assert restored.levels == added.levels
    assert restored.spaces == added.spaces
    assert restored.brief == added.brief
    assert restored.parent_revision_id == removed["committed_revision_id"]
    assert validate_snapshot(restored) == []


def test_export_after_removal_contains_only_surviving_floor_sheets(studio, monkeypatch):
    client, project, _ = studio
    pid = project["project_id"]
    added_id = add(client, pid, project["revision_id"])
    mock_proposal(monkeypatch)
    removed = chat(client, pid, added_id)
    response = client.post(f"/api/v1/projects/{pid}/exports", json={"revision_id": removed["committed_revision_id"]})
    assert response.status_code == 200, response.text
    exported = response.json()["data"]
    assert "A-104 roof" in exported["sheets"]
    assert all("level_3" not in sheet for sheet in exported["sheets"])
    pdf = client.get(f"/artifacts/{exported['artifact_id']}")
    with pymupdf.open(stream=pdf.content, filetype="pdf") as document:
        assert len(document) == len(exported["sheets"])
        assert all(removed["committed_revision_id"] in page.get_text() for page in document)
    model = client.get(f"/artifacts/{exported['model_artifact_id']}").json()
    assert all(level["name"] != "level_3" for level in model["levels"])
    assert all(row["revision_id"] == removed["committed_revision_id"] for row in exported["results"])


def test_stale_remove_proposal_cannot_overwrite_concurrent_add(studio, monkeypatch):
    client, project, _ = studio
    pid = project["project_id"]
    async def propose(text, context):
        await asyncio.to_thread(add, client, pid, project["revision_id"])
        return {"execution_status": "completed", "proposal": Proposal(intent="remove_level", explanation="Remove the highest floor.").model_dump()}
    monkeypatch.setattr(main, "propose", propose)
    result = chat(client, pid, project["revision_id"])
    assert result["execution_status"] == "blocked"
    assert result["issue"]["code"] == "STALE_REVISION"
    head = client.get(f"/api/v1/projects/{pid}").json()["data"]
    assert snapshot(client, pid, head["revision_id"]).brief.floors_above_ground == 3


def test_meta_schema_keeps_remove_level_typed_and_bounded(monkeypatch):
    calls = []
    monkeypatch.setattr(orchestrate, "meta_status", lambda: {"configured": True, "reasoning_model": "muse-wonder-1.0"})
    async def response(body):
        calls.append(body)
        proposal = Proposal(intent="remove_level", explanation="Remove the highest living floor.")
        return {"execution_status": "completed", "raw": {"status": "completed", "output": [{"content": [{"type": "output_text", "text": proposal.model_dump_json()}]}]}}
    monkeypatch.setattr(orchestrate, "response", response)
    result = asyncio.run(orchestrate.propose("remove last level", "{}"))
    assert result["proposal"]["intent"] == "remove_level"
    assert result["proposal"]["level"] is None
    assert "remove_level" in calls[0]["text"]["format"]["schema"]["properties"]["intent"]["enum"]
    assert calls[0]["reasoning"] == {"effort": "low"}
    assert calls[0]["max_output_tokens"] == 4096
