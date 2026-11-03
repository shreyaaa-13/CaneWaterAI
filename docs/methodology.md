# Methodology (educational prototype)

## Calculations (all in Python, no LLM)
| Quantity | Formula | Units |
|---|---|---|
| ETc | Kc x ETo | mm/day |
| Crop demand | ETc x planning period days | mm |
| Effective rainfall | fraction x user rainfall (mm) | mm |
| TAW | 1000 x (FC - PWP)/100 x root depth | mm (FC, PWP volumetric %, depth m) |
| RAW | p x TAW | mm |
| Depletion now | 1000 x (FC - moisture)/100 x root depth, clamped 0..TAW | mm |
| Depletion end | clamp(now + demand - effective rain, 0, TAW) | mm |
| Net irrigation | depletion end (soil balance) / max(0, demand - eff. rain) (no soil data) / depletion now (no ETo) | mm |
| Gross irrigation | net / (efficiency/100), only if the user gives efficiency | mm |
| Volume | depth x area(ha) x 10 | m3 |
| Duration | gross volume / pump flow | hours |

1 acre = 0.40468564224 ha; 1 m3 = 1000 L.

## Assumptions and thresholds
* **Kc**: Germination 0.40, Grand growth 1.25, Maturity 0.75 follow the sugarcane values in FAO-56 (Table 12); Tillering 0.80 is a **prototype interpolation**. All are editable in the UI. Check against FAO-56 and local data.
* **Effective rainfall fraction 0.80** and **p = 0.65** are configurable prototype assumptions.
* **Stage-age ranges** and **rainfall category bands** only trigger warnings; they never alter inputs or numbers.
* Soil type, weather class and irrigation method are context only. Efficiency is never inferred from method.
* A generic moisture % is not treated as volumetric content or plant-available water; the soil-water balance runs only if the user confirms volumetric data and supplies FC, PWP and root depth.

## Scheduler rules
IRRIGATE_NOW if depletion >= RAW (or projected within a day); SCHEDULE_LATER if projected to reach RAW before the planning period ends (days = (RAW - Dr)/(ETc - rain/period)); DEFER_REASSESS otherwise; heavy unquantified rain downgrades IRRIGATE_NOW to DEFER_REASSESS; no soil data -> REVIEW_PENDING_SOIL_DATA; no data -> INSUFFICIENT_DATA. The planning window is a user-chosen review interval, not an optimal interval.

## Limitations
Single crop coefficient only (no stress or soil-evaporation split); no deep percolation/runoff/capillary rise; ETo and rainfall are manual; validator is keyword/regex based; Hindi/Marathi quality unreviewed; Tamil/Telugu not implemented.
