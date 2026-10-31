"""Old deployed villa data survives the real controller, history and export path."""
from __future__ import annotations

import hashlib
import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app import main
from app.database import BudgetRow, CommandReceiptRow, MetaUsageRow, ProjectRow, RevisionRow
from domain.models import ProjectSnapshot
from geometry.validate import validate_snapshot
from fixtures.legacy_villa import build_legacy_villa


@pytest.fixture
def legacy_studio(tmp_path, monkeypatch):
    monkeypatch.delenv("META_API_KEY", raising=False)
    application = main.create_app(f"sqlite:///{tmp_path / 'legacy.db'}", tmp_path / "artifacts")
    with TestClient(application) as client:
        actor = client.post("/api/v1/demo/sessions").json()["data"]["actor_id"]
        original = build_legacy_villa(str(uuid.uuid4()))
        original.title = "Retained original villa"
        original.pool.water_length_m = 9
        original.spaces[0].name = "Family reading room"
        original.spaces[0].target_area_m2 = 59.5
        original.with_hash()
        # Persist actual old-format bytes, not today's seed with its architecture
        # field removed. Whitespace and absent modern defaults must also survive.
        old_data = original.model_dump(mode="json", exclude={"architecture", "material_palette"})
        raw = json.dumps(old_data, indent=3)
        with application.state.session_factory.begin() as db:
            db.add(ProjectRow(id=original.project_id, actor_id=actor,
                              current_revision_id=original.revision_id))
            db.add(RevisionRow(revision_id=original.revision_id, project_id=original.project_id,
                               revision_number=original.revision_number, snapshot_json=raw))
        yield client, original, raw, application
    application.state.engine.dispose()


def headers(revision_id, key=None):
    return {"If-Match": f'"{revision_id}"', "Idempotency-Key": key or str(uuid.uuid4())}


def command(client, original, kind="upgrade_architecture", *, base=None, key=None, command_id=None, **fields):
    rid = base or original.revision_id
    return client.post(f"/api/v1/projects/{original.project_id}/commands",
        json={"base_revision_id": rid, "commands": [{"type": kind,
              "command_id": command_id or str(uuid.uuid4()), **fields}]},
        headers=headers(rid, key))


def snapshot(client, project_id, revision_id):
    response = client.get(f"/api/v1/projects/{project_id}/revisions/{revision_id}")
    assert response.status_code == 200, response.text
    return ProjectSnapshot.model_validate(response.json()["data"])


def upgraded(client, original):
    response = command(client, original)
    assert response.status_code == 200, response.text
    return snapshot(client, original.project_id, response.json()["data"]["revision_id"])


def assert_old_bytes(original, raw, application):
    with application.state.session_factory() as db:
        stored = db.get(RevisionRow, original.revision_id)
        assert stored.snapshot_json == raw
        assert ProjectSnapshot.model_validate_json(stored.snapshot_json).compute_hash() == original.content_hash


def test_upgrade_preserves_original_identity_edits_and_bytes(legacy_studio):
    client, original, raw, application = legacy_studio
    original_api = client.get(f"/api/v1/projects/{original.project_id}/revisions/{original.revision_id}").json()["data"]
    before = client.post(f"/api/v1/projects/{original.project_id}/analyses",
                         json={"revision_id": original.revision_id})
    assert before.status_code == 200, before.text
    response = command(client, original)
    assert response.status_code == 200, response.text
    mutation = response.json()["data"]
    assert {"architecture", "structure", "pool", "documents"} <= set(mutation["invalidated_result_groups"])
    current = snapshot(client, original.project_id, mutation["revision_id"])
    assert current.revision_number == original.revision_number + 1
    assert current.parent_revision_id == original.revision_id
    assert current.project_id == original.project_id and current.title == original.title
    assert current.pool == original.pool
    assert current.levels == original.levels
    assert current.brief == original.brief and current.site == original.site
    assert current.content_hash == current.compute_hash() != original.content_hash
    assert current.architecture.revision_id == current.revision_id
    assert len(current.architecture.stairs) == 3
    assert validate_snapshot(current) == []
    old_by_id = {space.id: space for space in original.spaces}
    new_by_id = {space.id: space for space in current.spaces}
    assert old_by_id.keys() <= new_by_id.keys()
    for identifier, old in old_by_id.items():
        new = new_by_id[identifier]
        assert new.model_dump(exclude={"polygon"}) == old.model_dump(exclude={"polygon"})
        if old.classification == "principal" or old.use in {"pool_hall", "roof_terrace"}:
            assert new.polygon == old.polygon
    assert client.get(f"/api/v1/projects/{original.project_id}/revisions/{original.revision_id}").json()["data"] == original_api
    stale = client.get(f"/api/v1/projects/{original.project_id}/analyses",
                       params={"revision_id": original.revision_id}).json()["data"]
    assert stale["results"] and all(row["freshness_status"] == "stale" for row in stale["results"])
    assert_old_bytes(original, raw, application)
    with application.state.session_factory() as db:
        assert db.query(MetaUsageRow).count() == 0
        assert db.get(BudgetRow, "application").spent_microusd == 0


