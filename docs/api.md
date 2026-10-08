# REST API

Base URL: `http://localhost:8000`. Interactive docs (Swagger) are served at `/docs`.

Most endpoints accept `lang=de|en` for any text they return. There is no authentication (see the README's privacy section).

## Overview

| Endpoint | Description |
|---|---|
| `GET /healthz` | Health check |
| `GET /api/stats` | Dashboard numbers: CTL, ATL, TSB, weekly TSS and hours, ramp rate, form text, FTP, threshold pace, max HR |
| `GET /api/training-load` | Daily CTL / ATL / TSB history |
| `GET /api/greetings` | Greeting counts from activity descriptions |
| `POST /api/recompute` | Sync from Strava, then recompute analytics. Query: `skip_sync`, `full` |

## Activities

| Endpoint | Description |
|---|---|
| `GET /api/activities` | Paginated activity list, filterable by sport |
| `GET /api/activities/types` | Activity types present in the database |
| `GET /api/activities/{id}` | One activity |
| `GET /api/activities/{id}/streams` | 1 Hz sensor streams (HR, power, speed, altitude, GPS) |
| `GET /api/activities/{id}/laps` | Laps |
| `GET /api/activities/{id}/splits` | Km splits with outliers marked |
| `GET /api/activities/{id}/analytics` | Decoupling, intensity factor, HR drift, zones, split outliers |

## Analytics

| Endpoint | Description |
|---|---|
| `GET /api/weekly-volume` | Weekly volume by sport |
| `GET /api/monthly-stats` | Monthly totals by sport |
| `GET /api/race-predictions` | Riegel predictions with confidence tiers |
| `GET /api/power-curve` | All-time and 6-week power-duration curve, CP / W′ fit |
| `GET /api/time-in-zone` | Weekly hours per HR or power zone. Query: `sport`, `weeks`, `ftp_w` |
| `GET /api/decoupling-timeline` | Decoupling of aerobic (Z2–Z3) activities over time |
| `GET /api/effective-pace` | Pace of aerobic (Z2–Z3) runs over time |
| `GET /api/heatmap` | Simplified GPS tracks and map center |
| `GET /api/segments/cities` | Cities configured in `WIND_CITIES` |
| `GET /api/segments/wind` | Starred segments with current wind. Query: `city` |

## Training plan

| Endpoint | Description |
|---|---|
| `GET /api/training-plan/calendar` | Planned and completed workouts for a month |
| `GET /api/training-plan/workouts` | All planned workouts |
| `GET /api/training-plan/workouts/{id}` | One planned workout with its steps |
| `POST /api/training-plan/workouts` | Create a planned workout |
| `PATCH /api/training-plan/workouts/{id}` | Update a planned workout |
| `DELETE /api/training-plan/workouts/{id}` | Delete a planned workout |

## MCP

`/mcp` serves the MCP server over Streamable HTTP (when `MCP_HTTP_ENABLED=1`). See [mcp.md](mcp.md).
