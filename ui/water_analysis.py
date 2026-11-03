"""Water requirement analysis with FAO-56 metrics, formula breakdowns, and missing-data audits."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from ui.styles import render_tag, render_disclaimer


def fmt(v, unit="", nd=1):
    return "Not calculated" if v is None else f"{v:,.{nd}f} {unit}".strip()


def render_water_analysis(result: dict, on_navigate):
    """Render the Water Analysis results page with full transparency, math, and data completeness audit."""
    st.markdown("## 🧮 Water Requirement Estimation & Balance")
    render_tag("calc")
    render_disclaimer()

    if not result.get("valid"):
        st.error("🚫 **Cannot execute calculations:** Validation errors exist in Field Assessment.")
        for err in result.get("errors", []):
            st.markdown(f"- {err}")
        if st.button("⬅️ Return to Field Assessment to Fix Inputs"):
            on_navigate("Field Assessment")
            st.rerun()
        return

    est = result["estimates"]
    inp = result["inputs_used"]
    period = est.get("planning_period_days", 7)

    # Provisional warning if ETo is missing
    if result.get("provisional"):
        st.warning(
            "⚠️ **Provisional Assessment:** Reference evapotranspiration ($ET_o$) was not provided. "
            "Crop water demand cannot be calculated. Values are strictly limited to existing soil moisture depletion."
        )

    # Top Metric Banner
    st.markdown("### Key Water Balances & Requirements")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Crop ET (ETc)</div>
                <div class="cw-metric-value">{fmt(est.get('etc_mm_day'), 'mm/day', 2)}</div>
                <div class="cw-metric-sub">Kc ({est.get('kc')}) × ETo ({inp.get('eto_mm_day') or 'n/a'})</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Crop Demand ({period} Days)</div>
                <div class="cw-metric-value">{fmt(est.get('crop_demand_mm'), 'mm', 1)}</div>
                <div class="cw-metric-sub">ETc × {period} days window</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Net Irrigation Need</div>
                <div class="cw-metric-value">{fmt(est.get('net_irrigation_mm'), 'mm', 1)}</div>
                <div class="cw-metric-sub">Basis: {est.get('net_basis', 'n/a')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Gross Irrigation Need</div>
                <div class="cw-metric-value">{fmt(est.get('gross_irrigation_mm'), 'mm', 1)}</div>
                <div class="cw-metric-sub">Eff: {fmt(est.get('efficiency_pct'), '%', 0)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # Second row of metrics: Volumes & Rain
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Effective Rainfall</div>
                <div class="cw-metric-value">{fmt(est.get('effective_rain_mm'), 'mm', 1)}</div>
                <div class="cw-metric-sub">Rain: {fmt(est.get('rain_mm'), 'mm', 1)} (80% credit)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col6:
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Rain Minus Demand</div>
                <div class="cw-metric-value">{fmt(est.get('rain_minus_demand_mm'), 'mm', 1)}</div>
                <div class="cw-metric-sub">Surplus (+) or Deficit (-)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col7:
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Net Water Volume</div>
                <div class="cw-metric-value">{fmt(est.get('net_volume_m3'), 'm³', 0)}</div>
                <div class="cw-metric-sub">Area: {fmt(est.get('area_ha'), 'ha', 2)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col8:
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Gross Water Volume</div>
                <div class="cw-metric-value">{fmt(est.get('gross_volume_m3'), 'm³', 0)}</div>
                <div class="cw-metric-sub">Volume needed at pump</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # Visualizations
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("#### Water Budget Breakdown (mm)")
        if est.get("crop_demand_mm") is not None:
            fig_budget = go.Figure()
            fig_budget.add_trace(
                go.Bar(
                    x=["Crop Demand", "Effective Rain", "Net Irrigation Depth"],
                    y=[est["crop_demand_mm"], est.get("effective_rain_mm") or 0.0, est.get("net_irrigation_mm") or 0.0],
                    text=[f"{est['crop_demand_mm']:.1f} mm", f"{est.get('effective_rain_mm') or 0:.1f} mm", f"{est.get('net_irrigation_mm') or 0:.1f} mm"],
                    textposition="auto",
                    marker_color=["#1B4332", "#38BDF8", "#D97706"],
                )
            )
            fig_budget.update_layout(
                height=280,
                margin=dict(t=30, b=20, l=40, r=20),
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#F8FAFC",
                font=dict(family="Inter"),
                yaxis_title="Millimeters (mm)",
            )
            st.plotly_chart(fig_budget, use_container_width=True)
        else:
            st.info("💡 **Water budget chart requires ETo.** Please provide ETo in Field Assessment.")

    with col_chart2:
        st.markdown("#### Root-Zone Soil Moisture Status")
        if "taw_mm" in est and "depletion_now_mm" in est:
            taw = est["taw_mm"]
            raw = est["raw_mm"]
            dr = est["depletion_now_mm"]
            avail_water = taw - dr

            fig_soil = go.Figure()
            fig_soil.add_trace(go.Bar(
                name="Remaining Water",
                x=["Soil Root Zone"],
                y=[avail_water],
                marker_color="#2D6A4F",
                text=[f"Current: {avail_water:.1f} mm"],
                textposition="inside",
            ))
            fig_soil.add_trace(go.Bar(
                name="Root Depletion (Dr)",
                x=["Soil Root Zone"],
                y=[dr],
                marker_color="#DC2626" if dr >= raw else "#F59E0B",
                text=[f"Depleted: {dr:.1f} mm"],
                textposition="inside",
            ))
            fig_soil.update_layout(
                barmode="stack",
                height=280,
                margin=dict(t=30, b=20, l=40, r=20),
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#F8FAFC",
                font=dict(family="Inter"),
                yaxis_title="Total Available Water TAW (mm)",
            )
            st.plotly_chart(fig_soil, use_container_width=True)
            st.caption(f"TAW: {taw:.1f} mm | Allowable Depletion RAW: {raw:.1f} mm | Current Depletion Dr: {dr:.1f} mm")
        else:
            st.info("ℹ️ **Volumetric soil balance not enabled.** Check 'I have volumetric soil-water data' in Field Assessment to view root-zone depletion.")

    st.write("")

    # Expandable "How was this calculated?" section
    with st.expander("🔬 How Was This Calculated? (FAO-56 Methodology & Mathematical Formulas)", expanded=True):
        st.markdown(
            r"""
            This application uses a deterministic calculation engine based on **FAO Irrigation and Drainage Paper 56**:
            
            #### 1. Crop Evapotranspiration ($ET_c$)
            $$ET_c = K_c \times ET_o$$
            - **$ET_c$**: Crop water consumption under standard conditions ($mm/day$).
            - **$K_c$**: Single crop coefficient for sugarcane ($0.40$ Germination, $0.80$ Tillering, $1.25$ Grand growth, $0.75$ Maturity).
            - **$ET_o$**: Reference grass evapotranspiration ($mm/day$).
            
            #### 2. Crop Water Demand Over Planning Period
            $$\text{Crop Demand} = ET_c \times \text{Planning Period Days}$$
            
            #### 3. Effective Rainfall ($P_{\text{eff}}$)
            $$P_{\text{eff}} = f_{\text{rain}} \times P_{\text{user}}$$
            - Configured prototype retention fraction: $f_{\text{rain}} = 0.80$.
            
            #### 4. Total and Readily Available Soil Water (TAW & RAW)
            $$\text{TAW} = 1000 \times \left(\frac{FC - PWP}{100}\right) \times Z_r$$
            $$\text{RAW} = p \times \text{TAW}$$
            - **$FC$**: Field Capacity (volumetric %).
            - **$PWP$**: Permanent Wilting Point (volumetric %).
            - **$Z_r$**: Effective sugarcane rooting depth ($m$).
            - **$p$**: Allowable depletion fraction without water stress ($0.65$ default for sugarcane).
            
            #### 5. Net Irrigation Requirement ($I_{\text{net}}$)
            - **With volumetric soil-water balance:** Refills the root zone to Field Capacity at end of period:
              $$I_{\text{net}} = \min(\max(D_{r,\text{now}} + \text{Demand} - P_{\text{eff}}, 0), \text{TAW})$$
            - **Without soil-water data:** Crop demand minus effective rainfall:
              $$I_{\text{net}} = \max(0, \text{Demand} - P_{\text{eff}})$$
            
            #### 6. Gross Irrigation Requirement & Volumetric Water Demand
            $$I_{\text{gross}} = \frac{I_{\text{net}}}{\text{Efficiency} / 100}$$
            $$\text{Volume } (m^3) = I_{\text{depth}} (mm) \times \text{Area } (ha) \times 10$$
            *(Note: $1\text{ mm}$ over $1\text{ ha} = 10\text{ m}^3 = 10,000\text{ litres}$)*
            """
        )

    # Missing Data & Data Completeness Audit Panel
    with st.expander("📋 Data Completeness Audit & Assumptions", expanded=False):
        c_a1, c_a2 = st.columns(2)
        with c_a1:
            st.markdown("#### Input Data Completeness")
            miss_labels = {
                "eto": ("Reference ETo", "Enter ETo to enable forward crop demand projection"),
                "rainfall_mm": ("Quantitative Rainfall (mm)", "Enter mm value to receive rainfall deduction credit"),
                "soil_water_data": ("Volumetric Soil Parameters", "Enter FC, PWP, and Root Depth to calculate root zone storage"),
                "efficiency": ("Irrigation Efficiency (%)", "Enter efficiency to calculate gross volume needed at pump"),
                "area": ("Field Area", "Enter area to calculate total volumetric water in cubic meters"),
                "pump_flow": ("Pump Flow Rate (m³/h)", "Enter flow rate to calculate required pump operating duration"),
            }
            missing = result.get("missing_inputs", [])
            for key, (label, desc) in miss_labels.items():
                if key in missing:
                    st.markdown(f"❌ **{label}:** Not provided ({desc})")
                else:
                    st.markdown(f"✅ **{label}:** Supplied and incorporated")
        with c_a2:
            st.markdown("#### Configured Assumptions")
            for a in result.get("assumptions", []):
                st.markdown(f"- {a}")
            st.markdown("#### Documented Limitations")
            for lim in result.get("limitations", []):
                st.markdown(f"- {lim}")

    # Navigation Footer
    st.write("")
    c_n1, c_n2 = st.columns([1, 1])
    with c_n1:
        if st.button("⬅️ Return to Field Assessment", use_container_width=True):
            on_navigate("Field Assessment")
            st.rerun()
    with c_n2:
        if st.button("Proceed to Irrigation Planner ➡️", type="primary", use_container_width=True):
            on_navigate("Irrigation Planner")
            st.rerun()
