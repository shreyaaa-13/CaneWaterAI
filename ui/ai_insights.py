"""GenAI explanation interface with Groq integration, multilingual generation, and strict origin delineation."""
from __future__ import annotations

import json
import streamlit as st
from genai_explainer import (
    LANGUAGES, check_api_status, explain, fallback_explanation, DEFAULT_MODEL
)
from response_validator import collect_facts
from ui.styles import render_tag, render_disclaimer


def render_ai_insights(result: dict, sched: dict, on_navigate):
    """Render the AI Insights showcase with side-by-side comparison, multilingual support, and validation logs."""
    st.markdown("## 🤖 Multilingual GenAI Explanation & Advisory")
    st.caption("Powered by Groq Cloud Inference (`openai/gpt-oss-20b`) with bounded self-correction and deterministic fallback.")
    render_disclaimer()

    if not result.get("valid"):
        st.error("🚫 Cannot generate AI explanation: Field inputs are invalid.")
        if st.button("⬅️ Return to Field Assessment"):
            on_navigate("Field Assessment")
            st.rerun()
        return

    # Check API status safely
    api_status = check_api_status()

    # Model & Connectivity Banner
    c_m1, c_m2, c_m3 = st.columns([2.5, 1.5, 1.2])
    with c_m1:
        if api_status["available"]:
            st.success(f"🟢 **Groq API Connected:** Model `{api_status['model']}` ready for live generation.")
        else:
            st.warning(f"🟡 **Deterministic Fallback Active:** {api_status['reason']}. Explanations use the deterministic rule engine.")
    with c_m2:
        lang = st.selectbox(
            "Explanation Language",
            list(LANGUAGES.keys()),
            key="language",
            format_func=lambda k: LANGUAGES[k],
            help="Select preferred language for explanation. Hindi and Marathi use native Devanagari script."
        )
    with c_m3:
        st.write("")
        st.caption("Hindi & Marathi translations are prototype outputs.")

    st.write("")

    # Generation Trigger Buttons
    col_btn1, col_btn2, col_sp = st.columns([1.6, 1.6, 3])
    with col_btn1:
        gen_clicked = st.button("✨ Generate AI Explanation", type="primary", use_container_width=True)
    with col_btn2:
        regen_clicked = st.button("🔄 Regenerate Explanation", use_container_width=True)

    # Process generation on click
    if gen_clicked or regen_clicked:
        with st.spinner(f"Contacting {DEFAULT_MODEL} via Groq and validating explanation in {LANGUAGES[lang]}..."):
            out = explain(result, sched, lang)

        # Update persistent stats
        stt = st.session_state["stats"]
        stt["runs"] += 1
        stt["validation_failures"] += out.get("validation_failures", 0)
        stt["corrections"] += int(out.get("corrected", False))
        stt["api_failures"] += int(out.get("fallback_reason") in ("api_failure", "api_unavailable"))
        stt["fallbacks"] += int(out.get("source") == "fallback")
        if out.get("source") == "ai":
            stt["attempts"].append(out.get("attempts", 1))

        out["fingerprint"] = (repr(result.get("inputs_used")), sched.get("status_code"))
        st.session_state["explanation"] = out
        st.rerun()

    # Retrieve current explanation from session state
    out = st.session_state.get("explanation")
    current_fp = (repr(result.get("inputs_used")), sched.get("status_code"))
    has_valid_explanation = (
        out is not None
        and out.get("language") == lang
        and out.get("fingerprint") == current_fp
    )

    st.write("")

    # Side-by-Side Comparison: Application Facts vs AI Explanation
    st.markdown("### ⚖️ Side-by-Side Verification: Engine Facts vs. AI Explanation")
    c_left, c_right = st.columns([1, 1.25])

    # Left Column: Calculated by Application
    with c_left:
        st.markdown(
            """
            <div style="background: #F0FDF4; border: 1.5px solid #86EFAC; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.8rem;">
                <span class="cw-tag cw-tag-calc">Calculated by the Application (Deterministic)</span>
                <div style="font-weight: 700; color: #166534; font-size: 1.1rem; margin-top: 0.3rem;">
                    Objective Ground Truth
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        facts = collect_facts(result, sched)
        est = result.get("estimates", {})

        ground_truth_items = [
            ("Crop Stage & Age", f"{facts['numeric'].get('crop_age_months', {}).get('value', 'n/a')} mo ({result['inputs_used'].get('growth_stage')})"),
            ("ETc (Crop Consumption)", f"{facts['numeric'].get('etc_mm_day', {}).get('value', 'n/a')} mm/day"),
            ("Effective Rainfall", f"{facts['numeric'].get('effective_rain_mm', {}).get('value', 0)} mm"),
            ("Net Irrigation Depth", f"{facts['numeric'].get('net_irrigation_mm', {}).get('value', 'n/a')} mm"),
            ("Gross Irrigation Depth", f"{facts['numeric'].get('gross_irrigation_mm', {}).get('value', 'n/a')} mm"),
            ("Gross Volume Needed", f"{facts['numeric'].get('gross_volume_m3', {}).get('value', 'n/a')} m³"),
            ("Scheduler Status", f"{sched.get('status_label')} ({sched.get('status_code')})"),
            ("Next Review Date", f"{sched.get('review_date') or 'Not calculable'}"),
            ("Pump Operating Time", f"{facts['numeric'].get('irrigation_duration_h', {}).get('value', 'n/a')} hours"),
        ]
        import pandas as pd
        df_gt = pd.DataFrame(ground_truth_items, columns=["Verified Parameter", "Value"])
        st.dataframe(df_gt, hide_index=True, use_container_width=True)

        st.caption("🔒 *All numbers above are strictly immutable. The AI model receives these facts and is forbidden from altering them.*")

    # Right Column: Explained by Generative AI
    with c_right:
        st.markdown(
            """
            <div style="background: #FFFBEB; border: 1.5px solid #FDE68A; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.8rem;">
                <span class="cw-tag cw-tag-ai">Explained by Generative AI (LLM Layer)</span>
                <div style="font-weight: 700; color: #92400E; font-size: 1.1rem; margin-top: 0.3rem;">
                    Farmer-Facing Natural Language Advisory
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if has_valid_explanation:
            if out.get("source") == "ai":
                att = out.get("attempts", 1)
                corrected_badge = " (Self-Corrected on Attempt 2)" if out.get("corrected") else ""
                st.markdown(
                    f"""
                    <div class="cw-pill cw-pill-green" style="margin-bottom: 0.75rem;">
                        <span>✓ Passed Automated Output Validation</span> &nbsp;|&nbsp;
                        <span>Attempts used: {att}/3{corrected_badge}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                reason = out.get("fallback_reason", "deterministic")
                st.markdown(
                    f"""
                    <div class="cw-pill cw-pill-amber" style="margin-bottom: 0.75rem;">
                        <span>Deterministic Fallback Explanation Active (Reason: {reason})</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Display explanation text in a styled card
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 1.2rem; line-height: 1.65; font-size: 0.95rem; color: #1E293B;">
                    {out['text'].replace(chr(10) + chr(10), '<br><br>')}
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Validation Audit Summary
            with st.expander("🔍 Validation Audit Log & Inspection Details", expanded=False):
                col_l1, col_l2 = st.columns(2)
                with col_l1:
                    st.json({
                        "source": out.get("source"),
                        "attempts_used": out.get("attempts"),
                        "validation_failures": out.get("validation_failures"),
                        "self_corrected": out.get("corrected"),
                        "api_error_category": out.get("api_error_category"),
                        "fallback_reason": out.get("fallback_reason"),
                    })
                with col_l2:
                    st.write("**Validation History per Attempt:**")
                    st.json(out.get("validation_history", []))

        else:
            st.info(
                f"👈 Click **Generate AI Explanation** to produce a validated natural language advisory in **{LANGUAGES[lang]}**.\n\n"
                "If no Groq API key is present in your environment, the system gracefully activates the deterministic fallback."
            )
            with st.expander(f"👁️ Preview Deterministic Fallback in {LANGUAGES[lang]}", expanded=True):
                preview_text = fallback_explanation(result, sched, lang)
                st.write(preview_text)

    st.write("")

    # Navigation Footer
    c_n1, c_n2 = st.columns([1, 1])
    with c_n1:
        if st.button("⬅️ Back to Irrigation Planner", use_container_width=True):
            on_navigate("Irrigation Planner")
            st.rerun()
    with c_n2:
        if st.button("Proceed to Validation Lab 🔬", type="primary", use_container_width=True):
            on_navigate("Validation Lab")
            st.rerun()
