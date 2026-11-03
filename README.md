# CaneWater AI — Precision Sugarcane Irrigation & Generative AI Decision Support

**A Generative AI-Powered Sugarcane Water Requirement Estimation and Irrigation Scheduling System** — an educational prototype designed for academic evaluation, viva demonstration, and precision agriculture study (*not* a certified agronomic recommendation system).

---

## 🌟 Executive Summary

**CaneWater AI** bridges the gap between deterministic agronomic science and modern Generative AI. While black-box AI often hallucinates quantities or offers risky ungrounded agricultural advice, CaneWater AI enforces strict architectural separation:

1. **Deterministic Core:** All water requirements ($ET_c = K_c \times ET_o$), effective rainfall credits, root-zone moisture balances (TAW / RAW), and irrigation review dates are computed exclusively by a deterministic, transparent mathematical engine based on **FAO Irrigation & Drainage Paper 56**.
2. **GenAI Layer:** **GPT-OSS-20B** (via Groq Cloud Inference) is employed strictly as an **explainer and translator**, translating structured facts into accessible natural language advisories in **English**, **Hindi (हिन्दी)**, and **Marathi (मराठी)**.
3. **Response Validator & Self-Correction:** An automated regex and rules-based validator intercepts all AI-generated texts. It verifies numeric invariance, unit preservation, forbidden agronomic claims (fertilizers, pesticides, yield guarantees), and schedule consistency. Validation failures trigger a bounded self-correction loop (max 2 retries) with targeted error feedback.
4. **Deterministic Fallback:** If Groq is offline or without an API key, the system automatically activates an offline deterministic explanation engine, ensuring zero downtime and complete presentation reliability.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Inputs ["Input Layer"]
        A[User / Farmer Field Inputs]
        B[Input Validation Guardrails]
        A --> B
    end

    subgraph DeterministicCore ["Deterministic Calculation Core (No LLM)"]
        C[Water Requirement Engine<br/>FAO-56 ETc, Effective Rain, TAW/RAW]
        D[Irrigation Scheduling Engine<br/>Allowable Depletion & Review Dates]
        E[Ground Truth Structured Facts JSON<br/>Immutable Reference Data]
        B --> C --> D --> E
    end

    subgraph GenAILayer ["GenAI Explanation & Guardrail Layer"]
        F[Groq API: openai/gpt-oss-20b<br/>Multilingual Natural Language Explanation]
        G[Response Validator<br/>Numbers, Units, Contradictions, Forbidden Claims]
        H[Deterministic Fallback Engine<br/>Offline Multilingual Template Engine]
        E --> F
        F --> G
        G -- Passed Validation --> J[Verified Final Output]
        G -- Failed (Retries Left) -->|Targeted Feedback Prompt| F
        G -- Failed (Retries Exhausted) --> H
        F -- API Key Absent or Offline --> H
        H --> J
    end

    subgraph Presentation ["Streamlit Presentation UI"]
        J --> K[Modern Agricultural Dashboard & Export]
    end

    style C fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px;
    style D fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px;
    style E fill:#DCFCE7,stroke:#16A34A,stroke-width:2px;
    style F fill:#FEF3C7,stroke:#D97706,stroke-width:2px;
    style G fill:#E0F2FE,stroke:#0284C7,stroke-width:2px;
    style H fill:#FEE2E2,stroke:#DC2626,stroke-width:2px;
    style J fill:#F0FDF4,stroke:#15803D,stroke-width:2px;
```

---

## 🚀 Key Modules & Application Structure

| Module File | Component Role | LLM Used? | Key Responsibilities |
|---|---|---|---|
| `water_requirement_engine.py` | Calculation Engine | No | Implements FAO-56 single crop coefficient ($ET_c = K_c \times ET_o$), volumetric soil water balance (TAW, RAW, $D_r$), effective rainfall credit, and gross volume math. |
| `irrigation_scheduler.py` | Irrigation Scheduler | No | Deterministic state machine that evaluates allowable depletion, projects action review dates, assigns statuses, and calculates pump running time. |
| `response_validator.py` | Safety & Output Validator | No | Intercepts model responses; checks numbers, units, schedule contradictions, missing disclaimers, and forbidden content (fertilizer, pesticide, yield guarantees). |
| `genai_explainer.py` | GenAI Orchestration | Yes (Groq) | Formats ground truth prompts, calls `openai/gpt-oss-20b`, handles bounded retry loops with feedback, and provides deterministic fallback text (EN/HI/MR). |
| `app.py` | Main Application | No | Orchestrates Streamlit multi-page layout, session state persistence, top header, status pills, and navigation. |
| `ui/landing.py` | Landing Hero Section | No | Sugarcane visual hero, value propositions, interactive action buttons, and workflow diagrams. |
| `ui/overview.py` | Executive Dashboard | No | Real-time metric cards, Plotly soil moisture gauge, crop demand vs rainfall chart, and schedule timeline. |
| `ui/field_assessment.py` | Field Inputs Form | No | Categorized 4-section form (Crop, Soil, Weather, Irrigation) with live validation warnings and sample profile loaders. |
| `ui/water_analysis.py` | Water Analysis View | No | Scientific breakdown of ETc, net/gross irrigation, water deficit/surplus, LaTeX formulas, and missing-data audits. |
| `ui/irrigation_planner.py` | Scheduler Interface | No | Visual status badges, pump running duration, water sufficiency metrics, and decision-tree rule explanations. |
| `ui/ai_insights.py` | Multilingual GenAI Hub | Yes (Groq) | Side-by-side comparison of Application Facts vs AI Explanation in English, Hindi, and Marathi with retry tracking. |
| `ui/validation_lab.py` | Reliability & Viva Lab | No | Visual self-correction pipeline, real assessment audit, viva simulation mode with preset hallucination test cases, freeform validator playground, and live pytest runner. |
| `ui/scenarios.py` | Scenario Explorer | No | Interactive comparative analysis for rainfall variations, soil moisture levels, and water storage sufficiency with Plotly charts. |
| `ui/about_methodology.py` | Architecture & Viva Prep | No | Complete methodology documentation, Mermaid diagram, tech stack, and Faculty Viva Q&A Guide. |
| `ui/reporting.py` | Report Generator | No | Generates downloadable Markdown/Text assessment summaries and CSV schedule exports without leaking secrets. |

---

## 🛠️ Installation & Setup (Windows & VS Code)

### Prerequisites
- Python 3.10+ (Recommended Python 3.12)
- Git (optional)
- VS Code (recommended)

### 1. Open Project & Activate Virtual Environment
Open PowerShell or the VS Code Integrated Terminal (`Ctrl + ~`) in the `CaneWaterAI` root directory:

```powershell
# Navigate to the project directory
cd C:\Users\Shreya\CaneWaterAI

