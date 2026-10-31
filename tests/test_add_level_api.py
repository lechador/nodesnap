"""Added storeys use the real controller, immutable history and geometry pipeline."""
from __future__ import annotations

import asyncio
import json
import uuid

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app import main, orchestrate
from app.database import BudgetRow, CommandReceiptRow
from app.orchestrate import Proposal
from domain.models import ProjectSnapshot
from geometry.validate import validate_snapshot


@pytest.fixture
def studio(tmp_path, monkeypatch):
    # All inference is controlled in this module; no provider credentials or
    # network calls are needed to exercise the actual persistence/geometry path.
    monkeypatch.setattr(main, "meta_status", lambda: {
        "configured": True, "reasoning_model": "muse-wonder-1.0",
    })
    application = main.create_app(f"sqlite:///{tmp_path / 'studio.db'}", tmp_path / "artifacts")
    with TestClient(application) as client:
        client.post("/api/v1/demo/sessions")
        project = client.post("/api/v1/projects", json={"seed": True}).json()["data"]
        yield client, project, application
    application.state.engine.dispose()


def headers(revision_id, key=None):
    return {"If-Match": f'"{revision_id}"', "Idempotency-Key": key or str(uuid.uuid4())}


def get_snapshot(client, pid, revision_id):
    response = client.get(f"/api/v1/projects/{pid}/revisions/{revision_id}")
    assert response.status_code == 200, response.text
    return ProjectSnapshot.model_validate(response.json()["data"])


def mock_proposal(monkeypatch, proposal, contexts=None):
    async def propose(text, context):
        if contexts is not None:
            contexts.append(json.loads(context))
        return {"execution_status": "completed", "model": "muse-wonder-1.0",
                "usage": {"input_tokens": 100, "output_tokens": 20},
                "proposal": proposal.model_dump()}
    monkeypatch.setattr(main, "propose", propose)


def chat(client, pid, revision_id, text="I want you to add another level", key=None):
    response = client.post(f"/api/v1/projects/{pid}/conversations",
        json={"text": text, "base_revision_id": revision_id}, headers=headers(revision_id, key))
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_add_level_chat_commits_geometry_once_and_invalidates_old_results(studio, monkeypatch):
    client, project, application = studio
    pid, original_id = project["project_id"], project["revision_id"]
    original = get_snapshot(client, pid, original_id)
    client.post(f"/api/v1/projects/{pid}/analyses", json={"revision_id": original_id})
    contexts = []
    mock_proposal(monkeypatch, Proposal(intent="add_level", explanation="Add another living floor."), contexts)

    result = chat(client, pid, original_id, key="one-new-storey")
    assert result["execution_status"] == "completed"
    assert result["committed_revision_number"] == 2
    assert "Added Level 3" in result["explanation"]
    assert "inherited 3.4 m" in result["explanation"]
    assert "Raised the roof and terrace" in result["explanation"]
    assert "structural capacity" in result["explanation"]
    assert {"architecture", "structure", "documents", "hvac"} <= set(result["invalidated_result_groups"])
    added = get_snapshot(client, pid, result["committed_revision_id"])
    assert len(added.levels) == 5
    assert added.brief.floors_above_ground == 3
    assert len(added.architecture.stairs) == 4
    assert added.architecture.revision_id == added.revision_id
    assert validate_snapshot(added) == []
    assert next(level.elevation_m for level in added.levels if level.name == "roof") == pytest.approx(10.2)
    upper = next(level for level in original.levels if level.name == "upper")
    third = next(level for level in added.levels if level.name == "level_3")
    original_rooms = [space for space in original.spaces if space.level_id == upper.id]
    copied_rooms = [space for space in added.spaces if space.level_id == third.id]
    assert len(copied_rooms) == len(original_rooms)
    assert {space.id for space in copied_rooms}.isdisjoint(space.id for space in original.spaces)
    assert [(space.name, space.polygon) for space in copied_rooms] == [(space.name, space.polygon) for space in original_rooms]
    assert get_snapshot(client, pid, original_id) == original

    replay = chat(client, pid, original_id, key="one-new-storey")
    assert replay == result
    assert len(contexts) == 1
    assert contexts[0]["living_floor_count"] == 2
    assert contexts[0]["bedroom_count"] == 5
    assert len(client.get(f"/api/v1/projects/{pid}/conversations").json()["data"]) == 1
    assert len(client.get(f"/api/v1/projects/{pid}/revisions").json()["data"]) == 2
    previous = client.get(f"/api/v1/projects/{pid}/analyses", params={"revision_id": original_id}).json()["data"]
    assert all(item["freshness_status"] == "stale" for item in previous["results"])
    with application.state.session_factory() as db:
        assert db.query(CommandReceiptRow).count() == 1
        assert db.get(BudgetRow, "application").reserved_microusd == 0


