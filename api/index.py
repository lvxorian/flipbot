import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DATA_EXPORT_PATH", str(BASE_DIR / "data" / "data.json"))

from fastapi import Request
from fastapi.responses import JSONResponse
from web.app import app


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "path": str(request.url.path),
        },
    )


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "data_file": os.environ.get("DATA_EXPORT_PATH", "not set"),
        "data_exists": Path(os.environ.get("DATA_EXPORT_PATH", "")).exists(),
    }
