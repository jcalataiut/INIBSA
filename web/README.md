# Smart Demand Signals — Web Dashboard

> Dashboard d'alertes comercials per Inibsa. Part del projecte **Smart Demand Signals** (Interhack BCN 2026).

---

## Tecnologia

| Capa | Tecnologia |
|---|---|
| Backend | Python (FastAPI) |
| Frontend | React 19 + TypeScript (Vite) |
| Base de dades | PostgreSQL 16 (Alpine) |
| Mapes | Leaflet + react-leaflet |
| Orquestració | Docker Compose |

---

## Estructura

```
web/
├── backend/
│   ├── main.py                 # Punt d'entrada FastAPI
│   ├── config.py               # Configuració (avui, etc.)
│   ├── database.py             # Inicialització i cache de BD
│   ├── requirements.txt        # Dependències Python
│   ├── Dockerfile
│   ├── routers/                # Endpoints API
│   │   ├── alerts.py
│   │   ├── stats.py
│   │   ├── treated.py
│   │   └── clients.py
│   ├── models/                 # Models de dades
│   └── engine/                 # Motor de càlcul d'alertes
├── frontend/
│   ├── src/                    # Codi font React
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── Dockerfile
├── data/                       # Volum muntat amb els CSVs
└── docker-compose.yml
```

---

## Execució

### Requisits

- Docker + Docker Compose

### Arrancar

```bash
docker compose up --build
```

S'aixequen tres serveis:

| Servei | Port |
|---|---|
| PostgreSQL | 5432 |
| API (FastAPI) | 8000 |
| Frontend (React) | 5173 |

### Endpoints API

| Mètode | Path | Descripció |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/alerts` | Llista d'alertes actives |
| GET | `/api/stats` | Estadístiques agregades |
| GET | `/api/clients` | Cerca i detall de clients |
| POST | `/api/treated` | Marcar alerta com tractada |
| POST | `/api/refresh` | Forçar recàlcul d'alertes |

---

## Desenvolupament

### Backend (sense Docker)

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### Frontend (sense Docker)

```bash
cd frontend
npm install
npm run dev
```

Requereix un PostgreSQL en execució o modificar `backend/config.py` per apuntar a la BD desitjada.
