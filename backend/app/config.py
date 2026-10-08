from pathlib import Path
from pydantic_settings import BaseSettings

# The .env lives next to this file (backend/app/.env  or  backend/.env).
# Search both so the CLI works regardless of the working directory.
_HERE = Path(__file__).parent          # backend/app/
_ENV_CANDIDATES = [
    _HERE / ".env",                    # backend/app/.env  (less common)
    _HERE.parent / ".env",             # backend/.env      (canonical)
    Path.cwd() / ".env",               # wherever the user runs from
    _HERE.parent.parent / ".env",      # repo root (the one docker compose reads)
]
_ENV_FILE = next((p for p in _ENV_CANDIDATES if p.exists()), _HERE.parent / ".env")


class Settings(BaseSettings):
    db_path: str = "/data/strava.db"
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_port: int = 8888
    backend_port: int = 8000

    # Analytics — set in .env to pin a value; leave empty (or 0) to auto-detect
    # it from recent training (see app/sync/recompute.py).
    ftp_w: int = 0                   # 0 = auto: best 20 min of the last 90 days × 0.95 (only rises)
    threshold_pace_ms: float = 0.0   # 0 = auto: fastest hard 20–75 min run of the last 60 days
    rest_hr: int = 40
    max_hr: int = 0                  # 0 = auto: highest HR held ≥10 s (only rises)

    # Wind page city switcher: "Name:lat:lng" pairs, comma-separated,
    # e.g. "Munich:48.14:11.58,Berlin:52.52:13.40". Empty = wind per segment location.
    wind_cities: str = ""

    # Heatmap start position, "lat:lng" (e.g. "48.14:11.58"). Empty = center of
    # the area with the most activities.
    heatmap_center: str = ""

    # env_ignore_empty: `FTP_W=` in .env means "not set" instead of failing to parse
    model_config = {"env_file": str(_ENV_FILE), "env_file_encoding": "utf-8", "env_ignore_empty": True}


settings = Settings()
