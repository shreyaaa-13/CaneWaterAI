"""Architecture, scientific methodology, technology stack, and viva defense guide."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from ui.styles import render_tag, render_disclaimer


def render_about_methodology(on_navigate):
    """Render comprehensive architecture, methodology formulas, and viva defense Q&A."""
    st.markdown("## 📖 System Architecture, Methodology & Viva Guide")
    st.caption("Detailed architectural blueprints, scientific formulas, system limitations, and faculty evaluation notes.")
    render_disclaimer()

    tab_arch, tab_math, tab_stack, tab_viva = st.tabs([
        "🏗️ System Architecture & Data Flow",
        "📐 FAO-56 Methodology & Equations",
        "💻 Technology Stack & Responsibilities",
        "🎓 Viva & Presentation Q&A Guide",
    ])

    # ---------------- Tab 1: Architecture ----------------
    with tab_arch:
        st.markdown("### Architectural Pipeline & Fault-Tolerant Workflow")
        st.markdown(
            """
            ```mermaid
            flowchart TD
                subgraph Inputs ["Input Layer"]
                    A[Farmer / User Field Inputs]
                    B[Deterministic Input Validator]
                    A --> B
                end

                subgraph Engines ["Deterministic Core (No LLM)"]
                    C[Water Requirement Engine<br/>FAO-56 ETc, Rainfall, Soil Water]
                    D[Irrigation Scheduling Engine<br/>RAW Depletion & Action Rules]
                    E[Structured Facts JSON<br/>Immutable Ground Truth]
                    B --> C --> D --> E
                end

                subgraph AI ["GenAI & Safety Layer"]
                    F[Groq API: openai/gpt-oss-20b<br/>Multilingual Natural Language]
                    G[Response Validator<br/>Numbers, Units, Contradictions, Forbidden Claims]
                    H[Deterministic Fallback Engine<br/>Offline Rule-Based Text]
                    E --> F
                    F --> G
                    G -- Passed Validation --> J[Verified Final Output]
                    G -- Failed Validation (Retries Left) -->|Targeted Feedback| F
                    G -- Failed Validation (Retries Exhausted) --> H
                    F -- API Unavailable / Network Failure --> H
                    H --> J
                end

                subgraph UI ["User Interface"]
                    J --> K[Streamlit Modern Dashboard]
                end

                style C fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px;
                style D fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px;
                style E fill:#DCFCE7,stroke:#16A34A,stroke-width:2px;
                style F fill:#FEF3C7,stroke:#D97706,stroke-width:2px;
                style G fill:#E0F2FE,stroke:#0284C7,stroke-width:2px;
                style H fill:#FEE2E2,stroke:#DC2626,stroke-width:2px;
                style J fill:#F0FDF4,stroke:#15803D,stroke-width:2px;
            ```
            """
        )

        st.markdown(
            """
            #### Key Architectural Design Principles:
            1. **Strict Separation of Concerns:**
               Calculations and scheduling decisions are **100% deterministic**. The LLM is strictly an explainer and translator. It never receives the authority to alter numbers or scheduling dates.
            2. **Ground Truth Facts JSON:**
               Both the LLM prompt and the validator consume the exact same structured dictionary (`facts_json`).
            3. **Bounded Generate-Validate-Retry Loop:**
               Retries are strictly bounded (`max_retries = 2`, total 3 attempts). This prevents runaway infinite loops and unbounded API costs.
            4. **Graceful Deterministic Fallback:**
               If Groq is unreachable, rate-limited, or if the model fails validation on all 3 attempts, the application seamlessly activates an offline deterministic template explanation in English, Hindi, or Marathi.
            """
        )

    # ---------------- Tab 2: Scientific Methodology ----------------
    with tab_math:
        st.markdown("### Agronomic Formulas & Mathematical Specifications")
        st.markdown(
            r"""
            All calculations follow **FAO Irrigation & Drainage Paper 56**:
            
            | Quantity | Formula | Units | Scientific Role |
            |---|---|---|---|
            | **Crop ET ($ET_c$)** | $ET_c = K_c \times ET_o$ | $mm/day$ | Sugarcane daily consumptive water use |
            | **Crop Demand** | $ET_c \times \text{Days}$ | $mm$ | Cumulative water need over planning period |
            | **Effective Rain** | $f_{\text{rain}} \times \text{Rainfall}$ | $mm$ | Readily infiltrating rainwater ($f=0.80$) |
            | **TAW** | $1000 \times \left(\frac{FC - PWP}{100}\right) \times Z_r$ | $mm$ | Total Available Water stored in root zone |
            | **RAW** | $p \times \text{TAW}$ | $mm$ | Readily Available Water before moisture stress |
            | **Root Depletion ($D_r$)** | $1000 \times \left(\frac{FC - \theta}{100}\right) \times Z_r$ | $mm$ | Current depleted soil moisture depth |
            | **Net Irrigation ($I_{\text{net}}$)** | $\min(\max(D_r + \text{Demand} - P_{\text{eff}}, 0), \text{TAW})$ | $mm$ | Refill depth required to restore root zone |
            | **Gross Irrigation ($I_{\text{gross}}$)** | $I_{\text{net}} / (\text{Efficiency} / 100)$ | $mm$ | Adjusted depth considering irrigation losses |
            | **Water Volume ($V$)** | $\text{Depth (mm)} \times \text{Area (ha)} \times 10$ | $m^3$ | $1\text{ mm}$ over $1\text{ ha} = 10\text{ m}^3 = 10,000\text{ litres}$ |
            | **Pump Run Time** | $V_{\text{gross}} / Q_{\text{pump}}$ | $hours$ | Required operating run time of pump |
            """
        )

        st.markdown("#### Documented Agronomic Limitations:")
        st.markdown(
            """
            - **Single Crop Coefficient:** Uses single $K_c$ rather than dual $K_{cb} + K_e$ (soil evaporation and crop transpiration are not separately decoupled).
            - **Manual Inputs:** Weather and soil parameters are manually entered; no IoT sensors or live weather APIs are claimed.
            - **Planning Window:** The 7-day or user-selected window is an operational review interval, not a fixed irrigation frequency.
            """
        )

    # ---------------- Tab 3: Tech Stack & Module Responsibilities ----------------
    with tab_stack:
        st.markdown("### Software Architecture & Module Responsibilities")
        modules_info = [
            ("water_requirement_engine.py", "Core Calculation Engine", "No (Pure Python)", "Validates agronomic inputs, calculates ETc, effective rainfall credits, TAW/RAW, soil-water balances, and volumetric conversions."),
            ("irrigation_scheduler.py", "Deterministic Scheduler", "No (Pure Python)", "Evaluates root-zone depletion against RAW; projects review dates; assigns action status codes; determines pump run durations."),
            ("response_validator.py", "Safety & Guardrail Validator", "No (Regex / Python)", "Extracts facts from engine/scheduler, inspects LLM responses for changed numbers, altered units, contradictory advice, and forbidden agronomic claims."),
            ("genai_explainer.py", "GenAI Orchestration", "Yes (Groq / gpt-oss-20b)", "Constructs ground truth prompt, invokes Groq inference, coordinates bounded retry loops, and generates deterministic fallback text in en/hi/mr."),
            ("app.py & ui/*", "Streamlit Presentation Dashboard", "No (Streamlit / Plotly)", "Provides responsive, presentation-ready dashboard, guided demonstration stepper, interactive forms, and metric visualizations."),
        ]
        df_mod = pd.DataFrame(modules_info, columns=["Module File", "Subsystem Role", "Uses LLM?", "Key Responsibilities"])
        st.dataframe(df_mod, hide_index=True, use_container_width=True)

        st.markdown("#### Core Dependencies:")
        st.markdown("- **Streamlit:** Frontend application framework.\n- **Groq SDK:** Cloud inference for `openai/gpt-oss-20b`.\n- **Plotly & Pandas:** Interactive data visualization and structured tabular analysis.\n- **Pytest:** Automated testing framework.")

    # ---------------- Tab 4: Viva Defense Guide ----------------
    with tab_viva:
        st.markdown("### 🎓 Faculty Viva & Evaluation Q&A Cheat Sheet")
        st.caption("Common questions evaluators and faculty ask during project demonstrations:")

        with st.expander("❓ Q1: Why didn't you let the LLM calculate the water requirement directly?", expanded=True):
            st.markdown(
                """
                **Answer:**
                Large Language Models are probabilistic next-token predictors. When tasked with arithmetic, they suffer from numerical drift, hallucinations, and round-off errors.
                In precision agriculture, calculating irrigation depths with an LLM is dangerous and irresponsible.
                Instead, we employ an **objective, deterministic mathematical engine** based on FAO-56 standards for all calculations, and utilize Generative AI **exclusively for natural language explanation and translation**.
                """
            )

        with st.expander("❓ Q2: What happens if the Groq API key is invalid or offline?", expanded=True):
            st.markdown(
                """
                **Answer:**
                The application features a complete **Deterministic Fallback Engine**. All water requirement calculations and irrigation schedules run 100% locally offline.
                If the Groq API fails or no key is present, the app catches the condition without leaking API errors and renders a deterministic rule-based explanation in English, Hindi, or Marathi.
                """
            )

        with st.expander("❓ Q3: How does your self-correction mechanism work?", expanded=False):
            st.markdown(
                """
                **Answer:**
                We implemented a **bounded generate-validate-retry loop**:
                1. The LLM generates an explanation from structured JSON facts.
                2. The `response_validator` inspects the text for unauthorized numbers, altered units, status contradictions, and forbidden claims (e.g., urea, pesticides, yield guarantees).
                3. If validation fails, the validator produces targeted correction feedback which is fed back into the model prompt for attempt 2.
                4. Retries are strictly bounded to `max_retries = 2` (maximum 3 total attempts) to prevent infinite loops. If validation still fails, the deterministic fallback activates.
                """
            )

        with st.expander("❓ Q4: Why is irrigation efficiency not inferred from the irrigation method?", expanded=False):
            st.markdown(
                """
                **Answer:**
                Inferring efficiency solely from method (e.g. assuming all drip systems operate at 90%) is inaccurate because field condition, pipe clogging, pressure regulation, and farmer maintenance cause huge variations (drip can range from 60% to 95%).
                Our engine treats irrigation method as **contextual metadata** only and requires explicit user-specified efficiency before computing gross water volumes.
                """
            )

    # Navigation Footer
    st.write("")
    if st.button("⬅️ Return to Overview Dashboard", use_container_width=True):
        on_navigate("Overview")
        st.rerun()
