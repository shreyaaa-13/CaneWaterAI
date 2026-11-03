"""Validation Lab: Demonstrates reliability, self-correction, mock failure presets, and live testing."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
import pandas as pd
import streamlit as st
from response_validator import collect_facts, validate_explanation
from ui.styles import render_tag, render_disclaimer


def render_validation_lab(result: dict, sched: dict, on_navigate):
    """Render the comprehensive Validation Lab for viva defense and faculty evaluation."""
    st.markdown("## 🔬 Validation Lab & Self-Correction Architecture")
    st.caption("Demonstrating reliability mechanisms, bounded retry loops, and safety guardrails against LLM hallucination.")
    render_disclaimer()

    if not result.get("valid"):
        st.error("🚫 Cannot inspect validation: Field inputs are invalid.")
        if st.button("⬅️ Return to Field Assessment"):
            on_navigate("Field Assessment")
            st.rerun()
        return

    facts = collect_facts(result, sched)
    out = st.session_state.get("explanation")
    current_lang = st.session_state.get("language", "en")

    # 1. Architectural Pipeline Visualizer
    st.markdown("### 🔄 1. Reliability & Self-Correction Sequence")
    c1, arr1, c2, arr2, c3, arr3, c4, arr4, c5 = st.columns([1.2, 0.2, 1.2, 0.2, 1.2, 0.2, 1.2, 0.2, 1.2])

    with c1:
        st.markdown(
            """
            <div class="cw-pipe-node active">
                <div style="font-size: 1.1rem;">🧮</div>
                <div>Calculation</div>
                <div style="font-size: 0.72rem; color: #166534;">Deterministic</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with arr1:
        st.markdown('<div class="cw-pipe-arrow">➔</div>', unsafe_allow_html=True)

    with c2:
        st.markdown(
            """
            <div class="cw-pipe-node active">
                <div style="font-size: 1.1rem;">📅</div>
                <div>Scheduler</div>
                <div style="font-size: 0.72rem; color: #166534;">Rule-based</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with arr2:
        st.markdown('<div class="cw-pipe-arrow">➔</div>', unsafe_allow_html=True)

    with c3:
        st.markdown(
            """
            <div class="cw-pipe-node active">
                <div style="font-size: 1.1rem;">🤖</div>
                <div>GenAI Layer</div>
                <div style="font-size: 0.72rem; color: #92400E;">GPT-OSS-20B</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with arr3:
        st.markdown('<div class="cw-pipe-arrow">➔</div>', unsafe_allow_html=True)

    with c4:
        st.markdown(
            """
            <div class="cw-pipe-node active">
                <div style="font-size: 1.1rem;">🛡️</div>
                <div>Validator</div>
                <div style="font-size: 0.72rem; color: #1E3A8A;">Strict Checks</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with arr4:
        st.markdown('<div class="cw-pipe-arrow">➔</div>', unsafe_allow_html=True)

    with c5:
        st.markdown(
            """
            <div class="cw-pipe-node active">
                <div style="font-size: 1.1rem;">✅</div>
                <div>Verified Output</div>
                <div style="font-size: 0.72rem; color: #166534;">Safe or Fallback</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.caption("Flow: GenAI outputs are intercepted by the response validator. On validation failure, targeted feedback triggers a retry (bounded up to 2 corrections). If retries are exhausted or API fails, the deterministic fallback is served.")

    c_sc1, c_sc2 = st.columns([2.5, 1])
    with c_sc1:
        st.info("🔬 **Dedicated Experiment:** Looking for the formal **ReAct-Reflexion Self-Correction Experiment** with TC01–TC07 scenarios and iteration audit traces?")
    with c_sc2:
        if st.button("🚀 Go to Self-Correction Experiment", type="primary", use_container_width=True):
            on_navigate("Self-Correction Experiment")
            st.rerun()

    st.write("")

    # 2. Tabs: Real Assessment Audit vs Controlled Simulation vs Freeform Validator vs Live Pytest
    tab_audit, tab_sim, tab_freeform, tab_pytest = st.tabs([
        "📋 Current Assessment Audit",
        "🧪 Controlled Simulation (Viva Demo)",
        "✍️ Freeform Validator Playground",
        "🧪 Live Automated Tests (pytest)",
    ])

    # ---------------- Tab 1: Current Assessment Audit ----------------
    with tab_audit:
        st.markdown("### Real Assessment Validation Audit")
        if out and out.get("language") == current_lang:
            st.markdown(f"**Explanation Source:** `{out.get('source').upper()}` | **Attempts Used:** `{out.get('attempts')}` | **Self-Corrected:** `{out.get('corrected')}`")

            # Run validator live on active text to show exact checks
            v_result = validate_explanation(out["text"], facts, current_lang)

            col_a1, col_a2 = st.columns([1.2, 1])
            with col_a1:
                st.markdown("#### Validated Explanation Text")
                st.info(out["text"])

            with col_a2:
                st.markdown("#### Validation Checks Performed")
                check_definitions = [
                    ("Numerical Invariance", "Ensures numbers match engine calculation facts exactly"),
                    ("Unit Preservation", "Checks that mm, m³, hours, days, % are not swapped"),
                    ("Interval Hallucination Guard", "Prevents model inventing repeating schedules (e.g. 'every 7 days')"),
                    ("Status Contradiction Guard", "Blocks advising to irrigate when schedule is 'Defer & Reassess'"),
                    ("Forbidden Agronomic Claims", "Blocks fertilizer (urea/npk), pesticide, and yield guarantee claims"),
                    ("Required Content Verification", "Verifies net/gross mm, review date, and duration are included"),
                    ("Uncertainty & Prototype Warning", "Ensures uncertainty and educational prototype disclaimer are present"),
                    ("Language Script Integrity", "Ensures text is genuinely in English or Devanagari script"),
                ]
                df_checks = pd.DataFrame(check_definitions, columns=["Validation Guardrail", "Rule Description"])
                st.dataframe(df_checks, hide_index=True, use_container_width=True)

                if v_result["passed"]:
                    st.success("✅ **Result:** All validation guardrails passed successfully!")
                else:
                    st.error("❌ **Result:** Validation detected issues:")
                    for iss in v_result["issues"]:
                        st.markdown(f"- `[{iss['code']}]` {iss['message']}")
        else:
            st.info("💡 No explanation generated yet for current field parameters. Go to **AI Insights** to generate, or use the **Controlled Simulation** tab below.")

    # ---------------- Tab 2: Controlled Simulation Mode ----------------
    with tab_sim:
        st.markdown(
            """
            <div style="background: #EFF6FF; border: 1.5px solid #93C5FD; border-radius: 8px; padding: 0.85rem 1rem; margin-bottom: 1rem;">
                <strong style="color: #1E40AF;">🧪 CONTROLLED SIMULATION MODE (MOCK DEMONSTRATION FOR VIVA):</strong><br>
                <span style="font-size: 0.85rem; color: #1E3A8A;">
                    Simulate controlled LLM hallucination and failure modes to demonstrate the validator and bounded retry loop
                    to faculty evaluators. This simulation does <strong>not</strong> overwrite your real field assessment.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        n = facts["numeric"]
        net_val = n.get("net_irrigation_mm", {}).get("value", 35.0)
        gross_val = n.get("gross_irrigation_mm", {}).get("value", 45.0)
        rev_date = sched.get("review_date") or "2026-10-27"

        # Preset Mocks
        sim_presets = {
            "Case 1: Hallucinated Fertilizer Advice (Forbidden Content)": {
                "text": (
                    f"This is an educational prototype. The sugarcane crop requires {net_val:g} mm net irrigation. "
                    f"Review date is {rev_date}. Also apply 50 kg urea fertilizer per hectare to boost growth. "
                    "These numbers are estimates based on assumptions."
                ),
                "expected": "fertilizer",
                "desc": "Simulates LLM venturing out of scope into fertilizer/chemical advice.",
            },
            "Case 2: Invented Yield Guarantee (Unsupported Claim)": {
                "text": (
                    f"This is an educational prototype. The irrigation schedule recommends {net_val:g} mm on {rev_date}. "
                    "Following this schedule guarantees higher yield and saves 40% water this season. "
                    "Values are uncertain estimates."
                ),
                "expected": "unsupported_claim",
                "desc": "Simulates LLM making unwarranted agronomic yield or water-saving claims.",
            },
            "Case 3: Altered Numeric Value (Hallucinated Quantity)": {
                "text": (
                    f"This is an educational prototype. You must apply 999 mm of water to your field by {rev_date}. "
                    "The estimates contain assumptions and uncertainties."
                ),
                "expected": "unsupported_number",
                "desc": "Simulates LLM altering the calculated net irrigation quantity from the ground truth.",
            },
            "Case 4: Schedule Status Contradiction": {
                "text": (
                    f"This is an educational prototype. You should irrigate now immediately! "
                    f"Net requirement is {net_val:g} mm and review is {rev_date}. Some inputs are assumptions."
                ),
                "expected": "contradiction",
                "desc": "Simulates LLM commanding 'irrigate now' when the scheduler determined deferment or later planning.",
            },
            "Case 5: Fully Compliant Valid Advisory": {
                "text": (
                    f"This is an educational prototype. The scheduling engine recommends reviewing on {rev_date}. "
                    f"The estimated net irrigation requirement is {net_val:g} mm and gross requirement is {gross_val:g} mm. "
                    "These figures are provisional estimates with uncertainties and assumptions."
                ),
                "expected": "none (pass)",
                "desc": "Simulates a clean, fully compliant response matching all ground truth facts.",
            },
        }

        selected_case = st.selectbox("Select Simulation Scenario to Test:", list(sim_presets.keys()))
        case_info = sim_presets[selected_case]
        st.caption(f"**Scenario Objective:** {case_info['desc']} (Expected code: `{case_info['expected']}`)")

        col_s1, col_s2 = st.columns([1.2, 1])
        with col_s1:
            st.markdown("#### Simulated Mock Response:")
            st.code(case_info["text"], language="text")

            sim_check = validate_explanation(case_info["text"], facts, "en")

        with col_s2:
            st.markdown("#### Real-Time Validator Response:")
            if sim_check["passed"]:
                st.markdown(
                    """
                    <div style="background: #DCFCE7; border: 1.5px solid #86EFAC; border-radius: 8px; padding: 0.8rem; color: #166534; font-weight: 600;">
                        ✅ PASSED ALL VALIDATION CHECKS
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.write("Response is safe to display to user.")
            else:
                st.markdown(
                    """
                    <div style="background: #FEE2E2; border: 1.5px solid #FCA5A5; border-radius: 8px; padding: 0.8rem; color: #991B1B; font-weight: 600;">
                        ❌ VALIDATION FAILED — GUARDRAIL TRIGGERED
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                for iss in sim_check["issues"]:
                    st.markdown(f"- **Code:** `{iss['code']}` — {iss['message']}")

                st.markdown("#### Automated Correction Feedback to LLM:")
                st.info(f"Feedback sent to retry attempt:\n\n`{sim_check['feedback']}`")

    # ---------------- Tab 3: Freeform Playground ----------------
    with tab_freeform:
        st.markdown("### ✍️ Freeform Validator Playground")
        st.caption("Type or paste any arbitrary sentence to test how the response validator evaluates it against active facts.")
        user_test_text = st.text_area(
            "Test Text to Validate:",
            value=f"This is an educational prototype. Net water requirement is {net_val:g} mm. Review date is {rev_date}. Some inputs are assumptions.",
            height=120,
        )

        if st.button("🔍 Run Live Validator", type="primary"):
            live_res = validate_explanation(user_test_text, facts, current_lang)
            if live_res["passed"]:
                st.success("✅ **Passed!** The provided text complies with all facts, constraints, and disclaimers.")
            else:
                st.error("❌ **Failed validation!** Detected the following issues:")
                for iss in live_res["issues"]:
                    st.markdown(f"- **`{iss['code']}`**: {iss['message']}")
                st.markdown(f"**Feedback string:** `{live_res['feedback']}`")

    # ---------------- Tab 4: Live Automated Tests ----------------
    with tab_pytest:
        st.markdown("### 🧪 Live Automated Test Suite Execution")
        st.caption("Demonstrate code quality live to faculty by running the automated pytest test suite inside CaneWater AI.")

        if st.button("▶️ Run Automated Test Suite (pytest)", type="primary"):
            with st.spinner("Executing pytest on CaneWater AI test suite..."):
                proc = subprocess.run(
                    [sys.executable, "-m", "pytest", "-v"],
                    cwd=Path(__file__).parent.parent,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                st.session_state["pytest_output"] = (proc.stdout + proc.stderr)

        test_out = st.session_state.get("pytest_output")
        if test_out:
            st.code(test_out, language="text")
            m = {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed)", test_out)}
            p_count = m.get("passed", 0)
            f_count = m.get("failed", 0)
            st.success(f"🎯 **Measured in this test run:** Passed = `{p_count}`, Failed = `{f_count}`")

        # Session Metrics Table
        st.markdown("#### Evaluation Results & Session Metrics")
        stt = st.session_state.get("stats", {})
        avg_att = f"{sum(stt['attempts']) / len(stt['attempts']):.2f}" if stt.get("attempts") else "Not measured"

        parsed = {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed)", test_out or "")}
        total_tests = (parsed.get("passed", 0) + parsed.get("failed", 0)) if test_out else "Run pytest above"

        metrics_df = pd.DataFrame({
            "Evaluation Metric": [
                "Total Automated Test Cases",
                "Passed Test Cases",
                "Failed Test Cases",
                "Validation Failures Intercepted (Session)",
                "Successful Self-Corrections (Session)",
                "Average Attempts for AI Outputs (Session)",
                "API Failures Handled Gracefully (Session)",
                "Fallback Activations (Session)",
            ],
            "Measured Value": [
                total_tests,
                parsed.get("passed", "Run pytest above"),
                parsed.get("failed", "Run pytest above"),
                stt.get("validation_failures", 0),
                stt.get("corrections", 0),
                avg_att,
                stt.get("api_failures", 0),
                stt.get("fallbacks", 0),
            ],
        })
        st.table(metrics_df.astype(str))
        st.caption("Measured live in session. No fabricated accuracy or performance claims.")

    # Navigation Footer
    st.write("")
    c_n1, c_n2 = st.columns([1, 1])
    with c_n1:
        if st.button("⬅️ Back to AI Insights", use_container_width=True):
            on_navigate("AI Insights")
            st.rerun()
    with c_n2:
        if st.button("Explore Scenario Comparisons 📊", type="primary", use_container_width=True):
            on_navigate("Scenario Comparison")
            st.rerun()
