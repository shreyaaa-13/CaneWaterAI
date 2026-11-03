"""Automated pytest suite for the ReAct-Reflexion Self-Correction Framework."""
from __future__ import annotations

from datetime import date
import pytest

from irrigation_scheduler import build_schedule
from response_validator import collect_facts, validate_explanation
from self_correction import (
    DEMO_SCENARIOS,
    STATUS_API_UNAVAILABLE,
    STATUS_CORRECTION_SUCCESSFUL,
    STATUS_FALLBACK_USED,
    STATUS_INITIAL_VALID,
    STATUS_MAX_ATTEMPTS_REACHED,
    MockLLMClient,
    SelfCorrectionConfig,
    build_valid_explanation,
    compute_experiment_metrics,
    run_self_correction_framework,
)
from water_requirement_engine import EngineConfig, FieldInputs, estimate_water_requirement

TODAY = date(2026, 10, 20)


@pytest.fixture
def field_context():
    """Provides standard sugarcane field parameters and deterministic calculation results."""
    inputs = FieldInputs(
        crop_age_months=6.0,
        growth_stage="Grand growth",
        eto_mm_day=4.5,
        soil_moisture_pct=24.0,
        moisture_is_volumetric=True,
        field_capacity_pct=32.0,
        wilting_point_pct=16.0,
        root_depth_m=0.6,
        area=1.5,
        irrigation_efficiency_pct=80.0,
        pump_flow_m3_per_h=12.0,
        rainfall_category="Light",
    )
    result = estimate_water_requirement(inputs, EngineConfig(), TODAY)
    schedule = build_schedule(result, TODAY)
    facts = collect_facts(result, schedule)
    return result, schedule, facts


def test_build_valid_explanation_passes_validator_all_languages(field_context):
    """Verify that build_valid_explanation satisfies all validator guardrails in en, hi, and mr."""
    result, schedule, facts = field_context
    for lang in ("en", "hi", "mr"):
        explanation = build_valid_explanation(facts, lang)
        v = validate_explanation(explanation, facts, lang)
        assert v["passed"], f"Failed for {lang}: {v.get('feedback')}"


def test_tc01_valid_initial_response(field_context):
    """TC01: Initial response is valid; passes without correction on attempt 1."""
    result, schedule, _ = field_context
    res = run_self_correction_framework(
        result,
        schedule,
        language="en",
        mock_scenario_id="TC01",
    )
    assert res.overall_status == STATUS_INITIAL_VALID
    assert res.total_attempts == 1
    assert res.initial_passed is True
    assert res.corrected is False
    assert res.fallback_used is False
    assert res.source == "ai"
    assert len(res.attempts_history) == 1
    assert res.attempts_history[0].validation_passed is True


def test_tc02_incorrect_numerical_value_detected(field_context):
    """TC02: Initial explanation alters numerical value; validator intercepts mismatch."""
    result, schedule, _ = field_context
    config = SelfCorrectionConfig(max_correction_attempts=2)
    res = run_self_correction_framework(
        result,
        schedule,
        language="en",
        config=config,
        mock_scenario_id="TC02",
    )
    assert res.fallback_used is True
    assert res.source == "fallback"
    # All attempts should have reported unsupported_number
    assert len(res.attempts_history) == 3  # 1 initial + 2 retries
    for attempt in res.attempts_history:
        assert not attempt.validation_passed
        issue_codes = [iss["code"] for iss in attempt.issues]
        assert "unsupported_number" in issue_codes


def test_tc03_contradictory_irrigation_decision_detected(field_context):
    """TC03: Explanation contradicts the calculation engine status."""
    result, schedule, _ = field_context
    config = SelfCorrectionConfig(max_correction_attempts=1)
    res = run_self_correction_framework(
        result,
        schedule,
        language="en",
        config=config,
        mock_scenario_id="TC03",
    )
    assert res.fallback_used is True
    for attempt in res.attempts_history:
        issue_codes = [iss["code"] for iss in attempt.issues]
        assert "contradiction" in issue_codes


def test_tc04_unsupported_agronomic_claim_detected(field_context):
    """TC04: Explanation introduces fertilizer and yield guarantee claims."""
    result, schedule, _ = field_context
    config = SelfCorrectionConfig(max_correction_attempts=1)
    res = run_self_correction_framework(
        result,
        schedule,
        language="en",
        config=config,
        mock_scenario_id="TC04",
    )
    assert res.fallback_used is True
    att1 = res.attempts_history[0]
    issue_codes = [iss["code"] for iss in att1.issues]
    assert "fertilizer" in issue_codes or "unsupported_claim" in issue_codes


def test_tc05_successful_self_correction_loop(field_context):
    """TC05: Attempt 1 fails (bad number); structured feedback triggers Attempt 2 which passes."""
    result, schedule, _ = field_context
    res = run_self_correction_framework(
        result,
        schedule,
        language="en",
        mock_scenario_id="TC05",
    )
    assert res.overall_status == STATUS_CORRECTION_SUCCESSFUL
    assert res.total_attempts == 2
    assert res.initial_passed is False
    assert res.corrected is True
    assert res.fallback_used is False
    assert res.source == "ai"

    # Attempt 1 failed
    assert res.attempts_history[0].validation_passed is False
    assert "unsupported_number" in [i["code"] for i in res.attempts_history[0].issues]
    assert "AUTOMATIC VALIDATION FEEDBACK" in res.attempts_history[0].structured_feedback

    # Attempt 2 passed
    assert res.attempts_history[1].validation_passed is True


