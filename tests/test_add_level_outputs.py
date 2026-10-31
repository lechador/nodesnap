"""Added-storey quantities and actual PDF pages, independent of chat/provider output."""
from __future__ import annotations

import math

import pymupdf
import pytest

from app.analysis import compute_results, with_freshness
from domain.commands import MAX_LIVING_LEVELS, apply_commands
from domain.models import new_id
from domain.seed import build_seed
from engineering.services import build_inventories
from reports.pdf import build_review_package


@pytest.fixture(scope="module")
def revisions():
    seed = build_seed(new_id())
    third = apply_commands(seed, [{"type": "add_level"}])
    fourth = apply_commands(third, [{"type": "add_level"}])
    return [(snapshot, compute_results(snapshot)) for snapshot in (seed, third, fourth)]


@pytest.mark.parametrize("height_m", [3.4, 4.0])
def test_added_storey_envelope_matches_closed_form(height_m):
    seed = build_seed(new_id())
    changed = apply_commands(seed, [{"type": "add_level", "height_m": height_m}])
    before = build_inventories(seed)["hvac_energy"]
    after = build_inventories(changed)["hvac_energy"]
    a, b = before["area_reconciliation"], after["area_reconciliation"]
    # 18 x 15.5m enclosure: 67m perimeter, 250mm slab between storeys.
    gross = 67 * (height_m - .25)
    # Independent seed-window schedule: eight principal openings (six north/
    # south plus two west) and four 1.8 x 1.15m support-room windows. Room
    # widths use the declared 420:260:240 and 240:380:300 strips, each15m wide.
    principal_width = 4 * 4.4 + 2 * (15 * 240 / 920 - .8) + (15 * 260 / 920 - .8) + (15 * 300 / 920 - .8)
    glazing = principal_width * 2.35 + 4 * 1.8 * 1.15
    assert b["gross_wall_area_m2"] - a["gross_wall_area_m2"] == pytest.approx(gross)
    assert b["window_area_m2"] - a["window_area_m2"] == pytest.approx(glazing)
    assert b["opaque_wall_area_m2"] - a["opaque_wall_area_m2"] == pytest.approx(gross - glazing)
    assert b["door_area_m2"] == a["door_area_m2"]
    assert b["unfilled_opening_area_m2"] == 0
    # Declared scenario assumptions, not code inputs or equipment capacities.
    expected_delta_w = ((gross - glazing) * .30 + glazing * 1.60) * 22
    assert after["total_conduction_w"] - before["total_conduction_w"] == pytest.approx(expected_delta_w)
    assert after["revision_id"] == changed.revision_id
    assert all(row["revision_id"] == changed.revision_id for row in after["envelope_conduction"])


def test_added_lighting_and_fixtures_count_only_new_spaces(revisions):
    seed, third, fourth = [pair[0] for pair in revisions]
    for before, after in ((seed, third), (third, fourth)):
        old, new = build_inventories(before), build_inventories(after)
        new_ids = {space.id for space in after.spaces} - {space.id for space in before.spaces}
        added_lighting = [item for item in new["electrical"]["items"] if item.get("space_id") in new_ids]
        # Two strips, each6.95m deep less300mm outer and75mm inner wall.
        # Across three rooms,15m less300mm exterior + five75mm deductions.
        clear_area = 2 * (6.95 - .30 - .075) * (15 - .30 - 5 * .075)
        assert len(added_lighting) == 6
        assert sum(item["clear_area_m2"] for item in added_lighting) == pytest.approx(clear_area)
        assert new["electrical"]["connected_load_w"] - old["electrical"]["connected_load_w"] == pytest.approx(clear_area * 12)
        assert len(new["plumbing"]["fixtures"]) - len(old["plumbing"]["fixtures"]) == 3
        assert new["plumbing"]["sum_of_fixture_flows_l_min"] - old["plumbing"]["sum_of_fixture_flows_l_min"] == 20
        old_allowances = {item["space_id"]: item["power_w"] for item in old["electrical"]["items"] if "space_id" in item}
        assert all(item["power_w"] == old_allowances[item["space_id"]] for item in new["electrical"]["items"] if item.get("space_id") in old_allowances)


def test_raised_roof_keeps_one_projected_catchment(revisions):
    base_ids = None
    for snapshot, _ in revisions:
        drainage = build_inventories(snapshot)["drainage"]
        assert drainage["roof_area_m2"] == pytest.approx(18 * 15.5)
        assert drainage["terrace_area_m2"] == pytest.approx(9 * 9.29)
        assert sum(zone["area_m2"] for zone in drainage["catchments"]) == pytest.approx(279)
        assert drainage["runoff_l_s"] == pytest.approx(.95 * 100 * 279 / 3600)
        assert all(zone["revision_id"] == snapshot.revision_id for zone in drainage["catchments"])
        if base_ids is None:
            base_ids = drainage["roof_object_ids"]
        assert drainage["roof_object_ids"] == base_ids