def test_upgrade_replay_and_stale_requests_never_duplicate_revision(legacy_studio):
    client, original, raw, application = legacy_studio
    key = f"upgrade-architecture:{original.revision_id}"
    first = command(client, original, key=key, command_id=original.revision_id)
    assert first.status_code == 200, first.text
    replay = command(client, original, key=key, command_id=original.revision_id)
    assert replay.status_code == 200 and replay.json()["data"] == first.json()["data"]
    assert command(client, original).status_code == 412
    history = client.get(f"/api/v1/projects/{original.project_id}/revisions").json()["data"]
    assert len(history) == 2 and sum(row["is_current"] for row in history) == 1
    with application.state.session_factory() as db:
        assert db.query(CommandReceiptRow).count() == 1
    assert_old_bytes(original, raw, application)


def test_concurrent_upgrade_commits_only_one_current_revision(legacy_studio):
    client, original, raw, application = legacy_studio
    cookies = dict(client.cookies)
    barrier = threading.Barrier(2)
    def attempt(_):
        with TestClient(application) as worker:
            worker.cookies.update(cookies)
            barrier.wait()
            return command(worker, original)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(attempt, range(2)))
    assert sorted(response.status_code for response in responses) == [200, 412]
    history = client.get(f"/api/v1/projects/{original.project_id}/revisions").json()["data"]
    assert len(history) == 2
    assert_old_bytes(original, raw, application)


def test_upgrade_requires_owner_and_preserves_data_on_invalid_legacy_geometry(legacy_studio):
    client, original, raw, application = legacy_studio
    with TestClient(application) as stranger:
        assert command(stranger, original).status_code == 401
        stranger.post("/api/v1/demo/sessions")
        assert command(stranger, original).status_code == 403
    # A historical pool edit outside the original pool hall is not silently
    # recentered or resized by a compatibility operation.
    original.pool.water_length_m = 11
    original.pool.origin_x_m = 2
    original.with_hash()
    invalid_raw = original.model_dump_json(exclude={"architecture", "material_palette"})
    with application.state.session_factory.begin() as db:
        db.get(RevisionRow, original.revision_id).snapshot_json = invalid_raw
    response = command(client, original)
    assert response.status_code == 422
    history = client.get(f"/api/v1/projects/{original.project_id}/revisions").json()["data"]
    assert len(history) == 1 and history[0]["revision_id"] == original.revision_id
    assert_old_bytes(original, invalid_raw, application)
    with application.state.session_factory() as db:
        assert db.query(CommandReceiptRow).count() == 0


def test_upgraded_villa_can_add_then_remove_a_level(legacy_studio):
    client, original, raw, application = legacy_studio
    current = upgraded(client, original)
    added_response = command(client, original, "add_level", base=current.revision_id)
    assert added_response.status_code == 200, added_response.text
    added = snapshot(client, original.project_id, added_response.json()["data"]["revision_id"])
    assert added.brief.floors_above_ground == 3
    assert len(added.architecture.stairs) == 4 and validate_snapshot(added) == []
    removed_response = command(client, original, "remove_level", base=added.revision_id)
    assert removed_response.status_code == 200, removed_response.text
    removed = snapshot(client, original.project_id, removed_response.json()["data"]["revision_id"])
    assert removed.levels == current.levels and removed.spaces == current.spaces
    assert removed.pool == current.pool == original.pool
    assert validate_snapshot(removed) == []
    assert_old_bytes(original, raw, application)


