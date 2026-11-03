"""Validates a generated explanation against the deterministic result and schedule.

Checks: required content, changed/unsupported numbers, changed units, unsupported intervals, contradiction
with the schedule status, fertilizer/pesticide/outcome claims, and retained uncertainty/prototype wording.
Limits (documented honestly): regex/keyword based; a number that coincides with some allowed fact passes;
Hindi/Marathi keyword lists are small and not exhaustive.
"""
from __future__ import annotations

import json
import re

_DEV = str.maketrans("०१२३४५६७८९", "0123456789")
_NUM_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")
_UNIT_RE = re.compile(r"\s*(mm/day|mm|m_cubed|hours?|hrs?|ha|days?|months?|%|litres?|liters?)(?![A-Za-z])", re.I)
_UNIT_NORM = {"hour": "hours", "hours": "hours", "hr": "hours", "hrs": "hours", "day": "days", "days": "days",
              "month": "months", "months": "months", "m_cubed": "m3", "litre": "litres", "litres": "litres",
              "liter": "litres", "liters": "litres"}
_DEV_RANGE = "\u0900-\u097F"
_NEG_EN = ("not", "don't", "do not", "no need", "avoid", "defer", "instead of", "without", "unnecessary")
_NEG_DEV = ("न ", "नहीं", "टाल", "नका", "नाही", "टाळा")

FORBIDDEN = {
    "fertilizer": [r"fertili[sz]er", r"\burea\b", r"\bnpk\b", r"manure", r"compost",
                   rf"(?<![{_DEV_RANGE}])(उर्वरक|खाद|यूरिया|युरिया|खत|खते)(?![{_DEV_RANGE}])"],
    "pesticide": [r"pesticide", r"insecticide", r"herbicide", r"fungicide", r"कीटनाशक|कीटकनाशक|कीटनाशी"],
    "unsupported_claim": [r"guarantee", r"increase(s|d)? (the )?yield", r"yield (will|would) (rise|increase|improve)",
                          r"save(s|d)? (\w+ ){0,2}water", r"water[- ]sav(ing|ings)", r"गारंटी|उपज बढ़|उत्पादन वाढ|हमी"],
}
INTERVAL_RE = re.compile(r"(every|each)\s+\d+\s+days?|हर\s*[\d०-९]+\s*दिन|दर\s*[\d०-९]+\s*दिवसां", re.I)
NOW_RE = re.compile(r"(irrigate|water the (field|crop)) (now|immediately|today)|start irrigation (now|today)|"
                    r"अभी सिंचाई करें|तुरंत सिंचाई करें|आज सिंचाई करें|आता सिंचन करा|त्वरित सिंचन करा|आज सिंचन करा", re.I)
NO_IRR_RE = re.compile(r"do not irrigate|don't irrigate|no irrigation is needed|skip irrigation|"
                       r"सिंचाई न करें|सिंचाई की जरूरत नहीं|सिंचन करू नका|सिंचनाची गरज नाही", re.I)
PROTOTYPE_WORDS = ("prototype", "प्रोटोटाइप")
UNCERTAIN_WORDS = ("missing", "not available", "unknown", "insufficient", "assum", "uncertain", "estimate",
                   "अनुमान", "कमी", "उपलब्ध नहीं", "अपर्याप्त", "अंदाज", "अपुरी", "उपलब्ध नाही", "कमतरता")

