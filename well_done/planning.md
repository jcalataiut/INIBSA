# Smart Demand Signals — Refactor Well Done

## Arquitectura: Docker Compose · FastAPI · Vite · PostgreSQL

```
┌─────────────────────────────────────────────────────────┐
│                   Docker Compose                         │
│                                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────┐  │
│  │   Frontend    │   │   Backend    │   │ PostgreSQL │  │
│  │   (Vite +     │──▶│  (FastAPI)   │──▶│  (DB)      │  │
│  │    React)     │   │              │   │            │  │
│  │   :5173       │   │   :8000      │   │   :5432    │  │
│  └──────────────┘   └──────────────┘   └────────────┘  │
│                           │                             │
│                    ┌──────┴──────┐                      │
│                    │  CSV Loader  │                      │
│                    │  (seed.py)   │                      │
│                    └──────┘──────┘                      │
│                           │                             │
│                    ┌──────┴──────┐                      │
│                    │  Engine      │                      │
│                    │  (lògica     │                      │
│                    │   existent)  │                      │
│                    └─────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

## Estructura de fitxers

```
well_done/
├── docker-compose.yml          # Orquestra els 3 serveis
├── Dockerfile.backend          # Backend build
├── Dockerfile.frontend         # Frontend build
├── .env                        # Variables d'entorn
│
├── backend/
│   ├── requirements.txt        # fastapi, uvicorn, pandas, numpy, psycopg2
│   ├── main.py                 # FastAPI app + endpoints
│   ├── config.py               # Config (DB URL, paths, thresholds)
│   ├── database.py             # Connection pool, init_db, CSV seeding
│   ├── models/
│   │   └── schemas.py          # Pydantic models per alerts, segments
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── commodities_engine.py   # ← Lògica existent adaptada (llegeix de DB)
│   │   ├── segmenter.py            # Lògica de segmentació extreta
│   │   └── alerts.py               # Generació d'alertes + priorització
│   └── routers/
│       ├── alerts.py               # GET /api/alerts?today=&family=
│       ├── segments.py             # GET /api/segments
│       ├── clients.py              # GET /api/clients/{id}
│       ├── stats.py                # GET /api/stats (resums, gaps)
│       └── treated.py              # POST/PUT/DELETE /api/treated
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts           # Fetch wrapper (alerts, segments, stats)
│       ├── components/
│       │   ├── AlertCard.tsx        # Targeta d'alerta individual
│       │   ├── AlertList.tsx        # Llista amb filtres
│       │   ├── Filters.tsx          # Filtres (tipus, segment, urgència)
│       │   ├── MetricsBar.tsx       # Mètriques superiors
│       │   ├── FugatsTab.tsx        # Pestanya de fugats
│       │   └── Header.tsx           # Logo + data selector
│       └── types/
│           └── index.ts             # TypeScript interfaces
│
├── scripts/
│   ├── seed_db.py               # Carrega master_*.csv a PostgreSQL
│   └── seed_db.sh               # Wrapper per cridar seed_db.py al container
│
└── data/                        # Muntat com a volum (o copiat al build)
    ├── master_commodities.csv
    └── master_technicals.csv
```

## Base de dades (PostgreSQL)

### Taula `ventas` — dades de venda unificades
| Columna | Tipus | Notes |
|---|---|---|
| id | SERIAL PK | |
| num_fact | VARCHAR | |
| fecha | DATE | Indexat |
| id_cliente | INTEGER | Indexat |
| id_producto | INTEGER | |
| bloque_analitico | VARCHAR | |
| categoria_h | VARCHAR | |
| familia_h | VARCHAR | |
| familia_potencial | VARCHAR | |
| es_commodity | BOOLEAN | |
| cod_postal | VARCHAR | |
| provincia | VARCHAR | |
| unidades | NUMERIC | |
| valores_h | NUMERIC | |
| es_devolucion | BOOLEAN | |
| en_campana | BOOLEAN | |
| potencial_eur_anual | NUMERIC | |
| anyo | INTEGER | |
| mes | INTEGER | |
| trimestre | INTEGER | |
| dia_semana | INTEGER | |
| dia_anyo | INTEGER | |

### Taula `treated_alerts` — persistència d'alertes tractades
| Columna | Tipus | Notes |
|---|---|---|
| id | SERIAL PK | |
| client_familia_tipus | VARCHAR UNIQUE | `{id_cliente}_{familia}_{tipus}` |
| treated_date | DATE | |
| created_at | TIMESTAMP | |

### Taula `alertes_cache` — cache del daily run
| Columna | Tipus |
|---|---|
| id | SERIAL PK |
| id_cliente | INTEGER |
| ... | (totes les columnes de l'alerta) |
| data_alerta | DATE |
| prioritat | NUMERIC |

## API Endpoints (FastAPI)

```
GET  /api/alerts?today=2025-12-01&family=&segment=&tipus=&urgencia=&pendents=
      → Llista d'alertes prioritzades (del cache o genera si no existeix)

