# MCP server (AI coach)

The backend includes an [MCP](https://modelcontextprotocol.io) server that gives Claude (or any MCP client) access to your training data and training plan. It uses the same analytics code and database as the dashboard.

## Connecting

The server is served two ways:

- **Streamable HTTP** at `http://<host>:8000/mcp`, mounted in the backend (`MCP_HTTP_ENABLED=1`, the default). To connect from another machine, add its host to `MCP_ALLOWED_HOSTS`.
- **stdio** with `python -m app.mcp_server`. Run it inside the backend container with `docker exec -i`, so the container stays the only process writing to the database.

Setup for Claude Code and Claude Desktop is in the [README](../README.md#ai-coach-mcp).

## Tools

### Training state and analysis

| Tool | Description |
|---|---|
| `get_training_state()` | Current CTL, ATL, TSB, form zone, ramp rate, 7-day trend, weekly volume, FTP status |
| `get_recent_form(weeks)` | Volume by week, key sessions, decoupling trend |
| `get_recent_activities(n, sport)` | Last N activities as one-line summaries, optionally filtered by sport |
| `analyze_workout(activity_id)` | Full breakdown: TSS, NP, IF, decoupling, HR drift, HR and power zones, split outliers |
| `get_activity_streams(activity_id, downsample_to)` | Downsampled HR, power, pace and altitude for one activity |

### Performance

| Tool | Description |
|---|---|
| `predict_race(distance_m, target_date)` | Riegel prediction with confidence interval and tier, optionally checked against a goal date |
| `get_power_curve()` | All-time and 6-week power-duration curve with the CP / W′ fit |

### Training plan

| Tool | Description |
|---|---|
| `assess_upcoming_week()` | Checks the next 7 planned days against current form and ramp rate, with warnings |
| `list_planned_workouts(date_from, date_to)` | Planned workouts in a range (default: today to 4 weeks ahead) |
| `get_planned_workout(workout_id)` | One planned workout, step by step |
| `create_workout(date, sport, title, steps, …)` | Add a structured workout |
| `bulk_create_workouts(workouts)` | Create many workouts at once, e.g. a full training block |
| `update_workout(workout_id, …)` | Edit a planned workout (past ones are frozen) |
| `bulk_update_workouts(updates)` | Apply several changes at once |
| `delete_workout(workout_id)` | Remove a future workout |
| `delete_workouts_in_range(date_from, date_to)` | Remove all future workouts in a range |
| `log_completed_workout(planned_id, activity_id)` | Link a Strava activity to a planned workout |

## Example prompts

- "What's my current training state?" → `get_training_state`
- "How has the last month gone?" → `get_recent_form`
- "Analyse my long run from yesterday." → `get_recent_activities` + `analyze_workout`
- "Why did my heart rate spike around minute 40 of that ride?" → `get_activity_streams`
- "What could I run a half marathon in right now?" → `predict_race`
- "What do I have planned this week?" → `list_planned_workouts`
- "Build me a 12-week 10k block starting next Monday." → `bulk_create_workouts`
- "I'm feeling beat up, can we ease off this week?" → `assess_upcoming_week` + `bulk_update_workouts`

A good way to start a coaching conversation is to ask for your training state and the upcoming week together. That gives Claude your current fitness and your plan in one go.
