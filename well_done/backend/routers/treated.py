from fastapi import APIRouter
from sqlalchemy import text
from datetime import date
from database import get_engine
from models.schemas import AlertaTreatedIn, AlertaTreatedOut

router = APIRouter(prefix="/api/treated", tags=["treated"])

def make_key(id_cliente: int, familia: str, tipus: str) -> str:
    return f"{id_cliente}_{familia}_{tipus}"

@router.get("")
def get_treated():
    engine = get_engine()
    rows = []
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, client_familia_tipus, id_cliente, familia_potencial, tipus_alerta, treated_date FROM treated_alerts ORDER BY treated_date DESC")
        )
        for row in result:
            rows.append(AlertaTreatedOut(
                id=row[0],
                client_familia_tipus=row[1],
                id_cliente=row[2],
                familia_potencial=row[3],
                tipus_alerta=row[4],
                treated_date=str(row[5]),
            ))
    return rows

@router.post("")
def mark_treated(item: AlertaTreatedIn):
    engine = get_engine()
    key = make_key(item.id_cliente, item.familia_potencial, item.tipus_alerta)
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO treated_alerts (client_familia_tipus, id_cliente, familia_potencial, tipus_alerta, treated_date)
                VALUES (:key, :cli, :fam, :tip, :today)
                ON CONFLICT (client_familia_tipus) DO UPDATE SET treated_date = :today
            """),
            {"key": key, "cli": item.id_cliente, "fam": item.familia_potencial, "tip": item.tipus_alerta, "today": date.today()}
        )
    return {"status": "ok", "key": key}

@router.delete("/{item_id}")
def unmark_treated(item_id: int):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM treated_alerts WHERE id = :id"), {"id": item_id})
    return {"status": "deleted"}
