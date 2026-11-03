"""GenAI explanation layer (Groq + openai/gpt-oss-20b) with validation, bounded retries and fallback.

The model only EXPLAINS the deterministic result. It never changes numbers, status or schedule.
This is a bounded generate -> validate -> retry-with-feedback loop. It is NOT a full ReAct-Reflexion system.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from dotenv import load_dotenv

from response_validator import collect_facts, facts_json, validate_explanation

logger = logging.getLogger("canewater.genai")
DEFAULT_MODEL = "openai/gpt-oss-20b"
MAX_RETRIES = 2            # correction attempts after the first generation
LANGUAGES = {"en": "English", "hi": "Hindi (हिन्दी)", "mr": "Marathi (मराठी)"}   # Tamil/Telugu: future scope

SYSTEM_PROMPT = """You are an explanation assistant for an educational sugarcane irrigation prototype.
Explain ONLY the calculated results and schedule given in the facts JSON, in simple, farmer-friendly language.
Rules:
- Use only the supplied facts. Preserve every number, unit, date and condition exactly. Keep units as Latin
  symbols (mm, mm/day, m3, hours, days, %) and write numbers with Western digits.
- Explain why the scheduling engine produced its status. Do not change, override or re-decide the status,
  quantities or dates. Do not invent measurements, rainfall, crop condition, water quantities or intervals.
- Do not mention yield, water savings or guaranteed outcomes. Do not give fertilizer or pesticide advice.
- Clearly state uncertainty and missing inputs. State that this is an educational prototype and that
  decisions must be verified with field checks and a local agricultural adviser.
