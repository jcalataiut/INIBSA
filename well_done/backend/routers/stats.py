from fastapi import APIRouter, Query
from sqlalchemy import text
from backend.database import get_engine, ensure_cache
from backend.config import today_str

router = APIRouter(prefix="/api/stats", tags=["stats"])

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
            text("SELECT COUNT(*) FROM alertes_cache WHERE data_alerta = :today AND urgencia IN ('alta', 'critica')"),
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
