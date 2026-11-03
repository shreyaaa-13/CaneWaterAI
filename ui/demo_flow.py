"""Guided demonstration workflow and sample field profiles for viva and presentations."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, Any

DEMO_STEPS = [
    {"num": 1, "title": "Field Information", "page": "Field Assessment", "desc": "Inspect agronomic inputs"},
    {"num": 2, "title": "Water Analysis", "page": "Water Analysis", "desc": "ETc and volume calculations"},
    {"num": 3, "title": "Irrigation Planner", "page": "Irrigation Planner", "desc": "Scheduler decision & timing"},
    {"num": 4, "title": "AI Insights", "page": "AI Insights", "desc": "Multilingual GenAI explanation"},
    {"num": 5, "title": "Validation Lab", "page": "Validation Lab", "desc": "Self-correction & reliability"},
    {"num": 6, "title": "Scenario Explorer", "page": "Scenario Comparison", "desc": "Compare alternate conditions"},
]

# Preset 1: Complete Illustrative Sugarcane Field (Full Evaluation Demo)
SAMPLE_FULL_FIELD: Dict[str, Any] = {
    "f_age": 5.0,
    "f_stage": "Grand growth",
    "f_use_pdate": True,
    "f_pdate": date.today() - timedelta(days=152),
    "f_soil": "Medium",
    "f_moist": 22.0,
    "f_vol": True,
    "f_use_soilwater": True,
    "f_fc": 32.0,
    "f_pwp": 16.0,
    "f_root": 0.8,
    "f_weather": "Warm",
    "f_rain_cat": "Light",
    "f_use_rain": True,
    "f_rain_mm": 10.0,
    "f_use_eto": True,
    "f_eto": 4.5,
    "f_method": "Drip",
    "f_use_eff": True,
    "f_eff": 85.0,
    "f_use_area": True,
    "f_area": 1.5,
    "f_area_unit": "ha",
    "f_use_water": True,
    "f_water": 450.0,
    "f_use_flow": True,
    "f_flow": 25.0,
    # Engine configuration assumptions
    "c_period": 7,
    "c_reff": 0.80,
    "c_p": 0.65,
    "c_kc_Germination": 0.40,
    "c_kc_Tillering": 0.80,
    "c_kc_Grand growth": 1.25,
    "c_kc_Maturity": 0.75,
}

# Preset 2: Incomplete Data Profile (Data-Gap Demo: shows system refusing to invent facts)
SAMPLE_INCOMPLETE_FIELD: Dict[str, Any] = {
    "f_age": 5.0,
    "f_stage": "Grand growth",
    "f_use_pdate": False,
    "f_pdate": date.today() - timedelta(days=152),
    "f_soil": "Medium",
    "f_moist": 30.0,
    "f_vol": False,
    "f_use_soilwater": False,
    "f_fc": 30.0,
    "f_pwp": 15.0,
    "f_root": 0.5,
    "f_weather": "Warm",
    "f_rain_cat": "None",
    "f_use_rain": False,
    "f_rain_mm": 0.0,
    "f_use_eto": False,
    "f_eto": 4.0,
    "f_method": "Flood/furrow",
    "f_use_eff": False,
    "f_eff": 60.0,
    "f_use_area": False,
    "f_area": 1.0,
    "f_area_unit": "ha",
    "f_use_water": False,
    "f_water": 100.0,
    "f_use_flow": False,
    "f_flow": 20.0,
}


def load_preset(st_session, preset_type: str = "full"):
    """Load sample field data into session state without clobbering UI state."""
    preset = SAMPLE_FULL_FIELD if preset_type == "full" else SAMPLE_INCOMPLETE_FIELD
    for k, v in preset.items():
        st_session[k] = v
    # Reset any cached explanation so it regenerates cleanly with the new facts
    st_session["explanation"] = None
    st_session["demo_mode_active"] = True
    st_session["demo_preset_loaded"] = preset_type


def render_stepper(current_page: str):
    """Render the guided presentation stepper bar."""
    import streamlit as st

    # Map current page to step index
    page_to_step = {step["page"]: i for i, step in enumerate(DEMO_STEPS)}
    current_idx = page_to_step.get(current_page, 0)

    cols = st.columns([1] * len(DEMO_STEPS))
    for i, (col, step) in enumerate(zip(cols, DEMO_STEPS)):
        is_active = (i == current_idx)
        is_past = (i < current_idx)
        border_color = "#2D6A4F" if is_active else ("#A5D6A7" if is_past else "#CBD5E1")
        bg_color = "#E8F5E9" if is_active else ("#F8FAFC" if is_past else "#FFFFFF")
        text_color = "#1B4332" if is_active else ("#2E7D32" if is_past else "#64748B")
        badge = "✓" if is_past else str(step["num"])

        with col:
            st.markdown(
                f"""
                <div style="background: {bg_color}; border: 1.5px solid {border_color}; border-radius: 8px;
                            padding: 6px 8px; text-align: center; margin-bottom: 0.5rem;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: {text_color};">
                        Step {badge}
                    </div>
                    <div style="font-size: 0.75rem; font-weight: 600; color: #1E293B; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        {step['title']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
