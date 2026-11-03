"""ReAct-Reflexion Self-Correction Framework for Reliable GenAI Sugarcane Irrigation Advisory.

Architecture:
  Reason  : Ground-truth facts from the deterministic calculation engine are compiled.
  Act     : Initial or revised explanation generated via Groq API or controlled mock.
  Observe : Deterministic Response Validator inspects explanation across all safety rules.
  Reflect : Structured feedback generated with violated rule, expected fact, observed mismatch,
            and invariance instructions.
  Iterate : Bounded correction loop (default max 3 attempts) with safe fallback on exhaustion or error.

Academic Integrity:
  - Calculation engine is the sole source of truth. The LLM never alters numerical calculations.
  - Mock demonstrations are strictly demarcated from live LLM inference.
"""
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from genai_explainer import (
    DEFAULT_MODEL,
    LANGUAGES,
    SYSTEM_PROMPT,
    ExplainerUnavailable,
    _call,
    _messages,
    check_api_status,
    classify_error,
    fallback_explanation,
    get_client,
)
from response_validator import (
    RULES_METADATA,
    collect_facts,
    facts_json,
    format_structured_feedback,
    validate_explanation,
)

logger = logging.getLogger("canewater.self_correction")

# Status Labels required by specification
STATUS_INITIAL_VALID = "Initial Response Valid"
STATUS_VALIDATION_FAILED = "Validation Failed"
STATUS_CORRECTION_ATTEMPTED = "Correction Attempted"
STATUS_CORRECTION_SUCCESSFUL = "Correction Successful"
STATUS_MAX_ATTEMPTS_REACHED = "Maximum Attempts Reached"
STATUS_FALLBACK_USED = "Fallback Used"
STATUS_API_UNAVAILABLE = "API Unavailable"


@dataclass
class CorrectionAttempt:
    """Represents a single iteration in the ReAct-Reflexion loop."""
    attempt_number: int
    prompt_user_content: str
    candidate_text: str
    validation_passed: bool
    issues: List[Dict[str, Any]]
    feedback_text: str
    structured_feedback: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    latency_ms: float = 0.0


@dataclass
class SelfCorrectionConfig:
    """Configuration for the bounded self-correction loop."""
    max_correction_attempts: int = 3  # Maximum correction attempts after the initial generation (total calls <= 4)
    model: str = DEFAULT_MODEL
    language: str = "en"
    strict_mode: bool = True
    record_metrics: bool = True


@dataclass
class SelfCorrectionResult:
    """Complete audit record of the self-correction experiment."""
    final_text: str
    source: str                          # 'ai' or 'fallback'
    overall_status: str                  # One of the standardized status labels
    total_attempts: int
    initial_passed: bool
    corrected: bool
    attempts_history: List[CorrectionAttempt]
    facts: Dict[str, Any]
    language: str
    execution_mode: str                  # 'live_llm' or 'mock_demonstration'
    scenario_id: Optional[str] = None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    api_error_category: Optional[str] = None
    total_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Deterministic Generator for Compliant Advisory (Used in Baseline & Mocks)
