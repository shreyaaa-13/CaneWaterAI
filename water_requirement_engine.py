"""Deterministic water-requirement engine for CaneWater AI (educational prototype).

No language model is used here. All numbers come from the formulas below.

FORMULAS (units in brackets)
  ETc [mm/day]            = Kc [-] x ETo [mm/day]                    (FAO-56 single crop coefficient)
  crop_demand [mm]        = ETc x planning_period_days
  effective_rain [mm]     = effective_rain_fraction x rainfall_mm     (fraction is a CONFIGURABLE assumption)
  TAW [mm]                = 1000 x (FC - PWP)/100 x root_depth_m      (FC, PWP volumetric %; root depth m)
  RAW [mm]                = p x TAW                                   (p = depletion fraction, configurable)
  Dr_now [mm]             = 1000 x (FC - theta)/100 x root_depth_m, clamped to 0..TAW
  Dr_end [mm]             = clamp(Dr_now + crop_demand - effective_rain, 0, TAW)
  net_irrigation [mm]     = Dr_end                  (soil-water balance; refill root zone to FC)
                          = max(0, crop_demand - effective_rain)      (no soil data; no soil-water credit)
                          = Dr_now                  (soil data only; no ETo, no forward projection)
  gross_irrigation [mm]   = net_irrigation / (efficiency_pct/100)     (ONLY if user supplies efficiency)
  volume [m3]             = depth [mm] x area [ha] x 10               (1 mm over 1 ha = 10 m3)
  1 acre = 0.40468564224 ha;  1 m3 = 1000 litres

Kc defaults: Germination/Maturity/Grand growth follow the sugarcane Kc_ini 0.40, Kc_mid 1.25,
Kc_end 0.75 listed in FAO Irrigation & Drainage Paper 56 (Table 12). The Tillering value (0.80)
is a PROTOTYPE interpolation. Verify all values against FAO-56 and local data before real use.
Soil type, weather class and irrigation method are NOT used to invent numbers; they only give
context and consistency checks. Irrigation efficiency is NEVER inferred from the method.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

ACRE_TO_HA = 0.40468564224
M3_PER_MM_PER_HA = 10.0
LITRES_PER_M3 = 1000.0

STAGES = ("Germination", "Tillering", "Grand growth", "Maturity")
SOIL_TYPES = ("Light", "Medium", "Heavy")
WEATHER = ("Cool", "Warm", "Hot")
RAIN_CATEGORIES = ("None", "Light", "Moderate", "Heavy")
METHODS = ("Drip", "Sprinkler", "Flood/furrow")


@dataclass
class EngineConfig:
    """Configurable assumptions. Values marked PROTOTYPE are illustrative, not validated."""
    kc_by_stage: dict = field(default_factory=lambda: {
        "Germination": 0.40, "Tillering": 0.80, "Grand growth": 1.25, "Maturity": 0.75})
    effective_rain_fraction: float = 0.80      # PROTOTYPE assumption
    depletion_fraction_p: float = 0.65         # allowable depletion fraction (check FAO-56 / local)
    planning_period_days: int = 7              # user-selectable planning window
    # PROTOTYPE age ranges [months] for consistency warnings only (varies by variety/season)
    stage_age_ranges: dict = field(default_factory=lambda: {
        "Germination": (0.0, 1.5), "Tillering": (1.0, 4.5),
        "Grand growth": (3.5, 10.0), "Maturity": (8.0, 24.0)})
    # PROTOTYPE bands [mm over the planning period] for category/mm consistency warnings only
    rain_category_bands_mm: dict = field(default_factory=lambda: {
        "None": (0.0, 0.0), "Light": (0.0, 10.0), "Moderate": (10.0, 25.0), "Heavy": (25.0, 1e9)})
    max_crop_age_months: float = 24.0


@dataclass
class FieldInputs:
    crop_age_months: Optional[float] = 5.0
    growth_stage: str = "Grand growth"
    planting_date: Optional[date] = None
    soil_type: str = "Medium"
    soil_moisture_pct: Optional[float] = 30.0
    moisture_is_volumetric: bool = False      # generic reading unless the user states otherwise
    field_capacity_pct: Optional[float] = None    # volumetric %
    wilting_point_pct: Optional[float] = None     # volumetric %
    root_depth_m: Optional[float] = None
    weather: str = "Warm"
    rainfall_category: str = "None"
    rainfall_mm: Optional[float] = None       # manually supplied estimate for the planning period
    eto_mm_day: Optional[float] = None        # manually supplied reference ET
    irrigation_method: str = "Drip"
    irrigation_efficiency_pct: Optional[float] = None
    area: Optional[float] = None
    area_unit: str = "ha"                     # "ha" or "acre"
    available_water_m3: Optional[float] = None
    pump_flow_m3_per_h: Optional[float] = None


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def area_in_ha(area: Optional[float], unit: str) -> Optional[float]:
    if not _is_num(area):
        return None
    return area * ACRE_TO_HA if unit == "acre" else area


def depth_to_volume_m3(depth_mm: float, area_ha: float) -> float:
    """1 mm over 1 ha = 10 m3."""
    return depth_mm * area_ha * M3_PER_MM_PER_HA


def validate_inputs(inp: FieldInputs, cfg: EngineConfig, today: Optional[date] = None):
    """Return (errors, warnings). Errors block calculation; warnings never overwrite user input."""
    today = today or date.today()
    errors, warnings = [], []
    if not _is_num(inp.crop_age_months):
        errors.append("Crop age (months) is required.")
    elif not 0 <= inp.crop_age_months <= cfg.max_crop_age_months:
        errors.append(f"Crop age must be between 0 and {cfg.max_crop_age_months:g} months.")
    for val, allowed, label in ((inp.growth_stage, STAGES, "Growth stage"), (inp.soil_type, SOIL_TYPES, "Soil type"),
                                (inp.weather, WEATHER, "Weather condition"),
                                (inp.rainfall_category, RAIN_CATEGORIES, "Rainfall category"),
                                (inp.irrigation_method, METHODS, "Irrigation method")):
        if val not in allowed:
            errors.append(f"{label} must be one of: {', '.join(allowed)}.")
    if not _is_num(inp.soil_moisture_pct):
        errors.append("Soil moisture reading (%) is required.")
    elif not 0 <= inp.soil_moisture_pct <= 100:
        errors.append("Soil moisture must be between 0 and 100 %.")
    if inp.rainfall_mm is not None and (not _is_num(inp.rainfall_mm) or not 0 <= inp.rainfall_mm <= 500):
        errors.append("Expected rainfall must be between 0 and 500 mm.")
    if inp.eto_mm_day is not None and (not _is_num(inp.eto_mm_day) or not 0 <= inp.eto_mm_day <= 15):
        errors.append("ETo must be between 0 and 15 mm/day.")
    if inp.area is not None:
        if inp.area_unit not in ("ha", "acre"):
            errors.append("Area unit must be 'ha' or 'acre'.")
        elif not _is_num(inp.area) or not 0 < inp.area <= 10000:
            errors.append("Field area must be greater than 0 and at most 10000 ha/acres.")
    if inp.irrigation_efficiency_pct is not None and (
            not _is_num(inp.irrigation_efficiency_pct) or not 1 <= inp.irrigation_efficiency_pct <= 100):
        errors.append("Irrigation efficiency must be between 1 and 100 %.")
    if inp.available_water_m3 is not None and (not _is_num(inp.available_water_m3) or inp.available_water_m3 < 0):
        errors.append("Available irrigation water must be 0 m3 or more.")
    if inp.pump_flow_m3_per_h is not None and (not _is_num(inp.pump_flow_m3_per_h) or inp.pump_flow_m3_per_h <= 0):
        errors.append("Pump flow rate must be greater than 0 m3/h.")
    for v, label in ((inp.field_capacity_pct, "Field capacity"), (inp.wilting_point_pct, "Wilting point")):
        if v is not None and (not _is_num(v) or not 0 < v < 100):
            errors.append(f"{label} must be between 0 and 100 % (volumetric).")
    if inp.root_depth_m is not None and (not _is_num(inp.root_depth_m) or not 0.1 <= inp.root_depth_m <= 3.0):
        errors.append("Root-zone depth must be between 0.1 and 3.0 m.")
    if (inp.field_capacity_pct is not None and inp.wilting_point_pct is not None
            and _is_num(inp.field_capacity_pct) and _is_num(inp.wilting_point_pct)
            and inp.field_capacity_pct <= inp.wilting_point_pct):
        errors.append("Field capacity must be greater than permanent wilting point.")
    if errors:
        return errors, warnings

    # ---- warnings (inconsistencies are flagged, never silently corrected) ----
    lo, hi = cfg.stage_age_ranges[inp.growth_stage]
    if not lo <= inp.crop_age_months <= hi:
        warnings.append(f"Crop age ({inp.crop_age_months:g} months) is outside the illustrative range for "
                        f"'{inp.growth_stage}' ({lo:g}-{hi:g} months). Please check; your selection was kept.")
    if inp.planting_date is not None:
        if inp.planting_date > today:
            warnings.append("Planting date is in the future.")
        else:
            age_from_date = (today - inp.planting_date).days / 30.44
            if abs(age_from_date - inp.crop_age_months) > 0.5:
                warnings.append(f"Planting date implies about {age_from_date:.1f} months but you entered "
                                f"{inp.crop_age_months:g} months. Your entered age was used.")
    if inp.rainfall_mm is not None:
        lo_r, hi_r = cfg.rain_category_bands_mm[inp.rainfall_category]
        if not lo_r <= inp.rainfall_mm <= hi_r:
            warnings.append(f"Rainfall category '{inp.rainfall_category}' does not match {inp.rainfall_mm:g} mm "
                            "under the illustrative bands. The mm value was used.")
    if inp.eto_mm_day is not None:
        if inp.weather == "Hot" and inp.eto_mm_day < 3:
            warnings.append("ETo looks low for 'Hot' weather. Check the ETo value.")
        if inp.weather == "Cool" and inp.eto_mm_day > 6:
            warnings.append("ETo looks high for 'Cool' weather. Check the ETo value.")
    if inp.field_capacity_pct is not None and inp.soil_moisture_pct > inp.field_capacity_pct and inp.moisture_is_volumetric:
        warnings.append("Soil moisture is above field capacity (possible saturation or entry error).")
    if (inp.wilting_point_pct is not None and inp.moisture_is_volumetric
            and inp.soil_moisture_pct < inp.wilting_point_pct):
        warnings.append("Soil moisture is below the permanent wilting point (or entry error).")
    return errors, warnings


def _pick(inp: FieldInputs) -> dict:
    return {
        "crop_age_months": inp.crop_age_months, "growth_stage": inp.growth_stage, "soil_type": inp.soil_type,
        "soil_moisture_pct": inp.soil_moisture_pct, "moisture_is_volumetric": inp.moisture_is_volumetric,
        "weather": inp.weather, "rainfall_category": inp.rainfall_category, "rainfall_mm": inp.rainfall_mm,
        "irrigation_method": inp.irrigation_method, "eto_mm_day": inp.eto_mm_day,
        "irrigation_efficiency_pct": inp.irrigation_efficiency_pct,
        "available_water_m3": inp.available_water_m3, "pump_flow_m3_per_h": inp.pump_flow_m3_per_h,
        "field_capacity_pct": inp.field_capacity_pct, "wilting_point_pct": inp.wilting_point_pct,
        "root_depth_m": inp.root_depth_m, "area_ha": area_in_ha(inp.area, inp.area_unit),
    }


def estimate_water_requirement(inp: FieldInputs, cfg: Optional[EngineConfig] = None,
                               today: Optional[date] = None) -> dict:
    """Return a structured, JSON-serialisable result. Never raises for bad user input."""
    cfg = cfg or EngineConfig()
    errors, warnings = validate_inputs(inp, cfg, today)
    result = {"valid": not errors, "errors": errors, "warnings": warnings, "inputs_used": {},
              "method": {}, "estimates": {}, "assumptions": [], "limitations": [], "missing_inputs": [],
              "provisional": True, "advisory_reason": ""}
    result["limitations"] = [
        "Educational prototype; not a scientifically validated recommendation.",
        "Kc values are generic FAO-56-style values and may differ for your variety, region and season.",
        "Effective rainfall uses a configurable fraction; real losses vary with soil, slope and intensity.",
        "Soil type, weather class and irrigation method are context only and do not change the numbers.",
    ]
    if errors:
        result["advisory_reason"] = "Inputs are invalid, so no estimate was calculated."
        return result

    facts = _pick(inp)
    result["inputs_used"] = facts
    period = cfg.planning_period_days
    est: dict = result["estimates"]
    est["planning_period_days"] = period
    missing = result["missing_inputs"]
    result["assumptions"] = [
        f"Planning period is {period} days (user-selectable, not an optimum interval).",
        f"Effective rainfall fraction is {cfg.effective_rain_fraction:g} (prototype assumption).",
        f"Allowable depletion fraction p is {cfg.depletion_fraction_p:g} (verify locally).",
    ]

    # --- ETc ---
    kc = cfg.kc_by_stage[inp.growth_stage]
    est["kc"] = kc
    etc = None
    if inp.eto_mm_day is not None:
        etc = kc * inp.eto_mm_day
        est.update(eto_mm_day=inp.eto_mm_day, etc_mm_day=etc, crop_demand_mm=etc * period)
        result["method"]["etc"] = "ETc = Kc x ETo (FAO-56 single crop coefficient)"
        result["assumptions"].append(f"Kc is {kc:g} for the {inp.growth_stage} stage.")
    else:
        missing.append("eto")

    # --- rainfall ---
    rain_known = inp.rainfall_mm is not None or inp.rainfall_category == "None"
    rain_mm = inp.rainfall_mm if inp.rainfall_mm is not None else (0.0 if inp.rainfall_category == "None" else None)
    reff = cfg.effective_rain_fraction * rain_mm if rain_mm is not None else None
    est["rain_mm"] = rain_mm
    est["effective_rain_mm"] = reff
    est["rainfall_credit_applied"] = rain_known
    if not rain_known:
        missing.append("rainfall_mm")
        result["warnings"].append(
            f"Rainfall category '{inp.rainfall_category}' was not given in mm, so no rainfall credit was applied.")
    reff_used = reff if reff is not None else 0.0
    if etc is not None and reff is not None:
        est["rain_minus_demand_mm"] = reff - etc * period

    # --- soil-water balance (only with volumetric data) ---
    soil_ok = (inp.moisture_is_volumetric and inp.field_capacity_pct is not None
               and inp.wilting_point_pct is not None and inp.root_depth_m is not None)
    dr_now = dr_end = None
    if soil_ok:
        taw = 1000 * (inp.field_capacity_pct - inp.wilting_point_pct) / 100 * inp.root_depth_m
        raw = cfg.depletion_fraction_p * taw
        dr_now = min(max(1000 * (inp.field_capacity_pct - inp.soil_moisture_pct) / 100 * inp.root_depth_m, 0.0), taw)
        est.update(taw_mm=taw, raw_mm=raw, depletion_now_mm=dr_now)
        result["method"]["soil"] = "TAW, RAW and root-zone depletion from volumetric FC, PWP, root depth"
        if etc is not None:
            dr_end = min(max(dr_now + etc * period - reff_used, 0.0), taw)
            est["depletion_end_mm"] = dr_end
    else:
        missing.append("soil_water_data")
        if not inp.moisture_is_volumetric:
            result["warnings"].append("Soil moisture was entered as a generic reading; it is not converted to "
                                      "volumetric content or plant-available water.")

    # --- net irrigation requirement ---
    net = basis = None
    if soil_ok and dr_end is not None:
        net, basis = dr_end, "soil_water_balance"
    elif etc is not None:
        net, basis = max(0.0, etc * period - reff_used), "demand_minus_effective_rain"
        result["warnings"].append("No soil-water credit was applied (volumetric FC, PWP and root depth not all given).")
    elif soil_ok:
        net, basis = dr_now, "current_depletion_only"
        result["warnings"].append("ETo not given: only current root-zone depletion is reported; no forward projection.")
    est["net_irrigation_mm"], est["net_basis"] = net, basis
    result["method"]["net"] = basis

    # --- gross requirement and volumes ---
    eff = inp.irrigation_efficiency_pct
    if eff is None:
        missing.append("efficiency")
    est["efficiency_pct"] = eff
    gross = net / (eff / 100) if (net is not None and eff is not None) else None
    est["gross_irrigation_mm"] = gross
    area_ha = facts["area_ha"]
    if area_ha is None:
        missing.append("area")
    est["area_ha"] = area_ha
    est["net_volume_m3"] = depth_to_volume_m3(net, area_ha) if (net is not None and area_ha) else None
    est["gross_volume_m3"] = depth_to_volume_m3(gross, area_ha) if (gross is not None and area_ha) else None
    est["available_water_m3"] = inp.available_water_m3
    ref_vol = est["gross_volume_m3"]
    est["water_coverage_pct"] = (100 * inp.available_water_m3 / ref_vol
                                 if (ref_vol and inp.available_water_m3 is not None) else None)
    est["pump_flow_m3_per_h"] = inp.pump_flow_m3_per_h
    if inp.pump_flow_m3_per_h is None:
        missing.append("pump_flow")

    result["provisional"] = etc is None
    if etc is None:
        result["advisory_reason"] = ("ETo was not supplied, so crop water consumption was NOT calculated. "
                                     "Results are provisional and limited to what the other inputs support.")
    else:
        result["advisory_reason"] = (f"ETc = Kc x ETo = {kc:g} x {inp.eto_mm_day:g} mm/day over "
                                     f"{period} days, minus effective rainfall, using the {basis} basis.")
    return result


def rainfall_scenarios(inp: FieldInputs, rain_values_mm, cfg: Optional[EngineConfig] = None) -> list:
    """Re-run the engine for user-entered rainfall values (illustrative scenarios, not forecasts)."""
    rows = []
    for mm in rain_values_mm:
        r = estimate_water_requirement(FieldInputs(**{**inp.__dict__, "rainfall_mm": mm}), cfg)
        e = r["estimates"]
        rows.append({"rainfall_mm": mm, "effective_rain_mm": e.get("effective_rain_mm"),
                     "net_irrigation_mm": e.get("net_irrigation_mm"), "gross_irrigation_mm": e.get("gross_irrigation_mm"),
                     "valid": r["valid"]})
    return rows


def soil_moisture_scenarios(inp: FieldInputs, moisture_values_pct, cfg: Optional[EngineConfig] = None) -> list:
    """Re-run the engine across varying soil moisture percentages (illustrative scenarios)."""
    rows = []
    for m in moisture_values_pct:
        r = estimate_water_requirement(FieldInputs(**{**inp.__dict__, "soil_moisture_pct": m}), cfg)
        e = r["estimates"]
        rows.append({
            "soil_moisture_pct": m,
            "depletion_now_mm": e.get("depletion_now_mm"),
            "net_irrigation_mm": e.get("net_irrigation_mm"),
            "gross_irrigation_mm": e.get("gross_irrigation_mm"),
            "valid": r["valid"],
        })
    return rows


def water_availability_scenarios(result: dict, available_m3_values) -> list:
    """Compare user-entered water volumes with the gross (or net, if no efficiency) volume needed."""
    e = result.get("estimates", {})
    need = e.get("gross_volume_m3")
    label = "gross"
    if need is None:
        need, label = e.get("net_volume_m3"), "net"
    rows = []
    for v in available_m3_values:
        rows.append({"available_m3": v, "required_m3": need, "basis": label,
                     "coverage_pct": (100 * v / need) if need else None})
    return rows
