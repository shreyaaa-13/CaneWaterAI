# CaneWater AI — System Architecture & Workflow

```mermaid
flowchart TD
    subgraph Inputs ["Input Layer"]
        A[User Field Inputs] --> B[Input Validation Guardrails]
    end

    subgraph DeterministicCore ["Deterministic Calculation Core (No LLM)"]
        B --> C[Water Requirement Engine<br/>FAO-56 ETc, Effective Rain, TAW/RAW]
        C --> D[Irrigation Scheduling Engine<br/>Allowable Depletion & Review Dates]
        D --> E[Structured Facts JSON<br/>Immutable Ground Truth]
    end

    subgraph GenAILayer ["GenAI Explanation & Guardrail Layer"]
        E --> F[Groq API: openai/gpt-oss-20b<br/>Multilingual Natural Language Explanation]
        F --> G[Response Validator<br/>Numbers, Units, Contradictions, Forbidden Claims]
        G -- Passed Validation --> J[Verified Final Advisory]
        G -- Failed (Retries Left) -->|Targeted Feedback| F
        G -- Failed (Retries Exhausted) --> H[Deterministic Fallback Engine]
        F -- API Key Absent or Offline --> H
        H --> J
    end

    subgraph Presentation ["Streamlit Presentation UI"]
        C --> K[Modern Multi-Page Dashboard]
        D --> K
        J --> K
        K --> L[Assessment Summary Reports<br/>Markdown & CSV Export]
    end

    style C fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px;
    style D fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px;
    style E fill:#DCFCE7,stroke:#16A34A,stroke-width:2px;
    style F fill:#FEF3C7,stroke:#D97706,stroke-width:2px;
    style G fill:#E0F2FE,stroke:#0284C7,stroke-width:2px;
    style H fill:#FEE2E2,stroke:#DC2626,stroke-width:2px;
    style J fill:#F0FDF4,stroke:#15803D,stroke-width:2px;
```

## Subsystem Responsibilities

| Module | Subsystem Role | Uses LLM? | Key Responsibilities |
|---|---|---|---|
| `water_requirement_engine.py` | Core Calculation Engine | No | Validates agronomic inputs; calculates ETc, effective rainfall credits, TAW/RAW, soil-water balances, and volumetric conversions. |
| `irrigation_scheduler.py` | Deterministic Scheduler | No | Evaluates root-zone depletion against RAW; projects review dates; assigns action status codes; determines pump run durations. |
| `response_validator.py` | Safety & Guardrail Validator | No | Extracts facts from engine/scheduler; inspects LLM responses for changed numbers, altered units, contradictory advice, and forbidden agronomic claims. |
| `genai_explainer.py` | GenAI Orchestration | Yes (Groq) | Formats ground truth prompts, calls `openai/gpt-oss-20b`, coordinates bounded retry loops, and generates deterministic fallback text in en/hi/mr. |
| `app.py` & `ui/*` | Streamlit Presentation Dashboard | No | Provides responsive, presentation-ready dashboard, guided demonstration stepper, interactive forms, and metric visualizations. |
| `ui/reporting.py` | Export Subsystem | No | Generates downloadable Markdown/Text assessment summaries and CSV schedule exports without leaking secrets. |

## Key Architectural Constraints
1. **Zero LLM Authority Over Numbers:** The LLM receives an immutable structured dictionary of facts and can never write back or alter numbers.
2. **Bounded Retry Loop:** The retry loop (1 initial generation + max 2 correction attempts) is a *generate-validate-retry* loop. It is not an unbounded ReAct agent, preventing runaway API usage and latency.
3. **Full Offline Fallback:** If the Groq API key is missing or network connectivity fails, the application remains 100% operational through its deterministic fallback template engine.