# ---------------------------------------------------------------------------
def build_valid_explanation(facts: Dict[str, Any], language: str = "en") -> str:
    """Generate a fully compliant advisory guaranteed to pass all validation checks."""
    n = facts.get("numeric", {})
    net_val = n.get("net_irrigation_mm", {}).get("value", 35.0)
    gross_val = n.get("gross_irrigation_mm", {}).get("value", 50.0)
    dur_val = n.get("irrigation_duration_h", {}).get("value", 5.0)
    rev_date = facts.get("review_date") or "2026-10-27"
    code = facts.get("status_code", "SCHEDULE_LATER")

    if language == "hi":
        status_text = (
            "शेड्यूलिंग इंजन के अनुसार अभी सिंचाई पर विचार करें।"
            if code == "IRRIGATE_NOW"
            else f"शेड्यूलिंग इंजन के अनुसार बाद की तारीख ({rev_date}) के लिए सिंचाई की योजना बनाएं।"
        )
        return (
            f"यह एक शैक्षिक प्रोटोटाइप है। {status_text}\n\n"
            f"योजना अवधि के लिए अनुमानित शुद्ध सिंचाई आवश्यकता {net_val:g} mm है और सकल आवश्यकता {gross_val:g} mm है।\n\n"
            f"अनुमानित पंप चलाने का समय {dur_val:g} hours है। अगली समीक्षा तारीख {rev_date} है।\n\n"
            f"यह अनुमान मान्यताओं और अपर्याप्त जानकारी की अनिश्चितता पर आधारित है। निर्णय से पहले खेत में जांच करें।"
        )
    elif language == "mr":
        status_text = (
            "शेड्युलिंग इंजिननुसार आता सिंचनाचा विचार करा."
            if code == "IRRIGATE_NOW"
            else f"शेड्युलिंग इंजिननुसार पुढील तारीख ({rev_date}) पर्यंत सिंचन पुढे ढकला."
        )
        return (
            f"हा शैक्षणिक प्रोटोटाइप आहे. {status_text}\n\n"
            f"नियोजन कालावधीसाठी अंदाजे निव्वळ सिंचन गरज {net_val:g} mm आहे आणि एकूण गरज {gross_val:g} mm आहे।\n\n"
            f"अंदाजे पंप चालवण्याचा वेळ {dur_val:g} hours आहे. पुढील आढावा तारीख {rev_date} आहे.\n\n"
            f"ही मूल्ये गृहितकांवर आणि अपुरी माहितीच्या अनिश्चिततेवर आधारित आहेत. स्थानिक सल्लागाराकडून खात्री करा."
        )
    else:
        status_text = (
            "The scheduling engine recommends considering irrigation now."
            if code == "IRRIGATE_NOW"
            else f"The scheduling engine advises planning irrigation for a later date, around {rev_date}."
        )
        return (
            f"This is an educational prototype. {status_text}\n\n"
            f"The estimated net irrigation requirement for the planning period is {net_val:g} mm, and the gross requirement is {gross_val:g} mm.\n\n"
            f"Estimated pump running duration is {dur_val:g} hours. The next scheduled review date is {rev_date}.\n\n"
            f"These calculations represent provisional estimates with stated assumptions and data uncertainties. Verify with field checks."
        )


# ---------------------------------------------------------------------------
# Controlled Repeatable Demonstration Scenarios (TC01 - TC07)
# ---------------------------------------------------------------------------
DEMO_SCENARIOS = {
    "TC01": {
        "title": "TC01 — Valid Initial Response",
        "description": "The initial explanation faithfully preserves the calculator's decision and required values. Passes immediately without correction.",
        "expected_status": STATUS_INITIAL_VALID,
        "expected_attempts": 1,
        "expected_rule": "None (All Pass)",
    },
    "TC02": {
        "title": "TC02 — Incorrect Numerical Value",
        "description": "Initial explanation hallucinates an altered net irrigation value (999 mm). Validator intercepts the mismatch.",
        "expected_status": STATUS_MAX_ATTEMPTS_REACHED,
        "expected_attempts": 4,  # 1 initial + 3 retries
        "expected_rule": "unsupported_number (Numerical Invariance)",
    },
    "TC03": {
        "title": "TC03 — Incorrect Irrigation Decision",
        "description": "Explanation commands immediate watering despite engine status being SCHEDULE_LATER. Contradiction is detected.",
        "expected_status": STATUS_MAX_ATTEMPTS_REACHED,
        "expected_attempts": 4,
        "expected_rule": "contradiction (Decision Consistency)",
    },
    "TC04": {
        "title": "TC04 — Unsupported Claim",
        "description": "Explanation introduces unpermitted chemical fertilizer recommendations (urea) and yield guarantees.",
        "expected_status": STATUS_MAX_ATTEMPTS_REACHED,
        "expected_attempts": 4,
        "expected_rule": "fertilizer / unsupported_claim (Agronomic Scope)",
    },
    "TC05": {
        "title": "TC05 — Successful Self-Correction",
        "description": "Initial response fails with an altered number (999 mm). Structured feedback triggers Attempt 2, which rectifies the number and passes.",
        "expected_status": STATUS_CORRECTION_SUCCESSFUL,
        "expected_attempts": 2,
        "expected_rule": "Correction Verified on Attempt 2",
    },
    "TC06": {
        "title": "TC06 — Maximum Retry Limit",
        "description": "Model persistently produces non-compliant responses across all attempts. The loop bounds strictly at 3 correction attempts and activates fallback.",
        "expected_status": STATUS_MAX_ATTEMPTS_REACHED,
        "expected_attempts": 4,
        "expected_rule": "Maximum Retries Exhausted",
    },
    "TC07": {
        "title": "TC07 — API Failure Handling",
        "description": "Simulates API unavailability or timeout. Application intercepts the error safely without crashing and serves the safe fallback.",
        "expected_status": STATUS_API_UNAVAILABLE,
        "expected_attempts": 0,
        "expected_rule": "API Error Handled Safely",
    },
}


