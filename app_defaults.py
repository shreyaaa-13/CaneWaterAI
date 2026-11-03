"""Centralized state defaults and helpers for CaneWater AI."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, Any
from water_requirement_engine import EngineConfig, FieldInputs, STAGES

DEFAULTS: Dict[str, Any] = {
    "current_page": "Overview",
    "demo_mode_active": False,
    "demo_preset_loaded": "default",
    # Crop parameters
    "f_age": 5.0,
    "f_stage": "Grand growth",
    "f_use_pdate": False,
    "f_pdate": date.today() - timedelta(days=152),
    # Soil parameters
    "f_soil": "Medium",
    "f_moist": 30.0,
    "f_vol": False,
    "f_use_soilwater": False,
    "f_fc": 30.0,
    "f_pwp": 15.0,
    "f_root": 0.5,
    # Weather parameters
    "f_weather": "Warm",
    "f_rain_cat": "None",
    "f_use_rain": False,
    "f_rain_mm": 0.0,
    "f_use_eto": False,
    "f_eto": 4.0,
    # Irrigation parameters
    "f_method": "Drip",
    "f_use_eff": False,
    "f_eff": 70.0,
    "f_use_area": False,
    "f_area": 1.0,
    "f_area_unit": "ha",
    "f_use_water": False,
    "f_water": 100.0,
    "f_use_flow": False,
    "f_flow": 20.0,
    # Engine configuration assumptions
    "c_period": 7,
    "c_reff": 0.80,
    "c_p": 0.65,
    "c_kc_Germination": 0.40,
    "c_kc_Tillering": 0.80,
    "c_kc_Grand growth": 1.25,
    "c_kc_Maturity": 0.75,
    # GenAI and Session stats
    "language": "en",
    "explanation": None,
    "stats": {
        "runs": 0,
        "validation_failures": 0,
        "corrections": 0,
        "api_failures": 0,
        "fallbacks": 0,
        "attempts": [],
    },
}


def build_config_from_state(state: Dict[str, Any]) -> EngineConfig:
    """Build an EngineConfig instance from session state."""
    return EngineConfig(
        kc_by_stage={s: state.get(f"c_kc_{s}", 1.0) for s in STAGES},
        effective_rain_fraction=float(state.get("c_reff", 0.80)),
        depletion_fraction_p=float(state.get("c_p", 0.65)),
        planning_period_days=int(state.get("c_period", 7)),
    )


def build_inputs_from_state(state: Dict[str, Any]) -> FieldInputs:
    """Build a FieldInputs instance from session state."""
    soil = bool(state.get("f_use_soilwater", False))
    return FieldInputs(
        crop_age_months=state.get("f_age"),
        growth_stage=state.get("f_stage", "Grand growth"),
        planting_date=state.get("f_pdate") if state.get("f_use_pdate") else None,
        soil_type=state.get("f_soil", "Medium"),
        soil_moisture_pct=state.get("f_moist"),
        moisture_is_volumetric=bool(state.get("f_vol") and soil),
        field_capacity_pct=state.get("f_fc") if soil else None,
        wilting_point_pct=state.get("f_pwp") if soil else None,
        root_depth_m=state.get("f_root") if soil else None,
        weather=state.get("f_weather", "Warm"),
        rainfall_category=state.get("f_rain_cat", "None"),
        rainfall_mm=state.get("f_rain_mm") if state.get("f_use_rain") else None,
        eto_mm_day=state.get("f_eto") if state.get("f_use_eto") else None,
        irrigation_method=state.get("f_method", "Drip"),
        irrigation_efficiency_pct=state.get("f_eff") if state.get("f_use_eff") else None,
        area=state.get("f_area") if state.get("f_use_area") else None,
        area_unit=state.get("f_area_unit", "ha"),
        available_water_m3=state.get("f_water") if state.get("f_use_water") else None,
        pump_flow_m3_per_h=state.get("f_flow") if state.get("f_use_flow") else None,
    )
