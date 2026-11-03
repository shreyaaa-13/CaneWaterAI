"""Deterministic irrigation scheduler (separate from the GenAI layer).

Status codes: IRRIGATE_NOW, SCHEDULE_LATER, DEFER_REASSESS, REVIEW_PENDING_SOIL_DATA, INSUFFICIENT_DATA.
Rules (prototype logic, documented in docs/methodology.md):
  * Soil-water data present: irrigation is *considered* when depletion >= RAW; a later date is projected
    from days = (RAW - Dr_now) / (ETc - effective_rain/period) when ETo is known.
  * Heavy rainfall category without a mm value overrides 'IRRIGATE_NOW' to 'DEFER_REASSESS'.
  * Without soil-water data the engine cannot judge timing -> REVIEW_PENDING_SOIL_DATA.
  * Duration = gross volume / pump flow, only when both exist. Review interval = planning period, which is a
    user-selected window and not an optimal interval.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Optional

STATUS_LABELS = {
    "IRRIGATE_NOW": "Consider irrigating now",
    "SCHEDULE_LATER": "Plan irrigation for a later date",
    "DEFER_REASSESS": "Defer irrigation and reassess",
    "REVIEW_PENDING_SOIL_DATA": "Review on the date shown; soil-water data needed",
    "INSUFFICIENT_DATA": "Insufficient data for a schedule",
}


def _row(d: date, action: str, depth: Optional[float], note: str) -> dict:
    return {"date": d.isoformat(), "action": action, "net_depth_mm": depth, "note": note}


def build_schedule(result: dict, today: Optional[date] = None) -> dict:
    today = today or date.today()
    sched = {"status_code": "INSUFFICIENT_DATA", "status_label": STATUS_LABELS["INSUFFICIENT_DATA"],
             "review_date": None, "review_in_days": None, "irrigation_duration_h": None,
             "net_irrigation_mm": None, "gross_irrigation_mm": None, "gross_volume_m3": None,
             "water_sufficient": None, "water_coverage_pct": None, "rows": [], "reasons": [],
             "reassess_factors": ["Any change in rainfall, ETo, soil moisture or crop stage."],
             "message": ""}
    if not result.get("valid"):
        sched["message"] = "Inputs are invalid; no schedule was created."
        sched["reasons"].append("Input validation failed.")
        return sched
    est, inp = result["estimates"], result["inputs_used"]
    net = est.get("net_irrigation_mm")
    if net is None:
        sched["message"] = ("Not enough information: provide ETo, or volumetric soil data "
                            "(field capacity, wilting point, root depth), to get a schedule.")
        sched["reasons"].append("Neither crop demand nor root-zone depletion could be calculated.")
        return sched

    period = est["planning_period_days"]
    etc, raw, dr_now = est.get("etc_mm_day"), est.get("raw_mm"), est.get("depletion_now_mm")
    reff = est.get("effective_rain_mm") or 0.0
    status, review_days = None, period
    reasons = sched["reasons"]
    heavy_unquantified = inp["rainfall_category"] == "Heavy" and inp["rainfall_mm"] is None

    if raw is not None and dr_now is not None:
        if dr_now >= raw:
            status = "IRRIGATE_NOW"
            reasons.append("Estimated root-zone depletion has reached the allowable depletion (RAW).")
        elif etc is not None:
            net_daily = etc - reff / period
            if net_daily > 0:
                days = math.floor((raw - dr_now) / net_daily)
                if days <= 0:
                    status = "IRRIGATE_NOW"
                    reasons.append("Depletion is projected to reach RAW within the next day.")
                elif days < period:
                    status, review_days = "SCHEDULE_LATER", days
                    reasons.append("Depletion is projected to reach RAW before the end of the planning period.")
            if status is None:
                status = "DEFER_REASSESS"
                reasons.append("Depletion is not projected to reach RAW within the planning period.")
        else:
            status = "DEFER_REASSESS"
            reasons.append("Current depletion is below RAW; ETo is missing so no projection was made.")
    else:
        status = "REVIEW_PENDING_SOIL_DATA" if net > 0 else "DEFER_REASSESS"
        reasons.append("Rainfall covers the estimated crop demand for the planning period." if net == 0 else
                       "Crop demand exceeds effective rainfall, but timing cannot be judged without volumetric soil data.")

    if heavy_unquantified and status == "IRRIGATE_NOW":
        status = "DEFER_REASSESS"
        reasons.append("Heavy rain is expected but not quantified, so irrigation is deferred until reassessment.")

    sched["status_code"], sched["status_label"] = status, STATUS_LABELS[status]
    review_date = today + timedelta(days=0 if status == "IRRIGATE_NOW" else review_days)
    sched["review_date"] = review_date.isoformat()
    sched["review_in_days"] = (review_date - today).days
    sched["net_irrigation_mm"] = net
    sched["gross_irrigation_mm"] = est.get("gross_irrigation_mm")
    sched["gross_volume_m3"] = est.get("gross_volume_m3")

    # water availability and duration
    if sched["gross_volume_m3"] and est.get("available_water_m3") is not None:
        sched["water_coverage_pct"] = est["water_coverage_pct"]
        sched["water_sufficient"] = est["available_water_m3"] >= sched["gross_volume_m3"]
    if status in ("IRRIGATE_NOW", "SCHEDULE_LATER") and sched["gross_volume_m3"] and est.get("pump_flow_m3_per_h"):
        sched["irrigation_duration_h"] = sched["gross_volume_m3"] / est["pump_flow_m3_per_h"]

    depth_note = "Estimated net depth for the planning period; recalculate at the review date."
    if status == "IRRIGATE_NOW":
        sched["rows"].append(_row(today, "Consider irrigation", net, depth_note))
        sched["rows"].append(_row(today + timedelta(days=period), "Reassess", None, "Re-enter fresh field data."))
    elif status == "SCHEDULE_LATER":
        sched["rows"].append(_row(review_date, "Plan irrigation / recheck soil", net, depth_note))
    else:
        sched["rows"].append(_row(review_date, "Reassess", None, "Re-enter fresh field data."))
    sched["message"] = f"{sched['status_label']}."
    if est.get("rainfall_credit_applied") is False:
        sched["reassess_factors"].append("Rainfall was not quantified in mm.")
    if heavy_unquantified:
        sched["reassess_factors"].append("Heavy rainfall expected; reassess after it occurs.")
    return sched
