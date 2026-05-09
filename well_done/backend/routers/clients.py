from fastapi import APIRouter
from sqlalchemy import text
from backend.database import get_engine

router = APIRouter(prefix="/api/clients", tags=["clients"])

@router.get("/{client_id}")
def get_client(client_id: int):
    engine = get_engine()
    with engine.connect() as conn:
        info = conn.execute(
            text("SELECT DISTINCT id_cliente, cod_postal, provincia FROM ventas WHERE id_cliente = :id LIMIT 1"),
            {"id": client_id}
        ).first()

        if not info:
            return {"error": "Client not found"}

        historial = conn.execute(
            text("""
                SELECT fecha, num_fact, familia_potencial, valores_h, unidades
                FROM ventas WHERE id_cliente = :id AND es_devolucion = false
                ORDER BY fecha DESC LIMIT 100
            """),
            {"id": client_id}
        ).all()

        alertes = conn.execute(
            text("""
                SELECT * FROM alertes_cache WHERE id_cliente = :id ORDER BY prioritat DESC
            """),
            {"id": client_id}
        ).all()

        return {
            "id_cliente": info[0],
            "cod_postal": info[1],
            "provincia": info[2],
            "historial": [
                {"fecha": str(r[0]), "factura": r[1], "familia": r[2], "valor": float(r[3]), "unitats": float(r[4])}
                for r in historial
            ],
            "alertes": [
                {
                    "tipus_alerta": r.tipus_alerta,
                    "familia_potencial": r.familia_potencial,
                    "prioritat": float(r.prioritat),
                    "motiu": r.motiu,
                }
                for r in alertes
            ] if alertes else [],
        }