def test_results_are_revision_bound_and_fixed_frame_does_not_claim_added_capacity(revisions):
    seed, seed_results = revisions[0]
    before_frame = next(result for result in seed_results if result["method_id"] == "structural_frame_analysis")
    for snapshot, results in revisions[1:]:
        assert all(result["revision_id"] == snapshot.revision_id and result["input_hash"] == snapshot.content_hash for result in results)
        assert all(result["freshness_status"] == "stale" for result in with_freshness(seed_results, snapshot.revision_id))
        architecture = next(result for result in results if result["method_id"] == "area_schedule")
        assert {row["space_id"] for row in architecture["schedule"]} == {space.id for space in snapshot.spaces}
        assert all(row["revision_id"] == snapshot.revision_id for row in architecture["schedule"])
        frame = next(result for result in results if result["method_id"] == "structural_frame_analysis")
        assert frame["execution_status"] == "completed"
        assert frame["quantities"] == before_frame["quantities"]
        for result in results:
            assert result["check_outcome"] == "not_evaluated"
            if result["discipline"] in {"structure", "foundations"}:
                assert any(issue["code"] == "OUTSIDE_METHOD_DOMAIN" and issue.get("field") == "model_coupling" for issue in result["issues"])


@pytest.mark.parametrize("revision_index", [0, 1, 2])
def test_pdf_index_every_level_schedule_and_scale(revisions, revision_index):
    snapshot, results = revisions[revision_index]
    pdf, sheet_index = build_review_package(snapshot, results)
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        texts = [page.get_text() for page in document]
        assert len(document) == len(sheet_index)
        assert len(document) == (11, 14, 15)[revision_index]
        assert all(snapshot.revision_id in text and snapshot.content_hash[:16] in text for text in texts)
        assert all(sheet in text for sheet, text in zip(sheet_index, texts))
        levels = sorted(snapshot.levels, key=lambda level: level.elevation_m)
        plan_pages = [(index, sheet) for index, sheet in enumerate(sheet_index) if sheet.startswith("A-")]
        assert [sheet for _, sheet in plan_pages] == [f"A-{101 + index} {level.name}" for index, level in enumerate(levels)]
        cover = " ".join(texts[0].split())
        for (page_index, _), level in zip(plan_pages, levels):
            page, text = document[page_index], texts[page_index]
            assert level.label in text
            assert f"Level datum {level.elevation_m:+.2f} m" in text
            assert "1:75 at ARCH B / print at 100%" in text
            assert "18.000 m OUTSIDE" in text and "15.500 m OUTSIDE" in text
            assert page.rect.width == 18 * 72 and page.rect.height == 12 * 72
            assert f"A-{101 + levels.index(level)} {level.label}" in cover
            # Verify the actual vector rectangle width, not just a scale label.
            expected_width = 18 * 1000 / 75 * 72 / 25.4
            assert any(item[0] == "re" and math.isclose(item[1].width, expected_width, abs_tol=.01)
                       for drawing in page.get_drawings() for item in drawing["items"])
        schedule = "\n".join(text for sheet, text in zip(sheet_index, texts) if sheet.startswith("CALC-101"))
        for level in levels:
            assert sum(line.startswith(level.label) for line in schedule.splitlines()) == sum(space.level_id == level.id for space in snapshot.spaces)
        structural = texts[sheet_index.index("S-101")]
        assert "No capacity for an added level is established." in " ".join(structural.split())


def test_pdf_at_level_ceiling_preserves_all_pages_and_continuation_titles():
    snapshot = build_seed(new_id())
    for _ in range(MAX_LIVING_LEVELS - snapshot.brief.floors_above_ground):
        snapshot = apply_commands(snapshot, [{"type": "add_level"}])
    pdf, sheet_index = build_review_package(snapshot, compute_results(snapshot))
    assert snapshot.brief.floors_above_ground == MAX_LIVING_LEVELS == 12
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        assert len(document) == len(sheet_index) == 29
        assert len([sheet for sheet in sheet_index if sheet.startswith("A-")]) == len(snapshot.levels) == 14
        assert sheet_index.count("A-113 level_12") == 1
        assert sheet_index.count("A-114 roof") == 1
        texts = [page.get_text() for page in document]
        cover = " ".join(text for sheet, text in zip(sheet_index, texts) if sheet.startswith("COVER"))
        assert "A-113 Level 12" in cover and "A-114 Roof / terrace" in cover
        schedule_rows = [line for sheet, text in zip(sheet_index, texts) if sheet.startswith("CALC-101")
                         for line in text.splitlines() if " actual " in line]
        assert len(schedule_rows) == len(snapshot.spaces) == 130
        register_titles = [text.splitlines()[0] for sheet, text in zip(sheet_index, texts) if sheet.startswith("REG-101")]
        assert len(register_titles) >= 3  # Exercise repeated automatic page breaks.
        assert all(title.count("(continued)") == 1 for title in register_titles[1:])
        assert len(set(register_titles[1:])) == 1
        for page, sheet, text in zip(document, sheet_index, texts):
            assert snapshot.revision_id in text and sheet in text
            # Full text trace retains drawing extents, independently of extraction
            # that could omit a glyph clipped beyond the page boundary.
            assert all(0 <= span["bbox"][0] < span["bbox"][2] <= page.rect.width
                       and 0 <= span["bbox"][1] < span["bbox"][3] <= page.rect.height
                       for span in page.get_texttrace())
