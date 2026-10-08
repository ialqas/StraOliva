# Algorithm notes

How StraOliva calculates its numbers. The code is in `backend/app/analytics/`: pure functions with no database or HTTP access, shared by the REST API and the MCP server.

## Athlete values

| Value | Auto-detection |
|---|---|
| **FTP** | Best 20 min power of the last 90 days × 0.95. Only rises. |
| **Threshold pace** | Fastest 20 min of a hard run (≥ 85 % of max HR) in the last 60 days × 0.95 |
| **Max HR** | Highest heart rate held for ≥ 10 s in the last 12 months (filters sensor spikes). Only rises. |

Any of them can be pinned in `.env` (`FTP_W`, `THRESHOLD_PACE_MS`, `MAX_HR`).

## Training Stress Score (TSS)

- **Bike:** `duration_s × NP × IF / (FTP × 3600) × 100`, with `IF = NP / FTP`
- **Run (rTSS):** `duration_s × (NGP / threshold pace)² / 3600 × 100`
- **Fallback (hrTSS):** TRIMP-based, using heart-rate reserve (`REST_HR` to max HR), for activities without power or pace

## Fitness, fatigue, form

- **CTL** (fitness): 42-day exponentially weighted average of daily TSS
- **ATL** (fatigue): 7-day exponentially weighted average of daily TSS
- **TSB** (form): CTL − ATL. Race-ready is roughly +5 to +25.
- **Ramp rate:** CTL change per week over the last 28 days

## Zones

**Heart rate**, % of max HR:

| Zone | Range | Name |
|---|---|---|
| Z1 | 50–60 % | Very light |
| Z2 | 60–70 % | Endurance |
| Z3 | 70–80 % | Aerobic |
| Z4 | 80–90 % | Threshold |
| Z5 | 90–100 % | VO₂max |

Time below 50 % counts as Z1, time above max HR as Z5.

**Power** (Coggan), % of FTP: Z1 < 55, Z2 55–75, Z3 75–90, Z4 90–105, Z5 105–120, Z6 120–150, Z7 > 150.

**Run pace** (after Friel), % of threshold pace (time per km; more than 100 % is slower): Z1 > 129, Z2 114–129, Z3 106–114, Z4 97–106, Z5 90–97, Z6 < 90.

## Race predictions (Riegel)

- `T2 = T1 × (D2 / D1)^1.06`, applied to best efforts in the chosen lookback window
- Confidence tiers: **high** (≥ 3 similar runs), **medium** (1–2), **low** (extrapolated), **no data**
- Half marathon needs a long run ≥ 15 km, marathon ≥ 25 km

## Power-duration curve and CP / W′

- Best mean power for each duration, all-time and the last 6 weeks
- Hyperbolic model `P(t) = CP + W′ / t`, fitted with `scipy.optimize.curve_fit` on best efforts from 3 to 60 min
- Only drawn from 3 min upwards; the model diverges at short durations

## Aerobic decoupling

- Only activities ≥ 45 min whose average HR is in Z2–Z3 (60–80 % of max HR)
- The first 10 min are skipped as warm-up, the rest is split into two halves
- `ratio = output / HR` (power for bikes, speed for runs)
- `decoupling = (ratio_first − ratio_second) / ratio_first × 100`
- Below 5 % means a good aerobic base, above 7 % a limited one (Friel)

## Effective pace

Pace of runs ≥ 4 km whose average HR is in Z2–Z3. Getting faster at the same heart rate is the clearest sign of aerobic progress. The trend is a linear fit in seconds per km per month.

## Split outliers

Km splits more than 1.5 standard deviations from the median are marked as slow or fast.

## Wind

- Current wind from the DWD (German weather service) through [Bright Sky](https://brightsky.dev)
- Each segment's bearing (first to last GPS point) is compared with the wind direction, giving strong tailwind, tailwind, crosswind, slight headwind or headwind
- Loop segments (start ≈ end) are skipped
