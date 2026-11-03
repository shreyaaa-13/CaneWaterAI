from datetime import date
import pytest
from irrigation_scheduler import build_schedule
from water_requirement_engine import EngineConfig, FieldInputs, estimate_water_requirement

TODAY = date(2026, 10, 20)
SOIL = dict(moisture_is_volumetric=True, field_capacity_pct=30, wilting_point_pct=15, root_depth_m=0.5)


def sched(**kw):
    r = estimate_water_requirement(FieldInputs(**kw), EngineConfig(), TODAY)
    return build_schedule(r, TODAY)


def test_insufficient_data_has_no_schedule():
    s = sched()
    assert s["status_code"] == "INSUFFICIENT_DATA" and s["rows"] == [] and s["review_date"] is None


def test_invalid_input_has_no_schedule():
    assert sched(soil_moisture_pct=200)["status_code"] == "INSUFFICIENT_DATA"


def test_irrigate_now_when_depletion_reaches_raw():
    s = sched(eto_mm_day=4.0, soil_moisture_pct=20, **SOIL)       # Dr=50 >= RAW 48.75
    assert s["status_code"] == "IRRIGATE_NOW" and s["review_date"] == "2026-10-20"


def test_schedule_later_projects_date():
    s = sched(eto_mm_day=4.0, soil_moisture_pct=25, **SOIL)       # Dr=25, RAW=48.75, 5 mm/day -> 4 days
    assert s["status_code"] == "SCHEDULE_LATER" and s["review_in_days"] == 4
    assert s["review_date"] == "2026-10-24"


def test_defer_when_rain_covers_demand():
    s = sched(eto_mm_day=4.0, soil_moisture_pct=28, rainfall_category="Heavy", rainfall_mm=60, **SOIL)
    assert s["status_code"] == "DEFER_REASSESS" and s["review_in_days"] == 7


def test_heavy_unquantified_rain_defers():
    s = sched(eto_mm_day=4.0, soil_moisture_pct=20, rainfall_category="Heavy", **SOIL)
    assert s["status_code"] == "DEFER_REASSESS"
    assert any("Heavy rain" in r for r in s["reasons"])


def test_without_soil_data_review_pending():
    s = sched(eto_mm_day=5.0)
    assert s["status_code"] == "REVIEW_PENDING_SOIL_DATA" and s["net_irrigation_mm"] == pytest.approx(43.75)


def test_duration_needs_gross_volume_and_flow():
    kw = dict(eto_mm_day=4.0, soil_moisture_pct=20, area=1.0, **SOIL)
    assert sched(**kw)["irrigation_duration_h"] is None
    s = sched(irrigation_efficiency_pct=50.0, pump_flow_m3_per_h=10.0, **kw)
    assert s["irrigation_duration_h"] == pytest.approx(s["gross_volume_m3"] / 10.0)


def test_water_sufficiency():
    kw = dict(eto_mm_day=4.0, soil_moisture_pct=20, area=1.0, irrigation_efficiency_pct=50.0, **SOIL)
    assert sched(available_water_m3=10, **kw)["water_sufficient"] is False
    assert sched(available_water_m3=100000, **kw)["water_sufficient"] is True


def test_soil_only_no_eto():
    s = sched(soil_moisture_pct=20, **SOIL)
    assert s["status_code"] == "IRRIGATE_NOW"
    s = sched(soil_moisture_pct=28, **SOIL)
    assert s["status_code"] == "DEFER_REASSESS"
