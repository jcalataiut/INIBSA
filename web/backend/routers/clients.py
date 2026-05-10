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
                ORDER BY fecha DESC LIMIT 1000
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


@router.get("/{client_id}/share/{familia}")
def get_share_trend(client_id: int, familia: str):
    """Calcula la tendència del Share of Wallet (rolling 12m) i la velocitat."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT DATE_TRUNC('month', fecha)::date as mes,
                       SUM(valores_h) as euros,
                       MAX(potencial_eur_anual) as potencial
                FROM ventas
                WHERE id_cliente = :id
                  AND familia_potencial = :fam
                  AND es_commodity = true
                GROUP BY DATE_TRUNC('month', fecha)
                ORDER BY mes
            """),
            {"id": client_id, "fam": familia}
        ).all()

        if not rows or len(rows) < 2:
            return {"mesos": [], "potencial": 0}

        import pandas as pd
        df = pd.DataFrame(rows, columns=["mes", "euros", "potencial"])
        potencial = float(df["potencial"].max())
        if potencial <= 0:
            return {"mesos": [], "potencial": 0}

        # Reindexar a tots els mesos del calendari
        df["mes"] = pd.to_datetime(df["mes"])
        df = df.set_index("mes")
        all_months = pd.date_range(df.index.min(), df.index.max(), freq="MS")
        df = df.reindex(all_months)
        df["euros"] = df["euros"].fillna(0)

        # Rolling 12m share
        df["rolling_12m"] = df["euros"].rolling(12, min_periods=1).sum()
        df["share"] = (df["rolling_12m"] / potencial).clip(0, 1)
        df["velocity"] = df["share"].diff().fillna(0)
        df = df.reset_index().rename(columns={"index": "mes"})

        return {
            "potencial": round(potencial, 2),
            "mesos": [
                {
                    "mes": str(r["mes"].date()),
                    "euros": round(float(r["euros"]), 2),
                    "rolling_12m": round(float(r["rolling_12m"]), 2),
                    "share": round(float(r["share"]), 4),
                    "velocity": round(float(r["velocity"]), 4),
                }
                for _, r in df.iterrows()
            ],
        }
