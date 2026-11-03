"""CaneWater AI — Upgraded, Premium, Demo-Ready Streamlit Application."""
from __future__ import annotations

import logging
from datetime import date
from typing import Dict, Any

import streamlit as st

# Core Engines (Preserved 100% Deterministic)
from app_defaults import DEFAULTS, build_config_from_state, build_inputs_from_state
from genai_explainer import LANGUAGES, check_api_status
from irrigation_scheduler import build_schedule
from water_requirement_engine import estimate_water_requirement

# UI Modules
from ui.about_methodology import render_about_methodology
from ui.ai_insights import render_ai_insights
from ui.demo_flow import DEMO_STEPS, load_preset, render_stepper
from ui.field_assessment import render_field_assessment
from ui.header import render_app_header
from ui.irrigation_planner import render_irrigation_planner
from ui.overview import render_overview
from ui.reporting import generate_markdown_report, generate_schedule_csv
from ui.scenarios import render_scenario_comparison
from ui.styles import apply_custom_styles
from ui.validation_lab import render_validation_lab
from ui.self_correction_ui import render_self_correction_experiment

logging.basicConfig(level=logging.INFO)

# Streamlit Page Config
st.set_page_config(
    page_title="CaneWater AI — Sugarcane Water & Irrigation Decision Support",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Agricultural Design System
apply_custom_styles()

# Initialize Session State
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Retain widget state across navigation
for k in list(st.session_state):
    if k.startswith(("f_", "c_")):
        st.session_state[k] = st.session_state[k]

# Navigation Pages
PAGES = [
    "Overview",
    "Field Assessment",
    "Water Analysis",
    "Irrigation Planner",
    "AI Insights",
    "Validation Lab",
    "Self-Correction Experiment",
    "Scenario Comparison",
    "About and Methodology",
]


def navigate_to(page_name: str):
    """Callback for programmatic navigation across pages."""
    if page_name in PAGES:
        st.session_state["current_page"] = page_name


# ---------------- Sidebar Navigation ----------------
with st.sidebar:
    st.markdown(
        """
        <div style="text-align: center; padding: 0.5rem 0 1rem 0;">
            <div style="font-size: 2.2rem; line-height: 1;">🌾</div>
            <div style="font-weight: 800; font-size: 1.25rem; color: #1B4332; margin-top: 0.2rem;">
                CaneWater AI
            </div>
            <div style="font-size: 0.75rem; color: #4B5563; font-weight: 500;">
                Precision Irrigation Decision Support
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Navigation")
    current_page_idx = PAGES.index(st.session_state["current_page"]) if st.session_state["current_page"] in PAGES else 0
    selected_page = st.radio(
        "Go to",
        PAGES,
        index=current_page_idx,
        label_visibility="collapsed",
        key="nav_radio",
    )
    if selected_page != st.session_state["current_page"]:
        st.session_state["current_page"] = selected_page

    st.markdown("---")

    # Multilingual Selection
    st.markdown("### Language Selector")
    st.selectbox(
        "Advisory Language",
        list(LANGUAGES.keys()),
        index=list(LANGUAGES.keys()).index(st.session_state["language"]),
        format_func=lambda k: LANGUAGES[k],
        key="language",
        help="Applies to AI-generated explanations and deterministic fallback advisories.",
    )

    st.markdown("---")

    # Quick Guided Tour / Demo Mode Launcher
    st.markdown("### 🎯 Faculty Demo Mode")
    demo_active = st.checkbox("Enable Guided Demo Mode", value=st.session_state.get("demo_mode_active", False), key="demo_mode_toggle")
    st.session_state["demo_mode_active"] = demo_active

    if demo_active:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            if st.button("🌱 Full Field", use_container_width=True, help="Load complete sugarcane field profile"):
                load_preset(st.session_state, "full")
                st.toast("Loaded sample sugarcane profile", icon="🌱")
                st.rerun()
        with col_d2:
            if st.button("⚠️ Data Gap", use_container_width=True, help="Demonstrate honest data gap handling"):
                load_preset(st.session_state, "gap")
                st.toast("Loaded incomplete profile", icon="⚠️")
                st.rerun()

    st.markdown("---")

    # Download Report Quick Action
    st.markdown("### 📥 Export Assessment")
    # Execute calculations to generate fresh report
    cfg_export = build_config_from_state(st.session_state)
    inp_export = build_inputs_from_state(st.session_state)
    res_export = estimate_water_requirement(inp_export, cfg_export)
    sched_export = build_schedule(res_export)

    md_report = generate_markdown_report(
        res_export, sched_export, st.session_state.get("explanation"), st.session_state.get("language", "en")
    )
    csv_schedule = generate_schedule_csv(sched_export)

    st.download_button(
        "📄 Download Assessment (.md)",
        data=md_report,
        file_name=f"CaneWater_Assessment_{date.today().isoformat()}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.download_button(
        "📊 Download Schedule (.csv)",
        data=csv_schedule,
        file_name=f"CaneWater_Schedule_{date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown("---")
    st.caption("🎓 **Viva Evaluation Prototype**\nFAO-56 standard math + Groq `openai/gpt-oss-20b` explanation.")


# ---------------- Execute Real Deterministic Engine ----------------
CFG = build_config_from_state(st.session_state)
INP = build_inputs_from_state(st.session_state)
RESULT = estimate_water_requirement(INP, CFG)
SCHED = build_schedule(RESULT)

# ---------------- Render Consistent Header ----------------
render_app_header(st.session_state["current_page"])

# Render Guided Stepper if Demo Mode Active
if st.session_state.get("demo_mode_active"):
    render_stepper(st.session_state["current_page"])

# ---------------- Page Router ----------------
active_page = st.session_state["current_page"]

if active_page == "Overview":
    render_overview(RESULT, SCHED, on_navigate=navigate_to)

elif active_page == "Field Assessment":
    render_field_assessment(on_navigate=navigate_to)

elif active_page == "Water Analysis":
    from ui.water_analysis import render_water_analysis
    render_water_analysis(RESULT, on_navigate=navigate_to)

elif active_page == "Irrigation Planner":
    render_irrigation_planner(RESULT, SCHED, on_navigate=navigate_to)

elif active_page == "AI Insights":
    render_ai_insights(RESULT, SCHED, on_navigate=navigate_to)

elif active_page == "Validation Lab":
    render_validation_lab(RESULT, SCHED, on_navigate=navigate_to)

elif active_page == "Self-Correction Experiment":
    render_self_correction_experiment(RESULT, SCHED, on_navigate=navigate_to)

elif active_page == "Scenario Comparison":
    render_scenario_comparison(RESULT, on_navigate=navigate_to)

elif active_page == "About and Methodology":
    render_about_methodology(on_navigate=navigate_to)
