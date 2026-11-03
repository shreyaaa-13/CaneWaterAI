"""Interactive field input forms, agronomic validations, and assessment trigger."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from water_requirement_engine import (
    METHODS, RAIN_CATEGORIES, SOIL_TYPES, STAGES, WEATHER,
    FieldInputs, EngineConfig, estimate_water_requirement
)
from irrigation_scheduler import build_schedule
from app_defaults import build_config_from_state, build_inputs_from_state
from ui.demo_flow import load_preset
from ui.styles import render_tag, render_disclaimer


def render_field_assessment(on_navigate):
    """Render the Field Assessment form with 4 organized sections and live validation."""
    st.markdown("## 🌱 Field Assessment & Agronomic Parameters")
    render_tag("user")
    render_disclaimer()

    # Quick demo load actions right on top of form
    with st.expander("⚡ Quick Demo Presets (for evaluation or viva)", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🌱 Load Complete Sugarcane Field", use_container_width=True, key="form_load_full"):
                load_preset(st.session_state, "full")
                st.toast("Loaded complete sugarcane field sample profile!", icon="🌱")
                st.rerun()
        with c2:
            if st.button("⚠️ Load Incomplete Field Profile", use_container_width=True, key="form_load_gap"):
                load_preset(st.session_state, "gap")
                st.toast("Loaded incomplete field profile (data gap demo).", icon="⚠️")
                st.rerun()
        with c3:
            st.caption("Pre-fills all sections with realistic parameters according to FAO-56 standards.")

    # Two main columns: Left form (65%), Right summary (35%)
    col_form, col_summary = st.columns([1.8, 1.2])

    with col_form:
        # ---------------- Section A: Crop ----------------
        st.markdown('<div class="cw-form-section">🎋 A. Crop Information</div>', unsafe_allow_html=True)
        cA1, cA2 = st.columns(2)
        with cA1:
            st.number_input(
                "Crop Age (months)",
                min_value=0.0,
                max_value=24.0,
                step=0.5,
                key="f_age",
                help="Enter crop age from planting or ratoon initiation (0 to 24 months)."
            )
        with cA2:
            st.selectbox(
                "Growth Stage",
                STAGES,
                key="f_stage",
                help="Sugarcane physiological stage: Germination, Tillering, Grand growth, or Maturity."
            )

        if st.checkbox("Provide planting date (optional consistency verification)", key="f_use_pdate"):
            st.date_input(
                "Planting Date",
                key="f_pdate",
                help="Used for consistency warning against entered crop age. Never overwrites entered age."
            )

        # ---------------- Section B: Soil ----------------
        st.markdown('<div class="cw-form-section">🧱 B. Soil Information</div>', unsafe_allow_html=True)
        cB1, cB2 = st.columns(2)
        with cB1:
            st.selectbox(
                "Soil Texture Type",
                SOIL_TYPES,
                key="f_soil",
                help="Soil classification (Light, Medium, Heavy). Context only; does not fabricate water quantities."
            )
        with cB2:
            st.number_input(
                "Soil Moisture Reading (%)",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                key="f_moist",
                help="Reading from tensiometer, probe, or manual sample. Unless confirmed volumetric, treated as generic %."
            )

        if st.checkbox("I have volumetric soil-water data (Field Capacity, Wilting Point, Root Depth)", key="f_use_soilwater"):
            st.info("ℹ️ Volumetric soil parameters allow the engine to compute Total Available Water (TAW) and Readily Available Water (RAW).")
            st.checkbox("Confirm: this reading represents volumetric water content (%)", key="f_vol")
            s1, s2, s3 = st.columns(3)
            with s1:
                st.number_input("Field Capacity (FC vol %)", min_value=1.0, max_value=99.0, step=1.0, key="f_fc",
                                help="Volumetric soil water at field capacity (typically 25-40% for loams/clays).")
            with s2:
                st.number_input("Permanent Wilting Point (PWP vol %)", min_value=1.0, max_value=99.0, step=1.0, key="f_pwp",
                                help="Volumetric soil water at permanent wilting point (must be < FC).")
            with s3:
                st.number_input("Root-Zone Depth (m)", min_value=0.1, max_value=3.0, step=0.1, key="f_root",
                                help="Effective sugarcane rooting depth (typically 0.4 - 1.2 m).")

        # ---------------- Section C: Weather ----------------
        st.markdown('<div class="cw-form-section">⛅ C. Weather & Reference Evapotranspiration</div>', unsafe_allow_html=True)
        cW1, cW2 = st.columns(2)
        with cW1:
            st.selectbox("Weather Condition (General)", WEATHER, key="f_weather",
                         help="Qualitative condition (Cool, Warm, Hot).")
        with cW2:
            st.selectbox("Expected Rainfall Category", RAIN_CATEGORIES, key="f_rain_cat",
                         help="Categorical rainfall estimate for the planning window.")

        cW3, cW4 = st.columns(2)
        with cW3:
            if st.checkbox("Provide quantitative rainfall (mm)", key="f_use_rain"):
                st.number_input("Expected Rainfall (mm)", min_value=0.0, max_value=500.0, step=1.0, key="f_rain_mm",
                                help="User estimate for the planning period. Effective rain fraction (80%) is applied.")
        with cW4:
            if st.checkbox("Provide reference evapotranspiration ETo (mm/day)", key="f_use_eto"):
                st.number_input("Reference ETo (mm/day)", min_value=0.0, max_value=15.0, step=0.1, key="f_eto",
                                help="ETo from local weather bureau or Penman-Monteith estimation (typically 3-8 mm/day).")

        # ---------------- Section D: Irrigation ----------------
        st.markdown('<div class="cw-form-section">🚿 D. Irrigation System & Water Resources</div>', unsafe_allow_html=True)
        st.selectbox("Irrigation Method", METHODS, key="f_method",
                     help="Context only. Efficiency is never guessed from the method without user specification.")

        cI1, cI2 = st.columns(2)
        with cI1:
            if st.checkbox("Provide Field Area", key="f_use_area"):
                ca1, ca2 = st.columns([2, 1])
                with ca1:
                    st.number_input("Field Area", min_value=0.01, max_value=10000.0, step=0.1, key="f_area")
                with ca2:
                    st.selectbox("Unit", ["ha", "acre"], key="f_area_unit")

            if st.checkbox("Provide Irrigation Application Efficiency (%)", key="f_use_eff"):
                st.number_input("Application Efficiency (%)", min_value=1.0, max_value=100.0, step=1.0, key="f_eff",
                                help="Drip is typically 80-90%, furrow 50-70%. Used to calculate gross irrigation volume.")

        with cI2:
            if st.checkbox("Provide Available Water in Storage (m³)", key="f_use_water"):
                st.number_input("Available Water (m³)", min_value=0.0, max_value=1e7, step=10.0, key="f_water",
                                help="1 m³ = 1,000 litres. Used to evaluate water sufficiency.")

            if st.checkbox("Provide Pump Discharge Flow Rate (m³/h)", key="f_use_flow"):
                st.number_input("Pump Flow Rate (m³/h)", min_value=0.1, max_value=5000.0, step=1.0, key="f_flow",
                                help="Well/bore pump capacity. Used to calculate required irrigation run duration.")

        # ---------------- Advanced Configuration ----------------
        with st.expander("⚙️ Advanced Engine Configuration (Scientific Assumptions)", expanded=False):
            st.caption("Configurable scientific assumptions based on FAO-56. Defaults follow Table 12 sugarcane constants.")
            cf1, cf2, cf3 = st.columns(3)
            with cf1:
                st.number_input("Planning Window (days)", min_value=1, max_value=30, key="c_period",
                                help="Review period for water demand calculations (not an optimal interval).")
            with cf2:
                st.number_input("Effective Rain Fraction", min_value=0.0, max_value=1.0, step=0.05, key="c_reff",
                                help="Fraction of gross rainfall stored in root zone (default 0.80).")
            with cf3:
                st.number_input("Allowable Depletion Fraction (p)", min_value=0.1, max_value=1.0, step=0.05, key="c_p",
                                help="FAO-56 allowable soil water depletion fraction before moisture stress (default 0.65).")

            st.markdown("**Crop Coefficients (Kc) by Growth Stage:**")
            kc_cols = st.columns(4)
            for col, stage in zip(kc_cols, STAGES):
                with col:
                    st.number_input(f"Kc {stage}", min_value=0.1, max_value=1.6, step=0.05, key=f"c_kc_{stage}")

    # Right Column: Live Validation & Assessment Summary
    with col_summary:
        st.markdown("### 📋 Live Validation & Field Summary")

        # Run temporary validation check against current state
        temp_cfg = build_config_from_state(st.session_state)
        temp_inp = build_inputs_from_state(st.session_state)
        temp_res = estimate_water_requirement(temp_inp, temp_cfg)

        # Show Errors (Blocking)
        if temp_res["errors"]:
            st.error("🚫 **Validation Errors (Must be resolved):**")
            for err in temp_res["errors"]:
                st.markdown(f"- {err}")
        else:
            st.success("✅ **Inputs are scientifically valid.** Ready for calculation.")

        # Show Warnings (Inconsistencies)
        if temp_res["warnings"]:
            st.warning("⚠️ **Agronomic Inconsistency Flags:**")
            for warn in temp_res["warnings"]:
                st.markdown(f"- {warn}")

        st.write("")

        # Compact live table of active inputs
        st.markdown("#### Active Configuration")
        active_items = [
            ("Crop Age / Stage", f"{temp_inp.crop_age_months:g} mo / {temp_inp.growth_stage}"),
            ("Soil Type / Moisture", f"{temp_inp.soil_type} / {temp_inp.soil_moisture_pct:g}%"),
            ("Volumetric Soil Data", "Active (FC/PWP/Root)" if temp_inp.moisture_is_volumetric else "Generic (not volumetric)"),
            ("Weather / Rain Category", f"{temp_inp.weather} / {temp_inp.rainfall_category}"),
            ("Rainfall (mm)", f"{temp_inp.rainfall_mm:g} mm" if temp_inp.rainfall_mm is not None else "Not specified"),
            ("Reference ETo", f"{temp_inp.eto_mm_day:g} mm/day" if temp_inp.eto_mm_day is not None else "Not specified"),
            ("Irrigation Method", f"{temp_inp.irrigation_method}"),
            ("Efficiency", f"{temp_inp.irrigation_efficiency_pct:g}%" if temp_inp.irrigation_efficiency_pct is not None else "Not specified"),
            ("Field Area", f"{temp_inp.area} {temp_inp.area_unit}" if temp_inp.area is not None else "Not specified"),
            ("Available Storage", f"{temp_inp.available_water_m3:g} m³" if temp_inp.available_water_m3 is not None else "Not specified"),
            ("Pump Discharge", f"{temp_inp.pump_flow_m3_per_h:g} m³/h" if temp_inp.pump_flow_m3_per_h is not None else "Not specified"),
        ]
        df_active = pd.DataFrame(active_items, columns=["Field Parameter", "Configured Value"])
        st.dataframe(df_active, hide_index=True, use_container_width=True)

        st.write("")

        # Prominent Assessment Button
        btn_disabled = not temp_res["valid"]
        if st.button("🚀 Generate Irrigation Assessment", type="primary", use_container_width=True, disabled=btn_disabled):
            # Invalidate any old explanation
            st.session_state["explanation"] = None
            st.toast("Calculations executed successfully!", icon="✅")
            on_navigate("Water Analysis")
            st.rerun()

        if btn_disabled:
            st.caption("⚠️ Resolve validation errors in the form before generating the assessment.")
        else:
            st.caption("Click to calculate ETc, soil water balance, and deterministic irrigation schedule.")
