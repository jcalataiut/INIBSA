import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from config import DATABASE_URL

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
                data_alerta DATE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_cache_data ON alertes_cache(data_alerta)
        """))

def is_db_empty() -> bool:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM ventas"))
        count = result.scalar()
        return count == 0

def load_csv_to_db(csv_path: str):
    engine = get_engine()
    df = pd.read_csv(csv_path, low_memory=False)
    df.columns = [c.lower().replace(" ", "_").replace(".", "") for c in df.columns]
    if "id_cliente" in df.columns:
        df["id_cliente"] = df["id_cliente"].astype("Int64")
    if "cod_postal" in df.columns:
        df["cod_postal"] = df["cod_postal"].astype(str)
    df.to_sql("ventas", engine, if_exists="append", index=False, method="multi")
    return len(df)

def clear_cache(today: str):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM alertes_cache WHERE data_alerta = :today"), {"today": today})
