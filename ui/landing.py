"""Landing section with sugarcane hero banner, feature highlights, and actionable workflow buttons."""
from __future__ import annotations

import streamlit as st
from ui.styles import render_disclaimer


def render_landing_hero(on_navigate):
    """Render the hero section and landing page features."""
    # Sugarcane Hero Box
    st.markdown(
        """
        <div class="cw-hero">
            <span class="cw-hero-badge">🌾 Precision Agriculture Decision Support Prototype</span>
            <h2>Smarter Irrigation. Better-Informed Decisions.</h2>
            <p class="subtitle">
                An AI-powered sugarcane irrigation decision-support prototype that combines field information,
                transparent water calculations, scheduling logic, and multilingual AI explanations.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Hero Action Buttons
    c_btn1, c_btn2, c_sp = st.columns([1.8, 1.8, 3.4])
    with c_btn1:
        if st.button("🚀 Start Field Assessment", type="primary", use_container_width=True, key="hero_btn_assess"):
            on_navigate("Field Assessment")
            st.rerun()
    with c_btn2:
        if st.button("📖 Explore How It Works", use_container_width=True, key="hero_btn_explore"):
            on_navigate("About and Methodology")
            st.rerun()

    st.write("")

    # Feature Highlights (3 Compact Cards)
    st.markdown("### Core Capabilities")
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown(
            """
            <div class="cw-card" style="height: 100%;">
                <div style="font-size: 1.8rem; margin-bottom: 0.5rem;">💧</div>
                <div style="font-weight: 700; color: #1B4332; font-size: 1.05rem; margin-bottom: 0.4rem;">
                    1. Water Requirement Analysis
                </div>
                <div style="font-size: 0.85rem; color: #4B5563; line-height: 1.5;">
                    Estimates crop water consumption ($ET_c = K_c \\times ET_o$) using FAO-56 standards,
                    accounting for effective rainfall credits and root-zone water depletion.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with f2:
        st.markdown(
            """
            <div class="cw-card" style="height: 100%;">
                <div style="font-size: 1.8rem; margin-bottom: 0.5rem;">📅</div>
                <div style="font-weight: 700; color: #1B4332; font-size: 1.05rem; margin-bottom: 0.4rem;">
                    2. Irrigation Scheduling
                </div>
                <div style="font-size: 0.85rem; color: #4B5563; line-height: 1.5;">
                    Deterministic scheduling logic projects review dates and pump running duration.
                    Refuses to guess when data are missing, ensuring high operational integrity.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with f3:
        st.markdown(
            """
            <div class="cw-card" style="height: 100%;">
                <div style="font-size: 1.8rem; margin-bottom: 0.5rem;">🤖</div>
                <div style="font-weight: 700; color: #1B4332; font-size: 1.05rem; margin-bottom: 0.4rem;">
                    3. Multilingual GenAI Explanations
                </div>
                <div style="font-size: 0.85rem; color: #4B5563; line-height: 1.5;">
                    GPT-OSS-20B via Groq translates complex calculations into farmer-friendly explanations
                    in English, Hindi, and Marathi, validated against deterministic facts.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # Visual Workflow Pipeline
    st.markdown("### Transparent Processing Pipeline")
    st.markdown(
        """
        <div class="cw-pipeline">
            <div class="cw-pipe-node active">
                <div style="font-size: 1.1rem;">📝</div>
                <div>Field Details</div>
                <div style="font-size: 0.72rem; color: #64748B;">Crop, soil, weather & pump</div>
            </div>
            <div class="cw-pipe-arrow">➔</div>
            <div class="cw-pipe-node active">
                <div style="font-size: 1.1rem;">🧮</div>
                <div>Water Analysis</div>
                <div style="font-size: 0.72rem; color: #64748B;">FAO-56 ETc & Net/Gross mm</div>
            </div>
            <div class="cw-pipe-arrow">➔</div>
            <div class="cw-pipe-node active">
                <div style="font-size: 1.1rem;">📆</div>
                <div>Irrigation Schedule</div>
                <div style="font-size: 0.72rem; color: #64748B;">Depletion & pump duration</div>
            </div>
            <div class="cw-pipe-arrow">➔</div>
            <div class="cw-pipe-node active">
                <div style="font-size: 1.1rem;">🌐</div>
                <div>AI Explanation</div>
                <div style="font-size: 0.72rem; color: #64748B;">Multilingual & validated</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Educational Disclaimer
    render_disclaimer()
