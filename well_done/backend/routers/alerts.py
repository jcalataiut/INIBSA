import pandas as pd
import numpy as np
from fastapi import APIRouter, Query
from sqlalchemy import text
from backend.database import get_engine, ensure_cache
from backend.models.schemas import AlertaOut, GeoContextOut, GeoPointOut
from backend.config import today_str
from backend.engine.commodities_engine import get_geographical_context

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

@router.get("/geo-context", response_model=GeoContextOut)
def get_geo_context(
    family: str = Query(...),
    today: str = Query(default_factory=today_str),
):
    today_value = today if isinstance(today, str) else today.strftime("%Y-%m-%d")
    ensure_cache(today_value)
    points_df = get_geographical_context(today=today_value, family=family)
    points = [
        GeoPointOut(
            id_cliente=int(row["id_cliente"]),
            familia_potencial=row["familia_potencial"],
            cod_postal=row["cod_postal"],
            city=row["city"],
            provincia=row["provincia"] or "",
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            share_12m=float(v(row["share_12m"], 0)),
            gap_eur=float(v(row["gap_eur"], 0)),
        )
        for _, row in points_df.iterrows()
    ]
    return GeoContextOut(familia_potencial=family, points=points)

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

    query += " ORDER BY prioritat DESC NULLS LAST"

    df = pd.read_sql(text(query), engine, params=params)
    df = df.replace({np.nan: None, pd.NA: None})

    alerts = []
    for _, row in df.iterrows():
        key = make_cache_key(row)
        alert = AlertaOut(
            id_cliente=int(row["id_cliente"]),
            provincia=row.get("provincia") or "",
            cod_postal=v(row.get("cod_postal")),
            city=v(row.get("city")),
            latitude=float(v(row.get("latitude"))) if v(row.get("latitude")) is not None else None,
            longitude=float(v(row.get("longitude"))) if v(row.get("longitude")) is not None else None,
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
            share_velocity=float(v(row.get("share_velocity"))) if v(row.get("share_velocity")) is not None else None,
            share_alerta=v(row.get("share_alerta")),
            geo_neighbor_count=int(v(row.get("geo_neighbor_count"))) if v(row.get("geo_neighbor_count")) is not None else None,
            geo_neighbor_avg_share=float(v(row.get("geo_neighbor_avg_share"))) if v(row.get("geo_neighbor_avg_share")) is not None else None,
            geo_share_gap=float(v(row.get("geo_share_gap"))) if v(row.get("geo_share_gap")) is not None else None,
            tractada=key in treated_set,
        )
        alerts.append(alert)

    if pendents:
        alerts = [a for a in alerts if not a.tractada]

    return alerts
