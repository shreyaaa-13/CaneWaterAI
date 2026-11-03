"""Tests for new scenario helpers, API status checks, report generation, and demo presets."""
from __future__ import annotations

import os
from datetime import date
import pytest
from app_defaults import DEFAULTS, build_config_from_state, build_inputs_from_state
from genai_explainer import check_api_status
from irrigation_scheduler import build_schedule
from ui.demo_flow import SAMPLE_FULL_FIELD, SAMPLE_INCOMPLETE_FIELD, load_preset
from ui.reporting import generate_markdown_report, generate_schedule_csv
from water_requirement_engine import (
    EngineConfig, FieldInputs, estimate_water_requirement, soil_moisture_scenarios
)

TODAY = date(2026, 10, 20)


def test_soil_moisture_scenarios():
    inp = FieldInputs(
        eto_mm_day=4.0,
        growth_stage="Grand growth",
        soil_moisture_pct=25,
        moisture_is_volumetric=True,
        field_capacity_pct=30,
        wilting_point_pct=15,
        root_depth_m=0.5,
    )
    rows = soil_moisture_scenarios(inp, [15.0, 20.0, 25.0, 30.0], EngineConfig())
    assert len(rows) == 4
    # Lower moisture should have higher depletion
    assert rows[0]["depletion_now_mm"] > rows[3]["depletion_now_mm"]
    assert rows[0]["net_irrigation_mm"] >= rows[3]["net_irrigation_mm"]


def test_check_api_status_offline(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    status = check_api_status()
    assert status["available"] is False
    assert status["mode"] == "fallback"
    assert "No valid GROQ_API_KEY" in status["reason"]


def test_check_api_status_online(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_123456789")
    status = check_api_status()
    assert status["available"] is True
    assert status["mode"] == "ai"
    assert "AI Online" in status["label"]


def test_app_defaults_and_builders():
    state = dict(DEFAULTS)
    cfg = build_config_from_state(state)
    inp = build_inputs_from_state(state)
    assert cfg.planning_period_days == 7
    assert inp.growth_stage == "Grand growth"
    assert inp.soil_moisture_pct == 30.0


def test_demo_presets_load():
    fake_session: dict = {}
    load_preset(fake_session, "full")
    assert fake_session["demo_mode_active"] is True
    assert fake_session["demo_preset_loaded"] == "full"
    assert fake_session["f_stage"] == "Grand growth"
    assert fake_session["f_use_eto"] is True
    assert fake_session["f_eto"] == 4.5

    load_preset(fake_session, "gap")
    assert fake_session["demo_preset_loaded"] == "gap"
    assert fake_session["f_use_eto"] is False


def test_report_generation():
    inp = FieldInputs(
        eto_mm_day=4.0,
        soil_moisture_pct=22,
        moisture_is_volumetric=True,
        field_capacity_pct=32,
        wilting_point_pct=16,
        root_depth_m=0.8,
        area=1.5,
        irrigation_efficiency_pct=85.0,
        pump_flow_m3_per_h=25.0,
    )
    res = estimate_water_requirement(inp, EngineConfig(), TODAY)
    sched = build_schedule(res, TODAY)

    md = generate_markdown_report(res, sched, None, "en")
    assert "# CaneWater AI" in md
    assert "Net Irrigation Requirement" in md
    assert "Educational Prototype Disclaimer" in md
    # Ensure no secrets leak in report
    assert "gsk_" not in md and "sk-" not in md

    csv = generate_schedule_csv(sched)
    assert "date,action,net_depth_mm,note" in csv


def test_self_correction_page_registered():
    from app import PAGES
    from ui.self_correction_ui import render_self_correction_experiment
    assert "Self-Correction Experiment" in PAGES
    assert callable(render_self_correction_experiment)

