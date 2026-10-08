import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.activities import router as activities_router
from app.api.training_load import router as training_load_router
from app.api.streams_routes import router as streams_router
from app.api.stats import router as stats_router
from app.api.power_curve import router as power_curve_router
from app.api.weekly_volume import router as weekly_volume_router
from app.api.race_predictor import router as race_predictor_router
from app.api.monthly_stats import router as monthly_stats_router
from app.api.activity_analytics import router as activity_analytics_router
from app.api.heatmap import router as heatmap_router
from app.api.segments import router as segments_router
from app.api.decoupling_api import router as decoupling_router
from app.api.time_in_zone import router as time_in_zone_router
from app.api.effective_pace import router as effective_pace_router
from app.api.training_plan import router as training_plan_router
from app.api.recompute import router as recompute_router
from app.api.greetings import router as greetings_router
from app.db.session import init_db

# ── MCP server over Streamable HTTP ──────────────────────────────────────────
# Mounted into this same FastAPI app so one process/one container serves both
# the REST API and the MCP server (single DB writer). Endpoint: <host>:8000/mcp.
# Set MCP_HTTP_ENABLED=0 to disable (e.g. if running the MCP server standalone).
MCP_HTTP_ENABLED = os.getenv("MCP_HTTP_ENABLED", "1") == "1"

if MCP_HTTP_ENABLED:
    from app.mcp_server.server import mcp

    mcp.settings.streamable_http_path = "/"   # so the mount at "/mcp" resolves to /mcp
    mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if MCP_HTTP_ENABLED:
        # Run the MCP session manager for the lifetime of the app. Mounted
        # sub-apps don't get their lifespan run automatically, so wire it here.
        async with mcp.session_manager.run():
            yield
    else:
        yield


app = FastAPI(
    title="StraOliva",
    description="Personal Strava training dashboard API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS_ORIGINS: comma-separated allowed origins, or "*" for any (fine on a
# trusted LAN). Default covers local dev. Set to your server's host/IP in prod.
_cors_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(activities_router, prefix="/api")
app.include_router(training_load_router, prefix="/api")
app.include_router(streams_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(power_curve_router, prefix="/api")
app.include_router(weekly_volume_router, prefix="/api")
app.include_router(race_predictor_router, prefix="/api")
app.include_router(monthly_stats_router, prefix="/api")
app.include_router(activity_analytics_router, prefix="/api")
app.include_router(heatmap_router, prefix="/api")
app.include_router(segments_router, prefix="/api")
app.include_router(decoupling_router, prefix="/api")
app.include_router(time_in_zone_router, prefix="/api")
app.include_router(effective_pace_router, prefix="/api")
app.include_router(training_plan_router, prefix="/api")
app.include_router(recompute_router, prefix="/api")
app.include_router(greetings_router, prefix="/api")

# Mount the MCP Streamable HTTP server at /mcp (after all REST routers).
if MCP_HTTP_ENABLED:
    app.mount("/mcp", mcp_app)
