"""Independent surface quantities, service scope and measured PDF site geometry."""
from __future__ import annotations

import math

import pymupdf
import pytest

from app.analysis import compute_results
from domain.building import build_building
from domain.models import new_id
from engineering.registry import METHODS, methods_for_snapshot
from engineering.services import build_inventories, site_surface_quantities
from reports.pdf import build_review_package


def private_home_program(**overrides):
    return {
        "title": "Private garden home", "width_m": 12, "depth_m": 10,
        "floors": [{"label": "Ground", "height_m": 3.1, "rooms": [
            {"name": "Living", "use": "living", "target_area_m2": 24},
            {"name": "Kitchen", "use": "kitchen", "target_area_m2": 12},
            {"name": "Bedroom", "use": "bedroom", "target_area_m2": 14, "count": 2},
            {"name": "Bathroom", "use": "bathroom", "target_area_m2": 6, "classification": "support"},
        ]}],
        "yard": {"width_m": 12, "depth_m": 8},
        "garage": {"width_m": 3.6, "depth_m": 6, "height_m": 2.8, "vehicle_door_width_m": 2.6},
        "pool": {"water_length_m": 6, "water_width_m": 3, "water_depth_m": 1.4,
                 "level": "ground", "location": "outdoor"},
        **overrides,
    }


@pytest.fixture(scope="module")
def private_home():
    return build_building(new_id(), private_home_program())


def test_site_quantities_separate_grass_deck_water_and_unconditioned_garage(private_home):
    q = site_surface_quantities(private_home)
    assert q["revision_id"] == private_home.revision_id
    assert q["input_hash"] == private_home.content_hash
    assert q["yard_gross_area_m2"] == pytest.approx(12*8)
    assert q["yard_grass_area_m2"] == pytest.approx(12*8-7.2*4.2)
    assert q["pool_deck_area_m2"] == pytest.approx(7.2*4.2-6*3)
    assert q["outdoor_pool_water_area_m2"] == pytest.approx(6*3)
    assert sum(q[key] for key in ("yard_grass_area_m2", "pool_deck_area_m2", "outdoor_pool_water_area_m2")) == pytest.approx(q["yard_gross_area_m2"])
    assert q["garage_gross_floor_area_m2"] == pytest.approx(3.6*6)
    assert q["garage_clear_floor_area_m2"] == pytest.approx((3.6-.4)*(6-.4))
    assert q["driveway_area_m2"] == pytest.approx(3.6*6)
    assert "not enclosed floor area" in q["area_basis"]


def test_garage_roof_runoff_is_added_but_house_conduction_is_not(private_home):
    base = build_building(new_id(), private_home_program(yard=None, garage=None, pool=None))
    baseline = build_inventories(base)
    services = build_inventories(private_home)
    drainage, thermal = services["drainage"], services["hvac_energy"]
    assert thermal["total_conduction_w"] == pytest.approx(baseline["hvac_energy"]["total_conduction_w"])
    assert thermal["area_reconciliation"] == baseline["hvac_energy"]["area_reconciliation"]
    assert thermal["excluded_site_buildings"][0]["conditioning"] == "unconditioned"
    assert drainage["house_roof_area_m2"] == pytest.approx(120)
    assert drainage["garage_roof_area_m2"] == pytest.approx(21.6)
    assert drainage["roof_area_m2"] == pytest.approx(141.6)
    assert drainage["runoff_l_s"] == pytest.approx(.95*100*141.6/3600)
    assert sum(item["area_m2"] for item in drainage["catchments"]) == pytest.approx(141.6)
    assert private_home.site_layout.garage.id in drainage["roof_object_ids"]
    assert "Yard, paving and pool-deck runoff are excluded" in drainage["note"]
    assert thermal["pool_environment"]["indoor_dehumidification_applicable"] is False
    assert thermal["pool_environment"]["execution_status"] == "blocked"
    assert thermal["pool_environment"]["check_outcome"] == "not_evaluated"
    assert services["site_features"]["revision_id"] == private_home.revision_id
    assert len(services["plumbing"]["fixtures"]) == len(baseline["plumbing"]["fixtures"])
    assert not any("garage" in item["name"].lower() for item in services["electrical"]["items"])


