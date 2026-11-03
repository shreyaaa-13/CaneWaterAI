"""Self-Correction Experiment UI module for CaneWater AI.

Integrates the ReAct-Reflexion Self-Correction Framework into Streamlit:
- Displays field inputs and original deterministic engine results.
- Executes and visualizes the bounded generate-validate-feedback-retry loop.
- Supports both Repeatable Demonstration Mode (TC01-TC07) and Live LLM Mode.
- Shows clear status badges, step-by-step attempt trace, and faculty technical panel.
"""
from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from genai_explainer import LANGUAGES, check_api_status, DEFAULT_MODEL
from response_validator import collect_facts, RULES_METADATA
from self_correction import (
    DEMO_SCENARIOS,
    STATUS_API_UNAVAILABLE,
    STATUS_CORRECTION_SUCCESSFUL,
    STATUS_FALLBACK_USED,
    STATUS_INITIAL_VALID,
    STATUS_MAX_ATTEMPTS_REACHED,
    STATUS_VALIDATION_FAILED,
    SelfCorrectionConfig,
    SelfCorrectionResult,
    compute_experiment_metrics,
    run_self_correction_framework,
)
from ui.styles import render_disclaimer, render_tag


def render_status_badge(status: str, mode: str):
    """Render a clear, standardized status badge matching experiment requirements."""
    colors = {
        STATUS_INITIAL_VALID: ("#DCFCE7", "#166534", "#86EFAC", "✅"),
        STATUS_CORRECTION_SUCCESSFUL: ("#DCFCE7", "#166534", "#86EFAC", "🎯"),
        STATUS_MAX_ATTEMPTS_REACHED: ("#FEF3C7", "#92400E", "#FCD34D", "⚠️"),
        STATUS_FALLBACK_USED: ("#FEF3C7", "#92400E", "#FCD34D", "🛡️"),
        STATUS_API_UNAVAILABLE: ("#FEE2E2", "#991B1B", "#FCA5A5", "🔌"),
        STATUS_VALIDATION_FAILED: ("#FEE2E2", "#991B1B", "#FCA5A5", "❌"),
    }
    bg, fg, border, icon = colors.get(status, ("#F3F4F6", "#374151", "#D1D5DB", "ℹ️"))

    mode_badge = (
        '<span style="background: #DBEAFE; color: #1E40AF; padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; border: 1px solid #BFDBFE; margin-left: 0.6rem;">SIMULATED MOCK TEST</span>'
        if mode == "mock_demonstration"
        else '<span style="background: #D1FAE5; color: #065F46; padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; border: 1px solid #A7F3D0; margin-left: 0.6rem;">LIVE GROQ LLM</span>'
    )

    st.markdown(
        f"""
        <div style="background: {bg}; border: 1.5px solid {border}; border-radius: 10px; padding: 0.9rem 1.2rem; margin: 0.8rem 0 1.2rem 0; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
            <div style="display: flex; align-items: center; gap: 0.6rem;">
                <span style="font-size: 1.4rem;">{icon}</span>
                <div>
                    <div style="font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: {fg}; letter-spacing: 0.05em;">Experiment Status</div>
                    <div style="font-size: 1.2rem; font-weight: 800; color: {fg};">{status}</div>
                </div>
            </div>
            <div>{mode_badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_self_correction_experiment(result: dict, sched: dict, on_navigate):
    """Render the dedicated Self-Correction Experiment section."""
    st.markdown("## 🔬 Self-Correction Experiment")
    st.markdown(
        "**ReAct–Reflexion-Based Self-Correction Framework for Reliable GenAI-Driven Sugarcane Irrigation Advisory**"
    )
    st.caption(
        "Demonstrating automated error detection, structured reflection feedback, bounded retry loops, "
        "and safe deterministic fallback for reliable generative irrigation explanations."
    )
    render_disclaimer()

    # Ensure field inputs are valid
    if not result.get("valid"):
        st.error("🚫 Cannot run experiment: Current field inputs are invalid. Please check missing required parameters.")
        if st.button("⬅️ Return to Field Assessment", type="primary"):
            on_navigate("Field Assessment")
            st.rerun()
        return

    # Initialize experiment session state
    if "self_correction_history" not in st.session_state:
        st.session_state["self_correction_history"] = []
    if "self_correction_result" not in st.session_state:
        st.session_state["self_correction_result"] = None

    facts = collect_facts(result, sched)
    current_lang = st.session_state.get("language", "en")
    api_status = check_api_status()

    # -------------------------------------------------------------------------
    # 1. Experiment Setup & Control Panel
    # -------------------------------------------------------------------------
    st.markdown("### ⚙️ Experiment Configuration & Execution Mode")

    c_mode, c_cfg, c_lang = st.columns([1.6, 1.2, 1.2])

    with c_mode:
        exec_mode = st.radio(
            "Select Execution Mode",
            ["Repeatable Demonstration Mode (TC01–TC07)", "Live Groq Inference (openai/gpt-oss-20b)"],
            index=0,
            help="Repeatable Demonstration uses controlled mock responses for repeatable faculty evaluation. Live mode contacts the Groq API.",
        )

    with c_cfg:
        max_retries = st.slider(
            "Max Correction Attempts (Limit)",
            min_value=1,
            max_value=5,
            value=3,
            help="Configurable upper bound of correction attempts before safe fallback is triggered (finite loop guardrail). Default is 3.",
        )

    with c_lang:
        exp_lang = st.selectbox(
            "Advisory Language",
            list(LANGUAGES.keys()),
            index=list(LANGUAGES.keys()).index(current_lang) if current_lang in LANGUAGES else 0,
            format_func=lambda k: LANGUAGES[k],
            key="exp_lang_select",
        )

    # Mode-Specific Controls
    selected_scenario_id = None
    if "Repeatable Demonstration" in exec_mode:
        st.markdown("#### 🧪 Select Controlled Demonstration Scenario:")
        scenario_options = list(DEMO_SCENARIOS.keys())
        scenario_labels = [f"{k}: {DEMO_SCENARIOS[k]['title'].split('—')[-1].strip()}" for k in scenario_options]

        chosen_idx = st.selectbox(
            "Select Scenario to Execute:",
            range(len(scenario_options)),
            format_func=lambda i: scenario_labels[i],
            help="Controlled mock scenarios to test individual validation guardrails and loop mechanics.",
        )
        selected_scenario_id = scenario_options[chosen_idx]
        sc_meta = DEMO_SCENARIOS[selected_scenario_id]

        st.info(
            f"**{sc_meta['title']}**\n\n"
            f"• **Objective:** {sc_meta['description']}\n\n"
            f"• **Expected Result:** `{sc_meta['expected_status']}` | Expected calls: `{sc_meta['expected_attempts']}`\n\n"
            f"*(Marked clearly as simulated test case. Uses real validator and real correction loop code.)*"
        )
    else:
        st.markdown("#### 🤖 Live Groq Model Status:")
        if api_status["available"]:
            st.success(f"🟢 **Groq API Connected:** Model `{DEFAULT_MODEL}` ready for live generation and self-correction.")
        else:
            st.warning(
                f"🟡 **API Key Not Detected:** {api_status['reason']}\n\n"
                f"Live calls will gracefully trigger safe fallback. Set `GROQ_API_KEY` in environment or `.env` for cloud inference."
            )

    # Run Button
    col_run, col_clear, _ = st.columns([1.5, 1.2, 3])
    with col_run:
        btn_label = "▶️ Run Demonstration Scenario" if selected_scenario_id else "▶️ Run Live Self-Correction"
        run_clicked = st.button(btn_label, type="primary", use_container_width=True)

    with col_clear:
        if st.button("🔄 Reset Experiment", use_container_width=True):
            st.session_state["self_correction_result"] = None
            st.session_state["self_correction_history"] = []
            st.rerun()

    if run_clicked:
        cfg = SelfCorrectionConfig(max_correction_attempts=max_retries, language=exp_lang)
        with st.spinner(f"Executing self-correction loop for {exp_lang}..."):
            exp_res = run_self_correction_framework(
                result=result,
                schedule=sched,
                language=exp_lang,
                config=cfg,
                mock_scenario_id=selected_scenario_id,
            )
        st.session_state["self_correction_result"] = exp_res
        st.session_state["self_correction_history"].append(exp_res)
        st.toast(f"Completed run: {exp_res.overall_status}", icon="✅" if "Valid" in exp_res.overall_status or "Successful" in exp_res.overall_status else "ℹ️")

    st.write("---")

    # -------------------------------------------------------------------------
    # 2. Display Ground Truth Inputs & Deterministic Engine Output
    # -------------------------------------------------------------------------
    st.markdown("### 1️⃣ Field Inputs & Trusted Deterministic Calculation (Ground Truth)")
    st.caption("The deterministic calculation engine is the sole source of truth. The LLM only explains these values and cannot modify them.")

    col_in1, col_in2 = st.columns([1, 1.2])

    with col_in1:
        inp = result.get("inputs_used", {})
        st.markdown(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.9rem;">
                <span class="cw-tag cw-tag-user">Supplied Field Inputs</span>
                <ul style="margin: 0.4rem 0 0 0; padding-left: 1.2rem; font-size: 0.88rem; line-height: 1.6;">
                    <li><strong>Crop Growth Stage:</strong> {inp.get('growth_stage', 'N/A')} ({inp.get('crop_age_months', 'N/A')} months)</li>
                    <li><strong>Soil Moisture:</strong> {inp.get('soil_moisture_pct', 'N/A')}% (Volumetric: {inp.get('moisture_is_volumetric')})</li>
                    <li><strong>Reference ETo:</strong> {inp.get('eto_mm_day', 'N/A')} mm/day</li>
                    <li><strong>Rainfall Forecast:</strong> {inp.get('rainfall_mm', '0')} mm ({inp.get('rainfall_category')})</li>
                    <li><strong>Field Area:</strong> {inp.get('area', 'N/A')} {inp.get('area_unit', 'ha')} | <strong>Efficiency:</strong> {inp.get('irrigation_efficiency_pct', 'N/A')}%</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_in2:
        est = result.get("estimates", {})
        status_label = sched.get("status_label", "N/A")
        code = sched.get("status_code", "N/A")
        net_mm = est.get("net_irrigation_mm")
        gross_mm = est.get("gross_irrigation_mm")
        vol_m3 = est.get("gross_volume_m3")
        dur_h = sched.get("irrigation_duration_h")
        rev_d = sched.get("review_date", "N/A")

        st.markdown(
            f"""
            <div style="background: #F0FDF4; border: 1.5px solid #86EFAC; border-radius: 8px; padding: 0.9rem;">
                <span class="cw-tag cw-tag-calc">Calculated Ground Truth (Deterministic Engine)</span>
                <div style="font-size: 1.05rem; font-weight: 700; color: #166534; margin: 0.2rem 0;">
                    Decision: {status_label} <code>[{code}]</code>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem; font-size: 0.85rem; margin-top: 0.4rem;">
                    <div><strong>Net Requirement:</strong> {f'{net_mm:.1f} mm' if net_mm is not None else 'N/A'}</div>
                    <div><strong>Gross Requirement:</strong> {f'{gross_mm:.1f} mm' if gross_mm is not None else 'N/A'}</div>
                    <div><strong>Water Volume:</strong> {f'{vol_m3:.1f} m³' if vol_m3 is not None else 'N/A'}</div>
                    <div><strong>Pump Duration:</strong> {f'{dur_h:.1f} hours' if dur_h is not None else 'N/A'}</div>
                    <div><strong>Next Review Date:</strong> {rev_d}</div>
                    <div><strong>Crop ETc:</strong> {est.get('etc_mm_day', 'N/A')} mm/day</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # -------------------------------------------------------------------------
    # 3. Experiment Execution Results (Steps 3 - 10)
    # -------------------------------------------------------------------------
    cur_res: SelfCorrectionResult = st.session_state.get("self_correction_result")

    if not cur_res:
        st.info("👆 Click **'Run Demonstration Scenario'** or **'Run Live Self-Correction'** above to execute the experiment and view the audit trace.")
    else:
        # Status Label
        render_status_badge(cur_res.overall_status, cur_res.execution_mode)

        # Overview Metrics Pill Row
        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        c_m1.metric("Total Attempts", f"{cur_res.total_attempts} / {1 + max_retries}")
        c_m2.metric("Initial Validation", "Passed ✅" if cur_res.initial_passed else "Failed ❌")
        c_m3.metric("Self-Corrected", "Yes 🎯" if cur_res.corrected else ("No" if cur_res.initial_passed else "Fallback"))
        c_m4.metric("Output Origin", "Verified AI Layer" if cur_res.source == "ai" else "Safe Deterministic Fallback")

        st.write("")

        # ---------------------------------------------------------------------
        # Step-by-Step ReAct-Reflexion Trace Accordion
        # ---------------------------------------------------------------------
        st.markdown("### 2️⃣ ReAct–Reflexion Iteration Trace & Audit Log")
        st.caption("Detailed view of every generation (Act), validator evaluation (Observe), and structured feedback (Reflect).")

        if not cur_res.attempts_history:
            st.warning(f"⚠️ No generation attempts recorded. Reason: `{cur_res.fallback_reason}` ({cur_res.api_error_category}). Transitioned directly to safe fallback.")
        else:
            for att in cur_res.attempts_history:
                att_num = att.attempt_number
                is_init = att_num == 1
                stage_name = "Initial Generation (Attempt 1)" if is_init else f"Self-Correction Attempt {att_num}"
                badge = "✅ PASSED" if att.validation_passed else "❌ FAILED VALIDATION"
                color = "#166534" if att.validation_passed else "#991B1B"

                with st.expander(f"Iterative Step {att_num}: {stage_name} — {badge}", expanded=True):
                    col_gen, col_eval = st.columns([1.25, 1])

                    with col_gen:
                        st.markdown(f"**Generated Explanation Candidate ({cur_res.language.upper()}):**")
                        st.text_area(
                            f"Explanation Text (Attempt {att_num})",
                            value=att.candidate_text,
                            height=150,
                            disabled=True,
                            key=f"att_text_{att_num}",
                        )
                        st.caption(f"⏱️ Generation & Validation Latency: `{att.latency_ms:.1f} ms`")

                    with col_eval:
                        st.markdown(f"**Validator Verdict (Observe):**")
                        if att.validation_passed:
                            st.success("✅ **All Validation Guardrails Passed!**\n\n- Numerical invariance verified.\n- Decision status aligns.\n- Units preserved.\n- No unapproved agronomic claims.")
                        else:
                            st.error(f"❌ **Validation Failed:** `{len(att.issues)}` issue(s) detected:")
                            for iss in att.issues:
                                st.markdown(f"• **`[{iss['code']}]` {iss.get('rule') or iss['code']}:** {iss['message']}")

                    # Reflexion Feedback Display if Failed
                    if not att.validation_passed and att.structured_feedback:
                        st.markdown("---")
                        st.markdown("**🧠 Structured Reflection Feedback Injected for Correction (Reflect):**")
                        st.code(att.structured_feedback, language="text")

        st.write("")

        # ---------------------------------------------------------------------
        # Final Output Section (Farmer-Facing vs Technical Separation)
        # -------------------------------------------------------------------------
        st.markdown("### 3️⃣ Final Advisory Output Presented to Farmer")
        col_f1, col_f2 = st.columns([1.4, 1])

        with col_f1:
            if cur_res.source == "ai" and not cur_res.fallback_used:
                st.markdown(
                    """
                    <div style="background: #F0FDF4; border: 1.5px solid #86EFAC; border-radius: 8px; padding: 1rem;">
                        <span class="cw-tag cw-tag-ai">Verified AI Explanation</span>
                        <div style="font-weight: 700; color: #166534; font-size: 0.95rem; margin-top: 0.2rem;">
                            Passed All Deterministic Validation Checks
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.info(cur_res.final_text)
            else:
                st.markdown(
                    """
                    <div style="background: #FEF3C7; border: 1.5px solid #FCD34D; border-radius: 8px; padding: 1rem;">
                        <span class="cw-tag cw-tag-calc">Safe Deterministic Fallback</span>
                        <div style="font-weight: 700; color: #92400E; font-size: 0.95rem; margin-top: 0.2rem;">
                            AI Explanation Could Not Be Verified — Rule-Engine Fallback Served
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.warning(cur_res.final_text)
                st.caption(f"Fallback Reason: `{cur_res.fallback_reason}` | API Category: `{cur_res.api_error_category or 'none'}`")

        with col_f2:
            st.markdown("**Summary Audit Record:**")
            audit_df = pd.DataFrame({
                "Metric": [
                    "Experiment Status",
                    "Total Iterations",
                    "Initial Attempt Passed",
                    "Correction Triggered",
                    "Correction Successful",
                    "Safe Fallback Used",
                    "Execution Mode",
                    "Total Latency",
                ],
                "Value": [
                    cur_res.overall_status,
                    str(cur_res.total_attempts),
                    "Yes" if cur_res.initial_passed else "No",
                    "Yes" if cur_res.total_attempts > 1 else "No",
                    "Yes" if cur_res.corrected else "No",
                    "Yes" if cur_res.fallback_used else "No",
                    cur_res.execution_mode,
                    f"{cur_res.total_latency_ms:.1f} ms",
                ]
            })
            st.dataframe(audit_df, hide_index=True, use_container_width=True)

        st.write("")

        # ---------------------------------------------------------------------
        # Expandable Faculty Technical Details Panel
        # ---------------------------------------------------------------------
        with st.expander("🎓 Expandable Technical Details Panel (For Faculty Evaluation & Defense)", expanded=False):
            st.markdown("#### Complete Machine-Readable Audit Data")
            st.caption("Inspect the exact ground truth facts JSON, validation rules metadata, and raw JSON response.")

            t_tab1, t_tab2, t_tab3 = st.tabs(["📋 Ground Truth Facts JSON", "🛡️ Validation Guardrails Reference", "📦 Full Run JSON Audit"])

            with t_tab1:
                st.json(facts)

            with t_tab2:
                rules_table = [
                    {"Code": k, "Guardrail Rule": v["name"], "Scope Description": v["description"]}
                    for k, v in RULES_METADATA.items()
                ]
                st.table(pd.DataFrame(rules_table))

            with t_tab3:
                st.json(cur_res.to_dict())

    st.write("---")

    # -------------------------------------------------------------------------
    # 4. Repeatable Demonstration Matrix & Session Empirical Metrics
    # -------------------------------------------------------------------------
    st.markdown("### 4️⃣ Repeatable Test Matrix & Empirical Session Metrics")
    st.caption("Standardized test case reference and live aggregated metrics from your session runs.")

    tab_matrix, tab_metrics = st.tabs(["🧪 Standardized Scenarios (TC01–TC07)", "📊 Empirical Session Metrics"])

    with tab_matrix:
        matrix_rows = []
        for tc_id, tc_data in DEMO_SCENARIOS.items():
            matrix_rows.append({
                "Test ID": tc_id,
                "Scenario Name": tc_data["title"].split("—")[-1].strip(),
                "Target Guardrail / Failure Mode": tc_data["expected_rule"],
                "Expected Attempts": tc_data["expected_attempts"],
                "Expected Result": tc_data["expected_status"],
            })
        st.dataframe(pd.DataFrame(matrix_rows), hide_index=True, use_container_width=True)
        st.caption("All mock scenarios are deterministically reproducible for faculty demonstration.")

    with tab_metrics:
        history = st.session_state.get("self_correction_history", [])
        computed = compute_experiment_metrics(history)

        col_met1, col_met2, col_met3, col_met4 = st.columns(4)
        col_met1.metric("Total Runs", computed["total_runs"])
        col_met2.metric("Initial Pass Rate", f"{computed['initial_pass_rate']}%")
        col_met3.metric("Final Pass Rate", f"{computed['final_pass_rate']}%")
        col_met4.metric("Correction Success Rate", f"{computed['correction_success_rate']}%")

        col_met5, col_met6, col_met7, col_met8 = st.columns(4)
        col_met5.metric("Avg Attempts", computed["average_attempts"])
        col_met6.metric("Fallback Count", computed["fallback_count"])
        col_met7.metric("API Failures", computed["api_failure_count"])
        col_met8.metric("Avg Latency", f"{computed['average_latency_ms']:.1f} ms")

        st.caption(
            "Empirically calculated across your active session runs. "
            "Note: These metrics evaluate software validator reliability and correction convergence, "
            "not real-world agronomic yield outcomes."
        )

    # Navigation Footer
    st.write("")
    c_back, c_fwd = st.columns([1, 1])
    with c_back:
        if st.button("⬅️ Back to Validation Lab", use_container_width=True):
            on_navigate("Validation Lab")
            st.rerun()
    with c_fwd:
        if st.button("View AI Insights 🤖", type="primary", use_container_width=True):
            on_navigate("AI Insights")
            st.rerun()