GET  /api/alerts/{id}            → Alerta individual

GET  /api/segments?today=       → Segmentació completa (client, família, segment)

GET  /api/clients/{id}          → Info client + històric + alertes

GET  /api/stats?today=          → Mètriques: #alertes, gap total, per segment

POST /api/treated               → Marca alerta com a tractada
      {"id_cliente": 4523, "familia": "Anestesia", "tipus_alerta": "risc_fuga"}

DELETE /api/treated/{id}        → Desmarcar alerta tractada

GET  /api/treated               → Llista d'alertes tractades (actives)

POST /api/engine/run?today=     → Forçar execució del motor (esborra i regenera cache)
```

## Frontend (Vite + React + TypeScript)

### Pàgines / Vistes
- **Daily Briefing** (principal): llista d'alertes filtrable, botons ✅ Tractada
- **Fugats**: pestanya separada amb clients > 1 any sense comprar
- **Stats**: resum visual amb mètriques agregades

### Components
- `Header`: selector de data + logo
- `MetricsBar`: 4 targetes (Alertes, Pendents, Gap Total, Alta Urgència)
- `Filters`: multiselect per tipus, segment, urgència
- `AlertList`: llista de targetes amb scroll infinit o paginació
- `AlertCard`: targeta individual amb color segons tipus
- `FugatsTab`: llista de fugats amb botó "Recuperat"

## CSV Loader (seed_db.py)

```python
# Llegeix master_commodities.csv i master_technicals.csv
# Les insereix a PostgreSQL (taula ventas)
# Idempotent: TRUNCATE + INSERT si --force, sino només si taula buida
# Ús: python scripts/seed_db.py [--force]
```

## Docker Compose

```yaml
services:
  db:
    image: postgres:16
    volumes: pgdata:/var/lib/postgresql/data
    env: POSTGRES_DB=inibsa, POSTGRES_USER=inibsa, POSTGRES_PASSWORD=inibsa
    ports: 5432:5432
    healthcheck: pg_isready

  backend:
    build: Dockerfile.backend
    depends_on: db (condition: service_healthy)
    ports: 8000:8000
    volumes: ./data:/app/data  # per CSV loading
    command: >
      sh -c "python scripts/seed_db.py && uvicorn main:app --host 0.0.0.0 --port 8000"

  frontend:
    build: Dockerfile.frontend
    depends_on: backend
    ports: 5173:5173
```

## Flux d'execució

1. `docker compose up -d`
2. PostgreSQL arrenca → healthcheck OK
3. Backend arrenca → seed_db.py comprova si DB buida → carrega CSV a PostgreSQL
4. Backend serveix FastAPI a :8000
5. Frontend arrenca a :5173, es connecta al backend via API
6. Usuari obre http://localhost:5173 → veu el Daily Briefing
7. Usuari selecciona data → frontend crida GET /api/alerts?today=...
8. Backend comprova cache per today → si no existeix, executa engine → guarda cache → retorna
9. Usuari marca alerta com a tractada → POST /api/treated
10. Cada dia, el motor es pot executar manualment o amb un cron/scheduler dins el backend

## Tecnologies

| Capa | Tecnologia | Per què |
|---|---|---|
| DB | PostgreSQL 16 | Madura, potent, amb Docker |
| Backend | FastAPI (Python) | Reutilitza la lògica existent, rendiment alt, OpenAPI automàtic |
| Frontend | Vite + React + TypeScript | Modern, ràpid, tipat |
| Estil | TailwindCSS o CSS Modules | Lleuger, net |
| Orquestració | Docker Compose | Simple, reproducible |

## Migració des del codi actual

1. Copiar `commodities_engine.py` → `backend/engine/commodities_engine.py`
   - Modificar `load_data()` perquè llegeixi de PostgreSQL en lloc de CSV
   - La resta de lògica (segmentació, alertes, priorització) es manté idèntica
2. `daily_briefing.py` Streamlit → es substitueix per complet amb React
3. `treated_alerts.json` → es substitueix per taula PostgreSQL `treated_alerts`
4. Streamlit ja no cal → s'elimina de dependències

## Per fer (next steps)

- [ ] Backend: requirements.txt + config.py + database.py
- [ ] Backend: adaptar engine per llegir de PostgreSQL
- [ ] Backend: routers API (alerts, segments, clients, stats, treated)
- [ ] Backend: main.py amb FastAPI app
- [ ] Scripts: seed_db.py
- [ ] Frontend: Vite + React scaffolding
- [ ] Frontend: components (Header, AlertCard, AlertList, Filters, etc.)
- [ ] Frontend: API client + tipus
- [ ] Docker: Dockerfile.backend, Dockerfile.frontend
- [ ] Docker: docker-compose.yml
- [ ] Test: `docker compose up` i verificació
