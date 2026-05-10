"""
Motor de Predicció i Alertes — Commodities (Anestèsia + Bioseguretat)
======================================================================

QUÈ FA:
  Per cada (client, família) de productes commodity:
    1. Calcula el cicle de reposició (dies entre pedidos consecutius)
    2. Prediu la data del proper pedido
    3. Genera dos tipus d'alerta:
       - ANTICIPACIÓ: avui és dins de K dies ABANS de la data prevista
         (alerta baixa/soft: "ei, aquests haurien de demanar aviat")
       - REACTIVA: avui és DESPRÉS de la data prevista
         (alerta greu: "ja hauria d'haver comprat i no ha comprat")
         La urgència escala amb els dies de retard.

BASAT EN:
  smart_demand_signals.ipynb — només la part de predicció (sense KMeans)

COM S'USA:
    from backend.engine.commodities_engine import run
    alerts, segments = run(today="2025-12-01")

OUTPUT:
    DataFrame amb alertes prioritzades, compatible amb alertes_cache.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import text
from backend.database import get_engine
from backend.config import (
    EWM_HALF_LIFE,
    GEO_MIN_INDIVIDUAL_GAP,
    GEO_MIN_NEIGHBORS,
    GEO_MIN_SHARE_GAP,
    GEO_NEIGHBOR_RADIUS_KM,
    PROB_ANTICIPACIO,
    MAX_ALERTS,
    POSTAL_GEO_CSV,
)

POTENCIAL_COL = "potencial_eur_anual"
DIES_FUGAT_THR = 365
_POSTAL_LOOKUP_DF = None


def load_data(today=None):
    """Carrega les vendes de commodities (es_commodity = TRUE) des de PostgreSQL.

    Si today es proporciona, filtra només vendes fins a essa data.
    Exclou devolucions (es_devolucion == 0).
    """
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


def _ewm_stats(gaps_arr, half_life=None):
    """Calcula cicle i std amb decaïment exponencial (EWM).

    Els gaps més recents tenen més pes que els antics.
    half_life: nombre de gaps per reduir el pes a la meitat.
    """
    if half_life is None:
        half_life = EWM_HALF_LIFE
    n = len(gaps_arr)
    lam = np.log(2) / max(half_life, 0.1)
    weights = np.exp(lam * np.arange(n))
    weights /= weights.sum()
    cicle = float(np.dot(weights, gaps_arr))
    if n > 1:
        variance = float(np.dot(weights, (gaps_arr - cicle) ** 2))
        std = float(np.sqrt(variance))
    else:
        std = cicle * 0.30
    if np.isnan(std) or std <= 0:
        std = cicle * 0.30
    return cicle, std


def calc_restock_cycle(df):
    """Calcula el cicle de reposició per (client, família).

    Per cada parella:
      - cicle_mig_dies: interval mitjà entre pedidos consecutius
      - cicle_std_dies: desviació estàndard dels intervals
      - num_intervals: nombre d'intervals (fiabilitat del càlcul)
      - data_ultim_pedido: data del darrer pedido

    Exclou vendes en campanya per no distorsionar el cicle real.
    """
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
            })
        else:
            diffs = np.diff(dates.astype("datetime64[D]")).astype(float)
            cicle_ewm, cicle_ewm_std = _ewm_stats(diffs)
            records.append({
                "id_cliente": cli, "familia_potencial": fam,
                "cicle_mig_dies": cicle_ewm, "cicle_std_dies": cicle_ewm_std,
                "num_intervals": len(diffs),
                "data_ultim_pedido": dates[-1],
            })

    cycles = pd.DataFrame(records)
    cycles["data_ultim_pedido"] = pd.to_datetime(cycles["data_ultim_pedido"])
    return cycles


def calc_sow_and_gap(df, today):
    """Calcula share of wallet (últims 12m) i gap econòmic per (client, família).

    share_12m = euros_12m / potencial_eur  (capped at 100%)
    gap_eur   = potencial_eur - euros_12m  (euros no capturats)
    """
    today_ts = pd.Timestamp(today)
    cutoff = today_ts - pd.DateOffset(months=12)

    # (client, família) + potencial
    client_data = df[["id_cliente", "familia_potencial", POTENCIAL_COL]].drop_duplicates()

    # Vendes dels últims 12 mesos (sense devolucions)
    valid = df[(df["fecha"] >= cutoff) & (df["es_devolucion"] == 0)]

    sales_12m = valid.groupby(["id_cliente", "familia_potencial"])["valores_h"].sum().reset_index()
    sales_12m = sales_12m.rename(columns={"valores_h": "euros_12m"})

    sow = client_data.merge(sales_12m, on=["id_cliente", "familia_potencial"], how="left")
    sow["euros_12m"] = sow["euros_12m"].fillna(0)
    sow = sow.rename(columns={POTENCIAL_COL: "potencial_eur"})

    sow["share_12m"] = (sow["euros_12m"] / sow["potencial_eur"]).clip(0, 1)
    sow["gap_eur"] = (sow["potencial_eur"] - sow["euros_12m"]).clip(lower=0)

    return sow

def calc_share_velocity(df, today):
    """Calcula la velocitat del Share of Wallet (derivada mensual).

    Per cada (client, família):
      1. Agrega vendes per mes
      2. Reindexa a tots els mesos del calendari
      3. Calcula rolling 12m share
      4. share_velocity = diferència mes a mes del share

    Retorna:
        DataFrame amb (id_cliente, familia_potencial, share_velocity)
        share_velocity: canvi en punts percentuals respecte al mes anterior
        None si el client no té dades suficients
    """
    today_ts = pd.Timestamp(today)

    df_base = df[df["en_campana"] == 0].copy()
    df_base["year_month"] = df_base["fecha"].dt.to_period("M")

    monthly = df_base.groupby(["id_cliente", "familia_potencial", "year_month"]).agg(
        euros_venuts=("valores_h", "sum"),
        potencial_eur=(POTENCIAL_COL, "first"),
    ).reset_index()
    monthly["year_month_dt"] = monthly["year_month"].dt.to_timestamp()

    records = []
    for (cli, fam), grp in monthly.groupby(["id_cliente", "familia_potencial"]):
        cm = grp.sort_values("year_month_dt").copy()
        potencial = cm["potencial_eur"].iloc[0]
        if potencial <= 0:
            records.append({"id_cliente": cli, "familia_potencial": fam, "share_velocity": None})
            continue

        cm = cm.set_index("year_month_dt")
        all_months = pd.date_range(cm.index.min(), today_ts, freq="MS")
        cm = cm.reindex(all_months)
        cm["euros_venuts"] = cm["euros_venuts"].fillna(0)
        cm["potencial_eur"] = cm["potencial_eur"].ffill().bfill()

        cm["rolling_12m"] = cm["euros_venuts"].rolling(12, min_periods=1).sum()
        cm["share"] = (cm["rolling_12m"] / cm["potencial_eur"]).clip(0, 1)
        cm["share_velocity"] = cm["share"].diff()

        last_vel = cm["share_velocity"].iloc[-1]
        last_vel = round(float(last_vel * 100), 2) if not pd.isna(last_vel) else None
        records.append({"id_cliente": cli, "familia_potencial": fam, "share_velocity": last_vel})

    return pd.DataFrame(records)


def normalize_postal_code(value):
    if value is None or pd.isna(value):
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        return f"{int(float(text_value)):05d}"
    except (TypeError, ValueError):
        digits = "".join(ch for ch in text_value if ch.isdigit())
        if not digits:
            return None
        return digits[:5].zfill(5)


def load_postal_lookup():
    global _POSTAL_LOOKUP_DF
    if _POSTAL_LOOKUP_DF is None:
        try:
            lookup = pd.read_csv(POSTAL_GEO_CSV, dtype={"cod_postal": str})
        except FileNotFoundError:
            lookup = pd.DataFrame(columns=["cod_postal", "city", "latitude", "longitude"])
        if not lookup.empty:
            lookup["cod_postal"] = lookup["cod_postal"].apply(normalize_postal_code)
            lookup = lookup.dropna(subset=["cod_postal", "latitude", "longitude"])
            lookup = lookup.drop_duplicates(subset=["cod_postal"])
        _POSTAL_LOOKUP_DF = lookup
    return _POSTAL_LOOKUP_DF.copy()


def build_geo_points(raw, today):
    if raw.empty:
        return pd.DataFrame(columns=[
            "id_cliente", "familia_potencial", "share_12m", "gap_eur",
            "cod_postal", "city", "provincia", "latitude", "longitude",
        ])

    sow = calc_sow_and_gap(raw, today)
    latest_client = (
        raw.sort_values(["id_cliente", "fecha"], ascending=[True, False])[
            ["id_cliente", "cod_postal", "provincia"]
        ]
        .copy()
    )
    latest_client["cod_postal"] = latest_client["cod_postal"].apply(normalize_postal_code)
    latest_client = latest_client.dropna(subset=["cod_postal"]).drop_duplicates(subset=["id_cliente"])

    geo_lookup = load_postal_lookup()
    points = sow.merge(latest_client, on="id_cliente", how="left")
    points = points.merge(geo_lookup, on="cod_postal", how="left")
    points["city"] = points["city"].fillna("").astype(str).str.strip()
    points.loc[points["city"] == "", "city"] = points["provincia"].fillna("")
    points = points.dropna(subset=["latitude", "longitude"]).copy()
    points["latitude"] = pd.to_numeric(points["latitude"], errors="coerce")
    points["longitude"] = pd.to_numeric(points["longitude"], errors="coerce")
    points = points.dropna(subset=["latitude", "longitude"]).copy()
    return points


def haversine_km(lat1, lon1, latitudes, longitudes):
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(latitudes)
    lon2_rad = np.radians(longitudes)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def generate_geographical_alerts(cycles, sow, today, raw):
    geo_points = build_geo_points(raw, today)
    if geo_points.empty:
        return pd.DataFrame(), geo_points

    base = cycles.merge(sow, on=["id_cliente", "familia_potencial"], how="outer")
    base = base.merge(
        geo_points[["id_cliente", "familia_potencial", "cod_postal", "city", "provincia", "latitude", "longitude"]],
        on=["id_cliente", "familia_potencial"],
        how="inner",
    )
    base["share_12m"] = base["share_12m"].fillna(0)
    base["gap_eur"] = base["gap_eur"].fillna(0)
    base["euros_12m"] = base["euros_12m"].fillna(0)
    base["potencial_eur"] = base["potencial_eur"].fillna(0)

    alerts = []
    for family, grp in base.groupby("familia_potencial"):
        grp = grp.reset_index(drop=True).copy()
        if len(grp) < GEO_MIN_NEIGHBORS + 1:
            continue

        latitudes = grp["latitude"].to_numpy(dtype=float)
        longitudes = grp["longitude"].to_numpy(dtype=float)

        for idx, row in grp.iterrows():
            dists = haversine_km(row["latitude"], row["longitude"], latitudes, longitudes)
            neighbours = grp[(dists > 0) & (dists <= GEO_NEIGHBOR_RADIUS_KM)].copy()
            if len(neighbours) < GEO_MIN_NEIGHBORS:
                continue

            neighbours["distance_km"] = dists[(dists > 0) & (dists <= GEO_NEIGHBOR_RADIUS_KM)]
            stronger = neighbours[
                neighbours["share_12m"] >= row["share_12m"] + GEO_MIN_INDIVIDUAL_GAP
            ].sort_values(["distance_km", "share_12m"], ascending=[True, False])
            if len(stronger) < GEO_MIN_NEIGHBORS:
                continue

            top_neighbours = stronger.head(GEO_MIN_NEIGHBORS)
            neighbour_avg_share = float(top_neighbours["share_12m"].mean())
            share_gap = neighbour_avg_share - float(row["share_12m"])
            if share_gap < GEO_MIN_SHARE_GAP:
                continue

            last_order_date = row.get("data_ultim_pedido")
            dies_sense = int((pd.Timestamp(today) - last_order_date).days) if pd.notna(last_order_date) else 0
            if dies_sense > DIES_FUGAT_THR:
                continue

            cicle = row["cicle_mig_dies"] if pd.notna(row.get("cicle_mig_dies")) else None
            cicle_std = row["cicle_std_dies"] if pd.notna(row.get("cicle_std_dies")) else (cicle * 0.30 if cicle else None)
            proper_pedido = (
                last_order_date + pd.Timedelta(days=float(cicle))
                if cicle is not None and pd.notna(last_order_date)
                else None
            )

            if share_gap >= 0.35:
                urgencia = "alta"
                canal = "delegat"
                urgencia_score = 3
            elif share_gap >= 0.25:
                urgencia = "mitjana"
                canal = "delegat"
                urgencia_score = 2
            else:
                urgencia = "baixa"
                canal = "televenda"
                urgencia_score = 1

            neighbour_count = int(len(top_neighbours))
            priority = round(
                urgencia_score * 100000 + min(float(row["gap_eur"]), 99999) + share_gap * 1000,
                2,
            )
            client_share_pct = round(float(row["share_12m"]) * 100)
            neighbour_share_pct = round(neighbour_avg_share * 100)

            alerts.append({
                "id_cliente": int(row["id_cliente"]),
                "provincia": row.get("provincia") or "",
                "cod_postal": row.get("cod_postal"),
                "city": row.get("city") or row.get("provincia") or "",
                "latitude": round(float(row["latitude"]), 6),
                "longitude": round(float(row["longitude"]), 6),
                "familia_potencial": family,
                "segment": "leal" if row["share_12m"] >= 0.70 else "promiscuo",
                "segment_anterior": None,
                "tipus_alerta": "geografica",
                "urgencia": urgencia,
                "canal": canal,
                "share_12m": round(float(row["share_12m"]), 3),
                "potencial_anual_eur": round(float(row["potencial_eur"]), 2),
                "euros_12m": round(float(row["euros_12m"]), 2),
                "gap_eur": round(float(row["gap_eur"]), 2),
                "dies_sense_compra": dies_sense,
                "num_intervals": int(row["num_intervals"]) if pd.notna(row.get("num_intervals")) else 0,
                "cicle_mig_dies": round(float(cicle), 1) if cicle is not None else None,
                "cicle_std_dies": round(float(cicle_std), 1) if cicle_std is not None else None,
                "dies_retard": 0,
                "z_score": None,
                "proxim_pedido_esperat": proper_pedido.strftime("%Y-%m-%d") if proper_pedido is not None else None,
                "dies_stock": None,
                "prioritat": priority,
                "motiu": (
                    f"Geographical Alert: el client té un share del {client_share_pct}% a {family}. "
                    f"{neighbour_count} clients propers (<= {int(GEO_NEIGHBOR_RADIUS_KM)} km) tenen una mitjana del "
                    f"{neighbour_share_pct}%, cosa que indica demanda propera encara no capturada."
                ),
                "data_alerta": today,
                "share_velocity": None,
                "share_alerta": "oportunitat",
                "geo_neighbor_count": neighbour_count,
                "geo_neighbor_avg_share": round(neighbour_avg_share, 3),
                "geo_share_gap": round(float(share_gap), 3),
            })

    alerts_df = pd.DataFrame(alerts) if alerts else pd.DataFrame()
    if not alerts_df.empty:
        alerts_df = alerts_df.sort_values("prioritat", ascending=False).reset_index(drop=True)
    return alerts_df, geo_points


def get_geographical_context(today=None, family=None):
    if today is None:
        today = datetime.now().strftime("%Y-%m-%d")
    if isinstance(today, datetime):
        today = today.strftime("%Y-%m-%d")

    raw = load_data(today=today)
    if family:
        raw = raw[raw["familia_potencial"] == family]
    points = build_geo_points(raw, today)
    if points.empty:
        return points
    return points.sort_values(["share_12m", "gap_eur"], ascending=[False, False]).reset_index(drop=True)


def generate_alerts(cycles, sow, today, provincia_map=None, share_vel=None):
    """Genera alertes d'ANTICIPACIÓ i REACTIVA basades en la predicció de compra.

    Per cada (client, família) amb cicle calculat:
      1. proper_pedido_esperat = data_ultim_pedido + cicle_mig_dies
      2. dies_per_proper = (proper_pedido_esperat - today).days
         (positiu = futur, negatiu = passat)

    ANTICIPACIÓ (0 < dies_per_proper <= K):
      - Alerta soft: "aquest client hauria de demanar aviat"
      - Prioritat: més alta com més a prop de la data prevista

    REACTIVA (dies_per_proper <= 0):
      - Alerta greu: "ja hauria d'haver comprat i no ho ha fet"
      - Prioritat: escala amb els dies de retard respecte al cicle
      - Urgència: baixa→mitjana→alta→crítica segons retard_ratio
    """
    today_ts = pd.Timestamp(today)
    alerts = []

    share_vel_map = None
    if share_vel is not None:
        # Expected: dict[(id_cliente:int, familia_potencial:str), share_velocity:float|None]
        share_vel_map = share_vel

    data = cycles.merge(sow, on=["id_cliente", "familia_potencial"], how="left")
    data["euros_12m"] = data["euros_12m"].fillna(0)
    data["share_12m"] = data["share_12m"].fillna(0)
    data["gap_eur"] = data["gap_eur"].fillna(0)
    data["potencial_eur"] = data["potencial_eur"].fillna(0)

    for _, row in data.iterrows():
        if pd.isna(row["cicle_mig_dies"]) or row["num_intervals"] < 1:
            continue

        cicle = row["cicle_mig_dies"]
        cicle_std = row["cicle_std_dies"] if (
            not pd.isna(row["cicle_std_dies"]) and row["cicle_std_dies"] > 0
        ) else cicle * 0.30

        # Finestra d'anticipació dinàmica: proporcional a la variabilitat del client
        # Mínim 3 dies (no pot ser 0), adaptatiu a la desviació del cicle
        K = max(3, cicle_std * 0.5)

        # Predicció: proper pedido
        proper_pedido = row["data_ultim_pedido"] + pd.Timedelta(days=cicle)
        dies_per_proper = (proper_pedido - today_ts).days

        dies_sense = int((today_ts - row["data_ultim_pedido"]).days)

        # Fugats (no surten al briefing): >365 dies sense comprar O share = 0%
        if dies_sense > DIES_FUGAT_THR or row["share_12m"] < 0.01:
            continue

        share_vel_val = None
        share_alerta = None
        if share_vel_map is not None:
            key = (int(row["id_cliente"]), row["familia_potencial"])
            share_vel_val = share_vel_map.get(key)
            if share_vel_val is not None and not pd.isna(share_vel_val):
                share_vel_val = float(share_vel_val)
                if share_vel_val <= -5:
                    share_alerta = "fuga"
                elif share_vel_val >= 5:
                    share_alerta = "oportunitat"
            else:
                share_vel_val = None

        # Base comuna de l'alerta
        alert = {
            "id_cliente": int(row["id_cliente"]),
            "provincia": provincia_map.get(row["id_cliente"], "") if provincia_map else "",
            "cod_postal": None,
            "city": None,
            "latitude": None,
            "longitude": None,
            "familia_potencial": row["familia_potencial"],
            "segment": "leal" if row["share_12m"] >= 0.70 else "promiscuo",
            "segment_anterior": None,
            "share_12m": round(float(row["share_12m"]), 3),
            "potencial_anual_eur": round(float(row["potencial_eur"]), 2),
            "euros_12m": round(float(row["euros_12m"]), 2),
            "gap_eur": round(float(row["gap_eur"]), 2),
            "dies_sense_compra": dies_sense,
            "num_intervals": int(row["num_intervals"]),
            "cicle_mig_dies": round(float(cicle), 1),
            "cicle_std_dies": round(float(cicle_std), 1),
            "proxim_pedido_esperat": proper_pedido.strftime("%Y-%m-%d"),
            "data_alerta": today,
            "share_velocity": share_vel_val,
            "share_alerta": share_alerta,
            "geo_neighbor_count": None,
            "geo_neighbor_avg_share": None,
            "geo_share_gap": None,
        }

        # ═══════════════════════════════════════════════
        # ANTICIPACIÓ — alerta abans de la data prevista
        # ═══════════════════════════════════════════════
        if 0 < dies_per_proper <= K:
            alert["tipus_alerta"] = "anticipacio"
            alert["urgencia"] = "baixa"
            alert["canal"] = "televenda"
            alert["dies_retard"] = 0
            alert["z_score"] = 0.0
            alert["dies_stock"] = float(dies_per_proper)

            alert["prioritat"] = round(
                alert["gap_eur"] * PROB_ANTICIPACIO, 2
            )

            alert["motiu"] = (
                f"Client amb historial de {row['familia_potencial']}. "
                f"Proper pedido esperat en {dies_per_proper:.0f} dies "
                f"(cicle habitual: {cicle:.0f} dies ±{cicle_std:.0f}). "
                f"ANTICIPACIÓ: contactar per avançar-se a la compra."
            )
            alerts.append(alert)

        # ═══════════════════════════════════════════════
        # REACTIVA — alerta després de la data prevista
        # ═══════════════════════════════════════════════
        elif dies_per_proper <= 0:
            dies_retard = abs(dies_per_proper)
            z_score = dies_retard / cicle_std if cicle_std > 0 else 0.0
            retard_ratio = dies_retard / max(cicle, 1.0)

            alert["dies_retard"] = int(dies_retard)
            alert["z_score"] = round(float(z_score), 2)
            alert["dies_stock"] = None

            if retard_ratio >= 3.0:
                alert["urgencia"] = "critica"
                alert["canal"] = "delegat"
            elif retard_ratio >= 1.5:
                alert["urgencia"] = "alta"
                alert["canal"] = "delegat"
            elif retard_ratio >= 0.5:
                alert["urgencia"] = "mitjana"
                alert["canal"] = "televenda"
            else:
                alert["urgencia"] = "baixa"
                alert["canal"] = "televenda"

            alert["tipus_alerta"] = "reactiva"
            urgencia_score = {"critica": 4, "alta": 3, "mitjana": 2, "baixa": 1}.get(alert["urgencia"], 1)
            alert["prioritat"] = round(
                urgencia_score * 100000 + min(alert["gap_eur"], 99999), 2
            )

            alert["motiu"] = (
                f"Client de {row['familia_potencial']} que HAURIA D'HAVER COMPRAT. "
                f"Pedido esperat fa {dies_retard:.0f} dies "
                f"(cicle: {cicle:.0f} dies ±{cicle_std:.0f}). "
                f"Porta {dies_sense} dies sense comprar. "
                + (
                    "Risc alt de pèrdua — intervenció urgent."
                    if retard_ratio >= 1.0
                    else "Cal reactivar contacte."
                )
            )
            alerts.append(alert)

    if not alerts:
        return pd.DataFrame()

    alerts_df = pd.DataFrame(alerts)
    if "prioritat" in alerts_df.columns:
        alerts_df = alerts_df.sort_values("prioritat", ascending=False).reset_index(drop=True)
    return alerts_df


def generate_fugats(cycles, sow, today, provincia_map=None):
    """Genera alertes per clients FUGATS (>365 dies sense comprar).

    Aquests clients NO surten a la llista principal d'anticipacio/reactiva.
    Van a un llistat separat per tenir-los controlats.
    """
    today_ts = pd.Timestamp(today)
    alerts = []

    data = cycles.merge(sow, on=["id_cliente", "familia_potencial"], how="left")
    data["euros_12m"] = data["euros_12m"].fillna(0)
    data["share_12m"] = data["share_12m"].fillna(0)
    data["gap_eur"] = data["gap_eur"].fillna(0)
    data["potencial_eur"] = data["potencial_eur"].fillna(0)

    for _, row in data.iterrows():
        if pd.isna(row["data_ultim_pedido"]):
            continue

        dies_sense = int((today_ts - row["data_ultim_pedido"]).days)

        # Fugat: >365 dies sense comprar O share = 0%
        if dies_sense <= DIES_FUGAT_THR and row["share_12m"] > 0:
            continue

        cicle = row["cicle_mig_dies"] if not pd.isna(row["cicle_mig_dies"]) else None
        cicle_std = row["cicle_std_dies"] if (
            not pd.isna(row["cicle_std_dies"]) and row["cicle_std_dies"] > 0
        ) else (cicle * 0.30 if cicle is not None else None)

        alert = {
            "id_cliente": int(row["id_cliente"]),
            "provincia": provincia_map.get(row["id_cliente"], "") if provincia_map else "",
            "cod_postal": None,
            "city": None,
            "latitude": None,
            "longitude": None,
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
            "cicle_mig_dies": round(float(cicle), 1) if cicle is not None else None,
            "cicle_std_dies": round(float(cicle_std), 1) if cicle_std is not None else None,
            "dies_retard": 0,
            "z_score": None,
            "proxim_pedido_esperat": None,
            "dies_stock": None,
            "prioritat": round(float(row["gap_eur"]) * 0.01, 2),
            "motiu": (
                f"Client FUGAT de {row['familia_potencial']}. "
                f"Porta MÉS D'UN ANY sense comprar ({dies_sense} dies). "
                + (f"Cicle habitual era: {cicle:.0f} dies. " if cicle is not None else "")
                + "Requereix recuperació."
            ),
            "data_alerta": today,
            "share_velocity": None,
            "share_alerta": None,
            "geo_neighbor_count": None,
            "geo_neighbor_avg_share": None,
            "geo_share_gap": None,
        }
        alerts.append(alert)

    return pd.DataFrame(alerts) if alerts else pd.DataFrame()


def run(today=None, family=None, verbose=False):
    """Executa el motor complet de predicció i alertes per commodities.

    Args:
        today: Data de referència (str YYYY-MM-DD o datetime). Per defecte: avui.
        family: Nom de família per filtrar ('Anestesia', 'Bioseguridad') o None (totes).
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
        print(f"╔═ Motor Predicció Commodities ════ Data: {today} ═╗")
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

    # ── 2. Càlcul de cicles ──────────────────────────────
    if verbose:
        print("🔄 Cicles de reposició...", end=" ")
    cycles = calc_restock_cycle(raw)
    if verbose:
        n_amb_cicle = cycles["cicle_mig_dies"].notna().sum()
        print(f"{len(cycles):,} parelles ({n_amb_cicle:,} amb cicle)")

    # ── 3. Share of wallet ───────────────────────────────
    if verbose:
        print("💰 Share of wallet 12m...", end=" ")
    sow = calc_sow_and_gap(raw, today)
    if verbose:
        print(f"{len(sow):,} parelles")

    # ── 4. Share velocity (derivada mensual) ─────────────
    share_vel_df = calc_share_velocity(raw, today)
    share_vel_map = {
        (int(r["id_cliente"]), r["familia_potencial"]): r["share_velocity"]
        for _, r in share_vel_df.iterrows()
    } if not share_vel_df.empty else {}

    # ── 5. Mapa de províncies ────────────────────────────
    prov_map = raw[["id_cliente", "provincia"]].drop_duplicates()
    prov_map = prov_map.groupby("id_cliente")["provincia"].first().to_dict()

    # ── 6. Generar alertes principals ────────────────────
    if verbose:
        print("🔔 Generant alertes (anticipació + reactiva)...", end=" ")
    alerts = generate_alerts(cycles, sow, today, prov_map, share_vel=share_vel_map)
    if verbose:
        print(f"{len(alerts):,} alertes generades")
        if len(alerts) > 0:
            for tipus, count in alerts["tipus_alerta"].value_counts().items():
                print(f"   {tipus:>15s}: {count}")

    # ── 7. Generar alertes geogràfiques ────────────────
    if verbose:
        print("🗺️  Generant alertes geogràfiques...", end=" ")
    geo_alerts, geo_points = generate_geographical_alerts(cycles, sow, today, raw)
    if verbose:
        print(f"{len(geo_alerts)} alertes · {len(geo_points)} punts geolocalitzats")

    if not geo_alerts.empty:
        alerts = pd.concat([alerts, geo_alerts], ignore_index=True)

    # ── 8. Generar alertes de fugats ────────────────────
    if verbose:
        print("👻 Generant llista de fugats (>365 dies)...", end=" ")
    fugats = generate_fugats(cycles, sow, today, prov_map)
    n_fugats = len(fugats)
    if verbose:
        print(f"{n_fugats} clients fugats")

    # Combinar: fugats van al final (baixa prioritat)
    alerts = pd.concat([alerts, fugats], ignore_index=True) if not fugats.empty else alerts

    if len(alerts) > 0 and "prioritat" in alerts.columns:
        alerts = alerts.sort_values("prioritat", ascending=False).head(MAX_ALERTS).reset_index(drop=True)

    # ── 9. Top alertes ───────────────────────────────────
    actives = alerts[alerts["tipus_alerta"] != "fugat"] if len(alerts) > 0 else pd.DataFrame()
    if verbose and len(actives) > 0:
        print(f"\n{'─' * 60}")
        print("TOP 5 ALERTES PRIORITZADES (excloent fugats)")
        print(f"{'─' * 60}")
        for i, (_, a) in enumerate(actives.head(5).iterrows()):
            print(f"\n{i + 1}. #{a['id_cliente']}  |  {a.get('provincia', '?'):15s}  |  {a['familia_potencial']}")
            print(f"   🔸 {a['tipus_alerta']:>15s}  |  {a['urgencia']:>8s}")
            print(f"   Gap: {a['gap_eur']:>8.0f}€  |  Prioritat: {a['prioritat']:.1f}")
            print(f"   Pròxim pedido: {a['proxim_pedido_esperat']}  |  Cicle: {a['cicle_mig_dies']:.0f}d")
            print(f"   {a['motiu'][:130]}")

    # ── 10. Resum ────────────────────────────────────────
    if verbose:
        gap_total = alerts["gap_eur"].sum() if len(alerts) > 0 else 0
        n_actius = alerts[alerts["tipus_alerta"] != "fugat"]["id_cliente"].nunique() if len(alerts) > 0 else 0
        print(f"\n{'─' * 60}")
        print(f"📊 RESUM: {n_actius} clients amb alerta activa + {n_fugats} fugats")
        print(f"   Gap total recuperable: {gap_total:,.0f}€/any")
        if len(actives) > 0:
            print(f"   Prioritat mitjana (actives): {actives['prioritat'].mean():.0f}")

    # ── Segments (per compatibilitat amb ensure_cache) ───
    segments = cycles.merge(sow, on=["id_cliente", "familia_potencial"], how="left")
    segments["segment"] = segments["cicle_mig_dies"].apply(
        lambda x: "amb_historial" if not pd.isna(x) else "sense_historial"
    )

    return alerts, segments
