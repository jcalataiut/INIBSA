from fastapi import APIRouter
from sqlalchemy import text
from backend.database import get_engine
from backend.models.schemas import AlertaTreatedIn, AlertaTreatedOut, FeedbackStatsOut
from backend.config import today_str

router = APIRouter(prefix="/api/treated", tags=["treated"])

def make_key(id_cliente: int, familia: str, tipus: str) -> str:
    return f"{id_cliente}_{familia}_{tipus}"

@router.get("")
def get_treated():
    engine = get_engine()
    rows = []
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, client_familia_tipus, id_cliente, familia_potencial, tipus_alerta, treated_date, resultado, importe_venta FROM treated_alerts ORDER BY treated_date DESC")
        )
        for row in result:
            rows.append(AlertaTreatedOut(
                id=row[0],
                client_familia_tipus=row[1],
                id_cliente=row[2],
                familia_potencial=row[3],
                tipus_alerta=row[4],
                treated_date=str(row[5]),
                resultado=row[6],
                importe_venta=float(row[7]) if row[7] else None,
            ))
    return rows

@router.post("")
def mark_treated(item: AlertaTreatedIn):
    engine = get_engine()
    key = make_key(item.id_cliente, item.familia_potencial, item.tipus_alerta)
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO treated_alerts (client_familia_tipus, id_cliente, familia_potencial, tipus_alerta, treated_date, resultado, importe_venta, fecha_resultado)
                VALUES (:key, :cli, :fam, :tip, :today, :res, :imp, :today)
                ON CONFLICT (client_familia_tipus) DO UPDATE SET
                    treated_date = :today,
                    resultado = COALESCE(:res, treated_alerts.resultado),
                    importe_venta = COALESCE(:imp, treated_alerts.importe_venta),
                    fecha_resultado = CASE WHEN :res IS NOT NULL THEN :today ELSE treated_alerts.fecha_resultado END
            """),
            {
                "key": key, "cli": item.id_cliente, "fam": item.familia_potencial,
                "tip": item.tipus_alerta, "today": today_str(),
                "res": item.resultado, "imp": item.importe_venta,
            }
        )
    return {"status": "ok", "key": key}

@router.post("/feedback")
def update_feedback(item: AlertaTreatedIn):
    engine = get_engine()
    key = make_key(item.id_cliente, item.familia_potencial, item.tipus_alerta)
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE treated_alerts
                SET resultado = :res, importe_venta = :imp, fecha_resultado = :today
                WHERE client_familia_tipus = :key
            """),
            {"res": item.resultado, "imp": item.importe_venta, "today": today_str(), "key": key}
        )
    return {"status": "ok", "key": key}

@router.get("/stats")
def feedback_stats():
    engine = get_engine()
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM treated_alerts")).scalar() or 0
        convertides = conn.execute(text("SELECT COUNT(*) FROM treated_alerts WHERE resultado = 'convertido'")).scalar() or 0
        no_convertides = conn.execute(text("SELECT COUNT(*) FROM treated_alerts WHERE resultado = 'no_convertido'")).scalar() or 0
        import_total = conn.execute(text("SELECT COALESCE(SUM(importe_venta), 0) FROM treated_alerts WHERE resultado = 'convertido'")).scalar() or 0
    return FeedbackStatsOut(
        total_tractades=total,
        convertides=convertides,
        no_convertides=no_convertides,
        taxa_conversio=round(convertides / max(total, 1), 3),
        import_total=float(import_total),
    )

@router.delete("/{item_id}")
def unmark_treated(item_id: int):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM treated_alerts WHERE id = :id"), {"id": item_id})
    return {"status": "deleted"}