RULES_METADATA = {
    "empty": {
        "name": "Response Completeness & Format",
        "description": "Verifies explanation is not empty, blank, or malformed.",
    },
    "unsupported_number": {
        "name": "Numerical Invariance",
        "description": "Ensures all numerical quantities in the explanation exactly match supplied facts.",
    },
    "unit_changed": {
        "name": "Unit Preservation",
        "description": "Ensures units (mm, m3, hours, days, %, ha) are preserved and not swapped.",
    },
    "unsupported_interval": {
        "name": "Interval Constraint",
        "description": "Blocks hallucinated repeating irrigation schedules (e.g. 'every 7 days').",
    },
    "fertilizer": {
        "name": "Scope Constraint: No Fertilizer Claims",
        "description": "Disallows urea, NPK, fertilizer or compost recommendations.",
    },
    "pesticide": {
        "name": "Scope Constraint: No Pesticide Claims",
        "description": "Disallows chemical, pesticide, or insecticide recommendations.",
    },
    "unsupported_claim": {
        "name": "Scope Constraint: No Guaranteed Claims",
        "description": "Disallows yield increase guarantees or water saving assertions.",
    },
    "contradiction": {
        "name": "Irrigation Decision Consistency",
        "description": "Ensures action text strictly aligns with engine status code without contradiction.",
    },
    "missing_value": {
        "name": "Required Value Disclosure",
        "description": "Verifies key calculated values (net mm, gross mm, duration) appear in the advisory.",
    },
    "missing_date": {
        "name": "Review Date Integrity",
        "description": "Verifies scheduled review date is accurately stated.",
    },
    "missing_prototype_warning": {
        "name": "Educational Prototype Disclaimer",
        "description": "Verifies inclusion of required educational prototype disclaimer.",
    },
    "missing_uncertainty": {
        "name": "Uncertainty & Assumption Disclosure",
        "description": "Ensures data gaps and calculation assumptions are acknowledged.",
    },
    "wrong_language": {
        "name": "Target Language Script Integrity",
        "description": "Verifies text is predominantly in the target language and script (Latin or Devanagari).",
    },
}


def _norm(text: str) -> str:
    t = text.translate(_DEV)
    return re.sub(r"m\^?[3³]", "m_cubed", t)


def extract_numbers(text: str):
    """Return list of (value, unit) found in text; list markers like '1.' at line start are ignored."""
    t = re.sub(r"(?m)^\s*(?:[-*•]\s*)?\d+[.)]\s+", "", _norm(text))
    out = []
    for m in _NUM_RE.finditer(t):
        try:
            val = round(float(m.group().replace(",", "")), 2)
        except ValueError:
            continue
        u = _UNIT_RE.match(t[m.end():])
        unit = ""
        if u:
            unit = _UNIT_NORM.get(u.group(1).lower(), u.group(1).lower())
        out.append((val, unit))
    return out


def _variants(v: float):
    return {round(v, 2), round(v, 1), float(round(v))}


def collect_facts(result: dict, schedule: dict) -> dict:
    """Single source of facts for both the LLM prompt and the validator."""
    est, inp = result.get("estimates", {}), result.get("inputs_used", {})
    numeric = {}

    def add(name, value, unit):
        if value is not None:
            numeric[name] = {"value": round(float(value), 2), "unit": unit}

    add("crop_age_months", inp.get("crop_age_months"), "months")
    add("soil_moisture_reading_pct", inp.get("soil_moisture_pct"), "%")
    add("rainfall_mm_user_estimate", est.get("rain_mm"), "mm")
    add("effective_rain_mm", est.get("effective_rain_mm"), "mm")
    add("kc", est.get("kc"), "")
    add("eto_mm_day", est.get("eto_mm_day"), "mm/day")
    add("etc_mm_day", est.get("etc_mm_day"), "mm/day")
    add("planning_period_days", est.get("planning_period_days"), "days")
    add("crop_demand_mm", est.get("crop_demand_mm"), "mm")
    add("depletion_now_mm", est.get("depletion_now_mm"), "mm")
    add("allowable_depletion_raw_mm", est.get("raw_mm"), "mm")
    add("net_irrigation_mm", est.get("net_irrigation_mm"), "mm")
    add("efficiency_pct", est.get("efficiency_pct"), "%")
    add("gross_irrigation_mm", est.get("gross_irrigation_mm"), "mm")
    add("area_ha", est.get("area_ha"), "ha")
    add("gross_volume_m3", est.get("gross_volume_m3"), "m3")
    add("available_water_m3", est.get("available_water_m3"), "m3")
    add("water_coverage_pct", est.get("water_coverage_pct"), "%")
    add("irrigation_duration_h", schedule.get("irrigation_duration_h"), "hours")
    add("review_in_days", schedule.get("review_in_days"), "days")
    return {
        "numeric": numeric,
        "status_code": schedule.get("status_code"),
        "status_label": schedule.get("status_label"),
        "review_date": schedule.get("review_date"),
        "schedule_reasons": schedule.get("reasons", []),
        "reassess_factors": schedule.get("reassess_factors", []),
        "advisory_reason": result.get("advisory_reason", ""),
        "warnings": result.get("warnings", []),
        "missing_inputs": result.get("missing_inputs", []),
        "assumptions": result.get("assumptions", []),
        "limitations": result.get("limitations", []),
        "rainfall_category": inp.get("rainfall_category"),
        "provisional": result.get("provisional"),
    }