# If .venv does not exist, create it:
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure Environment Variables (Optional)
CaneWater AI runs **100% offline** using its built-in Deterministic Fallback Engine. If you wish to enable live cloud inference with `openai/gpt-oss-20b`:

```powershell
copy .env.example .env
```
Open `.env` in VS Code and set your Groq API key:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
```
*(Never commit `.env` to version control).*

### 4. Launch the Application
```powershell
streamlit run app.py
```
Streamlit will launch and open automatically in your browser at `http://localhost:8501`.

---

## 🧪 Automated Testing

Run the automated test suite with pytest:

```powershell
pytest -v
```

All **71 automated unit and integration tests** execute in under 2 seconds. All API tests use isolated mocks and never require active network calls or API keys.

---

## 🎯 Viva & Presentation Demonstration Guide

Follow this 6-step guided walkthrough to deliver a flawless presentation to faculty evaluators:

### Step 1: Landing Page & Problem Statement
- Start on the **Overview** page.
- Explain the problem: *Commercial LLMs cannot be trusted with mathematical irrigation calculations. CaneWater AI uses FAO-56 deterministic formulas for numbers and limits GenAI strictly to translation and explanation.*
- Point out the **API status pill** in the top header (`🟢 AI Online` or `🟡 Deterministic Fallback Mode`).

### Step 2: Load Sample Sugarcane Field
- Click the top toolbar button **"🌱 Load Sample Field"**.
- This prepopulates a realistic 5-month-old sugarcane field (Grand growth stage, 1.5 ha field, drip irrigation at 85% efficiency, 22% volumetric soil moisture, 4.5 mm/day reference ETo, and 10 mm expected rainfall).
- Show the 6 executive metric cards and interactive Plotly charts updating instantly.

### Step 3: Inspect Field Assessment & Water Analysis
- Navigate to **Field Assessment** to show how inputs are categorized (Crop, Soil, Weather, Irrigation) and explain that contradictory inputs (like age vs stage mismatch) trigger warnings rather than silent edits.
- Navigate to **Water Analysis** to showcase the transparent math:
  - $ET_c = K_c \times ET_o = 1.25 \times 4.5 = 5.62\text{ mm/day}$
  - Net irrigation depth, gross volume at pump, and water deficit/surplus.
  - Expand **"How was this calculated?"** to show LaTeX equations.

### Step 4: Examine Deterministic Irrigation Planner
- Navigate to **Irrigation Planner**.
- Show the decision badge (e.g. `Plan Irrigation for Later Date` or `Consider Irrigating Now`).
- Explain the projected review date, countdown in days, and pump run time calculated from gross volume and pump flow rate.
- Expand **"Why this schedule?"** to walk through the scheduler decision-tree rules.

### Step 5: Showcase Multilingual GenAI & Delineation
- Navigate to **AI Insights**.
- Highlight the visual and architectural separation:
  - **Left Card:** *Calculated by Application (Immutable Ground Truth Facts)*
  - **Right Card:** *Explained by Generative AI (LLM Layer)*
- Select **Hindi (हिन्दी)** or **Marathi (मराठी)** from the language selector and click **"Generate AI Explanation"**.
- Point out that the model explains the calculated facts in farmer-friendly language without altering numbers or dates.

### Step 6: Defend Reliability in the Validation Lab
- Navigate to **Validation Lab** (the centerpiece of the technical viva).
- Show the **Reliability Pipeline Flowchart**.
- Switch to the **"🧪 Controlled Simulation (Viva Demo)"** tab:
  - Select **"Case 1: Hallucinated Fertilizer Advice"** $\to$ Show how the validator catches the forbidden `fertilizer` keyword.
  - Select **"Case 2: Invented Yield Guarantee"** $\to$ Show how the validator blocks unsupported yield claims.
  - Select **"Case 3: Altered Numeric Value (999 mm)"** $\to$ Show how the validator detects unauthorized numbers.
  - Select **"Case 5: Fully Compliant Valid Advisory"** $\to$ Show clean passing verification.
- Switch to the **"🧪 Live Automated Tests"** tab and click **"Run Automated Test Suite (pytest)"** to show all **71 unit tests passing live** right in front of the faculty!
- Finally, click **"📄 Download Assessment (.md)"** in the sidebar to show the comprehensive, secret-free evaluation report.

---

## ⚖️ Responsible-Use Statement

**CaneWater AI is an educational decision-support prototype.** It is designed for demonstration, viva defense, and educational purposes. Values are estimates based on user-supplied inputs and stated FAO-56 scientific assumptions. Irrigation decisions must always be verified with on-site soil moisture monitoring, local agronomic extension guidelines, and certified agricultural professionals.