def get_mock_candidates_for_scenario(scenario_id: str, facts: Dict[str, Any], language: str = "en") -> List[str]:
    """Generate controlled deterministic mock candidate responses for each repeatable test case."""
    clean = build_valid_explanation(facts, language)
    n = facts.get("numeric", {})
    net_val = n.get("net_irrigation_mm", {}).get("value", 35.0)
    rev_date = facts.get("review_date") or "2026-10-27"
    code = facts.get("status_code", "SCHEDULE_LATER")

    if scenario_id == "TC01":
        # Returns compliant response on first attempt
        return [clean]

    elif scenario_id == "TC02":
        # Always hallucinates numbers (e.g. 999 mm, 888 mm, 777 mm, 666 mm)
        return [
            clean.replace(f"{net_val:g} mm", "999 mm"),
            clean.replace(f"{net_val:g} mm", "888 mm"),
            clean.replace(f"{net_val:g} mm", "777 mm"),
            clean.replace(f"{net_val:g} mm", "666 mm"),
        ]

    elif scenario_id == "TC03":
        # Always contradicts the irrigation action
        bad_action = (
            f"This is an educational prototype. You should irrigate now immediately! "
            f"Net need is {net_val:g} mm, gross is {n.get('gross_irrigation_mm', {}).get('value', 50):g} mm, "
            f"duration is {n.get('irrigation_duration_h', {}).get('value', 5):g} hours. "
            f"Review date is {rev_date}. Some inputs are assumptions."
        ) if code != "IRRIGATE_NOW" else (
            f"This is an educational prototype. Do not irrigate today, skip irrigation. "
            f"Net need is {net_val:g} mm, gross is {n.get('gross_irrigation_mm', {}).get('value', 50):g} mm, "
            f"duration is {n.get('irrigation_duration_h', {}).get('value', 5):g} hours. "
            f"Review date is {rev_date}. Some inputs are assumptions."
        )
        return [bad_action, bad_action, bad_action, bad_action]

    elif scenario_id == "TC04":
        # Introduces fertilizer advice or yield guarantee
        bad_claim1 = clean + "\n\nAdditionally, apply 50 kg urea fertilizer per hectare to accelerate vegetative growth."
        bad_claim2 = clean + "\n\nAdhering to this plan guarantees a 25% yield increase and saves 30% water this season."
        return [bad_claim1, bad_claim2, bad_claim1, bad_claim2]

    elif scenario_id == "TC05":
        # Attempt 1 fails (altered number 999 mm), Attempt 2 receives feedback and passes with clean text!
        bad_att1 = clean.replace(f"{net_val:g} mm", "999 mm")
        return [bad_att1, clean]

    elif scenario_id == "TC06":
        # Repeated persistent failures up to and exceeding retry limit
        return [
            clean.replace("prototype", "commercial tool"),
            clean.replace(f"{net_val:g} mm", "999 mm"),
            clean + " Add urea fertilizer.",
            clean + " Irrigate every 7 days.",
        ]

    elif scenario_id == "TC07":
        # Simulates network failure / API exception
        return []

    return [clean]


class MockLLMClient:
    """Mock client mimicking Groq chat completions interface for offline testing."""

    def __init__(self, candidates: Optional[List[str]] = None, exception_to_raise: Optional[Exception] = None):
        self.candidates = list(candidates or [])
        self.exception_to_raise = exception_to_raise
        self.calls = 0
        self.recorded_messages: List[List[Dict[str, str]]] = []
        self.chat = type("Chat", (), {"completions": self})()

    def create(self, **kwargs) -> Any:
        self.calls += 1
        self.recorded_messages.append(kwargs.get("messages", []))
        if self.exception_to_raise:
            raise self.exception_to_raise

        if not self.candidates:
            return type("Resp", (), {"choices": [type("Choice", (), {"message": type("Msg", (), {"content": ""})()})()]})()

        # Pick candidate for current call, clamp to last candidate if exhausted
        idx = min(self.calls - 1, len(self.candidates) - 1)
        text = self.candidates[idx]
        return type("Resp", (), {"choices": [type("Choice", (), {"message": type("Msg", (), {"content": text})()})()]})()