def test_restoring_old_revision_creates_valid_new_architecture_without_rewriting_it(legacy_studio):
    client, original, raw, application = legacy_studio
    current = upgraded(client, original)
    edited = command(client, original, "set_pool_dimensions", base=current.revision_id, water_length_m=9.5)
    assert edited.status_code == 200, edited.text
    edited_id = edited.json()["data"]["revision_id"]
    response = client.post(f"/api/v1/projects/{original.project_id}/restore",
        json={"base_revision_id": edited_id, "target_revision_id": original.revision_id},
        headers=headers(edited_id))
    assert response.status_code == 200, response.text
    restored = snapshot(client, original.project_id, response.json()["data"]["revision_id"])
    assert restored.parent_revision_id == edited_id and restored.revision_number == 4
    assert restored.pool == original.pool
    assert restored.spaces == current.spaces and restored.levels == current.levels
    assert restored.architecture.revision_id == restored.revision_id
    assert validate_snapshot(restored) == []
    assert_old_bytes(original, raw, application)


def test_upgraded_export_uses_accepted_revision_and_actual_bytes(legacy_studio):
    client, original, raw, application = legacy_studio
    current = upgraded(client, original)
    response = client.post(f"/api/v1/projects/{original.project_id}/exports",
                           json={"revision_id": current.revision_id})
    assert response.status_code == 200, response.text
    export = response.json()["data"]
    assert export["revision_id"] == current.revision_id
    assert export["content_hash"] == current.content_hash
    assert export["discipline_design_complete"] is False
    assert export["review_status"] == "unreviewed" and export["authority_process"] == "not_submitted"
    blobs = {}
    for kind, identity, digest in [
        ("pdf", export["artifact_id"], export["file_sha256"]),
        ("model", export["model_artifact_id"], export["model_sha256"]),
        ("manifest", export["manifest_artifact_id"], export["manifest_sha256_stored_externally"]),
    ]:
        downloaded = client.get(f"/artifacts/{identity}")
        assert downloaded.status_code == 200
        assert hashlib.sha256(downloaded.content).hexdigest() == digest
        blobs[kind] = downloaded.content
    assert ProjectSnapshot.model_validate_json(blobs["model"]) == current
    assert json.loads(blobs["manifest"]) == {k: v for k, v in export.items() if k != "manifest_sha256_stored_externally"}
    assert all(row["revision_id"] == current.revision_id and row["input_hash"] == current.content_hash
               for row in export["results"])
    pool = next(row for row in export["results"] if row["method_id"] == "pool_quantities")
    assert pool["quantities"]["surface_area_m2"] == pytest.approx(31.5)
    assert pool["quantities"]["volume_m3"] == pytest.approx(44.1)
    assert next(row for row in export["results"] if row["method_id"] == "area_schedule")["geometry_issues"] == []
    with pymupdf.open(stream=blobs["pdf"], filetype="pdf") as document:
        assert len(document) == len(export["sheets"])
        assert [sheet for sheet in export["sheets"] if sheet.startswith("A-")] == [
            "A-101 basement", "A-102 ground", "A-103 upper", "A-104 roof"]
        for page, sheet in zip(document, export["sheets"]):
            text = page.get_text()
            assert current.revision_id in text and current.content_hash[:16] in text
            assert sheet in text
        assert "Retained original villa" in document[0].get_text()
    with TestClient(application) as stranger:
        stranger.post("/api/v1/demo/sessions")
        for key in ("artifact_id", "model_artifact_id", "manifest_artifact_id"):
            assert stranger.get(f"/artifacts/{export[key]}").status_code == 403
    assert_old_bytes(original, raw, application)
