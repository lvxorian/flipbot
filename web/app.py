from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from web.routers.views import router

app = FastAPI(title="FlipBot", description="Realitní monitoring a analýza")

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(router)
