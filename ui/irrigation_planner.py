"""Irrigation planning interface based on deterministic scheduler outputs."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from ui.styles import render_tag, render_disclaimer


def render_irrigation_planner(result: dict, sched: dict, on_navigate):
    """Render the Irrigation Planner with decision badges, pump durations, timeline, and rule explanations."""
    st.markdown("## 📅 Deterministic Irrigation Planner")
    render_tag("calc")
    render_disclaimer()

    if not result.get("valid"):
        st.error("🚫 Cannot build irrigation schedule: field inputs are invalid.")
        if st.button("⬅️ Return to Field Assessment"):
            on_navigate("Field Assessment")
            st.rerun()
        return

    status_code = sched.get("status_code", "INSUFFICIENT_DATA")
    status_label = sched.get("status_label", "Insufficient Data")

    # Status Pill / Card Color Mapping
    status_colors = {
        "IRRIGATE_NOW": ("#E8F5E9", "#1B5E20", "#2E7D32", "🚨 Consider Irrigating Now"),
        "SCHEDULE_LATER": ("#E0F2FE", "#0369A1", "#0284C7", "📅 Plan Irrigation for Later Date"),
        "DEFER_REASSESS": ("#FEF3C7", "#92400E", "#D97706", "⏳ Defer Irrigation & Reassess"),
        "REVIEW_PENDING_SOIL_DATA": ("#FFF7ED", "#C2410C", "#EA580C", "🔍 Review Pending Soil Data"),
        "INSUFFICIENT_DATA": ("#F1F5F9", "#475569", "#64748B", "⚠️ Insufficient Information"),
    }
    bg, fg, border, display_title = status_colors.get(status_code, ("#F1F5F9", "#475569", "#64748B", status_label))

    # Prominent Status Card
    st.markdown(
        f"""
        <div style="background: {bg}; border: 2px solid {border}; border-radius: 12px; padding: 1.4rem 1.6rem; margin-bottom: 1.2rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: {fg}; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem;">
                Deterministic Scheduling Status
            </div>
            <div style="font-size: 1.7rem; font-weight: 800; color: {fg}; margin: 0 0 0.5rem 0;">
                {display_title}
            </div>
            <div style="font-size: 0.95rem; color: #1F2937; line-height: 1.5;">
                {sched.get('message', '')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4 Key Action Metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        rev_date = sched.get("review_date") or "Not calculable"
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Review / Action Date</div>
                <div class="cw-metric-value" style="font-size: 1.35rem;">{rev_date}</div>
                <div class="cw-metric-sub">ISO Date (YYYY-MM-DD)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        in_days = sched.get("review_in_days")
        days_str = f"{in_days} days" if in_days is not None else "n/a"
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Days From Today</div>
                <div class="cw-metric-value">{days_str}</div>
                <div class="cw-metric-sub">Based on depletion rate</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        dur = sched.get("irrigation_duration_h")
        dur_str = f"{dur:.1f} hours" if dur is not None else "Not calculated"
        sub_dur = "Gross vol / Pump flow" if dur is not None else "Needs volume & pump flow"
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Pump Operating Time</div>
                <div class="cw-metric-value" style="font-size: 1.25rem;">{dur_str}</div>
                <div class="cw-metric-sub">{sub_dur}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        suff = sched.get("water_sufficient")
        suff_str = {True: "Sufficient", False: "Deficit", None: "Not calculated"}.get(suff, "n/a")
        cov = sched.get("water_coverage_pct")
        cov_str = f"Coverage: {cov:.0f}%" if cov is not None else "Needs storage data"
        st.markdown(
            f"""
            <div class="cw-metric-card">
                <div class="cw-metric-title">Water Sufficiency</div>
                <div class="cw-metric-value" style="font-size: 1.35rem;">{suff_str}</div>
                <div class="cw-metric-sub">{cov_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # Schedule Action Rows / Timeline
    st.markdown("### 📋 Scheduled Operational Actions")
    rows = sched.get("rows", [])
    if rows:
        col_t1, col_t2 = st.columns([1.5, 1])
        with col_t1:
            df_sched = pd.DataFrame(rows)
            st.dataframe(df_sched, hide_index=True, use_container_width=True)

        with col_t2:
            fig = go.Figure()
            for r in rows:
                net_text = f"{r['net_depth_mm']:.1f} mm" if r.get("net_depth_mm") is not None else "No water"
                fig.add_trace(
                    go.Scatter(
                        x=[r["date"]],
                        y=[r["action"]],
                        mode="markers+text",
                        text=[f"{r['action']} ({net_text})"],
                        textposition="top center",
                        marker=dict(size=16, color="#1B4332"),
                        hovertext=f"Date: {r['date']}<br>Action: {r['action']}<br>Net: {net_text}<br>Note: {r['note']}",
                        hoverinfo="text",
                        showlegend=False,
                    )
                )
            fig.update_layout(
                height=220,
                margin=dict(t=30, b=25, l=40, r=40),
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#F8FAFC",
                font=dict(family="Inter"),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ No specific schedule actions could be computed. Insufficient data provided.")

    st.write("")

    # Reasons & Reassessment Triggers
    c_r1, c_r2 = st.columns(2)
    with c_r1:
        st.markdown("#### 🎯 Reasoning Behind Scheduling Decision")
        for r in sched.get("reasons", []):
            st.markdown(f"- {r}")

    with c_r2:
        st.markdown("#### 🔄 Factors Requiring Reassessment")
        for f in sched.get("reassess_factors", []):
            st.markdown(f"- {f}")
        st.caption("The planning period is a chosen review interval, not an agronomically fixed irrigation frequency.")

    st.write("")

    # Expandable "Why this schedule?"
    with st.expander("🧠 Why This Schedule? (Decision Tree & Rules of the Deterministic Scheduler)", expanded=True):
        st.markdown(
            r"""
            The scheduler executes a strict deterministic state machine without stochastic or LLM guessing:
            
            1. **Rule 1 (Soil Depletion Exceeds RAW):**
               If volumetric soil data exist and current root-zone depletion $D_r \ge \text{RAW}$, status is **IRRIGATE_NOW**.
            2. **Rule 2 (Forward Projection):**
               If $D_r < \text{RAW}$ and $ET_c$ is known, projects days until depletion reaches RAW:
               $$\text{Days} = \left\lfloor \frac{\text{RAW} - D_{r,\text{now}}}{ET_c - P_{\text{eff}} / \text{Period}} \right\rfloor$$
               - If $\text{Days} \le 0$: **IRRIGATE_NOW**.
               - If $0 < \text{Days} < \text{Period}$: **SCHEDULE_LATER** on date $(\text{Today} + \text{Days})$.
               - If $\text{Days} \ge \text{Period}$: **DEFER_REASSESS** at end of period.
            3. **Rule 3 (Heavy Unquantified Rain Override):**
               If user selected 'Heavy' rainfall category without numerical mm value, an IRRIGATE_NOW status is deferred to **DEFER_REASSESS** to prevent over-watering.
            4. **Rule 4 (Missing Soil Data):**
               If only crop demand is calculable but no volumetric soil water is provided, timing cannot be judged $\to$ **REVIEW_PENDING_SOIL_DATA**.
            5. **Rule 5 (Insufficient Inputs):**
               If neither crop demand nor soil depletion can be calculated $\to$ **INSUFFICIENT_DATA** (refuses to invent a fake date).
            """
        )

    # Navigation Footer
    st.write("")
    c_n1, c_n2 = st.columns([1, 1])
    with c_n1:
        if st.button("⬅️ Back to Water Analysis", use_container_width=True):
            on_navigate("Water Analysis")
            st.rerun()
    with c_n2:
        if st.button("Proceed to AI Insights 🤖", type="primary", use_container_width=True):
            on_navigate("AI Insights")
            st.rerun()
