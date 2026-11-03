"""Header component with real API status verification, language selector, and demo mode controls."""
from __future__ import annotations

import streamlit as st
from genai_explainer import LANGUAGES, check_api_status
from ui.demo_flow import load_preset


def render_app_header(current_section: str):
    """Render consistent top header with logo, title, section, API status, and demo quick actions."""
    api_status = check_api_status()

    # Determine pill styling
    if api_status["available"]:
        pill_class = "cw-pill-green"
        pill_icon = "🟢"
    else:
        pill_class = "cw-pill-amber"
        pill_icon = "🟡"

    # Header container
    st.markdown(
        f"""
        <div class="cw-header">
            <div>
                <h1>🌾 CaneWater AI</h1>
                <p><strong>Section:</strong> {current_section} &nbsp;|&nbsp; <em>Sugarcane Water Estimation & Irrigation Decision Support</em></p>
            </div>
            <div class="cw-header-badges">
                <span class="cw-pill {pill_class}" title="{api_status['detail']}">
                    <span>{pill_icon}</span>
                    <span>{api_status['label']}</span>
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Demo quick toolbar
    with st.container():
        c1, c2, c3, c4 = st.columns([3, 1.4, 1.4, 1.4])
        with c1:
            if st.session_state.get("demo_mode_active"):
                preset_name = st.session_state.get("demo_preset_loaded", "full").capitalize()
                st.caption(f"🎯 **Guided Demonstration Active:** `{preset_name} Sample Profile` loaded. Click navigation or steps below to present.")
            else:
                st.caption("💡 *Viva Presentation Tip: Click 'Load Sample Field' to prepopulate a complete sugarcane profile.*")
        with c2:
            if st.button("🌱 Load Sample Field", key="btn_load_sample_full", help="Load complete 5-month sugarcane field with soil water & pump data"):
                load_preset(st.session_state, "full")
                st.toast("Loaded complete sugarcane field sample profile!", icon="🌱")
                st.rerun()
        with c3:
            if st.button("⚠️ Load Incomplete Field", key="btn_load_sample_gap", help="Demonstrate honest data-gap handling (missing ETo and soil-water data)"):
                load_preset(st.session_state, "gap")
                st.toast("Loaded incomplete field profile to demonstrate data-gap handling.", icon="⚠️")
                st.rerun()
        with c4:
            if st.button("🔄 Reset to Default", key="btn_reset_defaults", help="Reset all fields to original defaults"):
                from app_defaults import DEFAULTS
                for k, v in DEFAULTS.items():
                    st.session_state[k] = v
                st.session_state["demo_mode_active"] = False
                st.session_state["explanation"] = None
                st.toast("Reset all inputs to system defaults.", icon="🔄")
                st.rerun()
