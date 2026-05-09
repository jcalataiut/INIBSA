import pandas as pd
from fastapi import APIRouter, Query
from sqlalchemy import text
from datetime import datetime
from backend.database import get_engine, clear_cache
from backend.engine.commodities_engine import run
from backend.models.schemas import AlertaOut

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

@router.get("")
def get_alerts(
    today: str = Query(default_factory=lambda: datetime.now().strftime("%Y-%m-%d")),
    family: str | None = Query(None),
    segment: str | None = Query(None),
    tipus: str | None = Query(None),
    urgencia: str | None = Query(None),
    pendents: bool = Query(False),
):
    engine = get_engine()
    today_str = today if isinstance(today, str) else today.strftime("%Y-%m-%d")

    with engine.connect() as conn:
        cached = conn.execute(
            text("SELECT COUNT(*) FROM alertes_cache WHERE data_alerta = :today"),
            {"today": today_str}
        ).scalar()

    if cached == 0:
        clear_cache(today_str)
        alerts_df, _ = run(today=today_str, family=family, verbose=False)
        if not alerts_df.empty:
            cols_to_save = [
                "id_cliente", "provincia", "familia_potencial", "segment",
                "segment_anterior", "tipus_alerta", "urgencia", "canal",
                "share_12m", "potencial_anual_eur", "euros_12m", "gap_eur",
                "dies_sense_compra", "num_intervals", "cicle_mig_dies",
                "cicle_std_dies", "dies_retard", "z_score",
                "proxim_pedido_esperat", "dies_stock", "prioritat", "motiu",
            ]
            for c in cols_to_save:
                if c not in alerts_df.columns:
                    alerts_df[c] = None
            alerts_df["data_alerta"] = today_str
            alerts_df[cols_to_save + ["data_alerta"]].to_sql(
                "alertes_cache", engine, if_exists="append", index=False, method="multi"
            )

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

    df = pd.read_sql(query, engine, params=params)

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
            share_12m=float(row["share_12m"] or 0),
            potencial_anual_eur=float(row["potencial_anual_eur"] or 0),
            euros_12m=float(row["euros_12m"] or 0),
            gap_eur=float(row["gap_eur"] or 0),
            dies_sense_compra=int(row["dies_sense_compra"] or 0),
            num_intervals=int(row["num_intervals"] or 0),
            cicle_mig_dies=float(row["cicle_mig_dies"]) if row.get("cicle_mig_dies") else None,
            cicle_std_dies=float(row["cicle_std_dies"]) if row.get("cicle_std_dies") else None,
            dies_retard=int(row["dies_retard"] or 0),
            z_score=float(row["z_score"]) if row.get("z_score") else None,
            proxim_pedido_esperat=row.get("proxim_pedido_esperat"),
            dies_stock=float(row["dies_stock"]) if row.get("dies_stock") else None,
            prioritat=float(row["prioritat"] or 0),
            motiu=row["motiu"] or "",
            data_alerta=str(row["data_alerta"]),
            tractada=key in treated_set,
        )
        alerts.append(alert)

    if pendents:
        alerts = [a for a in alerts if not a.tractada]

    return alerts