- Use 3 to 5 short paragraphs. No tables, no headings, no markdown lists."""


class ExplainerUnavailable(Exception):
    def __init__(self, category: str):
        super().__init__(category)
        self.category = category


def classify_error(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__.lower()
    if isinstance(exc, ExplainerUnavailable):
        return exc.category
    if status == 429 or "ratelimit" in name:
        return "rate_limit"
    if "timeout" in name or isinstance(exc, TimeoutError):
        return "timeout"
    if status in (401, 403) or "auth" in name:
        return "auth_error"
    if status == 404 or "notfound" in name:
        return "model_unavailable"
    return "api_error"


def check_api_status() -> dict:
    """Safely check Groq API readiness without exposing keys or crashing offline."""
    load_dotenv()
    key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    if not key or key.startswith("your_"):
        return {
            "available": False,
            "mode": "fallback",
            "model": model,
            "reason": "No valid GROQ_API_KEY detected in environment or .env.",
            "label": "Deterministic Fallback Mode",
            "detail": "Calculations and schedules are 100% active. Explanations use the deterministic rule engine.",
            "color": "amber",
        }
    return {
        "available": True,
        "mode": "ai",
        "model": model,
        "reason": "API Key is configured.",
        "label": f"AI Online: {model.split('/')[-1]}",
        "detail": f"Groq cloud inference active using {model}.",
        "color": "green",
    }


def get_client():
    load_dotenv()
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key or key.startswith("your_"):
        raise ExplainerUnavailable("no_api_key")
    try:
        from groq import Groq
    except ImportError as exc:  # pragma: no cover
        raise ExplainerUnavailable("sdk_missing") from exc
    return Groq(api_key=key, timeout=30.0, max_retries=1)


def _messages(facts: dict, language: str, feedback: Optional[str]):
    user = (f"Write the explanation in {LANGUAGES[language]}.\n\nFACTS (JSON):\n{facts_json(facts)}\n")
    if feedback:
        user += ("\nYour previous attempt failed automatic validation. Fix these problems, keep the facts "
                 f"unchanged, and write the full explanation again:\n{feedback}\n")
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def _call(client, messages) -> str:
    resp = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", DEFAULT_MODEL), messages=messages,
        temperature=0.2, max_completion_tokens=2500)
    return (resp.choices[0].message.content or "").strip()


# ------------------------- deterministic fallback -------------------------
_T = {
    "en": {
        "status": {"IRRIGATE_NOW": "The scheduling engine suggests considering irrigation now.",
                   "SCHEDULE_LATER": "The scheduling engine suggests planning irrigation for a later date.",
                   "DEFER_REASSESS": "The scheduling engine suggests deferring irrigation and reassessing.",
                   "REVIEW_PENDING_SOIL_DATA": "Timing cannot be judged without soil-water data; review on the date shown.",
                   "INSUFFICIENT_DATA": "There is insufficient data to give an irrigation schedule."},
        "net": "Estimated net irrigation requirement for the planning period: {v} mm.",
        "gross": "Estimated gross irrigation requirement (with your efficiency of {e} %): {v} mm.",
        "vol": "Estimated gross water volume: {v} m3.",
        "dur": "Estimated pump running time: {v} hours.",
        "date": "Next review or irrigation date: {v}.",
        "rain": "Rainfall was not given in mm, so no rainfall credit was applied.",
        "missing": "Missing inputs limit this estimate: {v}.",
        "labels": {"eto": "ETo", "rainfall_mm": "rainfall in mm", "soil_water_data": "volumetric soil-water data",
                   "efficiency": "irrigation efficiency", "area": "field area", "pump_flow": "pump flow rate"},
        "disc": "This is an educational prototype. Values are estimates based on your inputs and stated assumptions. "
                "Verify with field checks and a local agricultural adviser before deciding."},
    "hi": {
        "status": {"IRRIGATE_NOW": "शेड्यूलिंग इंजन के अनुसार अभी सिंचाई पर विचार करें।",
                   "SCHEDULE_LATER": "शेड्यूलिंग इंजन के अनुसार बाद की तारीख के लिए सिंचाई की योजना बनाएं।",
                   "DEFER_REASSESS": "शेड्यूलिंग इंजन के अनुसार अभी सिंचाई टालें और दोबारा आकलन करें।",
                   "REVIEW_PENDING_SOIL_DATA": "मिट्टी के पानी का डेटा नहीं है, इसलिए समय तय नहीं हो सकता; दी गई तारीख पर समीक्षा करें।",
                   "INSUFFICIENT_DATA": "जानकारी अपर्याप्त है, इसलिए सिंचाई कार्यक्रम नहीं दिया जा सकता।"},
        "net": "योजना अवधि के लिए अनुमानित शुद्ध सिंचाई आवश्यकता: {v} mm।",
        "gross": "अनुमानित सकल सिंचाई आवश्यकता (आपकी दक्षता {e} % के साथ): {v} mm।",
        "vol": "अनुमानित कुल पानी की मात्रा: {v} m3।",
        "dur": "अनुमानित पंप चलाने का समय: {v} hours।",
        "date": "अगली समीक्षा या सिंचाई की तारीख: {v}।",
        "rain": "बारिश mm में नहीं दी गई, इसलिए बारिश का कोई समायोजन नहीं किया गया।",
        "missing": "कमी वाली जानकारी इस अनुमान को सीमित करती है: {v}।",
        "labels": {"eto": "ETo", "rainfall_mm": "बारिश (mm)", "soil_water_data": "मिट्टी के पानी का डेटा",
                   "efficiency": "सिंचाई दक्षता", "area": "खेत का क्षेत्रफल", "pump_flow": "पंप प्रवाह दर"},
        "disc": "यह एक शैक्षिक प्रोटोटाइप है। मान आपके दिए आंकड़ों और बताई गई मान्यताओं पर आधारित अनुमान हैं। "
                "निर्णय से पहले खेत में जांच करें और स्थानीय कृषि सलाहकार से पुष्टि करें।"},
    "mr": {
        "status": {"IRRIGATE_NOW": "शेड्युलिंग इंजिननुसार आता सिंचनाचा विचार करा.",
                   "SCHEDULE_LATER": "शेड्युलिंग इंजिननुसार नंतरच्या तारखेसाठी सिंचनाचे नियोजन करा.",
                   "DEFER_REASSESS": "शेड्युलिंग इंजिननुसार सध्या सिंचन पुढे ढकला आणि पुन्हा आढावा घ्या.",
                   "REVIEW_PENDING_SOIL_DATA": "मातीतील पाण्याची माहिती नसल्याने वेळ ठरवता येत नाही; दिलेल्या तारखेला आढावा घ्या.",
                   "INSUFFICIENT_DATA": "माहिती अपुरी आहे, त्यामुळे सिंचन वेळापत्रक देता येत नाही."},
        "net": "नियोजन कालावधीसाठी अंदाजे निव्वळ सिंचन गरज: {v} mm.",
        "gross": "अंदाजे एकूण सिंचन गरज (तुमच्या कार्यक्षमता {e} % सह): {v} mm.",
        "vol": "अंदाजे एकूण पाण्याचे प्रमाण: {v} m3.",
        "dur": "अंदाजे पंप चालवण्याचा वेळ: {v} hours.",
        "date": "पुढील आढावा किंवा सिंचन तारीख: {v}.",
        "rain": "पाऊस mm मध्ये दिलेला नाही, त्यामुळे पावसाचे कोणतेही समायोजन केलेले नाही.",
        "missing": "अपुरी माहिती या अंदाजाला मर्यादा घालते: {v}.",
        "labels": {"eto": "ETo", "rainfall_mm": "पाऊस (mm)", "soil_water_data": "मातीतील पाण्याची माहिती",
                   "efficiency": "सिंचन कार्यक्षमता", "area": "शेताचे क्षेत्रफळ", "pump_flow": "पंपाचा प्रवाह दर"},
        "disc": "हा शैक्षणिक प्रोटोटाइप आहे. मूल्ये तुमच्या माहितीवर आणि सांगितलेल्या गृहितकांवर आधारित अंदाज आहेत. "
                "निर्णयापूर्वी शेतात तपासणी करा आणि स्थानिक कृषी सल्लागाराकडून खात्री करा."},
}


def _f(v: float) -> str:
    return f"{round(v, 2):g}"


def fallback_explanation(result: dict, schedule: dict, language: str = "en") -> str:
    """Deterministic, model-free explanation in en/hi/mr (translations not independently reviewed)."""
    t = _T.get(language, _T["en"])
    facts = collect_facts(result, schedule)
    n = facts["numeric"]
    lines = [t["status"].get(schedule.get("status_code"), t["status"]["INSUFFICIENT_DATA"])]
    if "net_irrigation_mm" in n:
        lines.append(t["net"].format(v=_f(n["net_irrigation_mm"]["value"])))
    if "gross_irrigation_mm" in n:
        lines.append(t["gross"].format(v=_f(n["gross_irrigation_mm"]["value"]), e=_f(n["efficiency_pct"]["value"])))
    if "gross_volume_m3" in n:
        lines.append(t["vol"].format(v=_f(n["gross_volume_m3"]["value"])))
    if "irrigation_duration_h" in n:
        lines.append(t["dur"].format(v=_f(n["irrigation_duration_h"]["value"])))
    if schedule.get("review_date"):
        lines.append(t["date"].format(v=schedule["review_date"]))
    if "rainfall_mm" in result.get("missing_inputs", []):
        lines.append(t["rain"])
    miss = [t["labels"][m] for m in result.get("missing_inputs", []) if m in t["labels"]]
    if miss:
        lines.append(t["missing"].format(v=", ".join(miss)))
    lines.append(t["disc"])
    return "\n\n".join(lines)


# ------------------------- orchestration -------------------------
def explain(result: dict, schedule: dict, language: str = "en", client=None,
            max_retries: int = MAX_RETRIES) -> dict:
    """Generate -> validate -> (bounded) retry -> fallback. The inputs are never modified."""
    language = language if language in LANGUAGES else "en"
    facts = collect_facts(result, schedule)
    outcome = {"text": "", "source": "fallback", "language": language, "attempts": 0,
               "validation_failures": 0, "corrected": False, "validation_history": [],
               "api_error_category": None, "fallback_reason": None}

    def fallback(reason):
        outcome.update(text=fallback_explanation(result, schedule, language), source="fallback", fallback_reason=reason)
        logger.info("fallback used reason=%s attempts=%d", reason, outcome["attempts"])
        return outcome

    if not result.get("valid"):
        return fallback("invalid_inputs")
    try:
        client = client or get_client()
    except ExplainerUnavailable as exc:
        outcome["api_error_category"] = exc.category
        return fallback("api_unavailable")

    feedback = None
    for attempt in range(1, max_retries + 2):
        outcome["attempts"] = attempt
        try:
            text = _call(client, _messages(facts, language, feedback))
        except Exception as exc:  # noqa: BLE001 - never leak raw API error details
            outcome["api_error_category"] = classify_error(exc)
            logger.warning("api failure category=%s", outcome["api_error_category"])
            return fallback("api_failure")
        check = validate_explanation(text, facts, language)
        outcome["validation_history"].append({"attempt": attempt, "passed": check["passed"],
                                              "codes": [i["code"] for i in check["issues"]]})
        logger.info("validation attempt=%d passed=%s codes=%s", attempt, check["passed"],
                    [i["code"] for i in check["issues"]])
        if check["passed"]:
            outcome.update(text=text, source="ai", corrected=attempt > 1)
            return outcome
        outcome["validation_failures"] += 1
        feedback = check["feedback"]
    return fallback("validation_failed")