def test_repeated_add_uses_current_levels_and_counts(studio, monkeypatch):
    client, project, _ = studio
    contexts = []
    mock_proposal(monkeypatch, Proposal(intent="add_level", explanation="Add another level."), contexts)
    first = chat(client, project["project_id"], project["revision_id"])
    second = chat(client, project["project_id"], first["committed_revision_id"])
    assert second["committed_revision_number"] == 3
    current = get_snapshot(client, project["project_id"], second["committed_revision_id"])
    assert current.brief.floors_above_ground == 4
    assert validate_snapshot(current) == []
    assert contexts[1]["living_floor_count"] == 3
    assert contexts[1]["bedroom_count"] == 9
    assert contexts[1]["default_new_level_source"] == "level_3"
    assert any(room["level"] == "level_3" for room in contexts[1]["rooms"])
    assert "Added Level 4" in second["explanation"]


def test_explicit_source_and_height_are_applied(studio, monkeypatch):
    client, project, _ = studio
    mock_proposal(monkeypatch, Proposal(intent="add_level", level="ground", level_height_m=4.1,
                                      explanation="Copy ground floor with a 4.1 m storey."))
    result = chat(client, project["project_id"], project["revision_id"], "Add a level like the ground floor, 4.1m high")
    current = get_snapshot(client, project["project_id"], result["committed_revision_id"])
    third = next(level for level in current.levels if level.name == "level_3")
    assert next(level.elevation_m for level in current.levels if level.name == "roof") == pytest.approx(10.9)
    assert sum(space.use == "bedroom" for space in current.spaces if space.level_id == third.id) == 1
    assert "requested 4.1 m" in result["explanation"]
    assert validate_snapshot(current) == []


@pytest.mark.parametrize("fields", [
    {"level": "level_99"}, {"level": "roof"}, {"level": "basement"},
    {"level_height_m": 2.5}, {"level_height_m": 4.6},
])
def test_invalid_added_level_is_atomic_and_replayable(studio, monkeypatch, fields):
    client, project, application = studio
    contexts = []
    mock_proposal(monkeypatch, Proposal(intent="add_level", explanation="Add a floor.", **fields), contexts)
    result = chat(client, project["project_id"], project["revision_id"], key="invalid-level")
    assert result["execution_status"] == "blocked"
    assert result["committed_revision_id"] is None
    assert result["issue"]["code"] == "DOMAIN_VALIDATION"
    assert client.get(f"/api/v1/projects/{project['project_id']}").json()["data"]["revision_id"] == project["revision_id"]
    assert len(client.get(f"/api/v1/projects/{project['project_id']}/revisions").json()["data"]) == 1
    assert chat(client, project["project_id"], project["revision_id"], key="invalid-level") == result
    assert len(contexts) == 1
    with application.state.session_factory() as db:
        assert db.query(CommandReceiptRow).count() == 0


def test_added_level_supports_regeneration_and_height_edits(studio, monkeypatch):
    client, project, _ = studio
    pid = project["project_id"]
    mock_proposal(monkeypatch, Proposal(intent="add_level", explanation="Add another level."))
    added = chat(client, pid, project["revision_id"])
    added_snapshot = get_snapshot(client, pid, added["committed_revision_id"])
    new_level = next(level for level in added_snapshot.levels if level.name == "level_3")
    rooms = [{"name": space.name, "use": space.use, "target_area_m2": space.target_area_m2}
             for space in added_snapshot.spaces if space.level_id == new_level.id and space.classification == "principal"]
    direct = client.post(f"/api/v1/projects/{pid}/generate", json={
        "base_revision_id": added_snapshot.revision_id, "level": "level_3", "rooms": rooms,
    }, headers=headers(added_snapshot.revision_id))
    assert direct.status_code == 200, direct.text
    generated = direct.json()["data"]
    assert generated["execution_status"] == "completed"
    assert validate_snapshot(get_snapshot(client, pid, generated["revision_id"])) == []

    mock_proposal(monkeypatch, Proposal(intent="regenerate_floor", level="level_3",
        room_name="Primary bedroom", room_target_area_ft2=450, explanation="Resize the Level 3 primary bedroom."))
    resized = chat(client, pid, generated["revision_id"], "Make the third floor primary bedroom 450 square feet")
    assert resized["execution_status"] == "completed"
    assert resized["solver_status"] in {"OPTIMAL", "FEASIBLE"}
    resized_snapshot = get_snapshot(client, pid, resized["committed_revision_id"])
    bedroom = next(space for space in resized_snapshot.spaces if space.level_id == new_level.id and space.name == "Primary bedroom")
    assert bedroom.target_area_m2 == pytest.approx(450 * 0.09290304)

    mock_proposal(monkeypatch, Proposal(intent="set_level_height", level="level_3", level_height_m=3.8, explanation="Raise the new storey."))
    raised = chat(client, pid, resized["committed_revision_id"], "Make level 3 3.8m high")
    assert raised["execution_status"] == "completed"
    raised_snapshot = get_snapshot(client, pid, raised["committed_revision_id"])
    assert next(level.elevation_m for level in raised_snapshot.levels if level.name == "roof") == pytest.approx(10.6)
    assert validate_snapshot(raised_snapshot) == []


