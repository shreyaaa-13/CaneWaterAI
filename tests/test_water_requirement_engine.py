from datetime import date
import pytest
from water_requirement_engine import (ACRE_TO_HA, EngineConfig, FieldInputs, area_in_ha, depth_to_volume_m3,
                                      estimate_water_requirement, rainfall_scenarios, water_availability_scenarios)

TODAY = date(2026, 10, 20)


def run(**kw):
    return estimate_water_requirement(FieldInputs(**kw), EngineConfig(), TODAY)


def test_valid_inputs_without_eto_are_provisional():
    r = run()
    assert r["valid"] and r["provisional"]
    assert r["estimates"]["net_irrigation_mm"] is None
    assert "eto" in r["missing_inputs"]
    assert "NOT calculated" in r["advisory_reason"]


@pytest.mark.parametrize("m", [-1, 100.1, None])
def test_invalid_moisture(m):
    r = run(soil_moisture_pct=m)
    assert not r["valid"] and r["errors"]


@pytest.mark.parametrize("age", [-0.1, 25, None])
def test_invalid_age(age):
    assert not run(crop_age_months=age)["valid"]


def test_stage_age_inconsistency_warns_and_keeps_selection():
    r = run(crop_age_months=11, growth_stage="Germination")
    assert r["valid"] and any("outside the illustrative range" in w for w in r["warnings"])
    assert r["inputs_used"]["growth_stage"] == "Germination"


def test_planting_date_inconsistency_and_future():
    assert any("Planting date implies" in w for w in run(planting_date=date(2026, 1, 1), crop_age_months=2)["warnings"])
    assert any("future" in w for w in run(planting_date=date(2027, 1, 1))["warnings"])


def test_etc_and_demand_no_soil_data():
    r = run(eto_mm_day=5.0, growth_stage="Grand growth")
    e = r["estimates"]
    assert e["etc_mm_day"] == pytest.approx(6.25)          # 1.25 x 5
    assert e["crop_demand_mm"] == pytest.approx(43.75)     # x 7 days
    assert e["net_irrigation_mm"] == pytest.approx(43.75)  # rainfall 'None' -> 0 mm
    assert e["net_basis"] == "demand_minus_effective_rain"
    assert any("No soil-water credit" in w for w in r["warnings"])


def test_rainfall_mm_reduces_requirement():
    e = run(eto_mm_day=5.0, rainfall_category="Moderate", rainfall_mm=20.0)["estimates"]
    assert e["effective_rain_mm"] == pytest.approx(16.0)
    assert e["net_irrigation_mm"] == pytest.approx(43.75 - 16.0)


def test_rain_larger_than_demand_gives_zero_not_negative():
    e = run(eto_mm_day=2.0, rainfall_category="Heavy", rainfall_mm=100.0)["estimates"]
    assert e["net_irrigation_mm"] == 0.0 and e["rain_minus_demand_mm"] > 0


def test_unquantified_rain_gives_no_credit_and_warns():
    r = run(eto_mm_day=5.0, rainfall_category="Light")
    assert r["estimates"]["rainfall_credit_applied"] is False
    assert "rainfall_mm" in r["missing_inputs"]


def test_category_mm_mismatch_warns():
    r = run(eto_mm_day=5.0, rainfall_category="None", rainfall_mm=30.0)
    assert any("does not match" in w for w in r["warnings"])


def test_soil_water_balance():
    r = run(eto_mm_day=4.0, growth_stage="Grand growth", soil_moisture_pct=25, moisture_is_volumetric=True,
            field_capacity_pct=30, wilting_point_pct=15, root_depth_m=0.5)
    e = r["estimates"]
    assert e["taw_mm"] == pytest.approx(75.0)
    assert e["raw_mm"] == pytest.approx(48.75)
    assert e["depletion_now_mm"] == pytest.approx(25.0)
    assert e["depletion_end_mm"] == pytest.approx(60.0)    # 25 + 35 - 0
    assert e["net_irrigation_mm"] == pytest.approx(60.0) and e["net_basis"] == "soil_water_balance"


def test_generic_moisture_is_not_treated_as_volumetric():
    r = run(eto_mm_day=4.0, soil_moisture_pct=25, moisture_is_volumetric=False,
            field_capacity_pct=30, wilting_point_pct=15, root_depth_m=0.5)
    assert "taw_mm" not in r["estimates"] and "soil_water_data" in r["missing_inputs"]


def test_fc_must_exceed_pwp():
    assert not run(field_capacity_pct=15, wilting_point_pct=20)["valid"]


def test_unit_conversions():
    assert depth_to_volume_m3(1, 1) == 10
    assert area_in_ha(10, "acre") == pytest.approx(10 * ACRE_TO_HA)
    assert area_in_ha(2, "ha") == 2 and area_in_ha(None, "ha") is None


def test_gross_requires_user_efficiency_and_volume_math():
    r = run(eto_mm_day=5.0, area=2.0, area_unit="ha")
    assert r["estimates"]["gross_irrigation_mm"] is None and "efficiency" in r["missing_inputs"]
    assert r["estimates"]["net_volume_m3"] == pytest.approx(43.75 * 2 * 10)
    r = run(eto_mm_day=5.0, area=2.0, irrigation_efficiency_pct=70.0, irrigation_method="Drip")
    assert r["estimates"]["gross_irrigation_mm"] == pytest.approx(43.75 / 0.7)
    assert r["estimates"]["gross_volume_m3"] == pytest.approx(43.75 / 0.7 * 20)


def test_method_does_not_change_numbers():
    a = run(eto_mm_day=5.0, irrigation_method="Drip")["estimates"]["net_irrigation_mm"]
    b = run(eto_mm_day=5.0, irrigation_method="Flood/furrow")["estimates"]["net_irrigation_mm"]
    assert a == b


@pytest.mark.parametrize("kw", [dict(eto_mm_day=16), dict(rainfall_mm=501), dict(area=0), dict(irrigation_efficiency_pct=0),
                                dict(pump_flow_m3_per_h=0), dict(available_water_m3=-1), dict(root_depth_m=5)])
def test_numeric_range_validation(kw):
    assert not run(**kw)["valid"]


def test_scenarios():
    rows = rainfall_scenarios(FieldInputs(eto_mm_day=5.0), [0, 10, 40])
    nets = [r["net_irrigation_mm"] for r in rows]
    assert nets == sorted(nets, reverse=True)
    r = run(eto_mm_day=5.0, area=1.0, irrigation_efficiency_pct=50.0)
    rows = water_availability_scenarios(r, [100, 1000])
    assert rows[0]["coverage_pct"] < rows[1]["coverage_pct"] and rows[0]["basis"] == "gross"
