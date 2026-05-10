from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db, clear_cache
from backend.config import today_str
from backend.routers import alerts, stats, treated, clients

app = FastAPI(
    title="Senyals de Demanda Intel·ligents — Inibsa",
    description="API del sistema d'alertes comercials per Inibsa",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts.router)
app.include_router(stats.router)
app.include_router(treated.router)
app.include_router(clients.router)

@app.on_event("startup")
def startup():
    init_db()
    clear_cache(today_str())

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/refresh")
def refresh():
    from backend.database import clear_cache, ensure_cache
    from backend.config import today_str
    today = today_str()
    clear_cache(today)
    ensure_cache(today, force=True)
    return {"status": "refreshed", "today": today}
