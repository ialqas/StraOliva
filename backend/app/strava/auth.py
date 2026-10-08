"""OAuth flow for the Strava API (one-time setup via CLI)."""

import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from app.config import settings
from app.db.models import StravaAuth
from app.db.session import get_db

_SCOPES = "read_all,activity:read_all"
_AUTH_URL = "https://www.strava.com/oauth/authorize"
_TOKEN_URL = "https://www.strava.com/oauth/token"


def _build_auth_url(redirect_port: int) -> str:
    params = {
        "client_id": settings.strava_client_id,
        "response_type": "code",
        "redirect_uri": f"http://localhost:{redirect_port}/auth/callback",
        "approval_prompt": "force",
        "scope": _SCOPES,
    }
    return f"{_AUTH_URL}?{urlencode(params)}"


class _CallbackHandler(BaseHTTPRequestHandler):
    auth_code: str | None = None
    error: str | None = None

    def do_GET(self) -> None:
        if not self.path.startswith("/auth/callback"):
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(urlparse(self.path).query)

        if "code" in params:
            _CallbackHandler.auth_code = params["code"][0]
            body = b"<h1>Authorization successful!</h1><p>You can close this tab.</p>"
            self.send_response(200)
        else:
            _CallbackHandler.error = params.get("error", ["unknown"])[0]
            body = b"<h1>Authorization failed.</h1><p>Check the terminal.</p>"
            self.send_response(400)

        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass  # suppress request logs during auth


def run_oauth_flow() -> dict:
    """Open the browser for Strava OAuth and block until the code arrives."""
    port = settings.strava_redirect_port
    _CallbackHandler.auth_code = None
    _CallbackHandler.error = None

    auth_url = _build_auth_url(port)
    print(f"\nOpening browser for Strava authorization …")
    print(f"If the browser does not open, navigate to:\n{auth_url}\n")

    server = HTTPServer(("localhost", port), _CallbackHandler)
    webbrowser.open(auth_url)
    server.serve_forever()  # blocks until _CallbackHandler calls server.shutdown()

    if _CallbackHandler.error:
        raise RuntimeError(f"Strava OAuth error: {_CallbackHandler.error}")
    if not _CallbackHandler.auth_code:
        raise RuntimeError("No authorization code received.")

    resp = httpx.post(
        _TOKEN_URL,
        data={
            "client_id": settings.strava_client_id,
            "client_secret": settings.strava_client_secret,
            "code": _CallbackHandler.auth_code,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def store_tokens(token_data: dict) -> None:
    """Upsert the token response into the singleton strava_auth row."""
    athlete = token_data.get("athlete", {})
    with get_db() as db:
        auth = db.query(StravaAuth).first()
        if auth is None:
            auth = StravaAuth(id=1)
            db.add(auth)
        auth.access_token = token_data["access_token"]
        auth.refresh_token = token_data["refresh_token"]
        auth.expires_at = token_data["expires_at"]
        auth.athlete_id = str(athlete.get("id", ""))
        auth.scope = token_data.get("scope", _SCOPES)
