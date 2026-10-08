"""Strava API client with automatic token refresh and rate-limit-friendly delays."""

import time

import httpx

from app.config import settings
from app.db.models import StravaAuth
from app.db.session import get_db

_BASE = "https://www.strava.com/api/v3"
_TOKEN_URL = "https://www.strava.com/oauth/token"
_DELAY = 0.5  # seconds between requests — well within 100 req/15 min


class StravaClient:
    def _get_valid_token(self) -> str:
        with get_db() as db:
            auth = db.query(StravaAuth).first()
            if auth is None:
                raise RuntimeError("Not authenticated. Run `strava-dash auth` first.")

            if auth.expires_at < time.time() + 60:
                resp = httpx.post(
                    _TOKEN_URL,
                    data={
                        "client_id": settings.strava_client_id,
                        "client_secret": settings.strava_client_secret,
                        "grant_type": "refresh_token",
                        "refresh_token": auth.refresh_token,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                auth.access_token = data["access_token"]
                auth.refresh_token = data["refresh_token"]
                auth.expires_at = data["expires_at"]

            return auth.access_token

    def _get(self, path: str, **params) -> dict | list:
        token = self._get_valid_token()
        time.sleep(_DELAY)
        for attempt in range(3):
            resp = httpx.get(
                f"{_BASE}{path}",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=30,
            )
            if resp.status_code == 429:
                wait = 900  # 15 minutes — reset the short-term window
                print(f"\nRate limited by Strava. Waiting {wait // 60} min …")
                time.sleep(wait)
                token = self._get_valid_token()
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError("Strava rate limit exceeded after 3 retries")

    # ── Athlete ──────────────────────────────────────────────────────────────

    def get_athlete(self) -> dict:
        return self._get("/athlete")

    # ── Activities ───────────────────────────────────────────────────────────

    def get_activities(
        self,
        after: int | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> list[dict]:
        params = {"page": page, "per_page": per_page}
        if after is not None:
            params["after"] = after
        return self._get("/athlete/activities", **params)

    def get_activity(self, activity_id: int) -> dict:
        return self._get(f"/activities/{activity_id}")

    # ── Streams ──────────────────────────────────────────────────────────────

    _STREAM_TYPES = "time,heartrate,watts,cadence,latlng,altitude,velocity_smooth"

    def get_activity_streams(self, activity_id: int) -> dict:
        return self._get(
            f"/activities/{activity_id}/streams",
            keys=self._STREAM_TYPES,
            key_by_type="true",
        )

    # ── Laps ─────────────────────────────────────────────────────────────────

    def get_activity_laps(self, activity_id: int) -> list[dict]:
        return self._get(f"/activities/{activity_id}/laps")

    # ── Segments ─────────────────────────────────────────────────────────────

    def get_starred_segments(self, page: int = 1, per_page: int = 200) -> list[dict]:
        return self._get("/segments/starred", page=page, per_page=per_page)

    def get_segment(self, segment_id: int) -> dict:
        return self._get(f"/segments/{segment_id}")
