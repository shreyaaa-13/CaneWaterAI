"""Overview dashboard with real-time metric cards, Plotly charts, and assessment summary."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from ui.landing import render_landing_hero
from ui.styles import render_tag


def render_overview(result: dict, sched: dict, on_navigate):
    """Render complete landing hero and executive overview dashboard."""
    # Top Landing Banner & Capabilities
    render_landing_hero(on_navigate)

    st.markdown("---")
    st.markdown("### 📊 Current Field Assessment Overview")
    render_tag("calc")

    est = result.get("estimates", {})
    inp = result.get("inputs_used", {})

    # 6 Metric Cards
    m1, m2, m3, m4, m5, m6 = st.columns(6)

    # 1. Crop Age
    with m1:
        age_val = f"{inp.get('crop_age_months', 'n/a')} mo" if inp.get("crop_age_months") is not None else "n/a"
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Crop Age</div>
                <div class="cw-metric-value">{age_val}</div>
                <div class="cw-metric-sub">Sugarcane Ratoon / Plant</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Growth Stage
    with m2:
        stage_val = inp.get("growth_stage", "n/a")
        kc_val = f"Kc {est.get('kc', 'n/a')}" if est.get("kc") is not None else ""
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Growth Stage</div>
                <div class="cw-metric-value" style="font-size: 1.15rem; word-break: break-word;">{stage_val}</div>
                <div class="cw-metric-sub">{kc_val}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 3. Soil Moisture Reading
    with m3:
        moist = inp.get("soil_moisture_pct")
        moist_str = f"{moist:.1f} %" if moist is not None else "n/a"
        vol_label = "Volumetric" if inp.get("moisture_is_volumetric") else "Generic reading"
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Soil Moisture</div>
                <div class="cw-metric-value">{moist_str}</div>
                <div class="cw-metric-sub">{vol_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 4. Water Requirement Status
    with m4:
        net_val = est.get("net_irrigation_mm")
        if not result.get("valid"):
            water_status = "Invalid inputs"
            water_sub = "Correct errors"
        elif result.get("provisional"):
            water_status = "Provisional"
            water_sub = "ETo missing"
        elif net_val is not None:
            water_status = f"{net_val:.1f} mm"
            water_sub = f"Net over {est.get('planning_period_days', 7)}d"
        else:
            water_status = "Not calculated"
            water_sub = "Missing data"
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Net Requirement</div>
                <div class="cw-metric-value">{water_status}</div>
                <div class="cw-metric-sub">{water_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 5. Irrigation Recommendation Status
    with m5:
        if not result.get("valid"):
            sched_status = "Invalid"
            sched_sub = "Validation failed"
        else:
            code = sched.get("status_code", "INSUFFICIENT_DATA")
            sched_status = {
                "IRRIGATE_NOW": "Irrigate Now",
                "SCHEDULE_LATER": "Schedule Later",
                "DEFER_REASSESS": "Defer & Reassess",
                "REVIEW_PENDING_SOIL_DATA": "Review Pending",
                "INSUFFICIENT_DATA": "Insufficient Data",
            }.get(code, "Unknown")
            review_in = sched.get("review_in_days")
            sched_sub = f"In {review_in} days" if review_in is not None else "No date"
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Schedule Status</div>
                <div class="cw-metric-value" style="font-size: 1.12rem;">{sched_status}</div>
                <div class="cw-metric-sub">{sched_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 6. AI Explanation Status
    with m6:
        expl = st.session_state.get("explanation")
        if expl and expl.get("language") == st.session_state.get("language"):
            if expl.get("source") == "ai":
                ai_status = "AI Ready"
                ai_sub = f"Passed (Att. {expl.get('attempts')})"
            else:
                ai_status = "Fallback"
                ai_sub = expl.get("fallback_reason", "Deterministic")
        else:
            ai_status = "Not Generated"
            ai_sub = f"Lang: {st.session_state.get('language', 'en').upper()}"
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">AI Advisory</div>
                <div class="cw-metric-value" style="font-size: 1.15rem;">{ai_status}</div>
                <div class="cw-metric-sub">{ai_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # Visualizations Row
    col_v1, col_v2 = st.columns([1, 1.3])

    # Left: Soil Moisture Reading Gauge
    with col_v1:
        st.markdown("#### Soil Moisture Reading")
        moist_num = inp.get("soil_moisture_pct") or 0.0
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=moist_num,
                number={"suffix": " %", "font": {"size": 32, "color": "#1B4332", "family": "Inter"}},
                title={"text": "User-Entered Soil Moisture", "font": {"size": 13, "color": "#4B5563"}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94A3B8"},
                    "bar": {"color": "#2D6A4F"},
                    "bgcolor": "#F1F5F9",
                    "steps": [
                        {"range": [0, 20], "color": "#FEE2E2"},
                        {"range": [20, 45], "color": "#DCFCE7"},
                        {"range": [45, 100], "color": "#E0F2FE"},
                    ],
                },
            )
        )
        fig_gauge.update_layout(
            height=260,
            margin=dict(t=35, b=15, l=25, r=25),
            paper_bgcolor="#FFFFFF",
            font=dict(family="Inter"),
        )
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.caption("Context gauge based on user entry. Color zones are illustrative benchmarks.")

    # Right: Water Balance / Demand vs Effective Rainfall
    with col_v2:
        st.markdown("#### Crop Demand vs Effective Rainfall")
        demand = est.get("crop_demand_mm")
        rain = est.get("effective_rain_mm") or 0.0
        net_irr = est.get("net_irrigation_mm")

        if demand is not None and net_irr is not None:
            fig_bar = go.Figure()
            fig_bar.add_trace(
                go.Bar(
                    x=["Crop Demand (ETc)", "Effective Rainfall", "Net Irrigation Need"],
                    y=[demand, rain, net_irr],
                    text=[f"{demand:.1f} mm", f"{rain:.1f} mm", f"{net_irr:.1f} mm"],
                    textposition="auto",
                    marker_color=["#2D6A4F", "#38BDF8", "#B45309"],
                )
            )
            fig_bar.update_layout(
                height=260,
                margin=dict(t=25, b=25, l=40, r=20),
                yaxis_title="Depth (mm over period)",
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#F8FAFC",
                font=dict(family="Inter"),
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            st.caption(f"Calculated for planning period of {est.get('planning_period_days', 7)} days.")
        else:
            st.info("💡 **Demand vs Rainfall chart requires reference ETo.** Enter ETo in 'Field Assessment' to view.")

    # Timeline Row & Compact Summary
    st.write("")
    col_t1, col_t2 = st.columns([1.4, 1])

    # Left: Irrigation Schedule Timeline
    with col_t1:
        st.markdown("#### Projected Action Timeline")
        rows = sched.get("rows", [])
        if rows:
            df_rows = pd.DataFrame(rows)
            fig_time = go.Figure()
            for idx, r in df_rows.iterrows():
                depth_text = f" ({r['net_depth_mm']:.1f} mm)" if r.get("net_depth_mm") is not None else ""
                fig_time.add_trace(
                    go.Scatter(
                        x=[r["date"]],
                        y=[r["action"]],
                        mode="markers+text",
                        text=[f"{r['action']}{depth_text}"],
                        textposition="top center",
                        marker=dict(size=14, color="#1B4332"),
                        hoverinfo="text",
                        hovertext=f"Date: {r['date']}<br>Action: {r['action']}<br>Note: {r['note']}",
                        showlegend=False,
                    )
                )
            fig_time.update_layout(
                height=180,
                margin=dict(t=25, b=20, l=40, r=40),
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#F8FAFC",
                font=dict(family="Inter"),
            )
            st.plotly_chart(fig_time, use_container_width=True)
            st.caption(f"Status: **{sched.get('status_label')}**. Next review date: **{sched.get('review_date') or 'n/a'}**.")
        else:
            st.info("No schedule entries available. Provide field parameters or load a sample field.")

    # Right: Compact Field Summary
    with col_t2:
        st.markdown("#### Field Parameter Summary")
        summary_data = [
            ("Crop Age & Stage", f"{inp.get('crop_age_months', 'n/a')} mo ({inp.get('growth_stage')})"),
            ("Soil Type & Reading", f"{inp.get('soil_type')} / {inp.get('soil_moisture_pct')}%"),
            ("Volumetric Data", "Provided (FC, PWP, Depth)" if inp.get("moisture_is_volumetric") else "Generic % (no credit)"),
            ("Weather & Rain", f"{inp.get('weather')} / {inp.get('rainfall_category')} ({inp.get('rainfall_mm') or 0} mm)"),
            ("Method & Area", f"{inp.get('irrigation_method')} / {inp.get('area_ha') or 'n/a'} ha"),
            ("Available Water", f"{inp.get('available_water_m3') or 'n/a'} m³"),
        ]
        df_sum = pd.DataFrame(summary_data, columns=["Parameter", "Active Value"])
        st.dataframe(df_sum, hide_index=True, use_container_width=True)

    # Quick Navigation Footer
    st.write("")
    c_nav1, c_nav2, c_nav3, c_nav4 = st.columns(4)
    with c_nav1:
        if st.button("📝 Edit Field Assessment", use_container_width=True):
            on_navigate("Field Assessment")
            st.rerun()
    with c_nav2:
        if st.button("🧮 View Water Analysis", use_container_width=True):
            on_navigate("Water Analysis")
            st.rerun()
    with c_nav3:
        if st.button("📆 Open Irrigation Planner", use_container_width=True):
            on_navigate("Irrigation Planner")
            st.rerun()
    with c_nav4:
        if st.button("🤖 Inspect AI Insights", use_container_width=True):
            on_navigate("AI Insights")
            st.rerun()