def _allowed(facts: dict):
    nums, pairs = set(), set()
    for item in facts["numeric"].values():
        for v in _variants(item["value"]):
            nums.add(v)
            pairs.add((v, item["unit"]))
    blob = " ".join([str(facts.get("review_date") or ""), facts.get("advisory_reason", "")]
                    + facts["schedule_reasons"] + facts["reassess_factors"] + facts["warnings"]
                    + facts["assumptions"] + facts["limitations"])
    for v, u in extract_numbers(blob):
        nums.add(v)
        pairs.add((v, u))
    return nums, pairs


def _negated(text: str, start: int) -> bool:
    window = text[max(0, start - 25):start].lower()
    return any(n in window for n in _NEG_EN + _NEG_DEV)


def format_structured_feedback(issues: list[dict]) -> str:
    """Build structured, machine-parseable and LLM-friendly feedback following Reflexion principles."""
    if not issues:
        return ""
    lines = [
        "AUTOMATIC VALIDATION FEEDBACK (Reflexion Diagnosis):",
        "Your previous explanation contained the following error(s) that violated system guardrails:",
    ]
    for idx, iss in enumerate(issues, 1):
        rule_name = iss.get("rule") or iss.get("code")
        code = iss.get("code")
        msg = iss.get("message")
        lines.append(f"{idx}. Rule Violated: [{code}] {rule_name}")
        if iss.get("expected"):
            lines.append(f"   Expected: {iss['expected']}")
        if iss.get("observed"):
            lines.append(f"   Observed Mismatch: {iss['observed']}")
        if iss.get("instruction"):
            lines.append(f"   Correction Instruction: {iss['instruction']}")
        else:
            lines.append(f"   Correction Instruction: Fix the error: {msg}")

    lines.append("")
    lines.append("CRITICAL INSTRUCTIONS FOR CORRECTION:")
    lines.append("- Preserve all original calculations, numbers, units, and review dates from the trusted facts.")
    lines.append("- Strictly align your recommendation with the calculation engine's irrigation status.")
    lines.append("- Do NOT introduce unapproved agronomic claims (fertilizers, pesticides, yield guarantees).")
    lines.append("- Output the complete corrected explanation incorporating these fixes.")
    return "\n".join(lines)


