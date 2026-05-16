from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from database import engine, Base
from routers import overview, resources, snapshots, backup, security, alerts, settings

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hyper-V Monitor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(overview.router)
app.include_router(resources.router)
app.include_router(snapshots.router)
app.include_router(backup.router)
app.include_router(security.router)
app.include_router(alerts.router)
app.include_router(settings.router)

# 靜態前端檔案
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "hv-dashboard")
if os.path.isdir(_FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_index():
        return FileResponse(os.path.join(_FRONTEND_DIR, "HV Dashboard.html"))


@app.get("/health")
def health():
    return {"status": "ok"}
