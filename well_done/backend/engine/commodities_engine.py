import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import text
from backend.database import get_engine
from backend.config import (
    SHARE_FIDEL_THR, SHARE_MARGINAL_THR, DIES_FUGAT_THR, DIES_NOU_THR,
    DIES_HISTORIAL_MIN, RATIO_EN_RISC, NUM_INTERVALS_MIN,
    LLINDAR_GROC_STD, LLINDAR_TARONJA_STD, LLINDAR_VERMELL_STD,
    FINESTRA_CAPTURA_PCT, FINESTRA_CAPTURA_MIN, FINESTRA_CAPTURA_MAX,
)

POTENCIAL_COL = "potencial_eur_anual"

def load_data(today=None):
    engine = get_engine()
    query = "SELECT * FROM ventas WHERE es_commodity = TRUE"
    params = {}
    if today:
        query += " AND fecha <= :today"
        params["today"] = today
    df = pd.read_sql(text(query), engine, params=params)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df[df["es_devolucion"] == 0].copy()
    df[POTENCIAL_COL] = pd.to_numeric(df[POTENCIAL_COL], errors="coerce")
    return df

def build_monthly_aggregate(df):
    df["any_mes"] = df["fecha"].dt.to_period("M")
    agg = df.groupby(
        ["id_cliente", "familia_potencial", "any_mes"],
        as_index=False
    ).agg(
        euros_venuts=("valores_h", "sum"),
        num_pedidos=("num_fact", "nunique"),
        unitats=("unidades", "sum"),
        en_campana=("en_campana", "max"),
    )
    agg["anyo"] = agg["any_mes"].dt.year
    agg["mes"] = agg["any_mes"].dt.month
    return agg

def calc_rolling_share(monthly):
    monthly = monthly.sort_values(["id_cliente", "familia_potencial", "any_mes"])
    monthly["euros_12m"] = (
        monthly.groupby(["id_cliente", "familia_potencial"])["euros_venuts"]
        .transform(lambda s: s.rolling(12, min_periods=1).sum())
    )
    monthly["euros_3m"] = (
        monthly.groupby(["id_cliente", "familia_potencial"])["euros_venuts"]
        .transform(lambda s: s.rolling(3, min_periods=1).sum())
    )
    return monthly

def attach_potencial(monthly, raw_df):
    potencial = raw_df[["id_cliente", "familia_potencial", POTENCIAL_COL]].drop_duplicates()
    monthly = monthly.merge(potencial, on=["id_cliente", "familia_potencial"], how="left")
    monthly["share_12m"] = (monthly["euros_12m"] / monthly[POTENCIAL_COL]).clip(0, 1)
    monthly["share_3m_annualized"] = ((monthly["euros_3m"] * 4) / monthly[POTENCIAL_COL]).clip(0, 1)
    monthly["gap_eur"] = (monthly[POTENCIAL_COL] - monthly["euros_12m"]).clip(lower=0)
    return monthly

def calc_restock_cycle(df):
    facturas = df[df["en_campana"] == 0][
        ["id_cliente", "familia_potencial", "num_fact", "fecha"]
    ].drop_duplicates().sort_values(["id_cliente", "familia_potencial", "fecha"])

    records = []
    for (cli, fam), grp in facturas.groupby(["id_cliente", "familia_potencial"]):
        dates = grp["fecha"].values
        if len(dates) < 2:
            records.append({
                "id_cliente": cli, "familia_potencial": fam,
                "cicle_mig_dies": np.nan, "cicle_std_dies": np.nan,
                "num_intervals": 0,
                "data_ultim_pedido": dates[-1] if len(dates) else pd.NaT,
                "data_primer_pedido": dates[0] if len(dates) else pd.NaT,
            })
        else:
            diffs = np.diff(dates.astype("datetime64[D]")).astype(float)
            records.append({
                "id_cliente": cli, "familia_potencial": fam,
                "cicle_mig_dies": diffs.mean(), "cicle_std_dies": diffs.std(),
                "num_intervals": len(diffs),
                "data_ultim_pedido": dates[-1], "data_primer_pedido": dates[0],
            })

    cycles = pd.DataFrame(records)
    cycles["data_ultim_pedido"] = pd.to_datetime(cycles["data_ultim_pedido"])
    cycles["data_primer_pedido"] = pd.to_datetime(cycles["data_primer_pedido"])
    return cycles

