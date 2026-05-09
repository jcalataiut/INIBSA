from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers import alerts, stats, treated, clients

app = FastAPI(
    title="Smart Demand Signals — Inibsa",
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

@app.get("/api/health")
def health():
    return {"status": "ok"}