def test_outdoor_pool_coverage_cannot_inherit_indoor_method_applicability(private_home):
    original = next(method for method in METHODS if method.id == "pool_environment")
    original_data = original.model_dump(mode="json")
    scoped = next(method for method in methods_for_snapshot(private_home) if method.id == "pool_environment")
    assert scoped.method_state.value == "research_required"
    assert "indoor dehumidification is not applicable" in scoped.purpose
    assert "No outdoor-pool method" in scoped.source
    assert "No outdoor evaporation" in scoped.exclusions
    assert original.model_dump(mode="json") == original_data
    plain = build_building(new_id(), private_home_program(yard=None, garage=None, pool=None))
    assert next(method for method in methods_for_snapshot(plain) if method.id == "pool_environment").model_dump(mode="json") == original_data


def test_site_pdf_true_scale_and_revision_identity(private_home):
    pdf, sheets = build_review_package(private_home, compute_results(private_home))
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        assert len(document) == len(sheets)
        texts = [page.get_text() for page in document]
        assert all(private_home.revision_id in text and private_home.content_hash[:16] in text for text in texts)
        assert "coordinated concept extent 23.1 x 31 m" in " ".join(texts[0].split())
        site = document[sheets.index("C-101")]
        text = site.get_text()
        assert "1:200 at ARCH B / print at 100%" in text
        for phrase in ("YARD / OPEN AIR", "DETACHED GARAGE / UNCONDITIONED", "DRIVEWAY / OPEN AIR", "OUTDOOR POOL WATER", "POOL DECK / OPEN AIR", "not a surveyed lot"):
            assert phrase in text
        assert "6.000 x 3.000 x 1.400 m deep" in text
        assert "2.600 x 2.200 m" in text
        # Independent PDF-vector check: 6 x 3 m water at true 1:200 print scale.
        expected_width, expected_height = 6*1000/200*72/25.4, 3*1000/200*72/25.4
        assert any(item[0] == "re" and math.isclose(item[1].width, expected_width, abs_tol=.01)
                   and math.isclose(item[1].height, expected_height, abs_tol=.01)
                   for drawing in site.get_drawings() for item in drawing["items"])
        house_plans = [text for sheet, text in zip(sheets, texts) if sheet.startswith("A-")]
        assert all("POOL WATER" not in text for text in house_plans)
        services = "\n".join(text for sheet, text in zip(sheets, texts) if sheet.startswith("MPE-101"))
        assert "indoor dehumidification is not applicable" in services
        assert "roof 21.60 m2" in services
        schedule = "\n".join(text for sheet, text in zip(sheets, texts) if sheet.startswith("CALC-101"))
        assert "Location: outdoor" in schedule
        for page in document:
            assert all(0 <= span["bbox"][0] < span["bbox"][2] <= page.rect.width and 0 <= span["bbox"][1] < span["bbox"][3] <= page.rect.height
                       for span in page.get_texttrace())


def test_yard_only_and_garage_only_site_drawings_remain_valid():
    for features, expected, absent in [
        ({"garage": None, "pool": None}, "YARD / OPEN AIR", "OUTDOOR POOL WATER"),
        ({"yard": None, "pool": None}, "DETACHED GARAGE / UNCONDITIONED", "YARD / OPEN AIR"),
    ]:
        snapshot = build_building(new_id(), private_home_program(**features))
        pdf, sheets = build_review_package(snapshot)
        with pymupdf.open(stream=pdf, filetype="pdf") as document:
            text = document[sheets.index("C-101")].get_text()
            assert expected in text and absent not in text
            assert snapshot.revision_id in text