def _is_perdut(row):
    dies_sense = row["dies_sense_compra"]
    dies_hist = row["dies_historial"]
    cicle = row.get("cicle_mig_dies")
    n_int = row.get("num_intervals", 0)
    if dies_hist < DIES_HISTORIAL_MIN:
        return False
    if pd.isna(cicle) or n_int == 0 or pd.isna(dies_sense):
        return dies_sense > 180 if not pd.isna(dies_sense) else True
    if n_int <= 2:
        return dies_sense > max(365, cicle * 3)
    return dies_sense > max(180, cicle * 2.5)

def _is_fugat(row):
    dies_sense = row["dies_sense_compra"]
    dies_hist = row["dies_historial"]
    if pd.isna(dies_sense) or dies_sense == 999:
        return True
    return dies_sense > DIES_FUGAT_THR and dies_hist > DIES_HISTORIAL_MIN

def segment_client(row):
    dies_hist = row["dies_historial"]
    share_12m = row["share_12m"]
    tendencia = row.get("tendencia_negativa", False)

    if dies_hist < DIES_NOU_THR:
        return "nou"
    if _is_fugat(row):
        return "fugat"
    if _is_perdut(row):
        return "perdut"
    if tendencia and share_12m > SHARE_MARGINAL_THR:
        return "en_risc"
    if share_12m >= SHARE_FIDEL_THR:
        return "fidel"
    if share_12m >= SHARE_MARGINAL_THR:
        return "promiscu"
    return "marginal"

def segment_all(monthly, cycles, today):
    today_ts = pd.Timestamp(today)
    latest = monthly.loc[
        monthly.groupby(["id_cliente", "familia_potencial"])["any_mes"].idxmax()
    ].copy()
    latest = latest.merge(cycles, on=["id_cliente", "familia_potencial"], how="left")
    latest["data_ultim_pedido"] = pd.to_datetime(latest["data_ultim_pedido"])
    latest["data_primer_pedido"] = pd.to_datetime(latest["data_primer_pedido"])
    latest["dies_sense_compra"] = (today_ts - latest["data_ultim_pedido"]).dt.days.fillna(999).astype(int)
    latest["dies_historial"] = (today_ts - latest["data_primer_pedido"]).dt.days.fillna(0).astype(int)
    latest["finestra_recent_mesos"] = latest["cicle_mig_dies"].apply(
        lambda c: 12 if (pd.notna(c) and c > 120) else (
            6 if (pd.notna(c) and c > 60) else 3
        )
    )
    latest["tendencia_negativa"] = (
        (latest["finestra_recent_mesos"] <= 6)
        & (latest["share_3m_annualized"] < latest["share_12m"] * RATIO_EN_RISC)
        & (latest["num_intervals"] >= NUM_INTERVALS_MIN)
    )
    latest["segment"] = latest.apply(segment_client, axis=1)

    segment_prev_map = {
        "en_risc": latest["share_12m"].apply(
            lambda s: "fidel" if s >= SHARE_FIDEL_THR else (
                "promiscu" if s >= SHARE_MARGINAL_THR else "marginal"
            )
        )
    }
    for seg, prev in segment_prev_map.items():
        latest.loc[latest["segment"] == seg, "segment_anterior"] = prev

    return latest

