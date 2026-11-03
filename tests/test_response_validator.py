from datetime import date
import pytest
from irrigation_scheduler import build_schedule
from response_validator import collect_facts, extract_numbers, validate_explanation
from water_requirement_engine import EngineConfig, FieldInputs, estimate_water_requirement

TODAY = date(2026, 10, 20)


@pytest.fixture
def ctx():
    r = estimate_water_requirement(FieldInputs(eto_mm_day=4.0, soil_moisture_pct=25, moisture_is_volumetric=True,
                                               field_capacity_pct=30, wilting_point_pct=15, root_depth_m=0.5,
                                               area=1.0, irrigation_efficiency_pct=50.0, pump_flow_m3_per_h=10.0),
                                   EngineConfig(), TODAY)
    s = build_schedule(r, TODAY)
    return r, s, collect_facts(r, s)


def good(ctx):
    r, s, f = ctx
    n = f["numeric"]
    return (f"This is an educational prototype. The engine says plan irrigation for a later date, {s['review_date']}. "
            f"The estimated net requirement is {n['net_irrigation_mm']['value']:g} mm and the gross requirement is "
            f"{n['gross_irrigation_mm']['value']:g} mm. Some inputs are assumptions and the estimate is uncertain.")


def test_good_text_passes(ctx):
    r = validate_explanation(good(ctx), ctx[2])
    assert r["passed"], r["feedback"]


def codes(res):
    return {i["code"] for i in res["issues"]}


def test_changed_number(ctx):
    t = good(ctx).replace("net requirement is ", "net requirement is 9")
    assert "unsupported_number" in codes(validate_explanation(t, ctx[2]))


def test_changed_unit(ctx):
    n = ctx[2]["numeric"]["net_irrigation_mm"]["value"]
    t = good(ctx).replace(f"{n:g} mm", f"{n:g} litres")
    assert "unit_changed" in codes(validate_explanation(t, ctx[2]))


def test_unsupported_interval(ctx):
    assert "unsupported_interval" in codes(validate_explanation(good(ctx) + " Irrigate every 7 days.", ctx[2]))


def test_unsupported_date_number(ctx):
    assert "unsupported_number" in codes(validate_explanation(good(ctx) + " Also irrigate on 3 November.", ctx[2]))


def test_contradiction_irrigate_now(ctx):
    assert "contradiction" in codes(validate_explanation(good(ctx) + " You should irrigate now.", ctx[2]))


def test_negated_irrigate_now_is_ok(ctx):
    assert "contradiction" not in codes(validate_explanation(good(ctx) + " Do not irrigate now.", ctx[2]))


@pytest.mark.parametrize("extra,code", [(" Add urea fertilizer.", "fertilizer"), (" Spray pesticide.", "pesticide"),
                                        (" This guarantees higher yield.", "unsupported_claim"),
                                        (" Water saving of a lot.", "unsupported_claim")])
def test_forbidden_content(ctx, extra, code):
    assert code in codes(validate_explanation(good(ctx) + extra, ctx[2]))


def test_missing_values_and_warnings(ctx):
    t = "Irrigation is planned for a later date and the plan is an educational prototype with uncertain inputs."
    c = codes(validate_explanation(t, ctx[2]))
    assert {"missing_value", "missing_date"} <= c
    assert "missing_prototype_warning" in codes(validate_explanation(good(ctx).replace("prototype", "tool"), ctx[2]))


def test_uncertainty_retained():
    r = estimate_water_requirement(FieldInputs(), EngineConfig(), TODAY)
    s = build_schedule(r, TODAY)
    f = collect_facts(r, s)
    t = "This is an educational prototype. The farm looks fine and the system is clear for the farmer today."
    assert "missing_uncertainty" in codes(validate_explanation(t, f))


def test_ir_irrigate_now_contradicted_by_no_irrigation():
    r = estimate_water_requirement(FieldInputs(eto_mm_day=4.0, soil_moisture_pct=20, moisture_is_volumetric=True,
                                               field_capacity_pct=30, wilting_point_pct=15, root_depth_m=0.5), EngineConfig(), TODAY)
    s = build_schedule(r, TODAY)
    assert s["status_code"] == "IRRIGATE_NOW"
    t = "Educational prototype with assumptions. Skip irrigation this week. Net 60 mm."
    assert "contradiction" in codes(validate_explanation(t, collect_facts(r, s)))


def test_language_check(ctx):
    assert "wrong_language" in codes(validate_explanation(good(ctx), ctx[2], "hi"))


def test_devanagari_digits_and_units():
    assert extract_numbers("१२.५ mm और 3 m³ तथा 5 hours") == [(12.5, "mm"), (3.0, "m3"), (5.0, "hours")]
    assert extract_numbers("1. First\n2) Second 4 days") == [(4.0, "days")]