@pytest.mark.parametrize("level_name", ["level_99", "basement", "roof"])
def test_bad_regeneration_level_is_rejected_without_crashing_chat(studio, monkeypatch, level_name):
    client, project, _ = studio
    mock_proposal(monkeypatch, Proposal(intent="regenerate_floor", level=level_name, explanation="Regenerate this floor."))
    result = chat(client, project["project_id"], project["revision_id"], f"Regenerate {level_name}")
    assert result["execution_status"] == "blocked"
    assert result["issue"]["code"] == "DOMAIN_VALIDATION"
    mock_proposal(monkeypatch, Proposal(intent="add_level", explanation="Add a floor."))
    assert chat(client, project["project_id"], project["revision_id"])["committed_revision_number"] == 2


def test_undo_restores_prior_level_program_without_rewriting_history(studio, monkeypatch):
    client, project, _ = studio
    pid = project["project_id"]
    original = get_snapshot(client, pid, project["revision_id"])
    mock_proposal(monkeypatch, Proposal(intent="add_level", explanation="Add a floor."))
    added = chat(client, pid, project["revision_id"])
    undo = client.post(f"/api/v1/projects/{pid}/undo")
    assert undo.status_code == 200, undo.text
    restored = get_snapshot(client, pid, undo.json()["data"]["revision_id"])
    assert restored.revision_number == 3
    assert restored.parent_revision_id == added["committed_revision_id"]
    assert restored.levels == original.levels
    assert restored.spaces == original.spaces
    assert restored.brief == original.brief
    assert validate_snapshot(restored) == []
    assert get_snapshot(client, pid, added["committed_revision_id"]).brief.floors_above_ground == 3
    assert len(client.get(f"/api/v1/projects/{pid}/revisions").json()["data"]) == 3


def test_stale_add_level_cannot_overwrite_an_intervening_direct_edit(studio, monkeypatch):
    client, project, _ = studio
    pid, revision_id = project["project_id"], project["revision_id"]
    async def proposal(text, context):
        edit = await asyncio.to_thread(client.post, f"/api/v1/projects/{pid}/commands", json={
            "base_revision_id": revision_id, "commands": [{"type": "set_pool_dimensions", "water_length_m": 9}],
        }, headers=headers(revision_id))
        assert edit.status_code == 200
        return {"execution_status": "completed", "proposal": Proposal(intent="add_level", explanation="Add a floor.").model_dump()}
    monkeypatch.setattr(main, "propose", proposal)
    result = chat(client, pid, revision_id)
    assert result["execution_status"] == "blocked"
    assert result["issue"]["code"] == "STALE_REVISION"
    current_id = client.get(f"/api/v1/projects/{pid}").json()["data"]["revision_id"]
    current = get_snapshot(client, pid, current_id)
    assert current.brief.floors_above_ground == 2
    assert current.pool.water_length_m == 9


def test_meta_strict_schema_accepts_add_level_and_dynamic_level_names(monkeypatch):
    requests = []
    monkeypatch.setattr(orchestrate, "meta_status", lambda: {"configured": True, "reasoning_model": "muse-wonder-1.0"})
    async def response(body):
        requests.append(body)
        proposal = Proposal(intent="add_level", level="level_3", level_height_m=3.6, explanation="Copy Level 3.")
        return {"execution_status": "completed", "raw": {"output": [{"content": [{"text": proposal.model_dump_json()}]}]}}
    monkeypatch.setattr(orchestrate, "response", response)
    output = asyncio.run(orchestrate.propose("Add a floor like Level 3", '{"living_floor_count":3}'))
    assert output["proposal"]["intent"] == "add_level"
    assert output["proposal"]["level"] == "level_3"
    schema = requests[0]["text"]["format"]["schema"]
    assert "add_level" in schema["properties"]["intent"]["enum"]
    assert set(schema["required"]) == set(schema["properties"])
    assert "five bedrooms across two" not in requests[0]["instructions"]
    assert requests[0]["reasoning"] == {"effort": "low"}
    assert requests[0]["max_output_tokens"] == 4096