def generate_alerts(segments, today, provincia_map=None):
    today_ts = pd.Timestamp(today)
    alerts = []

    PROB_CONVERSIO = {
        "fidel": 0.8, "promiscu": 0.6, "marginal": 0.2,
        "en_risc": 0.9, "perdut": 0.05, "fugat": 0.15, "nou": 0.4,
    }

    def calc_prioritat(gap, dies_retard, cicle_mig, prob, dies_stock=None):
        if cicle_mig and cicle_mig > 0 and not pd.isna(cicle_mig):
            cicle_segur = max(14, cicle_mig)
            urgencia_retard = max(0.1, min(1.0, dies_retard / cicle_segur))
        else:
            urgencia_retard = 0.5
        urgencia_stock = 0
        if dies_stock is not None and dies_stock < 14:
            urgencia_stock = max(0, 1 - dies_stock / 14)
        return round(gap * max(urgencia_retard, urgencia_stock) * prob, 2)

    for _, row in segments.iterrows():
        alert = {
            "id_cliente": row["id_cliente"],
            "provincia": provincia_map.get(row["id_cliente"], "") if provincia_map else "",
            "familia_potencial": row["familia_potencial"],
            "segment": row["segment"],
            "segment_anterior": row.get("segment_anterior", ""),
            "share_12m": round(row["share_12m"], 3),
            "potencial_anual_eur": round(row[POTENCIAL_COL], 2),
            "euros_12m": round(row["euros_12m"], 2),
            "gap_eur": round(row["gap_eur"], 2),
            "dies_sense_compra": int(row["dies_sense_compra"]) if pd.notna(row["dies_sense_compra"]) else 999,
            "num_intervals": int(row["num_intervals"]) if pd.notna(row["num_intervals"]) else 0,
            "data_alerta": today,
        }

        cicle_mig = row["cicle_mig_dies"]
        cicle_std = row["cicle_std_dies"]
        dies_sense = row["dies_sense_compra"]
        segment = row["segment"]

        if segment == "fugat":
            alert["tipus_alerta"] = "fugat"
            alert["urgencia"] = "mitjana"
            alert["canal"] = "delegat"
            if cicle_mig and not pd.isna(cicle_mig):
                alert["cicle_mig_dies"] = round(cicle_mig, 1)
                alert["dies_retard"] = int(max(0, dies_sense - cicle_mig))
            else:
                alert["cicle_mig_dies"] = None
                alert["dies_retard"] = dies_sense
            impacte = max(alert["gap_eur"], row[POTENCIAL_COL] * 0.8)
            alert["prioritat"] = calc_prioritat(
                impacte, alert["dies_retard"],
                cicle_mig if (cicle_mig and not pd.isna(cicle_mig)) else None,
                PROB_CONVERSIO["fugat"]
            )
            alert["cicle_std_dies"] = None
            alert["z_score"] = None
            alert["proxim_pedido_esperat"] = None
            alert["dies_stock"] = None
            alert["motiu"] = (
                f"Client FUGAT. Porta MÉS D'UN ANY sense comprar "
                f"({dies_sense} dies). Historial previ de {row['dies_historial']:.0f} dies. "
                f"Requereix recuperació directa per delegat. "
                f"Gap potencial: {impacte:,.0f}€/any."
            )
            alerts.append(alert)
            continue

        if segment == "perdut":
            impacte = max(alert["gap_eur"], row[POTENCIAL_COL] * 0.5)
            if impacte < 200:
                continue
            alert["tipus_alerta"] = "perdut"
            alert["urgencia"] = "baixa"
            alert["canal"] = "televenda"
            if cicle_mig and not pd.isna(cicle_mig):
                alert["cicle_mig_dies"] = round(cicle_mig, 1)
                alert["dies_retard"] = int(max(0, dies_sense - cicle_mig))
            else:
                alert["cicle_mig_dies"] = None
                alert["dies_retard"] = dies_sense
            alert["cicle_std_dies"] = None
            alert["z_score"] = None
            alert["proxim_pedido_esperat"] = None
            alert["dies_stock"] = None
            alert["prioritat"] = calc_prioritat(
                impacte, alert["dies_retard"],
                cicle_mig if (cicle_mig and not pd.isna(cicle_mig)) else None,
                PROB_CONVERSIO["perdut"]
            )
            alert["motiu"] = (
                f"Client sense comprar des de fa {dies_sense} dies. "
                f"Historial previ de {row['dies_historial']:.0f} dies. "
                f"Possible pèrdua de compte. Requereix trucada de reactivació."
            )
            alerts.append(alert)
            continue

        if segment == "nou":
            alert["tipus_alerta"] = "monitoritzar"
            alert["urgencia"] = "baixa"
            alert["canal"] = "televenda"
            alert["cicle_mig_dies"] = round(cicle_mig, 1) if (cicle_mig and not pd.isna(cicle_mig)) else None
            alert["cicle_std_dies"] = None
            alert["z_score"] = None
            alert["proxim_pedido_esperat"] = None
            alert["dies_stock"] = None
            alert["dies_retard"] = 0
            alert["prioritat"] = calc_prioritat(alert["gap_eur"], 0, None, PROB_CONVERSIO["nou"])
            alert["motiu"] = (
                f"Client NOU ({row['dies_historial']:.0f} dies d'historial). "
                f"Primers pedidos registrats. Fer seguiment de consolidació "
                f"per assegurar fidelització."
            )
            alerts.append(alert)
            continue

        if segment == "en_risc":
            retard = 0
            z_score = 0
            if cicle_mig and not pd.isna(cicle_mig):
                proper = row["data_ultim_pedido"] + pd.Timedelta(days=cicle_mig)
                retard = max(0, (today_ts - proper).days)
                z_score = retard / cicle_std if (cicle_std and cicle_std > 0) else 0

            alert["tipus_alerta"] = "risc_fuga"
            alert["dies_retard"] = int(retard)
            alert["z_score"] = round(z_score, 2)
            alert["cicle_mig_dies"] = round(cicle_mig, 1) if (cicle_mig and not pd.isna(cicle_mig)) else None
            alert["cicle_std_dies"] = round(cicle_std, 1) if (cicle_std and not pd.isna(cicle_std)) else None
            alert["proxim_pedido_esperat"] = None
            alert["dies_stock"] = None
            alert["prioritat"] = calc_prioritat(
                alert["gap_eur"], retard,
                cicle_mig if (cicle_mig and not pd.isna(cicle_mig)) else None,
                PROB_CONVERSIO["en_risc"]
            )
            share_3m = row["share_3m_annualized"]
            share_12m = row["share_12m"]
            canvi_pct = (share_3m - share_12m) / share_12m * 100 if share_12m > 0 else 0
            alert["urgencia"] = "alta" if canvi_pct < -30 else "mitjana"
            alert["canal"] = "delegat" if alert["urgencia"] == "alta" else "televenda"
            alert["motiu"] = (
                f"Client en RISC de fuga ({row.get('segment_anterior', 'actiu')}). "
                f"Share 12m: {share_12m:.0%} → Share últims 3m anualitzat: {share_3m:.0%} "
                f"({canvi_pct:+.0f}%). "
                f"Gap: {alert['gap_eur']:.0f}€/any. "
                f"Tendència negativa clara. Intervenir amb urgència."
            )
            alerts.append(alert)
            continue

        if cicle_mig is None or pd.isna(cicle_mig):
            if segment in ("fidel", "promiscu"):
                alert["tipus_alerta"] = "info"
                alert["urgencia"] = "baixa"
                alert["canal"] = "televenda"
                alert["cicle_mig_dies"] = None
                alert["cicle_std_dies"] = None
                alert["z_score"] = None
                alert["proxim_pedido_esperat"] = None
                alert["dies_stock"] = None
                alert["dies_retard"] = 0
                alert["prioritat"] = calc_prioritat(alert["gap_eur"], 0, None, PROB_CONVERSIO[segment])
                alert["motiu"] = (
                    f"Client {segment.upper()}. Sense dades suficients per "
                    f"calcular cicle de reposició. Contacte proactiu recomanat."
                )
                alerts.append(alert)
            elif segment == "marginal":
                alert["tipus_alerta"] = "oportunitat_captura"
                alert["urgencia"] = "baixa"
                alert["canal"] = "televenda"
                alert["cicle_mig_dies"] = None
                alert["cicle_std_dies"] = None
                alert["z_score"] = None
                alert["proxim_pedido_esperat"] = None
                alert["dies_stock"] = None
                alert["dies_retard"] = 0
                alert["prioritat"] = calc_prioritat(alert["gap_eur"], 0, None, PROB_CONVERSIO["marginal"])
                alert["motiu"] = (
                    f"Client MARGINAL ({row['share_12m']:.0%} share). "
                    f"Gap de captura: {alert['gap_eur']:.0f}€/any. "
                    f"Baixa vinculació amb Inibsa. Cal investigar."
                )
                alerts.append(alert)
            continue

        proper_pedido = row["data_ultim_pedido"] + pd.Timedelta(days=cicle_mig)
        dies_retard = max(0, (today_ts - proper_pedido).days)
        z_score = dies_retard / cicle_std if (cicle_std and cicle_std > 0) else 0

        alert["dies_retard"] = int(dies_retard)
        alert["z_score"] = round(z_score, 2)
        alert["cicle_mig_dies"] = round(cicle_mig, 1)
        alert["cicle_std_dies"] = round(cicle_std, 1) if (cicle_std and not pd.isna(cicle_std)) else None
        alert["proxim_pedido_esperat"] = proper_pedido.strftime("%Y-%m-%d")

        alert["dies_stock"] = None
        if segment == "fidel" and cicle_mig and not pd.isna(cicle_mig):
            dies_per_proper = max(0, (proper_pedido - today_ts).days)
            alert["dies_stock"] = round(dies_per_proper, 1)

        dies_stock = alert["dies_stock"]

        if segment == "fidel":
            if dies_retard == 0 and dies_stock is not None and dies_stock < 7:
                alert["tipus_alerta"] = "reposicio_preventiva"
                alert["dies_stock"] = float(f"{dies_stock:.0f}")
                if dies_stock < 3:
                    alert["urgencia"] = "alta"
                    alert["canal"] = "delegat"
                else:
                    alert["urgencia"] = "baixa"
                    alert["canal"] = "televenda"
                alert["prioritat"] = calc_prioritat(
                    alert["gap_eur"], dies_retard, cicle_mig, PROB_CONVERSIO["fidel"],
                    dies_stock=dies_stock
                )
                alert["motiu"] = (
                    f"Client FIDEL d'{row['familia_potencial']}. "
                    f"Proper pedido estimat dins de {dies_stock:.0f} dies "
                    f"(cicle habitual: {cicle_mig:.0f} dies). "
                    f"Stock estimat proper a l'esgotament. "
                    f"Contactar per anticipar reposició."
                )
                alerts.append(alert)
                continue

            if dies_retard > 0:
                if z_score >= LLINDAR_VERMELL_STD:
                    alert["tipus_alerta"] = "risc_fuga"
                    alert["urgencia"] = "alta"
                    alert["canal"] = "delegat"
                    alert["motiu"] = (
                        f"Client FIDEL d'{row['familia_potencial']} amb risc de FUGA. "
                        f"Cicle habitual: {cicle_mig:.0f} dies. Porta {dies_sense} dies "
                        f"sense comprar ({dies_retard} dies de retard, z={z_score:.1f}). "
                        + (f"Stock exhaurit. " if dies_stock is not None and dies_stock <= 0 else "")
                        + f"Prioritat màxima."
                    )
                elif z_score >= LLINDAR_TARONJA_STD:
                    alert["tipus_alerta"] = "reposicio_endarrerida"
                    alert["urgencia"] = "mitjana"
                    alert["canal"] = "televenda"
                    alert["motiu"] = (
                        f"Client FIDEL d'{row['familia_potencial']} amb reposició endarrerida. "
                        f"Cicle habitual: {cicle_mig:.0f} dies. Retard de {dies_retard} dies "
                        f"(z={z_score:.1f}). "
                        + (f"Proper pedido esperat fa {dies_retard} dies. " if dies_stock is not None else "")
                        + f"Contactar per confirmar estat."
                    )
                else:
                    alert["tipus_alerta"] = "reposicio_pendent"
                    alert["urgencia"] = "baixa"
                    alert["canal"] = "televenda"
                    alert["motiu"] = (
                        f"Client FIDEL d'{row['familia_potencial']} amb lleuger retard "
                        f"({dies_retard} dies). Cicle habitual: {cicle_mig:.0f} dies. "
                        + (f"Proper pedido: {dies_stock:.0f} dies enrere. " if dies_stock is not None else "")
                        + f"Seguiment rutina."
                    )
                alert["prioritat"] = calc_prioritat(
                    alert["gap_eur"], dies_retard, cicle_mig, PROB_CONVERSIO["fidel"],
                    dies_stock=dies_stock
                )
                alerts.append(alert)

        elif segment == "promiscu":
            dies_restants = -dies_retard
            finestra = max(FINESTRA_CAPTURA_MIN, min(FINESTRA_CAPTURA_MAX, round(cicle_mig * FINESTRA_CAPTURA_PCT)))
            if abs(dies_restants) <= finestra or dies_retard > 0:
                alert["tipus_alerta"] = "finestra_captura"
                alert["urgencia"] = "alta" if dies_retard > 0 else "mitjana"
                alert["canal"] = "delegat"
                alert["prioritat"] = calc_prioritat(
                    alert["gap_eur"], dies_retard, cicle_mig, PROB_CONVERSIO["promiscu"]
                )
                alert["motiu"] = (
                    f"Client PROMISCU d'{row['familia_potencial']} en FINESTRA DE CAPTURA. "
                    f"Cicle: {cicle_mig:.0f} dies. Share: {row['share_12m']:.0%}. "
                    f"Gap: {alert['gap_eur']:.0f}€/any. "
                    f"{'Retard en reposició urgent.' if dies_retard > 0 else 'Moment òptim per contactar.'}"
                )
                alerts.append(alert)

        elif segment == "marginal":
            alert["tipus_alerta"] = "oportunitat_captura"
            alert["urgencia"] = "baixa"
            alert["canal"] = "televenda"
            alert["dies_retard"] = 0
            alert["z_score"] = 0
            alert["prioritat"] = calc_prioritat(
                alert["gap_eur"], 0, cicle_mig, PROB_CONVERSIO["marginal"]
            )
            alert["motiu"] = (
                f"Client MARGINAL d'{row['familia_potencial']}. "
                f"Share: {row['share_12m']:.0%}. Gap: {alert['gap_eur']:.0f}€/any. "
                f"Baixa vinculació. Cal investigar."
            )
            alerts.append(alert)

    if not alerts:
        return pd.DataFrame()

    alerts_df = pd.DataFrame(alerts)

    abans = len(alerts_df)
    alerts_df = alerts_df[~(
        (alerts_df["dies_sense_compra"] > 730)
        & (alerts_df["num_intervals"] <= 2)
    )]

    if "prioritat" in alerts_df.columns:
        alerts_df = alerts_df.sort_values("prioritat", ascending=False).reset_index(drop=True)
    return alerts_df

def run(today=None, family=None, verbose=False):
    if today is None:
        today = datetime.now().strftime("%Y-%m-%d")
    if isinstance(today, datetime):
        today = today.strftime("%Y-%m-%d")

    raw = load_data(today=today)
    if family:
        raw = raw[raw["familia_potencial"] == family]

    monthly = build_monthly_aggregate(raw)
    monthly = calc_rolling_share(monthly)
    monthly = attach_potencial(monthly, raw)
    cycles = calc_restock_cycle(raw)
    segments = segment_all(monthly, cycles, today)

    prov_map = raw[["id_cliente", "provincia"]].drop_duplicates()
    prov_map = prov_map.groupby("id_cliente")["provincia"].first().to_dict()

    alerts = generate_alerts(segments, today, prov_map)
    return alerts, segments