# ---------------------------------------------------------------------------
# ReAct-Reflexion Self-Correction Engine Core
# ---------------------------------------------------------------------------
def run_self_correction_framework(
    result: Dict[str, Any],
    schedule: Dict[str, Any],
    language: str = "en",
    config: Optional[SelfCorrectionConfig] = None,
    client: Any = None,
    mock_scenario_id: Optional[str] = None,
) -> SelfCorrectionResult:
    """Execute the complete ReAct-Reflexion self-correction framework.

    Pipeline:
      1. Reason  : Extract immutable calculation facts and build system/user prompt.
      2. Act     : Generate explanation candidate (via Groq API or Mock Scenario).
      3. Observe : Deterministically validate response against agronomic facts and rules.
      4. Reflect : On failure, synthesize structured feedback diagnosing specific violations.
      5. Correct : Re-submit facts + feedback up to config.max_correction_attempts.
      6. Fallback: If exhausted or on API exception, activate safe deterministic fallback.
    """
    start_total_time = time.perf_counter()
    config = config or SelfCorrectionConfig()
    lang = language if language in LANGUAGES else "en"
    facts = collect_facts(result, schedule)

    attempts_history: List[CorrectionAttempt] = []
    is_mock = mock_scenario_id is not None
    execution_mode = "mock_demonstration" if is_mock else "live_llm"

    # Handle invalid engine inputs prior to LLM interaction
    if not result.get("valid"):
        safe_text = fallback_explanation(result, schedule, lang)
        return SelfCorrectionResult(
            final_text=safe_text,
            source="fallback",
            overall_status=STATUS_FALLBACK_USED,
            total_attempts=0,
            initial_passed=False,
            corrected=False,
            attempts_history=[],
            facts=facts,
            language=lang,
            execution_mode=execution_mode,
            scenario_id=mock_scenario_id,
            fallback_used=True,
            fallback_reason="invalid_inputs",
            total_latency_ms=(time.perf_counter() - start_total_time) * 1000,
        )

    # Initialize client for live or mock execution
    if is_mock:
        if mock_scenario_id == "TC07":
            # TC07 deliberately triggers an API exception
            client = MockLLMClient(exception_to_raise=TimeoutError("Simulated Groq Gateway Timeout (TC07)"))
        else:
            candidates = get_mock_candidates_for_scenario(mock_scenario_id, facts, lang)
            client = MockLLMClient(candidates=candidates)
    else:
        if client is None:
            try:
                client = get_client()
            except ExplainerUnavailable as exc:
                logger.warning("Groq API unavailable: %s", exc.category)
                safe_text = fallback_explanation(result, schedule, lang)
                return SelfCorrectionResult(
                    final_text=safe_text,
                    source="fallback",
                    overall_status=STATUS_API_UNAVAILABLE,
                    total_attempts=0,
                    initial_passed=False,
                    corrected=False,
                    attempts_history=[],
                    facts=facts,
                    language=lang,
                    execution_mode=execution_mode,
                    scenario_id=mock_scenario_id,
                    fallback_used=True,
                    fallback_reason="api_unavailable",
                    api_error_category=exc.category,
                    total_latency_ms=(time.perf_counter() - start_total_time) * 1000,
                )

    feedback: Optional[str] = None
    structured_feedback: str = ""
    max_total_calls = 1 + config.max_correction_attempts  # Initial + Retries

    for attempt_idx in range(1, max_total_calls + 1):
        attempt_start = time.perf_counter()

        # Step A & D: Build prompt messages incorporating previous Reflexion feedback
        messages = _messages(facts, lang, feedback)
        user_prompt_content = messages[-1]["content"]

        # Step B: Call generator (Act)
        try:
            candidate_text = _call(client, messages)
        except Exception as exc:  # noqa: BLE001
            err_cat = classify_error(exc)
            logger.warning("Exception during LLM generation at attempt %d: %s", attempt_idx, err_cat)
            safe_text = fallback_explanation(result, schedule, lang)
            return SelfCorrectionResult(
                final_text=safe_text,
                source="fallback",
                overall_status=STATUS_API_UNAVAILABLE,
                total_attempts=attempt_idx - 1,
                initial_passed=False,
                corrected=False,
                attempts_history=attempts_history,
                facts=facts,
                language=lang,
                execution_mode=execution_mode,
                scenario_id=mock_scenario_id,
                fallback_used=True,
                fallback_reason="api_failure",
                api_error_category=err_cat,
                total_latency_ms=(time.perf_counter() - start_total_time) * 1000,
            )

        # Step C: Deterministic Observation & Validation (Observe)
        v_check = validate_explanation(candidate_text, facts, lang)
        latency = (time.perf_counter() - attempt_start) * 1000

        # Construct Attempt Record
        attempt_rec = CorrectionAttempt(
            attempt_number=attempt_idx,
            prompt_user_content=user_prompt_content,
            candidate_text=candidate_text,
            validation_passed=v_check["passed"],
            issues=v_check["issues"],
            feedback_text=v_check.get("feedback", ""),
            structured_feedback=v_check.get("structured_feedback", ""),
            latency_ms=latency,
        )
        attempts_history.append(attempt_rec)

        # Success condition: validate passed immediately
        if v_check["passed"]:
            total_duration = (time.perf_counter() - start_total_time) * 1000
            if attempt_idx == 1:
                status = STATUS_INITIAL_VALID
                corrected = False
            else:
                status = STATUS_CORRECTION_SUCCESSFUL
                corrected = True

            return SelfCorrectionResult(
                final_text=candidate_text,
                source="ai",
                overall_status=status,
                total_attempts=attempt_idx,
                initial_passed=(attempt_idx == 1),
                corrected=corrected,
                attempts_history=attempts_history,
                facts=facts,
                language=lang,
                execution_mode=execution_mode,
                scenario_id=mock_scenario_id,
                fallback_used=False,
                total_latency_ms=total_duration,
            )

        # Failure condition: Prepare Reflexion feedback for next correction cycle
        feedback = v_check.get("structured_feedback") or v_check.get("feedback")
        structured_feedback = v_check.get("structured_feedback", "")
        logger.info(
            "Attempt %d failed validation with %d issue(s). Prepared feedback for retry.",
            attempt_idx,
            len(v_check["issues"]),
        )

    # If all bounded correction attempts are exhausted: Safe Fallback
    total_duration = (time.perf_counter() - start_total_time) * 1000
    safe_text = fallback_explanation(result, schedule, lang)

    return SelfCorrectionResult(
        final_text=safe_text,
        source="fallback",
        overall_status=STATUS_MAX_ATTEMPTS_REACHED,
        total_attempts=len(attempts_history),
        initial_passed=False,
        corrected=False,
        attempts_history=attempts_history,
        facts=facts,
        language=lang,
        execution_mode=execution_mode,
        scenario_id=mock_scenario_id,
        fallback_used=True,
        fallback_reason="max_retries_exhausted",
        total_latency_ms=total_duration,
    )


