"""Removal must disappear from current drawings/quantities, including a middle storey."""
from __future__ import annotations

import pymupdf
import pytest

from app.analysis import compute_results, with_freshness
from domain.commands import apply_commands
from domain.models import new_id
from domain.seed import build_seed
from reports.pdf import build_review_package


@pytest.fixture(scope="module", params=["top", "middle"])
def removal(request):
    seed = build_seed(new_id())
    third = apply_commands(seed, [{"type": "add_level", "height_m": 4.0}])
    before = apply_commands(third, [{"type": "add_level", "height_m": 3.4}])
    target = next(level for level in before.levels if level.name == ("level_4" if request.param == "top" else "level_3"))
    # Unique fixture names prove current sheet rows disappear, despite other
    # copied storeys ordinarily sharing the source floor's room names.
    removed_spaces = [space for space in before.spaces if space.level_id == target.id]
    for index, space in enumerate(removed_spaces):
        space.name = f"Deleted fixture room {index + 1:02d}"
    before = before.with_hash()
    ordered = sorted(before.levels, key=lambda level: level.elevation_m)
    height_m = ordered[ordered.index(target) + 1].elevation_m - target.elevation_m
    command = {"type": "remove_level"}
    if request.param == "middle":
        command["level_id"] = target.id
    after = apply_commands(before, [command])
    return before, after, target, removed_spaces, height_m, compute_results(before), compute_results(after)


def test_removed_storey_service_reduction_and_roof_catchment(removal):
    before, after, removed, removed_spaces, height_m, old_results, new_results = removal
    old = next(result["quantities"] for result in old_results if result["method_id"] == "services_inventories")
    new = next(result["quantities"] for result in new_results if result["method_id"] == "services_inventories")
    a, b = old["hvac_energy"]["area_reconciliation"], new["hvac_energy"]["area_reconciliation"]
    # Independent 67m enclosure perimeter,250mm inter-storey slab and seed's
    # eight principal windows plus four1.8x1.15m support-room windows.
    gross = 67 * (height_m - .25)
    principal_width = 4 * 4.4 + 2 * (15 * 240 / 920 - .8) + (15 * 260 / 920 - .8) + (15 * 300 / 920 - .8)
    glazing = principal_width * 2.35 + 4 * 1.8 * 1.15
    assert a["gross_wall_area_m2"] - b["gross_wall_area_m2"] == pytest.approx(gross)
    assert a["window_area_m2"] - b["window_area_m2"] == pytest.approx(glazing)
    assert a["opaque_wall_area_m2"] - b["opaque_wall_area_m2"] == pytest.approx(gross - glazing)
    assert a["door_area_m2"] == b["door_area_m2"]
    assert old["hvac_energy"]["total_conduction_w"] - new["hvac_energy"]["total_conduction_w"] == pytest.approx(((gross - glazing) * .30 + glazing * 1.60) * 22)
    # Independent clear rectangle area for six principal rooms in two strips.
    clear_area = 2 * (6.95 - .30 - .075) * (15 - .30 - 5 * .075)
    assert old["electrical"]["connected_load_w"] - new["electrical"]["connected_load_w"] == pytest.approx(clear_area * 12)
    assert old["plumbing"]["sum_of_fixture_flows_l_min"] - new["plumbing"]["sum_of_fixture_flows_l_min"] == 20
    deleted_ids = {space.id for space in removed_spaces}
    assert all(item.get("space_id") not in deleted_ids for item in new["electrical"]["items"] + new["plumbing"]["fixtures"])
    assert all(surface["level_id"] != removed.id for surface in new["hvac_energy"]["surface_ledger"])
    for inventory in (old, new):
        drainage = inventory["drainage"]
        assert drainage["roof_area_m2"] == pytest.approx(279)
        assert drainage["terrace_area_m2"] == pytest.approx(83.61)
        assert sum(zone["area_m2"] for zone in drainage["catchments"]) == pytest.approx(279)
        assert drainage["runoff_l_s"] == pytest.approx(.95 * 100 * 279 / 3600)
    assert old["drainage"]["roof_object_ids"] == new["drainage"]["roof_object_ids"]
    assert all(component["revision_id"] == after.revision_id for component in (new["hvac_energy"], new["electrical"], new["plumbing"], new["drainage"]))


def test_removal_results_exclude_deleted_rows_and_keep_structural_scope(removal):
    before, after, removed, removed_spaces, _, old_results, new_results = removal
    deleted_ids = {space.id for space in removed_spaces}
    architecture = next(result for result in new_results if result["method_id"] == "area_schedule")
    assert {row["space_id"] for row in architecture["schedule"]} == {space.id for space in after.spaces}
    assert not ({row["space_id"] for row in architecture["schedule"]} & deleted_ids)
    assert not any(row["level"] == removed.label for row in architecture["schedule"])
    assert all(row["revision_id"] == after.revision_id for row in architecture["schedule"])
    assert all(result["freshness_status"] == "stale" for result in with_freshness(old_results, after.revision_id))
    assert all(result["revision_id"] == after.revision_id and result["input_hash"] == after.content_hash for result in new_results)
    old_frame = next(result for result in old_results if result["method_id"] == "structural_frame_analysis")
    new_frame = next(result for result in new_results if result["method_id"] == "structural_frame_analysis")
    assert new_frame["quantities"] == old_frame["quantities"]
    for result in new_results:
        if result["discipline"] in {"structure", "foundations"}:
            assert result["check_outcome"] == "not_evaluated"
            assert any(issue["code"] == "OUTSIDE_METHOD_DOMAIN" and issue.get("field") == "model_coupling" for issue in result["issues"])


def test_removed_level_pdf_and_actual_manifest_index(removal):
    before, after, removed, removed_spaces, height_m, old_results, new_results = removal
    pdf, sheet_index = build_review_package(after, new_results)
    levels = sorted(after.levels, key=lambda level: level.elevation_m)
    # The API writes this exact actual-page index into the export manifest.
    plans = [sheet for sheet in sheet_index if sheet.startswith("A-")]
    assert plans == [f"A-{101 + index} {level.name}" for index, level in enumerate(levels)]
    assert len(plans) == 5 and plans[-1] == "A-105 roof"
    assert not any(sheet.endswith(f" {removed.name}") for sheet in plans)
    assert plans[-2] == ("A-104 level_3" if removed.name == "level_4" else "A-104 level_4")
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        assert len(document) == len(sheet_index)
        texts = [page.get_text() for page in document]
        assert all(after.revision_id in text and sheet in text for sheet, text in zip(sheet_index, texts))
        current_text = "\n".join(text for sheet, text in zip(sheet_index, texts)
                                 if sheet.startswith(("COVER", "A-", "CALC-101")))
        assert removed.label not in current_text
        assert all(space.name not in current_text for space in removed_spaces)
        schedule = [line for sheet, text in zip(sheet_index, texts) if sheet.startswith("CALC-101")
                    for line in text.splitlines() if " actual " in line]
        assert len(schedule) == len(after.spaces) == 40
        cover = " ".join(texts[0].split())
        for index, level in enumerate(levels):
            assert f"A-{101 + index} {level.label}" in cover
            text = texts[sheet_index.index(f"A-{101 + index} {level.name}")]
            assert f"Level datum {level.elevation_m:+.2f} m" in text
            if level.elevation_m >= removed.elevation_m:
                original = next(old for old in before.levels if old.id == level.id)
                assert level.elevation_m == pytest.approx(original.elevation_m - height_m)
        structural_text = " ".join(texts[sheet_index.index("S-101")].split())
        assert "not the structural model of this architectural revision" in structural_text
