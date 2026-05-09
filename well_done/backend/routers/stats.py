import pandas as pd
import numpy as np
from fastapi import APIRouter, Query
from sqlalchemy import text
from backend.database import get_engine, clear_cache
from backend.engine.commodities_engine import run
from backend.models.schemas import StatsOut
from backend.config import today_str

router = APIRouter(prefix="/api/stats", tags=["stats"])

def ensure_cache(today_str: str):
    engine = get_engine()
    with engine.connect() as conn:
        cached = conn.execute(
            text("SELECT COUNT(*) FROM alertes_cache WHERE data_alerta = :today"),
            {"today": today_str}
        ).scalar()
    if cached == 0:
        clear_cache(today_str)
        try:
            alerts_df, _ = run(today=today_str, verbose=False)
        except Exception:
            alerts_df = pd.DataFrame()
        if not alerts_df.empty:
            alerts_df = alerts_df.replace({np.nan: None})
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

            active_keys = set(
                f"{r['id_cliente']}_{r['familia_potencial']}_{r['tipus_alerta']}"
                for _, r in alerts_df.iterrows()
            )
            with engine.begin() as conn:
                existing = conn.execute(
                    text("SELECT client_familia_tipus FROM treated_alerts")
                ).all()
                to_remove = [row[0] for row in existing if row[0] not in active_keys]
                for k in to_remove:
                    conn.execute(
                        text("DELETE FROM treated_alerts WHERE client_familia_tipus = :key"),
                        {"key": k}
                    )

@router.get("")
def get_stats(today: str = Query(default_factory=today_str)):
    engine = get_engine()
    today_str = today if isinstance(today, str) else today.strftime("%Y-%m-%d")

    ensure_cache(today_str)

    with engine.connect() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM alertes_cache WHERE data_alerta = :today"),
            {"today": today_str}
        ).scalar() or 0

        tratades = conn.execute(
            text("""
                SELECT COUNT(*) FROM alertes_cache c
                JOIN treated_alerts t ON t.client_familia_tipus = CONCAT(c.id_cliente, '_', c.familia_potencial, '_', c.tipus_alerta)
                WHERE c.data_alerta = :today AND t.treated_date <= :today
            """),
            {"today": today_str}
        ).scalar() or 0

        gap = conn.execute(
            text("SELECT COALESCE(SUM(gap_eur), 0) FROM alertes_cache WHERE data_alerta = :today"),
            {"today": today_str}
        ).scalar() or 0

        alta_urgencia = conn.execute(
            text("SELECT COUNT(*) FROM alertes_cache WHERE data_alerta = :today AND urgencia = 'alta'"),
            {"today": today_str}
        ).scalar() or 0

        rows = conn.execute(
            text("SELECT segment, COUNT(*) as cnt FROM alertes_cache WHERE data_alerta = :today GROUP BY segment"),
            {"today": today_str}
        ).all()
        per_segment = {r[0]: r[1] for r in rows}

        rows2 = conn.execute(
            text("SELECT tipus_alerta, COUNT(*) as cnt FROM alertes_cache WHERE data_alerta = :today GROUP BY tipus_alerta"),
            {"today": today_str}
        ).all()
        per_tipus = {r[0]: r[1] for r in rows2}

    return StatsOut(
        total_alertes=total,
        pendents=total - tratades,
        tractades=tratades,
        gap_total=float(gap),
        alta_urgencia=alta_urgencia,
        per_segment=per_segment,
        per_tipus=per_tipus,
    )
