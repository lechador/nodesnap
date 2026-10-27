"""M4: hand-checked component math + inventory integrity."""
from domain.models import new_id
from domain.seed import build_seed
from engineering.services import (build_inventories, conduction_w,
                                  electrical_totals, plumbing_totals,
                                  roof_runoff_l_s)


def test_conduction_hand_check():
    assert conduction_w(100.0, 0.3, 20.0) == 600.0


def test_runoff_conversion():
    # 0.95 * 100 mm/h * 279 m2 / 3600 = 7.3625 L/s
    assert abs(roof_runoff_l_s(279.0, 100.0, 0.95) - 7.3625) < 1e-9


def test_electrical_current_model():
    out = electrical_totals([{"name": "x", "power_w": 2400, "count": 2}], voltage_v=240.0)
    assert out["connected_load_w"] == 4800
    assert out["current_at_connected_load_a"] == 20.0
    assert out["demand_load_w"] is None  # no invented demand factor


def test_plumbing_sum():
    out = plumbing_totals([{"name": "shower", "flow_l_min": 9.0, "count": 2}])
    assert out["sum_of_fixture_flows_l_min"] == 18.0


def test_inventories_from_seed():
    snap = build_seed(new_id())
    inv = build_inventories(snap)
    assert inv["plumbing"]["sum_of_fixture_flows_l_min"] > 0
    assert inv["electrical"]["connected_load_w"] > 19250  # equipment alone sums to 19,250 W
    assert inv["hvac_energy"]["total_conduction_w"] > 0
    assert inv["drainage"]["runoff_l_s"] > 0
    # equipment input powers are electrical inputs, not thermal outputs
    names = [i["name"] for i in inv["electrical"]["items"]]
    assert any("Pool heater" in n for n in names)
