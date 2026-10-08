from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
