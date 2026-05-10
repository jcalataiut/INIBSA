import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from backend.config import DATABASE_URL

_engine: Engine | None = None

def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5)
    return _engine

def init_db():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ventas (
                id SERIAL PRIMARY KEY,
                num_fact VARCHAR(50),
                fecha DATE NOT NULL,
                id_cliente INTEGER NOT NULL,
                id_producto INTEGER,
                bloque_analitico VARCHAR(50),
                categoria_h VARCHAR(50),
                familia_h VARCHAR(50),
                familia_potencial VARCHAR(50),
                es_commodity BOOLEAN,
                cod_postal VARCHAR(20),
                provincia VARCHAR(100),
                unidades NUMERIC,
                valores_h NUMERIC,
                es_devolucion BOOLEAN DEFAULT FALSE,
                en_campana BOOLEAN DEFAULT FALSE,
                potencial_eur_anual NUMERIC,
                anyo INTEGER,
                mes INTEGER,
                trimestre INTEGER,
                dia_semana INTEGER,
                dia_anyo INTEGER
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ventas_cliente ON ventas(id_cliente)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ventas_familia ON ventas(familia_potencial)
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS treated_alerts (
                id SERIAL PRIMARY KEY,
                client_familia_tipus VARCHAR(255) UNIQUE NOT NULL,
                id_cliente INTEGER NOT NULL,
                familia_potencial VARCHAR(50) NOT NULL,
                tipus_alerta VARCHAR(50) NOT NULL,
                treated_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alertes_cache (
                id SERIAL PRIMARY KEY,
                id_cliente INTEGER NOT NULL,
                provincia VARCHAR(100),
                cod_postal VARCHAR(20),
                city VARCHAR(120),
                latitude NUMERIC,
                longitude NUMERIC,
                familia_potencial VARCHAR(50),
                segment VARCHAR(20),
                segment_anterior VARCHAR(20),
                tipus_alerta VARCHAR(50),
                urgencia VARCHAR(20),
                canal VARCHAR(20),
                share_12m NUMERIC,
                potencial_anual_eur NUMERIC,
                euros_12m NUMERIC,
                gap_eur NUMERIC,
                dies_sense_compra INTEGER,
                num_intervals INTEGER,
                cicle_mig_dies NUMERIC,
                cicle_std_dies NUMERIC,
                dies_retard INTEGER,
                z_score NUMERIC,
                proxim_pedido_esperat VARCHAR(20),
                dies_stock NUMERIC,
                prioritat NUMERIC,
                motiu TEXT,
                share_velocity NUMERIC,
                share_alerta VARCHAR(20),
                geo_neighbor_count INTEGER,
                geo_neighbor_avg_share NUMERIC,
                geo_share_gap NUMERIC,
                data_alerta DATE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("ALTER TABLE alertes_cache ADD COLUMN IF NOT EXISTS cod_postal VARCHAR(20)"))
        conn.execute(text("ALTER TABLE alertes_cache ADD COLUMN IF NOT EXISTS city VARCHAR(120)"))
        conn.execute(text("ALTER TABLE alertes_cache ADD COLUMN IF NOT EXISTS latitude NUMERIC"))
        conn.execute(text("ALTER TABLE alertes_cache ADD COLUMN IF NOT EXISTS longitude NUMERIC"))
        conn.execute(text("ALTER TABLE alertes_cache ADD COLUMN IF NOT EXISTS geo_neighbor_count INTEGER"))
        conn.execute(text("ALTER TABLE alertes_cache ADD COLUMN IF NOT EXISTS geo_neighbor_avg_share NUMERIC"))
        conn.execute(text("ALTER TABLE alertes_cache ADD COLUMN IF NOT EXISTS geo_share_gap NUMERIC"))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_cache_data ON alertes_cache(data_alerta)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_cache_cliente ON alertes_cache(id_cliente)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_cache_prioritat ON alertes_cache(data_alerta, prioritat DESC)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_treated_date ON treated_alerts(treated_date)
        """))

def is_db_empty() -> bool:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM ventas"))
        count = result.scalar()
        return count == 0

def load_csv_to_db(csv_path: str):
    engine = get_engine()
    total_len = 0
    for df in pd.read_csv(csv_path, low_memory=False, chunksize=10000):
        df.columns = [c.lower().replace(" ", "_").replace(".", "_") for c in df.columns]
        if "id_cliente" in df.columns:
            df["id_cliente"] = df["id_cliente"].astype("Int64")
        if "cod_postal" in df.columns:
            df["cod_postal"] = df["cod_postal"].astype(str)
        for col in ["es_commodity", "es_devolucion", "en_campana"]:
            if col in df.columns:
                df[col] = df[col].astype(bool)
        df.to_sql("ventas", engine, if_exists="append", index=False, chunksize=1000)
        total_len += len(df)
    return total_len

def clear_cache(today: str):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM alertes_cache WHERE data_alerta = :today"), {"today": today})

COLS_CACHE = [
    "id_cliente", "provincia", "cod_postal", "city", "latitude", "longitude", "familia_potencial", "segment",
    "segment_anterior", "tipus_alerta", "urgencia", "canal",
    "share_12m", "potencial_anual_eur", "euros_12m", "gap_eur",
    "dies_sense_compra", "num_intervals", "cicle_mig_dies",
    "cicle_std_dies", "dies_retard", "z_score",
    "proxim_pedido_esperat", "dies_stock", "prioritat", "motiu",
    "share_velocity", "share_alerta", "geo_neighbor_count", "geo_neighbor_avg_share", "geo_share_gap",
]

def ensure_cache(today_str: str, family: str | None = None):
    from backend.engine.commodities_engine import run
    engine = get_engine()
    with engine.connect() as conn:
        cached = conn.execute(
            text("SELECT COUNT(*) FROM alertes_cache WHERE data_alerta = :today"),
            {"today": today_str}
        ).scalar()
        geo_ready = conn.execute(
            text("""
                SELECT COUNT(*) FROM alertes_cache
                WHERE data_alerta = :today
                  AND (tipus_alerta = 'geografica' OR cod_postal IS NOT NULL)
            """),
            {"today": today_str}
        ).scalar()
    if cached > 0 and geo_ready > 0:
        return
    clear_cache(today_str)
    try:
        alerts_df, _ = run(today=today_str, verbose=False)
    except Exception:
        alerts_df = pd.DataFrame()
    if alerts_df.empty:
        return
    alerts_df = alerts_df.replace({np.nan: None})
    for c in COLS_CACHE:
        if c not in alerts_df.columns:
            alerts_df[c] = None
    alerts_df["data_alerta"] = today_str
    alerts_df[COLS_CACHE + ["data_alerta"]].to_sql(
        "alertes_cache", engine, if_exists="append", index=False, method="multi"
    )
    active_keys = set(
        f"{r['id_cliente']}_{r['familia_potencial']}_{r['tipus_alerta']}"
        for _, r in alerts_df.iterrows()
    )
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT client_familia_tipus FROM treated_alerts")
        ).all()
        to_remove = [row[0] for row in existing if row[0] not in active_keys]
        if to_remove:
            conn.execute(
                text("DELETE FROM treated_alerts WHERE client_familia_tipus = ANY(:keys)"),
                {"keys": to_remove}
            )
