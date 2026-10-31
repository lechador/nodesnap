"""Whole-building outputs derive from actual programs and canonical geometry."""
from __future__ import annotations

import math
import re

import pymupdf
import pytest

from app.analysis import compute_results
from domain.building import build_building
from domain.models import new_id
from engineering.services import build_inventories
from geometry.validate import validate_snapshot
from reports.pdf import build_review_package


def room(name, use, area, count=1, classification="principal"):
    return {"name": name, "use": use, "target_area_m2": area, "count": count,
            "classification": classification}


def building_programs():
    return {
        "small": {"title": "Two-bedroom garden home", "width_m": 12, "depth_m": 10,
                  "floors": [{"label": "Garden floor", "height_m": 3.1,
                              "rooms": [room("Living", "living", 24), room("Kitchen", "kitchen", 12),
                                        room("Bedroom", "bedroom", 14, 2), room("Bathroom", "bathroom", 6, classification="support")]}]},
        "workplace": {"title": "Three-floor creative workplace", "building_use": "office", "width_m": 24, "depth_m": 20,
                      "floors": [
                          {"label": "Arrival", "height_m": 3.8, "rooms": [room("Reception", "reception", 60), room("Office", "office", 28, 6), room("Meeting", "meeting", 40), room("WC", "bathroom", 8, 2, "support")]},
                          {"label": "Work studios", "height_m": 3.4, "rooms": [room("Studio", "studio", 42, 8), room("WC", "bathroom", 8, 2, "support")]},
                          {"label": "Workshops", "height_m": 4, "rooms": [room("Workshop", "workshop", 80, 3), room("WC", "bathroom", 8, 2, "support")]},
                      ]},
        "pool": {"title": "Pool residence with roof terrace", "width_m": 22, "depth_m": 18,
                 "floors": [
                     {"label": "Day floor", "height_m": 3.4, "rooms": [room("Living", "living", 48), room("Dining", "dining", 26), room("Kitchen", "kitchen", 24), room("Guest room", "bedroom", 24), room("Bathroom", "bathroom", 8, classification="support")]},
                     {"label": "Night floor", "height_m": 3.2, "rooms": [room("Bedroom", "bedroom", 30, 3), room("Study", "study", 20), room("Lounge", "family", 40), room("Bathroom", "bathroom", 8, 2, "support")]},
                 ],
                 "basement": {"label": "Leisure basement", "height_m": 3.4, "rooms": [room("Pool hall", "pool_hall", 100), room("Fitness", "fitness", 40), room("Changing", "changing", 8, classification="support"), room("Plant", "plant", 8, classification="support")]},
                 "pool": {"water_length_m": 8, "water_width_m": 3, "water_depth_m": 1.4, "level": "basement"},
                 "roof_terrace_area_m2": 60},
        "dense": {"title": "Twenty-room working floor", "building_use": "office", "width_m": 40, "depth_m": 30,
                  "floors": [{"label": "Studios", "height_m": 3.4,
                              "rooms": [room("North office", "office", 30, 10), room("South office", "office", 30, 8), room("WC", "bathroom", 8, 2, "support")]}]},
        "large": {"title": "Four-hall exhibition building", "building_use": "exhibition", "width_m": 60, "depth_m": 60,
                  "floors": [{"label": "Exhibitions", "height_m": 4.5,
                              "rooms": [room("Exhibition hall", "gallery", 500, 4), room("WC", "bathroom", 10, 2, "support")]}]},
    }


@pytest.fixture(scope="module")
def buildings():
    return {name: build_building(new_id(), program) for name, program in building_programs().items()}


