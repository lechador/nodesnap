"""Private-home site features use real geometry, owned revisions and typed chat edits."""
from __future__ import annotations

import asyncio
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import main, orchestrate
from app.database import CommandReceiptRow
from app.orchestrate import Proposal, SiteEdit
from domain.models import ProjectSnapshot
from geometry.validate import validate_snapshot
from test_building_design_api import house_program


def feature_program():
    program = house_program()
    program.update(
        title="House with a yard, detached garage and outdoor pool",
        yard={"width_m": 16, "depth_m": 9},
        garage={"width_m": 3.6, "depth_m": 6, "height_m": 2.8, "side": "right", "vehicle_door_width_m": 2.6},
        pool={"water_length_m": 8, "water_width_m": 3.5, "water_depth_m": 1.4, "level": "ground", "location": "outdoor"},
    )
    return program


@pytest.fixture
def studio(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "meta_status", lambda: {"configured": True, "reasoning_model": "muse-wonder-1.0"})
    application = main.create_app(f"sqlite:///{tmp_path / 'site.db'}", tmp_path / "artifacts")
    with TestClient(application) as client:
        client.post("/api/v1/demo/sessions")
        yield client, application
    application.state.engine.dispose()


def create(client, program):
    response = client.post("/api/v1/designs", json={"program": program}, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["execution_status"] == "completed", result
    return result


def snapshot(client, pid, revision):
    response = client.get(f"/api/v1/projects/{pid}/revisions/{revision}")
    assert response.status_code == 200, response.text
    return ProjectSnapshot.model_validate(response.json()["data"])


def chat(client, pid, revision, key="site-change", text="Add a small yard, a garage and an outdoor pool"):
    return client.post(f"/api/v1/projects/{pid}/conversations", json={"text": text, "base_revision_id": revision},
        headers={"If-Match": revision, "Idempotency-Key": key})


def edits_from_program(program):
    return [SiteEdit(type="set_yard", yard=program["yard"]),
            SiteEdit(type="set_garage", garage=program["garage"]),
            SiteEdit(type="set_outdoor_pool", pool=program["pool"])]


def mock_edits(monkeypatch, edits, contexts=None):
    async def propose(text, context):
        if contexts is not None:
            contexts.append(json.loads(context))
        return {"execution_status": "completed", "proposal": Proposal(intent="set_site_features", site_edits=edits,
            explanation="I’ll add the requested private-home features.").model_dump()}
    monkeypatch.setattr(main, "propose", propose)


def test_new_home_brief_creates_actual_yard_vehicle_garage_and_outdoor_pool(studio, monkeypatch):
    client, _ = studio
    seen = []
    async def propose(text, history, context):
        seen.append(text)
        return {"execution_status": "completed", "proposal": {"intent": "design_building", "program": feature_program(), "explanation": "A home with outdoor space."}}
    monkeypatch.setattr(main, "propose_design", propose)
    request = "i want a new house with a small yard and a garage and a pool"
    response = client.post("/api/v1/designs", json={"text": request}, headers={"Idempotency-Key": "private-home"})
    result = response.json()["data"]
    assert result["execution_status"] == "completed", result
    model = snapshot(client, result["project_id"], result["committed_revision_id"])
    assert seen == [request]
    assert validate_snapshot(model) == []
    assert model.site_layout.yard and model.site_layout.garage and model.site_layout.driveway
    assert model.site_layout.pool_deck and model.pool.location == "outdoor"
    assert not any(space.use == "pool_hall" for space in model.spaces)
    assert model.site_layout.garage.vehicle_door_width_m == pytest.approx(2.6)
    assert "16 × 9 m rear yard" in result["explanation"]
    assert "3.6 × 6 m detached garage" in result["explanation"]
    assert "8 × 3.5 m outdoor pool" in result["explanation"]


def test_compound_chat_preserves_house_and_commits_once_with_replay_and_access_guards(studio, monkeypatch):
    client, application = studio
    created = create(client, house_program())
    pid, revision = created["project_id"], created["committed_revision_id"]
    original = snapshot(client, pid, revision)
    assert client.post(f"/api/v1/projects/{pid}/analyses", json={"revision_id": revision}).status_code == 200
    contexts = []
    mock_edits(monkeypatch, edits_from_program(feature_program()), contexts)
    first = chat(client, pid, revision).json()["data"]
    assert first["execution_status"] == "completed", first
    assert first["committed_revision_number"] == 2
    after = snapshot(client, pid, first["committed_revision_id"])
    assert after.spaces == original.spaces
    assert after.levels == original.levels
    assert after.site_layout.garage and after.site_layout.yard
    assert after.pool.location == "outdoor"
    assert validate_snapshot(after) == []
    assert snapshot(client, pid, revision).content_hash == original.content_hash
    assert contexts[0]["site_layout"] is None
    assert "detached garage" in first["explanation"] and "driveway" in first["explanation"]
    assert chat(client, pid, revision).json()["data"] == first
    assert len(contexts) == 1
    assert chat(client, pid, revision, text="Make it different").status_code == 409
    assert chat(client, pid, revision, key="stale-request").status_code == 412
    assert len(client.get(f"/api/v1/projects/{pid}/revisions").json()["data"]) == 2
    with application.state.session_factory() as db:
        assert db.query(CommandReceiptRow).filter_by(revision_id=after.revision_id).count() == 3
    previous_results = client.get(f"/api/v1/projects/{pid}/analyses", params={"revision_id": revision}).json()["data"]["results"]
    assert previous_results and all(result["freshness_status"] == "stale" for result in previous_results)
    with TestClient(application) as other:
        other.post("/api/v1/demo/sessions")
        assert chat(other, pid, after.revision_id).status_code == 403
        assert other.get(f"/api/v1/projects/{pid}/revisions/{after.revision_id}").status_code == 403


def test_removing_yard_and_pool_together_is_atomic_and_undo_restores_features(studio, monkeypatch):
    client, _ = studio
    created = create(client, feature_program())
    pid, revision = created["project_id"], created["committed_revision_id"]
    before = snapshot(client, pid, revision)
    mock_edits(monkeypatch, [SiteEdit(type="set_yard", yard=None)])
    blocked = chat(client, pid, revision, key="remove-yard", text="Remove the yard").json()["data"]
    assert blocked["execution_status"] == "blocked", blocked
    assert blocked["committed_revision_id"] is None
    mock_edits(monkeypatch, [SiteEdit(type="set_yard", yard=None), SiteEdit(type="set_outdoor_pool", pool=None)])
    removed = chat(client, pid, revision, key="remove-both", text="Remove the yard and outdoor pool").json()["data"]
    assert removed["committed_revision_number"] == 2, removed
    state = snapshot(client, pid, removed["committed_revision_id"])
    assert state.pool is None
    assert state.site_layout.yard is None and state.site_layout.garage.id == before.site_layout.garage.id
    restored = client.post(f"/api/v1/projects/{pid}/undo").json()["data"]
    recovered = snapshot(client, pid, restored["revision_id"])
    assert recovered.pool == before.pool
    assert recovered.site_layout.yard == before.site_layout.yard
    assert recovered.site_layout.garage == before.site_layout.garage
    assert recovered.spaces == before.spaces


def test_outdoor_coverage_and_export_do_not_claim_indoor_pool_environment_method(studio):
    client, _ = studio
    created = create(client, feature_program())
    pid, revision = created["project_id"], created["committed_revision_id"]
    coverage = client.get(f"/api/v1/projects/{pid}/coverage", params={"revision_id": revision}).json()["data"]
    method = next(row for row in coverage["methods"] if row["id"] == "pool_environment")
    assert method["method_state"] == "research_required"
    assert "outdoor" in method["purpose"].lower()
    export = client.post(f"/api/v1/projects/{pid}/exports", json={"revision_id": revision})
    assert export.status_code == 200, export.text
    manifest = export.json()["data"]
    assert next(row for row in manifest["coverage"]["methods"] if row["id"] == "pool_environment") == method
    saved = client.get(f"/artifacts/{manifest['model_artifact_id']}").json()
    assert saved["revision_id"] == revision and saved["pool"]["location"] == "outdoor"
    assert saved["site_layout"]["garage"]["vehicle_door_width_m"] == pytest.approx(2.6)


def test_site_schema_is_strict_nested_and_old_edit_responses_remain_compatible(monkeypatch):
    captured = []
    monkeypatch.setattr(orchestrate, "meta_status", lambda: {"configured": True, "reasoning_model": "muse-wonder-1.0"})
    async def provider(payload):
        captured.append(payload)
        proposal = Proposal(intent="set_site_features", site_edits=edits_from_program(feature_program()), explanation="A rear yard and detached garage with an outdoor pool.")
        return {"execution_status": "completed", "raw": {"status": "completed", "output": [{"content": [{"text": proposal.model_dump_json()}]}]}}
    monkeypatch.setattr(orchestrate, "response", provider)
    result = asyncio.run(orchestrate.propose("Add a yard, garage and outdoor pool", "{}"))
    assert len(result["proposal"]["site_edits"]) == 3
    schema = captured[0]["text"]["format"]["schema"]
    for definition in [schema, *schema["$defs"].values()]:
        if definition.get("type") == "object":
            assert set(definition["required"]) == set(definition["properties"])
            assert definition["additionalProperties"] is False
    assert "set_site_features" in captured[0]["instructions"]
    assert "Attached/integral" in captured[0]["instructions"]
    old = Proposal.model_validate({"intent": "set_pool_dimensions", "pool_length_m": 9, "explanation": "Resize the pool."})
    assert old.site_edits is None and old.pool_length_m == 9


@pytest.mark.parametrize("edits", [
    [],
    [{"type": "set_yard"}],
    [{"type": "set_yard", "yard": {"depth_m": 8}}, {"type": "set_yard", "yard": None}],
    [{"type": "set_yard", "garage": {"width_m": 3.6}}],
    [{"type": "set_outdoor_pool", "pool": {"water_length_m": 8, "water_width_m": 3.5, "level": "ground", "location": "indoor"}}],
])
def test_invalid_site_proposals_are_rejected_before_commands(edits):
    with pytest.raises(ValidationError):
        Proposal.model_validate({"intent": "set_site_features", "site_edits": edits, "explanation": "A site edit."})


def test_bounded_repair_cannot_drop_or_relabel_site_requirements():
    original = main.BuildingProgram.model_validate(feature_program())
    protected = main.repair_requirements(original)
    for key, value in (("yard", None), ("garage", None), ("pool", None)):
        changed = original.model_copy(deep=True)
        setattr(changed, key, value)
        assert main.repair_requirements(changed) != protected
    changed = original.model_copy(deep=True)
    changed.pool.location = "indoor"
    assert main.repair_requirements(changed) != protected


def test_relocating_existing_indoor_pool_preserves_its_identity_and_explains_retained_hall(studio, monkeypatch):
    client, _ = studio
    created = client.post("/api/v1/projects", json={"seed": True}).json()["data"]
    pid, revision = created["project_id"], created["revision_id"]
    before = snapshot(client, pid, revision)
    pool = {"water_length_m": before.pool.water_length_m, "water_width_m": before.pool.water_width_m,
            "water_depth_m": before.pool.water_depth_m, "level": "ground", "location": "outdoor"}
    contexts = []
    mock_edits(monkeypatch, [SiteEdit(type="set_outdoor_pool", pool=pool)], contexts)
    result = chat(client, pid, revision, text="Move the pool outdoors").json()["data"]
    assert result["execution_status"] == "completed", result
    after = snapshot(client, pid, result["committed_revision_id"])
    assert contexts[0]["pool"]["location"] == "indoor"
    assert after.pool.id == before.pool.id
    assert after.spaces == before.spaces
    assert after.pool.location == "outdoor" and after.site_layout.yard
    assert "former indoor pool hall remains" in result["explanation"]
    assert "yard was added as a siting assumption" in result["explanation"]
    assert validate_snapshot(after) == []


def test_site_change_cannot_overwrite_a_newer_revision(studio, monkeypatch):
    client, _ = studio
    created = create(client, house_program())
    pid, revision = created["project_id"], created["committed_revision_id"]
    async def propose(text, context):
        edit = await asyncio.to_thread(client.post, f"/api/v1/projects/{pid}/commands",
            json={"base_revision_id": revision, "commands": [{"type": "set_material_palette", "palette": "warm_concrete"}]},
            headers={"If-Match": revision, "Idempotency-Key": "intervening"})
        assert edit.status_code == 200
        return {"execution_status": "completed", "proposal": Proposal(intent="set_site_features",
            site_edits=[SiteEdit(type="set_garage", garage=feature_program()["garage"])], explanation="Add a detached garage.").model_dump()}
    monkeypatch.setattr(main, "propose", propose)
    result = chat(client, pid, revision).json()["data"]
    assert result["execution_status"] == "blocked"
    assert result["issue"]["code"] == "STALE_REVISION"
    assert result["committed_revision_id"] is None
    head = client.get(f"/api/v1/projects/{pid}").json()["data"]
    after = snapshot(client, pid, head["revision_id"])
    assert after.site_layout is None and after.material_palette == "warm_concrete"