def validate_explanation(text: str, facts: dict, language: str = "en") -> dict:
    issues = []

    def flag(code, msg, expected=None, observed=None, instruction=None):
        rule_meta = RULES_METADATA.get(code, {})
        rule_name = rule_meta.get("name", code)
        issues.append({
            "code": code,
            "rule": rule_name,
            "message": msg,
            "expected": expected or "",
            "observed": observed or "",
            "instruction": instruction or msg,
        })

    if not text or len(text.strip()) < 40:
        observed_len = len(text.strip()) if text else 0
        flag(
            "empty",
            "Explanation is empty or too short.",
            expected="Complete 3-5 paragraph explanation with at least 40 characters.",
            observed=f"Response had {observed_len} characters.",
            instruction="Generate a comprehensive explanation containing 3-5 paragraphs based on the supplied facts.",
        )
        return _finish(issues)

    nums, pairs = _allowed(facts)

    for val, unit in extract_numbers(text):
        if val not in nums:
            flag(
                "unsupported_number",
                f"Number {val:g}{(' ' + unit) if unit else ''} is not in the supplied facts.",
                expected="Only numerical values that exist in the calculation facts.",
                observed=f"{val:g}{(' ' + unit) if unit else ''}",
                instruction=f"Remove or correct the number {val:g} to match the trusted calculation facts.",
            )
        elif unit and (val, unit) not in pairs:
            flag(
                "unit_changed",
                f"Value {val:g} is used with unit '{unit}', which differs from the supplied unit.",
                expected="Original unit defined in facts for this quantity.",
                observed=f"Value {val:g} paired with unit '{unit}'",
                instruction=f"Restore the correct unit for {val:g} as given in the facts JSON.",
            )

    interval_match = INTERVAL_RE.search(_norm(text)) or INTERVAL_RE.search(text)
    if interval_match:
        flag(
            "unsupported_interval",
            "A repeating irrigation interval was introduced; none is supplied.",
            expected="No recurring irrigation intervals (e.g. 'every N days').",
            observed=interval_match.group(0),
            instruction="Remove the recurring interval statement. Direct the farmer to the single calculated review date.",
        )

    for key, pats in FORBIDDEN.items():
        for p in pats:
            m = re.search(p, text, re.I)
            if m:
                flag(
                    key,
                    f"Content of type '{key}' is not allowed.",
                    expected=f"Exclusively irrigation water advice with zero {key} claims.",
                    observed=m.group(0),
                    instruction=f"Remove all mention of {key} from the advisory text.",
                )
                break

    code = facts.get("status_code")
    if code != "IRRIGATE_NOW":
        for m in NOW_RE.finditer(text):
            if not _negated(text, m.start()):
                flag(
                    "contradiction",
                    "Text tells the farmer to irrigate now, but the schedule status differs.",
                    expected=f"Status statement matching engine decision '{code}' ({facts.get('status_label', '')}).",
                    observed=m.group(0),
                    instruction="Do not tell the farmer to irrigate immediately. Follow the scheduled review or deferral recommendation.",
                )
                break
    else:
        for m in NO_IRR_RE.finditer(text):
            flag(
                "contradiction",
                "Text says not to irrigate, but the schedule status is 'consider irrigating now'.",
                expected="Affirmative recommendation to consider irrigating now.",
                observed=m.group(0),
                instruction="State that irrigation should be considered now to replenish soil moisture deficit.",
            )
            break

    # required content
    tnums = {v for v, _ in extract_numbers(text)}
    for key in ("net_irrigation_mm", "gross_irrigation_mm", "irrigation_duration_h"):
        item = facts["numeric"].get(key)
        if item and not (_variants(item["value"]) & tnums):
            flag(
                "missing_value",
                f"Required value '{key}' ({item['value']:g} {item['unit']}) is missing.",
                expected=f"{key} = {item['value']:g} {item['unit']}",
                observed="Metric was not mentioned in the text.",
                instruction=f"Include the calculated {key.replace('_', ' ')}: {item['value']:g} {item['unit']}.",
            )
    rd = facts.get("review_date")
    if rd:
        y, _, d = rd.split("-")
        if not ({float(y), float(d)} <= tnums):
            flag(
                "missing_date",
                f"Review date {rd} is missing or changed.",
                expected=f"Review date '{rd}'",
                observed="Review date missing or modified.",
                instruction=f"Clearly state the calculated next review or irrigation date: {rd}.",
            )
    low = text.lower()
    if not any(w in low for w in PROTOTYPE_WORDS):
        flag(
            "missing_prototype_warning",
            "The educational-prototype warning is missing.",
            expected="Explicit mention that this is an 'educational prototype'.",
            observed="Educational prototype disclaimer was omitted.",
            instruction="Include the required statement: 'This is an educational prototype.'",
        )
    if (facts.get("missing_inputs") or facts.get("provisional") or facts.get("warnings")) \
            and not any(w in low for w in UNCERTAIN_WORDS):
        flag(
            "missing_uncertainty",
            "Uncertainty / missing-input information was not retained.",
            expected="Mention that estimates contain assumptions, uncertainties, or data gaps.",
            observed="No uncertainty or assumption disclosure found.",
            instruction="Acknowledge the uncertainties, assumptions, and limitations of this estimate.",
        )
    letters = [c for c in text if c.isalpha()]
    if letters and language in ("hi", "mr"):
        dev = sum("\u0900" <= c <= "\u097F" for c in letters) / len(letters)
        if dev < 0.3:
            flag(
                "wrong_language",
                "Text is not mainly in the selected language.",
                expected=f"Text composed in native Devanagari script for {language}.",
                observed=f"Only {dev*100:.1f}% Devanagari characters detected.",
                instruction=f"Translate and write the response in proper {language} using Devanagari script.",
            )
    elif letters and language == "en":
        if sum("\u0900" <= c <= "\u097F" for c in letters) / len(letters) > 0.1:
            flag(
                "wrong_language",
                "Text is not in English.",
                expected="English language text using Latin script.",
                observed="Devanagari characters detected in English response.",
                instruction="Write the response purely in English.",
            )
    return _finish(issues)


def _finish(issues):
    feedback = "; ".join(f"[{i['code']}] {i['message']}" for i in issues)
    structured_feedback = format_structured_feedback(issues)
    return {
        "passed": not issues,
        "issues": issues,
        "feedback": feedback,
        "structured_feedback": structured_feedback,
    }


def facts_json(facts: dict) -> str:
    return json.dumps(facts, ensure_ascii=False, indent=2)