def test_small_house_services_reconcile_with_independent_envelope_and_no_pool(buildings):
    snapshot = buildings["small"]
    assert validate_snapshot(snapshot) == []
    assert snapshot.pool is None
    assert {level.name for level in snapshot.levels} == {"ground", "roof"}
    inventories = build_inventories(snapshot)
    hvac = inventories["hvac_energy"]
    # Single 3.1m storey, 250mm slab; no occupied roof enclosure.
    gross = 2*(12+10)*(3.1-.25)
    reconciliation = hvac["area_reconciliation"]
    assert reconciliation["gross_wall_area_m2"] == pytest.approx(gross)
    assert sum(reconciliation[key] for key in ("opaque_wall_area_m2", "window_area_m2", "door_area_m2", "unfilled_opening_area_m2")) == pytest.approx(gross)
    assert inventories["drainage"]["roof_area_m2"] == pytest.approx(120)
    assert inventories["drainage"]["runoff_l_s"] == pytest.approx(.95*100*120/3600)
    assert inventories["drainage"]["terrace_area_m2"] == 0
    assert not any("Pool" in item["name"] for item in inventories["electrical"]["items"])
    assert len(inventories["plumbing"]["fixtures"]) == 5  # bathroom3 + kitchen2
    assert all(component["revision_id"] == snapshot.revision_id for component in inventories.values() if isinstance(component, dict))


def test_requested_pool_uses_its_geometry_without_seed_defaults(buildings):
    snapshot = buildings["pool"]
    results = compute_results(snapshot)
    quantity = next(result for result in results if result["method_id"] == "pool_quantities")["quantities"]
    assert quantity["surface_area_m2"] == 24
    assert quantity["volume_m3"] == pytest.approx(33.6)
    drainage = build_inventories(snapshot)["drainage"]
    assert drainage["roof_area_m2"] == pytest.approx(22*18)
    assert sum(item["area_m2"] for item in drainage["catchments"]) == pytest.approx(396)
    assert drainage["terrace_area_m2"] == pytest.approx(60)


@pytest.mark.parametrize("name,expected_scale", [("small",50),("workplace",100),("pool",100),("dense",200),("large",300)])
def test_actual_pdf_plans_gross_area_true_scale_and_optional_content(buildings,name,expected_scale):
    snapshot = buildings[name]
    program = building_programs()[name]
    assert validate_snapshot(snapshot) == []
    results = compute_results(snapshot)
    pdf, index = build_review_package(snapshot, results)
    with pymupdf.open(stream=pdf,filetype="pdf") as document:
        assert len(document)==len(index)
        texts = [page.get_text() for page in document]
        assert all(snapshot.revision_id in text and snapshot.content_hash[:16] in text for text in texts)
        assert all(sheet in text for sheet,text in zip(index,texts))
        plans = [(page,text,sheet) for page,text,sheet in zip(document,texts,index) if sheet.startswith("A-")]
        assert len(plans)==len(snapshot.levels)
        for page,text,sheet in plans:
            assert f'{program["width_m"]:.3f} m OUTSIDE' in text
            assert f'{program["depth_m"]:.3f} m OUTSIDE' in text
            assert f'1:{expected_scale} at ARCH B / print at 100%' in text
            assert f'{program["width_m"]*program["depth_m"]:,.2f} m2' in text
            # Measured vector geometry establishes scale independently of the label.
            expected_width=program["width_m"]*1000/expected_scale*72/25.4
            assert any(item[0]=="re" and math.isclose(item[1].width,expected_width,abs_tol=.01)
                       for drawing in page.get_drawings() for item in drawing["items"])
        schedule="\n".join(text for sheet,text in zip(index,texts) if sheet.startswith("CALC-101"))
        assert len([line for line in schedule.splitlines() if re.search(r"\sactual\s+[0-9]",line)])==len(snapshot.spaces)
        if not snapshot.pool:
            assert "No pool is modeled in this revision" in schedule
            assert "Pool water:" not in schedule
            assert "pool quantities" not in texts[0]
            assert all(result["method_id"]!="pool_quantities" for result in results)
        if name=="dense":
            assert any(sheet.startswith("AR-") for sheet in index)
            full_register="\n".join(text for sheet,text in zip(index,texts) if sheet.startswith(("A-","AR-")))
            for number in range(1,len([space for space in snapshot.spaces if space.level_id==snapshot.levels[0].id])+1):
                assert f"R{number:02d}" in full_register
        structural=texts[index.index("S-101")]
        assert "not the structural model of this architectural revision" in " ".join(structural.split())
        for page in document:
            assert all(0<=span["bbox"][0]<span["bbox"][2]<=page.rect.width and 0<=span["bbox"][1]<span["bbox"][3]<=page.rect.height
                       for span in page.get_texttrace())
