"""
Motor de Detecció d'Anomalies — Productes Tècnics (Biomaterials)
======================================================================

QUÈ FA:
  Per cada (client, família) de productes tècnics:
    1. Calcula el patró individual de compra (freqüència, volum, variabilitat)
    2. Classifica el client (actiu_regular, actiu_esporàdic, inactiu_recent)
    3. Genera alertes per desviació del patró:
       - ANOMALIA GROGA: silenci > freq_mig + 1*std (vigilar)
       - ANOMALIA VERMELLA: silenci > freq_mig + 2*std (risc real)
       - Per esporàdics: llindar més permissiu (+3*std)

BASAT EN:
  README.md §5.3 — Motor Tècnics (Detecció d'Anomalia)

COM S'USA:
    from backend.engine.technicals_engine import run
    alerts, segments = run(today="2025-12-01")

OUTPUT:
    DataFrame amb alertes prioritzades, compatible amb alertes_cache.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import text
from backend.database import get_engine

POTENCIAL_COL = "potencial_eur_anual"
DIES_FUGAT_THR = 365

# Llindars de classificació
PEDIDOS_REGULAR_THR = 4
PEDIDOS_ESPORADIC_MIN = 1
PEDIDOS_ESPORADIC_MAX = 3

# Llindars d'anomalia (multiples de std)
LLINDAR_GROGA_STD = 1.0
LLINDAR_VERMELLA_STD = 2.0
LLINDAR_ESPORADIC_STD = 3.0


def load_data(today=None):
    """Carrega les vendes de productes tècnics (es_commodity = FALSE) des de PostgreSQL.

    Si today es proporciona, filtra només vendes fins a essa data.
    Exclou devolucions (es_devolucion == 0).
    """
    engine = get_engine()
    query = "SELECT * FROM ventas WHERE es_commodity = FALSE"
    params = {}
    if today:
        query += " AND fecha <= :today"
        params["today"] = today
    df = pd.read_sql(text(query), engine, params=params)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df[df["es_devolucion"] == 0].copy()
    df[POTENCIAL_COL] = pd.to_numeric(df[POTENCIAL_COL], errors="coerce")
    return df


def calc_individual_pattern(df):
    """Calcula el patró individual de compra per (client, família).

    Per cada parella:
      - freq_mig_dies: interval mitjà entre pedidos consecutius
      - freq_std_dies: desviació estàndard dels intervals
      - vol_mig_eur: import mitjà per pedido
      - num_intervals: nombre d'intervals (fiabilitat)
      - n_pedidos_12m: nombre de pedidos en els últims 12 mesos
      - data_ultim_pedido: data del darrer pedido
      - data_primer_pedido: data del primer pedido

    Exclou vendes en campanya per no distorsionar el patró real.
    """
    today_max = df["fecha"].max()

    facturas = df[df["en_campana"] == 0][
        ["id_cliente", "familia_potencial", "num_fact", "fecha", "valores_h"]
    ].drop_duplicates(subset=["id_cliente", "familia_potencial", "num_fact", "fecha"]).sort_values(
        ["id_cliente", "familia_potencial", "fecha"]
    )

    # Per compte de pedidos en últims 12m (incloent campanyes)
    cutoff_12m = today_max - pd.DateOffset(months=12)
    pedidos_12m = df[df["fecha"] >= cutoff_12m][
        ["id_cliente", "familia_potencial", "num_fact"]
    ].drop_duplicates().groupby(
        ["id_cliente", "familia_potencial"]
    )["num_fact"].nunique().reset_index()
    pedidos_12m = pedidos_12m.rename(columns={"num_fact": "n_pedidos_12m"})

    records = []
    for (cli, fam), grp in facturas.groupby(["id_cliente", "familia_potencial"]):
        dates = grp["fecha"].values
        valores = grp.groupby("fecha")["valores_h"].sum()

        if len(dates) < 2:
            records.append({
                "id_cliente": cli, "familia_potencial": fam,
                "freq_mig_dies": np.nan, "freq_std_dies": np.nan,
                "vol_mig_eur": float(valores.mean()) if len(valores) > 0 else 0.0,
                "vol_ratio": None,
                "num_intervals": 0,
                "data_ultim_pedido": dates[-1] if len(dates) else pd.NaT,
                "data_primer_pedido": dates[0] if len(dates) else pd.NaT,
            })
        else:
            diffs = np.diff(dates.astype("datetime64[D]")).astype(float)
            vol_per_order = grp.groupby("fecha")["valores_h"].sum().values
            vol_mig = float(np.mean(vol_per_order))
            if len(vol_per_order) >= 4:
                vol_recent = float(np.mean(vol_per_order[-2:]))
                vol_ratio = round(vol_recent / vol_mig, 3) if vol_mig > 0 else 1.0
            elif len(vol_per_order) >= 2:
                vol_recent = float(vol_per_order[-1])
                vol_ratio = round(vol_recent / vol_mig, 3) if vol_mig > 0 else 1.0
            else:
                vol_ratio = None
            records.append({
                "id_cliente": cli, "familia_potencial": fam,
                "freq_mig_dies": float(np.mean(diffs)),
                "freq_std_dies": float(np.std(diffs, ddof=1)) if len(diffs) > 1 else float(np.mean(diffs) * 0.5),
                "vol_mig_eur": vol_mig,
                "vol_ratio": vol_ratio,
                "num_intervals": len(diffs),
                "data_ultim_pedido": dates[-1],
                "data_primer_pedido": dates[0],
            })

    patterns = pd.DataFrame(records)
    patterns["data_ultim_pedido"] = pd.to_datetime(patterns["data_ultim_pedido"])
    patterns["data_primer_pedido"] = pd.to_datetime(patterns["data_primer_pedido"])
    patterns["freq_std_dies"] = patterns["freq_std_dies"].fillna(patterns["freq_mig_dies"] * 0.5)
    patterns["freq_std_dies"] = patterns["freq_std_dies"].clip(lower=1)

    patterns = patterns.merge(pedidos_12m, on=["id_cliente", "familia_potencial"], how="left")
    patterns["n_pedidos_12m"] = patterns["n_pedidos_12m"].fillna(0).astype(int)

    return patterns


def calc_sow_and_gap(df, today):
    """Calcula share of wallet (últims 12m) i gap econòmic per (client, família).

    share_12m = euros_12m / potencial_eur  (capped at 100%)
    gap_eur   = potencial_eur - euros_12m  (euros no capturats)
    """
    today_ts = pd.Timestamp(today)
    cutoff = today_ts - pd.DateOffset(months=12)

    client_data = df[["id_cliente", "familia_potencial", POTENCIAL_COL]].drop_duplicates(subset=["id_cliente", "familia_potencial"], keep="first")

    valid = df[(df["fecha"] >= cutoff) & (df["es_devolucion"] == 0)]

    sales_12m = valid.groupby(["id_cliente", "familia_potencial"])["valores_h"].sum().reset_index()
    sales_12m = sales_12m.rename(columns={"valores_h": "euros_12m"})

    sow = client_data.merge(sales_12m, on=["id_cliente", "familia_potencial"], how="left")
    sow["euros_12m"] = sow["euros_12m"].fillna(0)
    sow = sow.rename(columns={POTENCIAL_COL: "potencial_eur"})

    sow["share_12m"] = (sow["euros_12m"] / sow["potencial_eur"]).clip(0, 1)
    sow["gap_eur"] = (sow["potencial_eur"] - sow["euros_12m"]).clip(lower=0)

    return sow


def segment_client(row):
    """Classifica un (client, família) tècnic segons el seu patró de compra.

    Ordre:
      1. 'inactiu_recent': porta massa temps sense comprar
      2. 'actiu_regular': ≥4 pedidos en els últims 12m
      3. 'actiu_esporàdic': 1-3 pedidos en els últims 12m
      4. 'inactiu_total': sense cap pedido (historial buit)
    """
    n_ped = row["n_pedidos_12m"]
    dies_sense = row["dies_sense_compra"]
    freq = row["freq_mig_dies"]
    std = row["freq_std_dies"]
    n_int = row["num_intervals"]

    # Sense historial
    if pd.isna(dies_sense) or dies_sense == 999:
        return "inactiu_total"

    # Inactiu recent: silenci > llindar dinàmic
    if n_int > 0 and not pd.isna(freq) and not pd.isna(std) and std > 0:
        if n_ped <= PEDIDOS_ESPORADIC_MAX:
            llindar = freq + LLINDAR_ESPORADIC_STD * std
        else:
            llindar = freq + LLINDAR_VERMELLA_STD * std

        if dies_sense > llindar and n_int >= 1:
            return "inactiu_recent"

    # Inactiu per llindar absolut (gens d'historial o molt poc)
    if n_int == 0 and dies_sense > 180:
        return "inactiu_recent"
    if n_int <= 2 and dies_sense > 365:
        return "inactiu_recent"

    # Actiu per volum de pedidos
    if n_ped >= PEDIDOS_REGULAR_THR:
        return "actiu_regular"
    if n_ped >= PEDIDOS_ESPORADIC_MIN:
        return "actiu_esporadic"

    return "inactiu_recent"


def classify_all(patterns, sow, today):
    """Aplica segmentació a tots els (client, família) tècnics."""
    today_ts = pd.Timestamp(today)

    data = patterns.merge(sow, on=["id_cliente", "familia_potencial"], how="left")
    data["euros_12m"] = data["euros_12m"].fillna(0)
    data["share_12m"] = data["share_12m"].fillna(0)
    data["gap_eur"] = data["gap_eur"].fillna(0)
    data["potencial_eur"] = data["potencial_eur"].fillna(0)

    data["dies_sense_compra"] = (today_ts - data["data_ultim_pedido"]).dt.days.fillna(999).astype(int)
    data["dies_historial"] = (today_ts - data["data_primer_pedido"]).dt.days.fillna(0).astype(int)

    data["segment"] = data.apply(segment_client, axis=1)
    data["segment_anterior"] = None

    return data


def generate_alerts(classified, today, provincia_map=None):
    """Genera alertes d'anomalia per productes tècnics.

    Per cada (client, família) amb patró calculat:
      1. Si silenci > freq_mig + 2*std → anomalia_vermella (risc real)
      2. Si silenci > freq_mig + 1*std → anomalia_groga (vigilar)
      3. Per esporàdics: llindar a +3*std (més permissiu)
    """
    today_ts = pd.Timestamp(today)
    alerts = []

    PROB_CONVERSIO = {
        "actiu_regular": 0.8,
        "actiu_esporadic": 0.5,
        "inactiu_recent": 0.3,
        "inactiu_total": 0.1,
    }

    def calc_prioritat(gap, z_score, prob):
        urgencia = min(1.0, max(0.1, abs(z_score) / LLINDAR_VERMELLA_STD))
        return round(gap * urgencia * prob, 2)

    for _, row in classified.iterrows():
        dies_sense = row["dies_sense_compra"]
        freq = row["freq_mig_dies"]
        std = row["freq_std_dies"]
        segment = row["segment"]
        n_ped = row["n_pedidos_12m"]

        if dies_sense > DIES_FUGAT_THR:
            continue

        alert = {
            "id_cliente": int(row["id_cliente"]),
            "provincia": provincia_map.get(row["id_cliente"], "") if provincia_map else "",
            "familia_potencial": row["familia_potencial"],
            "segment": segment,
            "segment_anterior": None,
            "share_12m": round(float(row["share_12m"]), 3),
            "potencial_anual_eur": round(float(row["potencial_eur"]), 2),
            "euros_12m": round(float(row["euros_12m"]), 2),
            "gap_eur": round(float(row["gap_eur"]), 2),
            "dies_sense_compra": dies_sense,
            "num_intervals": int(row["num_intervals"]),
            "cicle_mig_dies": round(float(freq), 1) if not pd.isna(freq) else None,
            "cicle_std_dies": round(float(std), 1) if not pd.isna(std) else None,
            "data_alerta": today,
        }

        # Si no tenim patró fiable o és inactiu total
        if pd.isna(freq) or pd.isna(std) or segment == "inactiu_total":
            prob = PROB_CONVERSIO.get(segment, 0.1)
            alert["tipus_alerta"] = "monitoritzar"
            alert["urgencia"] = "baixa"
            alert["canal"] = "televenda"
            alert["dies_retard"] = 0
            alert["z_score"] = None
            alert["proxim_pedido_esperat"] = None
            alert["prioritat"] = calc_prioritat(alert["gap_eur"], 0, prob)
            alert["motiu"] = (
                f"Client de {row['familia_potencial']} sense patró definit. "
                f"{'Sense historial de compra.' if segment == 'inactiu_total' else 'Poques dades per establir patró.'} "
                f"Requereix investigació."
            )
            alerts.append(alert)
            continue

        # Calcular z_score: quants std estem per sobre de la freqüència esperada
        # Si el silenci és menor que la freqüència, estem dins del normal → no alerta
        z_score = (dies_sense - freq) / std if std > 0 else 0.0

        esperat_str = f"Patró: cada {freq:.0f} dies ±{std:.0f}"

        # ── Anomalia temporal ─────────────────────────────────
        def _make_time_alert(tipus, urgencia, canal, prioritat, motiu):
            alert.update({
                "tipus_alerta": tipus, "urgencia": urgencia, "canal": canal,
                "z_score": round(float(z_score), 2),
                "dies_retard": int(max(0, dies_sense - freq)),
                "prioritat": prioritat, "motiu": motiu,
            })
            alerts.append(alert)
            return True

        if segment == "actiu_esporadic":
            if z_score >= LLINDAR_ESPORADIC_STD:
                prob = PROB_CONVERSIO.get(segment, 0.5)
                p = calc_prioritat(alert["gap_eur"], z_score, prob)
                _make_time_alert("anomalia_groga", "baixa", "televenda", p,
                    f"Client esporàdic de {row['familia_potencial']} amb ANOMALIA GROGA. "
                    f"Porta {dies_sense} dies sense comprar (z={z_score:.1f}). "
                    f"{esperat_str}. Vigilar.")
                continue
        else:
            if z_score >= LLINDAR_VERMELLA_STD:
                prob = PROB_CONVERSIO.get(segment, 0.6)
                p = calc_prioritat(alert["gap_eur"], z_score, prob)
                _make_time_alert("anomalia_vermella", "alta", "delegat", p,
                    f"Client de {row['familia_potencial']} amb ANOMALIA VERMELLA. "
                    f"Porta {dies_sense} dies sense comprar (z={z_score:.1f}). "
                    f"{esperat_str}. Risc alt de pèrdua — intervenció urgent.")
                continue

            elif z_score >= LLINDAR_GROGA_STD:
                prob = PROB_CONVERSIO.get(segment, 0.6)
                p = calc_prioritat(alert["gap_eur"], z_score, prob)
                _make_time_alert("anomalia_groga", "mitjana", "televenda", p,
                    f"Client de {row['familia_potencial']} amb ANOMALIA GROGA. "
                    f"Porta {dies_sense} dies sense comprar (z={z_score:.1f}). "
                    f"{esperat_str}. Vigilar evolució.")
                continue

        # ── Si no hi ha anomalia temporal, detectar caiguda de volum ──
        try:
            vol_ratio = float(row["vol_ratio"]) if "vol_ratio" in row.index and not pd.isna(row["vol_ratio"]) else None
        except (KeyError, ValueError, TypeError):
            vol_ratio = None

        if vol_ratio is not None and vol_ratio < 0.6 and row["num_intervals"] >= 3:
            alert["tipus_alerta"] = "caiguda_volum"
            alert["urgencia"] = "mitjana"
            alert["canal"] = "televenda"
            alert["z_score"] = round(float(z_score), 2)
            alert["dies_retard"] = int(max(0, dies_sense - freq))
            alert["proxim_pedido_esperat"] = None

            prob = PROB_CONVERSIO.get(segment, 0.5)
            caiguda_pct = round((1 - vol_ratio) * 100)
            alert["prioritat"] = round(alert["gap_eur"] * (1 - vol_ratio) * prob, 2)
            alert["motiu"] = (
                f"Client de {row['familia_potencial']} amb CAIGUDA DE VOLUM. "
                f"Últimes comandes un {caiguda_pct:.0f}% per sota del seu històric "
                f"(mitjana: {float(row['vol_mig_eur']):.0f}€). "
                f"Possible desviació de compra a competència."
            )
            alerts.append(alert)
            continue

    if not alerts:
        return pd.DataFrame()

    alerts_df = pd.DataFrame(alerts)
    if "prioritat" in alerts_df.columns:
        alerts_df = alerts_df.sort_values("prioritat", ascending=False).reset_index(drop=True)
    return alerts_df


def generate_fugats(classified, today, provincia_map=None):
    """Genera alertes per clients FUGATS (>365 dies sense comprar).

    Aquests clients NO surten a la llista principal d'anomalies.
    Van a un llistat separat per tenir-los controlats.
    """
    today_ts = pd.Timestamp(today)
    alerts = []

    for _, row in classified.iterrows():
        dies_sense = int(row["dies_sense_compra"])

        if dies_sense <= DIES_FUGAT_THR:
            continue

        freq = row["freq_mig_dies"] if not pd.isna(row["freq_mig_dies"]) else None
        std = row["freq_std_dies"] if (not pd.isna(row["freq_std_dies"])) else None

        alert = {
            "id_cliente": int(row["id_cliente"]),
            "provincia": provincia_map.get(row["id_cliente"], "") if provincia_map else "",
            "familia_potencial": row["familia_potencial"],
            "segment": "fugat",
            "segment_anterior": None,
            "tipus_alerta": "fugat",
            "urgencia": "baixa",
            "canal": "televenda",
            "share_12m": round(float(row["share_12m"]), 3),
            "potencial_anual_eur": round(float(row["potencial_eur"]), 2),
            "euros_12m": round(float(row["euros_12m"]), 2),
            "gap_eur": round(float(row["gap_eur"]), 2),
            "dies_sense_compra": dies_sense,
            "num_intervals": int(row["num_intervals"]) if not pd.isna(row["num_intervals"]) else 0,
            "cicle_mig_dies": round(float(freq), 1) if freq is not None else None,
            "cicle_std_dies": round(float(std), 1) if std is not None else None,
            "dies_retard": 0,
            "z_score": None,
            "proxim_pedido_esperat": None,
            "dies_stock": None,
            "prioritat": round(float(row["gap_eur"]) * 0.01, 2),
            "motiu": (
                f"Client FUGAT de {row['familia_potencial']}. "
                f"Porta MÉS D'UN ANY sense comprar ({dies_sense} dies). "
                + (f"Patró habitual era cada {freq:.0f} dies. " if freq is not None else "")
                + "Requereix recuperació."
            ),
            "data_alerta": today,
        }
        alerts.append(alert)

    return pd.DataFrame(alerts) if alerts else pd.DataFrame()


def run(today=None, family=None, verbose=False):
    """Executa el motor complet de detecció d'anomalies per productes tècnics.

    Args:
        today: Data de referència (str YYYY-MM-DD o datetime). Per defecte: avui.
        family: Nom de família per filtrar ('Biomateriales') o None (totes).
        verbose: Mostra output per consola.

    Returns:
        Tuple (alerts_df, segments_df):
          alerts_df:  DataFrame amb alertes prioritzades
          segments_df: DataFrame amb dades de segmentació (per compatibilitat)
    """
    if today is None:
        today = datetime.now().strftime("%Y-%m-%d")
    if isinstance(today, datetime):
        today = today.strftime("%Y-%m-%d")

    if verbose:
        print(f"╔═ Motor Detecció Tècnics ════ Data: {today} ═╗")
        if family:
            print(f"║  Família: {family}")

    # ── 1. Carregar dades ────────────────────────────────
    if verbose:
        print("📥 Carregant dades...", end=" ")
    raw = load_data(today=today)

    if family:
        raw = raw[raw["familia_potencial"] == family]

    if verbose:
        print(f"{len(raw):,} línies · {raw['id_cliente'].nunique():,} clients")

    # ── 2. Patró individual ──────────────────────────────
    if verbose:
        print("📐 Patró individual de compra...", end=" ")
    patterns = calc_individual_pattern(raw)
    if verbose:
        n_amb_patro = patterns["freq_mig_dies"].notna().sum()
        print(f"{len(patterns):,} parelles ({n_amb_patro:,} amb patró)")

    # ── 3. Share of wallet ───────────────────────────────
    if verbose:
        print("💰 Share of wallet 12m...", end=" ")
    sow = calc_sow_and_gap(raw, today)
    if verbose:
        print(f"{len(sow):,} parelles")

    # ── 4. Mapa de províncies ────────────────────────────
    prov_map = raw[["id_cliente", "provincia"]].drop_duplicates()
    prov_map = prov_map.groupby("id_cliente")["provincia"].first().to_dict()

    # ── 5. Classificació ─────────────────────────────────
    if verbose:
        print("🏷️  Classificant clients...", end=" ")
    classified = classify_all(patterns, sow, today)
    if verbose:
        dist = classified["segment"].value_counts()
        print(f"{len(classified):,} parelles")
        for seg in ["actiu_regular", "actiu_esporadic", "inactiu_recent", "inactiu_total"]:
            c = dist.get(seg, 0)
            print(f"   {seg:>17s}: {c}")

    # ── 6. Generar alertes d'anomalia ────────────────────
    if verbose:
        print("🔔 Generant alertes (anomalia)...", end=" ")
    alerts = generate_alerts(classified, today, prov_map)
    if verbose:
        print(f"{len(alerts):,} alertes generades")
        if len(alerts) > 0:
            for tipus, count in alerts["tipus_alerta"].value_counts().items():
                print(f"   {tipus:>20s}: {count}")

    # ── 7. Generar alertes de fugats ────────────────────
    if verbose:
        print("👻 Generant llista de fugats (>365 dies)...", end=" ")
    fugats = generate_fugats(classified, today, prov_map)
    n_fugats = len(fugats)
    if verbose:
        print(f"{n_fugats} clients fugats")

    alerts = pd.concat([alerts, fugats], ignore_index=True) if not fugats.empty else alerts

    # ── 8. Top alertes ───────────────────────────────────
    actives = alerts[alerts["tipus_alerta"] != "fugat"] if len(alerts) > 0 else pd.DataFrame()
    if verbose and len(actives) > 0:
        print(f"\n{'─' * 60}")
        print("TOP 5 ALERTES PRIORITZADES (excloent fugats)")
        print(f"{'─' * 60}")
        for i, (_, a) in enumerate(actives.head(5).iterrows()):
            print(f"\n{i + 1}. #{a['id_cliente']}  |  {a.get('provincia', '?'):15s}  |  {a['familia_potencial']}")
            print(f"   🔸 {a['tipus_alerta']:>20s}  |  {a['urgencia']:>8s}  |  {a['segment']}")
            print(f"   Gap: {a['gap_eur']:>8.0f}€  |  Prioritat: {a['prioritat']:.1f}")
            print(f"   {a['motiu'][:130]}")

    # ── 9. Resum ─────────────────────────────────────────
    if verbose:
        gap_total = alerts["gap_eur"].sum() if len(alerts) > 0 else 0
        n_actius = alerts[alerts["tipus_alerta"] != "fugat"]["id_cliente"].nunique() if len(alerts) > 0 else 0
        print(f"\n{'─' * 60}")
        print(f"📊 RESUM: {n_actius} clients amb alerta activa + {n_fugats} fugats")
        print(f"   Gap total recuperable: {gap_total:,.0f}€/any")
        if len(actives) > 0:
            print(f"   Prioritat mitjana (actives): {actives['prioritat'].mean():.0f}")

    # ── Segments (per compatibilitat amb ensure_cache) ───
    segments = classified[["id_cliente", "familia_potencial", "segment",
                           "share_12m", "gap_eur", "potencial_eur",
                           "freq_mig_dies", "freq_std_dies", "num_intervals"]].copy()
    segments = segments.rename(columns={
        "freq_mig_dies": "cicle_mig_dies",
        "freq_std_dies": "cicle_std_dies",
    })

    return alerts, segments