def test_live_shape_reasoning_budget_exhaustion_is_not_retried_or_committed(studio, monkeypatch):
    client, project, _ = studio
    calls = []
    monkeypatch.setattr(main, "propose", orchestrate.propose)
    monkeypatch.setattr(orchestrate, "meta_status", lambda: {"configured": True, "reasoning_model": "muse-wonder-1.0"})
    async def response(body):
        calls.append(body)
        return {"execution_status": "completed", "usage": {"input_tokens": 1135, "output_tokens": 1500,
                    "output_tokens_details": {"reasoning_tokens": 1498}},
                "raw": {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"},
                        "output": [{"type": "reasoning", "status": "incomplete", "summary": []}]}}
    monkeypatch.setattr(orchestrate, "response", response)
    result = chat(client, project["project_id"], project["revision_id"])
    assert result["execution_status"] == "error"
    assert result["issue"]["code"] == "PROVIDER_OUTPUT_LIMIT"
    assert result["committed_revision_id"] is None
    assert len(calls) == 1
    assert len(client.get(f"/api/v1/projects/{project['project_id']}/revisions").json()["data"]) == 1


@pytest.mark.parametrize("status", ["incomplete", "failed", "cancelled", "queued", "in_progress"])
def test_noncompleted_provider_response_cannot_commit_even_if_text_is_valid(monkeypatch, status):
    monkeypatch.setattr(orchestrate, "meta_status", lambda: {"configured": True, "reasoning_model": "muse-wonder-1.0"})
    async def response(body):
        proposal = Proposal(intent="add_level", explanation="Add a floor.")
        return {"execution_status": "completed", "raw": {"status": status,
                "output": [{"content": [{"type": "output_text", "text": proposal.model_dump_json()}]}]}}
    monkeypatch.setattr(orchestrate, "response", response)
    result = asyncio.run(orchestrate.propose("Add a floor", "{}"))
    assert result["execution_status"] == "error"
    assert result["proposal"] is None
    assert result["issue"]["code"] != "MALFORMED_OUTPUT"


def test_provider_refusal_is_distinguished_from_invalid_json(monkeypatch):
    monkeypatch.setattr(orchestrate, "meta_status", lambda: {"configured": True, "reasoning_model": "muse-wonder-1.0"})
    async def response(body):
        return {"execution_status": "completed", "raw": {"status": "completed",
                "output": [{"content": [{"type": "refusal", "refusal": "Cannot complete this request."}]}]}}
    monkeypatch.setattr(orchestrate, "response", response)
    result = asyncio.run(orchestrate.propose("Add a floor", "{}"))
    assert result["execution_status"] == "blocked"
    assert result["proposal"] is None
    assert result["issue"]["code"] == "PROVIDER_REFUSAL"


def test_added_level_export_manifest_matches_actual_pdf_pages(studio, monkeypatch):
    client, project, _ = studio
    pid = project["project_id"]
    mock_proposal(monkeypatch, Proposal(intent="add_level", explanation="Add a floor."))
    added = chat(client, pid, project["revision_id"])
    response = client.post(f"/api/v1/projects/{pid}/exports", json={"revision_id": added["committed_revision_id"]})
    assert response.status_code == 200, response.text
    exported = response.json()["data"]
    assert "A-104 level_3" in exported["sheets"]
    assert "A-105 roof" in exported["sheets"]
    assert "A-104 roof" not in exported["sheets"]
    pdf = client.get(f"/artifacts/{exported['artifact_id']}")
    with pymupdf.open(stream=pdf.content, filetype="pdf") as document:
        assert len(document) == len(exported["sheets"])
        for page in document:
            assert added["committed_revision_id"] in page.get_text()
        third_floor_page = document[exported["sheets"].index("A-104 level_3")].get_text()
        assert "Level 3" in third_floor_page
    model = client.get(f"/artifacts/{exported['model_artifact_id']}").json()
    assert any(level["name"] == "level_3" for level in model["levels"])
    assert model["revision_id"] == added["committed_revision_id"]
    assert all(result["revision_id"] == added["committed_revision_id"] for result in exported["results"])


@pytest.mark.parametrize("level_name", ["level_99", "basement", "roof"])
def test_generate_endpoint_rejects_nonliving_or_unknown_level(studio, level_name):
    client, project, _ = studio
    snapshot = get_snapshot(client, project["project_id"], project["revision_id"])
    ground = next(level for level in snapshot.levels if level.name == "ground")
    rooms = [{"name": space.name, "use": space.use, "target_area_m2": space.target_area_m2}
             for space in snapshot.spaces if space.level_id == ground.id and space.classification == "principal"]
    response = client.post(f"/api/v1/projects/{project['project_id']}/generate", json={
        "base_revision_id": snapshot.revision_id, "level": level_name, "rooms": rooms,
    }, headers=headers(snapshot.revision_id))
    assert response.status_code == 422
    assert len(client.get(f"/api/v1/projects/{project['project_id']}/revisions").json()["data"]) == 1
