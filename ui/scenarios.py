"""Scenario comparison feature for evaluating alternative rainfall, soil moisture, and water availability."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from water_requirement_engine import (
    FieldInputs, rainfall_scenarios, soil_moisture_scenarios, water_availability_scenarios
)
from app_defaults import build_config_from_state, build_inputs_from_state
from ui.styles import render_tag, render_disclaimer


def render_scenario_comparison(result: dict, on_navigate):
    """Render interactive scenario explorer for comparing alternative field conditions."""
    st.markdown("## 📊 Alternative Scenario Comparison")
    st.caption("Evaluate how the deterministic engine responds to alternative rainfall, soil moisture, and storage volumes.")
    render_disclaimer()

    if not result.get("valid"):
        st.error("🚫 Cannot run scenarios: Current field parameters are invalid.")
        if st.button("⬅️ Return to Field Assessment"):
            on_navigate("Field Assessment")
            st.rerun()
        return

    st.markdown(
        """
        <div class="cw-disclaimer" style="border-left-color: #0284C7; background: #F0F9FF; color: #0369A1;">
            ℹ️ <strong>Hypothetical Scenario Exploration Notice:</strong>
            All results on this page are deterministic projections of user-entered scenarios.
            They do not represent historical sensor logs, weather forecasts, or guaranteed agronomic outcomes.
        </div>
        """,
        unsafe_allow_html=True,
    )

    inp = build_inputs_from_state(st.session_state)
    cfg = build_config_from_state(st.session_state)

    tab_rain, tab_moist, tab_water = st.tabs([
        "🌧️ Rainfall Scenarios",
        "🌱 Soil Moisture Scenarios",
        "💧 Water Availability & Coverage",
    ])

    # ---------------- 1. Rainfall Scenarios ----------------
    with tab_rain:
        st.markdown("### Expected Rainfall Variation Scenarios")
        st.caption("Observe how different rainfall amounts over the planning window change effective rainfall credit and net irrigation demand.")

        vals_str = st.text_input("Enter alternative rainfall depths in mm (comma-separated):", "0, 10, 20, 35, 50, 75")
        try:
            rain_list = [float(x.strip()) for x in vals_str.split(",") if x.strip()]
            rows_rain = rainfall_scenarios(inp, rain_list, cfg)
            df_rain = pd.DataFrame(rows_rain).drop(columns="valid", errors="ignore")

            col_r1, col_r2 = st.columns([1.2, 1])
            with col_r1:
                st.dataframe(df_rain, hide_index=True, use_container_width=True)

            with col_r2:
                if df_rain["net_irrigation_mm"].notna().any():
                    fig_rain = go.Figure()
                    fig_rain.add_trace(go.Bar(
                        x=[f"{r:g} mm" for r in df_rain["rainfall_mm"]],
                        y=df_rain["net_irrigation_mm"],
                        name="Net Irrigation Need",
                        marker_color="#1B4332",
                        text=[f"{v:.1f} mm" if v is not None else "n/a" for v in df_rain["net_irrigation_mm"]],
                        textposition="auto",
                    ))
                    fig_rain.add_trace(go.Bar(
                        x=[f"{r:g} mm" for r in df_rain["rainfall_mm"]],
                        y=df_rain["effective_rain_mm"],
                        name="Effective Rain Credit (80%)",
                        marker_color="#38BDF8",
                        text=[f"{v:.1f} mm" if v is not None else "n/a" for v in df_rain["effective_rain_mm"]],
                        textposition="auto",
                    ))
                    fig_rain.update_layout(
                        barmode="group",
                        height=280,
                        margin=dict(t=25, b=20, l=40, r=20),
                        paper_bgcolor="#FFFFFF",
                        plot_bgcolor="#F8FAFC",
                        font=dict(family="Inter"),
                        yaxis_title="Millimeters (mm)",
                    )
                    st.plotly_chart(fig_rain, use_container_width=True)
                else:
                    st.info("Net irrigation requires reference ETo to be calculated.")
        except ValueError:
            st.error("Please enter a valid list of numbers separated by commas (e.g., 0, 15, 30, 50).")

    # ---------------- 2. Soil Moisture Scenarios ----------------
    with tab_moist:
        st.markdown("### Soil Moisture Variation Scenarios")
        st.caption("See how differing initial soil moisture levels alter current root-zone depletion and net irrigation requirement.")

        moist_str = st.text_input("Enter alternative soil moisture percentages (comma-separated):", "15, 20, 25, 30, 35")
        try:
            m_list = [float(x.strip()) for x in moist_str.split(",") if x.strip()]
            rows_m = soil_moisture_scenarios(inp, m_list, cfg)
            df_m = pd.DataFrame(rows_m).drop(columns="valid", errors="ignore")

            col_m1, col_m2 = st.columns([1.2, 1])
            with col_m1:
                st.dataframe(df_m, hide_index=True, use_container_width=True)

            with col_m2:
                if df_m["net_irrigation_mm"].notna().any():
                    fig_m = go.Figure()
                    fig_m.add_trace(go.Bar(
                        x=[f"{m:g}%" for m in df_m["soil_moisture_pct"]],
                        y=df_m["net_irrigation_mm"],
                        name="Net Irrigation Depth",
                        marker_color="#2D6A4F",
                        text=[f"{v:.1f} mm" if v is not None else "n/a" for v in df_m["net_irrigation_mm"]],
                        textposition="auto",
                    ))
                    fig_m.update_layout(
                        height=280,
                        margin=dict(t=25, b=20, l=40, r=20),
                        paper_bgcolor="#FFFFFF",
                        plot_bgcolor="#F8FAFC",
                        font=dict(family="Inter"),
                        yaxis_title="Net Irrigation (mm)",
                    )
                    st.plotly_chart(fig_m, use_container_width=True)
                else:
                    st.info("Volumetric soil parameters (FC, PWP, Depth) and ETo are needed for root-zone moisture balancing.")
        except ValueError:
            st.error("Please enter valid numbers separated by commas.")

    # ---------------- 3. Water Availability Scenarios ----------------
    with tab_water:
        st.markdown("### Available Water & Storage Sufficiency")
        st.caption("Compare how various water reserve volumes cover the required irrigation volume.")

        v_str = st.text_input("Enter alternative water volumes in m³ (comma-separated):", "50, 150, 300, 500, 800")
        try:
            v_list = [float(x.strip()) for x in v_str.split(",") if x.strip()]
            rows_w = water_availability_scenarios(result, v_list)
            df_w = pd.DataFrame(rows_w)

            col_w1, col_w2 = st.columns([1.2, 1])
            with col_w1:
                st.dataframe(df_w, hide_index=True, use_container_width=True)

            with col_w2:
                if df_w["coverage_pct"].notna().any():
                    fig_w = go.Figure()
                    fig_w.add_trace(go.Bar(
                        x=[f"{v:g} m³" for v in df_w["available_m3"]],
                        y=df_w["coverage_pct"],
                        name="Storage Coverage %",
                        marker_color=["#16A34A" if c >= 100 else "#DC2626" for c in df_w["coverage_pct"]],
                        text=[f"{c:.0f}%" if c is not None else "n/a" for c in df_w["coverage_pct"]],
                        textposition="auto",
                    ))
                    fig_w.add_shape(
                        type="line", line=dict(dash="dash", color="#334155", width=2),
                        x0=-0.5, x1=len(df_w) - 0.5, y0=100, y1=100,
                    )
                    fig_w.update_layout(
                        height=280,
                        margin=dict(t=25, b=20, l=40, r=20),
                        paper_bgcolor="#FFFFFF",
                        plot_bgcolor="#F8FAFC",
                        font=dict(family="Inter"),
                        yaxis_title="Coverage of Required Volume (%)",
                    )
                    st.plotly_chart(fig_w, use_container_width=True)
                    st.caption("Dashed line marks 100% sufficiency threshold.")
                else:
                    st.info("Field Area (and preferably Irrigation Efficiency) is required to calculate volumetric demand in m³.")
        except ValueError:
            st.error("Please enter numbers separated by commas.")

    # Navigation Footer
    st.write("")
    c_n1, c_n2 = st.columns([1, 1])
    with c_n1:
        if st.button("⬅️ Back to Validation Lab", use_container_width=True):
            on_navigate("Validation Lab")
            st.rerun()
    with c_n2:
        if st.button("View Architecture & Methodology 📖", type="primary", use_container_width=True):
            on_navigate("About and Methodology")
            st.rerun()
