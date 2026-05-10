import pandas as pd
import numpy as np
from fastapi import APIRouter, Query
from sqlalchemy import text
from backend.database import get_engine, ensure_cache
from backend.models.schemas import AlertaOut
from backend.config import today_str

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

def get_treated_set(today: str) -> set:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT client_familia_tipus FROM treated_alerts WHERE treated_date <= :today"),
            {"today": today}
        )
        return {row[0] for row in result}

def make_cache_key(row) -> str:
    return f"{row['id_cliente']}_{row['familia_potencial']}_{row['tipus_alerta']}"

def v(val, default=None):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return default
    return val

@router.get("")
def get_alerts(
    today: str = Query(default_factory=today_str),
    family: str | None = Query(None),
    segment: str | None = Query(None),
    tipus: str | None = Query(None),
    urgencia: str | None = Query(None),
    pendents: bool = Query(False),
):
    engine = get_engine()
    today_str = today if isinstance(today, str) else today.strftime("%Y-%m-%d")

    ensure_cache(today_str)

    treated_set = get_treated_set(today_str)

    query = "SELECT * FROM alertes_cache WHERE data_alerta = :today"
    params = {"today": today_str}
    if family:
        query += " AND familia_potencial = :family"
        params["family"] = family
    if segment:
        query += " AND segment = :segment"
        params["segment"] = segment
    if tipus:
        query += " AND tipus_alerta = :tipus"
        params["tipus"] = tipus
    if urgencia:
        query += " AND urgencia = :urgencia"
        params["urgencia"] = urgencia

    query += """
      ORDER BY
        CASE urgencia
          WHEN 'critica' THEN 4
          WHEN 'alta' THEN 3
          WHEN 'mitjana' THEN 2
          WHEN 'baixa' THEN 1
          ELSE 0
        END DESC,
        gap_eur DESC NULLS LAST
    """

    df = pd.read_sql(text(query), engine, params=params)
    df = df.replace({np.nan: None, pd.NA: None})

    alerts = []
    for _, row in df.iterrows():
        key = make_cache_key(row)
        alert = AlertaOut(
            id_cliente=int(row["id_cliente"]),
            provincia=row.get("provincia") or "",
            familia_potencial=row["familia_potencial"],
            segment=row["segment"],
            tipus_alerta=row["tipus_alerta"],
            urgencia=row["urgencia"],
            canal=row["canal"],
            share_12m=float(v(row["share_12m"], 0)),
            potencial_anual_eur=float(v(row["potencial_anual_eur"], 0)),
            euros_12m=float(v(row["euros_12m"], 0)),
            gap_eur=float(v(row["gap_eur"], 0)),
            dies_sense_compra=int(v(row["dies_sense_compra"], 0)),
            num_intervals=int(v(row["num_intervals"], 0)),
            cicle_mig_dies=float(v(row["cicle_mig_dies"])) if v(row["cicle_mig_dies"]) is not None else None,
            cicle_std_dies=float(v(row["cicle_std_dies"])) if v(row["cicle_std_dies"]) is not None else None,
            dies_retard=int(v(row["dies_retard"], 0)),
            z_score=float(v(row["z_score"])) if v(row["z_score"]) is not None else None,
            proxim_pedido_esperat=v(row["proxim_pedido_esperat"]),
            dies_stock=float(v(row["dies_stock"])) if v(row["dies_stock"]) is not None else None,
            prioritat=float(v(row["prioritat"], 0)),
            motiu=v(row["motiu"]) or "",
            data_alerta=str(row["data_alerta"]),
            tractada=key in treated_set,
        )
        alerts.append(alert)

    if pendents:
        alerts = [a for a in alerts if not a.tractada]

    return alerts

import pgeocode
nomi = pgeocode.Nominatim('es')

@router.get("/map")
def get_map_data(today: str = Query(default_factory=today_str)):
    engine = get_engine()
    today_str = today if isinstance(today, str) else today.strftime("%Y-%m-%d")
    ensure_cache(today_str)
    
    # Obtenir els clients actius amb el seu share de wallet i codi postal
    query = """
        SELECT a.id_cliente, a.familia_potencial, a.share_12m, v.cod_postal
        FROM alertes_cache a
        LEFT JOIN (
            SELECT id_cliente, MAX(cod_postal) as cod_postal
            FROM ventas
            GROUP BY id_cliente
        ) v ON a.id_cliente = v.id_cliente
        WHERE a.data_alerta = :today AND a.tipus_alerta != 'fugat'
    """
    df = pd.read_sql(text(query), engine, params={"today": today_str})
    
    if df.empty:
        return []
        
    def clean_cp(x):
        try:
            return str(x).replace('.0', '').zfill(5)
        except:
            return None
            
    df['cod_postal_clean'] = df['cod_postal'].apply(clean_cp)
    
    # Obtenir lats i lons ràpid
    unique_cps = df['cod_postal_clean'].dropna().unique()
    geo_data = {}
    for cp in unique_cps:
        res = nomi.query_postal_code(cp)
        if not pd.isna(res.latitude):
            geo_data[cp] = {"lat": float(res.latitude), "lon": float(res.longitude)}
            
    points = []
    for _, row in df.iterrows():
        cp = row['cod_postal_clean']
        if cp in geo_data and row['share_12m'] is not None:
            points.append({
                "id_cliente": int(row["id_cliente"]),
                "familia": row["familia_potencial"],
                "share_12m": float(row["share_12m"]),
                "cod_postal": cp,
                "lat": geo_data[cp]["lat"],
                "lon": geo_data[cp]["lon"]
            })
            
    return points