def test_tc06_maximum_retry_limit_enforcement(field_context):
    """TC06: Persistent failures halt strictly at configured limit and activate fallback."""
    result, schedule, _ = field_context
    config = SelfCorrectionConfig(max_correction_attempts=3)
    res = run_self_correction_framework(
        result,
        schedule,
        language="en",
        config=config,
        mock_scenario_id="TC06",
    )
    assert res.overall_status == STATUS_MAX_ATTEMPTS_REACHED
    assert res.fallback_used is True
    assert res.source == "fallback"
    assert res.fallback_reason == "max_retries_exhausted"
    # 1 initial + 3 retries = 4 total calls
    assert res.total_attempts == 4
    assert len(res.attempts_history) == 4


def test_tc07_api_failure_handled_safely(field_context):
    """TC07: Network/API exceptions do not crash the app and transition to fallback."""
    result, schedule, _ = field_context
    res = run_self_correction_framework(
        result,
        schedule,
        language="en",
        mock_scenario_id="TC07",
    )
    assert res.overall_status == STATUS_API_UNAVAILABLE
    assert res.fallback_used is True
    assert res.source == "fallback"
    assert res.api_error_category in ("timeout", "api_error")


def test_calculation_engine_facts_are_immutable(field_context):
    """Verify that neither the generator, validator, nor correction loop mutates calculation facts."""
    result, schedule, facts = field_context
    original_net = result["estimates"]["net_irrigation_mm"]
    original_status = schedule["status_code"]

    _ = run_self_correction_framework(
        result,
        schedule,
        language="en",
        mock_scenario_id="TC05",
    )

    assert result["estimates"]["net_irrigation_mm"] == original_net
    assert schedule["status_code"] == original_status


def test_structured_feedback_contents(field_context):
    """Verify that structured feedback contains the rule, expected fact, observed error, and guidelines."""
    result, schedule, facts = field_context
    bad_text = "This is an educational prototype. Irrigate with 999 mm water immediately today!"
    v = validate_explanation(bad_text, facts, "en")
    assert not v["passed"]
    fb = v["structured_feedback"]
    assert "AUTOMATIC VALIDATION FEEDBACK" in fb
    assert "Rule Violated:" in fb
    assert "Expected:" in fb
    assert "Observed Mismatch:" in fb
    assert "CRITICAL INSTRUCTIONS FOR CORRECTION:" in fb


def test_metrics_computation(field_context):
    """Verify that compute_experiment_metrics produces correct mathematical aggregations."""
    result, schedule, _ = field_context

    r1 = run_self_correction_framework(result, schedule, mock_scenario_id="TC01")
    r2 = run_self_correction_framework(result, schedule, mock_scenario_id="TC05")
    r3 = run_self_correction_framework(result, schedule, mock_scenario_id="TC06")
    r4 = run_self_correction_framework(result, schedule, mock_scenario_id="TC07")

    metrics = compute_experiment_metrics([r1, r2, r3, r4])
    assert metrics["total_runs"] == 4
    # r1 initial pass
    assert metrics["initial_pass_rate"] == 25.0
    # r1 and r2 final passed
    assert metrics["final_pass_rate"] == 50.0
    # out of r2 and r3 (r4 is API unavailable), r2 corrected -> 1/2 = 50%
    assert metrics["correction_success_rate"] == 50.0
    # fallbacks: r3, r4 -> 2
    assert metrics["fallback_count"] == 2
    # api failures: r4 -> 1
    assert metrics["api_failure_count"] == 1


def test_empty_or_malformed_response_handling(field_context):
    """Verify that an empty or whitespace-only response fails validation with 'empty' code and triggers retry."""
    result, schedule, _ = field_context
    client = MockLLMClient(["", "    \n\n  ", build_valid_explanation(collect_facts(result, schedule), "en")])
    res = run_self_correction_framework(
        result,
        schedule,
        language="en",
        client=client,
    )
    assert res.overall_status == STATUS_CORRECTION_SUCCESSFUL
    assert res.total_attempts == 3
    assert res.attempts_history[0].validation_passed is False
    assert "empty" in [i["code"] for i in res.attempts_history[0].issues]
    assert res.attempts_history[1].validation_passed is False
    assert "empty" in [i["code"] for i in res.attempts_history[1].issues]
    assert res.attempts_history[2].validation_passed is True


def test_missing_credentials_handling(field_context, monkeypatch):
    """Verify that missing GROQ_API_KEY is handled gracefully in live mode without crashing."""
    result, schedule, _ = field_context
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "")

    # Force live LLM mode by leaving mock_scenario_id=None
    res = run_self_correction_framework(
        result,
        schedule,
        language="en",
        client=None,
    )
    assert res.overall_status == STATUS_API_UNAVAILABLE
    assert res.fallback_used is True
    assert res.source == "fallback"
    assert res.api_error_category == "no_api_key"