# ---------------------------------------------------------------------------
# Metrics Aggregator for Academic Evaluation
# ---------------------------------------------------------------------------
def compute_experiment_metrics(runs_history: List[SelfCorrectionResult]) -> Dict[str, Any]:
    """Calculate defined empirical metrics across multiple self-correction experiment runs."""
    total_runs = len(runs_history)
    if total_runs == 0:
        return {
            "total_runs": 0,
            "initial_pass_rate": 0.0,
            "final_pass_rate": 0.0,
            "correction_success_rate": 0.0,
            "average_attempts": 0.0,
            "remaining_failures": 0,
            "fallback_count": 0,
            "api_failure_count": 0,
            "average_latency_ms": 0.0,
        }

    initial_passed_count = sum(1 for r in runs_history if r.initial_passed)
    final_passed_count = sum(1 for r in runs_history if r.source == "ai" and not r.fallback_used)
    correction_needed_count = sum(1 for r in runs_history if not r.initial_passed and r.overall_status != STATUS_API_UNAVAILABLE)
    correction_success_count = sum(1 for r in runs_history if r.corrected and r.source == "ai")
    fallback_count = sum(1 for r in runs_history if r.fallback_used)
    api_failure_count = sum(1 for r in runs_history if r.overall_status == STATUS_API_UNAVAILABLE)
    total_attempts = sum(r.total_attempts for r in runs_history)
    remaining_failures = sum(1 for r in runs_history if r.overall_status in (STATUS_MAX_ATTEMPTS_REACHED, STATUS_VALIDATION_FAILED))
    total_latency = sum(r.total_latency_ms for r in runs_history)

    return {
        "total_runs": total_runs,
        "initial_pass_rate": round(initial_passed_count / total_runs * 100, 1),
        "final_pass_rate": round(final_passed_count / total_runs * 100, 1),
        "correction_success_rate": round((correction_success_count / correction_needed_count * 100) if correction_needed_count > 0 else 0.0, 1),
        "average_attempts": round(total_attempts / total_runs, 2),
        "remaining_failures": remaining_failures,
        "fallback_count": fallback_count,
        "api_failure_count": api_failure_count,
        "average_latency_ms": round(total_latency / total_runs, 1),
    }
