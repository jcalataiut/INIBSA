"""
Motor de Segmentació i Alertes — Commodities (Anestèsia + Bioseguretat)
======================================================================

QUÈ FA:
  Per cada (client, família) de productes commodity, calcula:
    1. Share of wallet rolling 12 mesos (vs Potencial_EUR_anual)
    2. Cicle de reposició (dies entre pedidos consecutius)
    3. Segment actual (fidel, promiscu, marginal, en_risc, nou, perdut)
    4. Alertes prioritzades: reposició, risc de fuga, finestra de captura

COM S'USA:
    python commodities/commodities_engine.py
    python commodities/commodities_engine.py --today 2025-12-01
    python commodities/commodities_engine.py --family Anestesia
    python commodities/commodities_engine.py --output alertes.csv

OUTPUT:
    CSV amb alertes prioritzades, una fila per (client, família) que requereix acció.

DEPENDÈNCIES:
    pandas, numpy
"""

import pandas as pd
import numpy as np
import sys
import argparse
from datetime import datetime, timedelta

# =============================================================================
# CONFIGURACIÓ — Llindars de negoci ajustables
# =============================================================================
DATA_PATH = 'data/master_commodities_clean.csv'
POTENCIAL_COL = 'Potencial_EUR'  # al clean CSV (build_dataset.py genera _anual)

# ── Segmentació — llindars del README §5.2 ────────────────────────────────────
SHARE_FIDEL_THR = 0.70        # > 70% del seu potencial a Inibsa → fidel
SHARE_MARGINAL_THR = 0.20     # < 20% del potencial → marginal (poc vinculat)
DIES_PERDUT_THR = 90          # sense compra > 90 dies i tenia historial → perdut (README)
DIES_NOU_THR = 90             # < 90 dies des del primer pedido → nou (≡ 3 mesos)
DIES_HISTORIAL_MIN = 180      # cal tenir ≥ 180 dies d'historial per no ser "nou"

# ── Detecció de tendència (en_risc) ──────────────────────────────────────────
RATIO_EN_RISC = 0.75          # share_3m_annualized < share_12m * RATIO → en_risc
NUM_INTERVALS_MIN = 3         # cal ≥ 3 intervals per tenir patró fiable

# ── Alertes — llindars del README §5.2 ────────────────────────────────────────
LLINDAR_GROC_STD = 0.0        # qualsevol retard → alerta de reposició
LLINDAR_TARONJA_STD = 1.5     # > 1.5σ → risc moderat
LLINDAR_VERMELL_STD = 2.5     # > 2.5σ → risc alt de fuga
FINESTRA_CAPTURA_DIES = 3     # ±3 dies al voltant del proper pedido esperat (captura promiscus)


# =============================================================================
# 1. CÀRREGA I NETEJA
# =============================================================================
def load_data(path=DATA_PATH):
    """Carrega el dataset de commodities net i prepara les variables base."""
    df = pd.read_csv(path, low_memory=False)
    df['Fecha'] = pd.to_datetime(df['Fecha'])

    # Només vendes netes: excloent devolucions
    df = df[df['es_devolucion'] == 0].copy()

    # Potencial: assegurar que és numèric
    df[POTENCIAL_COL] = pd.to_numeric(df[POTENCIAL_COL], errors='coerce')

    return df


def build_monthly_aggregate(df):
    """Agrega vendes per (client, família, mes).

    Una fila per mes. Excloem devolucions. Marquem si hi va haver campanya.
    """
    df['any_mes'] = df['Fecha'].dt.to_period('M')

    agg = df.groupby(
        ['Id_Cliente', 'Familia_Potencial', 'any_mes'],
        as_index=False
    ).agg(
        euros_venuts=('Valores_H', 'sum'),
        num_pedidos=('Num.Fact', 'nunique'),
        unitats=('Unidades', 'sum'),
        en_campana=('en_campana', 'max'),
    )
    agg['anyo'] = agg['any_mes'].dt.year
    agg['mes'] = agg['any_mes'].dt.month
    return agg


# =============================================================================
# 2. SHARE OF WALLET ROLLING + TENDÈNCIA
# =============================================================================
def calc_rolling_share(monthly):
    """Calcula share of wallet rolling 12m i 3m (aquest últim anualitzat).

    share_wallet_12m: euros últims 12 mesos / Potencial_anual
    share_wallet_3m_annualized: (euros últims 3 mesos * 4) / Potencial_anual
    """
    monthly = monthly.sort_values(['Id_Cliente', 'Familia_Potencial', 'any_mes'])

    # Rolling 12 meses
    monthly['euros_12m'] = (
        monthly.groupby(['Id_Cliente', 'Familia_Potencial'])['euros_venuts']
        .transform(lambda s: s.rolling(12, min_periods=1).sum())
    )
    # Rolling 3 meses (per tendència)
    monthly['euros_3m'] = (
        monthly.groupby(['Id_Cliente', 'Familia_Potencial'])['euros_venuts']
        .transform(lambda s: s.rolling(3, min_periods=1).sum())
    )
    return monthly


def attach_potencial(monthly, raw_df):
    """Mergeja el Potencial_EUR i calcula els shares."""
    potencial = raw_df[[
        'Id_Cliente', 'Familia_Potencial', POTENCIAL_COL
    ]].drop_duplicates()

    monthly = monthly.merge(potencial, on=['Id_Cliente', 'Familia_Potencial'], how='left')

    # Share 12m capped at 1.0 (ratio 0-100%). Si supera el potencial,
    # el client està completament capturat — tractar com share=100%.
    monthly['share_12m'] = (monthly['euros_12m'] / monthly[POTENCIAL_COL]).clip(0, 1)
    monthly['share_3m_annualized'] = (
        (monthly['euros_3m'] * 4) / monthly[POTENCIAL_COL]
    ).clip(0, 1)

    # Gap = euros no capturats (anual). Si share ≥ 100%, gap = 0.
    monthly['gap_eur'] = (monthly[POTENCIAL_COL] - monthly['euros_12m']).clip(lower=0)

    return monthly


# =============================================================================
# 3. CICLE DE REPOSICIÓ
# =============================================================================
def calc_restock_cycle(df):
    """Calcula cicle de reposició per (client, família) des de dates de factura.

    Per cada parella client-família, pren totes les dates de pedido,
    calcula intervals entre dies consecutius, i n'extreu:
      - cicle_mig_dies: interval mitjà
      - cicle_std_dies: desviació estàndard
      - num_intervals: nombre d'intervals (fiabilitat)
      - data_ultim_pedido, data_primer_pedido
    """
    facturas = df[[
        'Id_Cliente', 'Familia_Potencial', 'Num.Fact', 'Fecha'
    ]].drop_duplicates().sort_values([
        'Id_Cliente', 'Familia_Potencial', 'Fecha'
    ])

    records = []
    for (cli, fam), grp in facturas.groupby(['Id_Cliente', 'Familia_Potencial']):
        dates = grp['Fecha'].values
        if len(dates) < 2:
            records.append({
                'Id_Cliente': cli, 'Familia_Potencial': fam,
                'cicle_mig_dies': np.nan, 'cicle_std_dies': np.nan,
                'num_intervals': 0,
                'data_ultim_pedido': dates[-1] if len(dates) else pd.NaT,
                'data_primer_pedido': dates[0] if len(dates) else pd.NaT,
            })
        else:
            diffs = np.diff(dates.astype('datetime64[D]')).astype(float)
            records.append({
                'Id_Cliente': cli, 'Familia_Potencial': fam,
                'cicle_mig_dies': diffs.mean(), 'cicle_std_dies': diffs.std(),
                'num_intervals': len(diffs),
                'data_ultim_pedido': dates[-1], 'data_primer_pedido': dates[0],
            })

    cycles = pd.DataFrame(records)
    cycles['data_ultim_pedido'] = pd.to_datetime(cycles['data_ultim_pedido'])
    cycles['data_primer_pedido'] = pd.to_datetime(cycles['data_primer_pedido'])
    return cycles


# =============================================================================
# 4. SEGMENTACIÓ
# =============================================================================
def segment_client(row):
    """Classifica un (client, família) segons l'estat actual.

    Ordre (README §5.2):
      1. 'nou': < 90 dies d'historial
      2. 'perdut': > 90 dies sense compra + tenia historial previ
      3. 'en_risc': era fidel/promiscu, tendència decreixent últims 3m
      4. 'fidel': share > 70%, compra regular
      5. 'promiscu': share 20-70%, compra regular però parcial
      6. 'marginal': share < 20%, molt per sota del potencial
    """
    dies_hist = row['dies_historial']
    dies_sense = row['dies_sense_compra']
    share_12m = row['share_12m']
    tendencia = row.get('tendencia_negativa', False)

    if dies_hist < DIES_NOU_THR:
        return 'nou'

    if dies_sense > DIES_PERDUT_THR and dies_hist > DIES_HISTORIAL_MIN:
        return 'perdut'

    if tendencia and share_12m > SHARE_MARGINAL_THR:
        return 'en_risc'

    if share_12m >= SHARE_FIDEL_THR:
        return 'fidel'

    if share_12m >= SHARE_MARGINAL_THR:
        return 'promiscu'

    return 'marginal'


def segment_all(monthly, cycles, today):
    """Aplica segmentació a tots els (client, família) a data 'today'.

    Agafa l'últim mes disponible per cada parella i classifica.
    """
    today_ts = pd.Timestamp(today)

    # Últim mes per cada (client, família)
    latest = monthly.loc[
        monthly.groupby(['Id_Cliente', 'Familia_Potencial'])['any_mes'].idxmax()
    ].copy()

    # Merge amb cicles
    latest = latest.merge(
        cycles, on=['Id_Cliente', 'Familia_Potencial'], how='left'
    )

    # Mètriques temporals
    latest['data_ultim_pedido'] = pd.to_datetime(latest['data_ultim_pedido'])
    latest['data_primer_pedido'] = pd.to_datetime(latest['data_primer_pedido'])
    latest['dies_sense_compra'] = (today_ts - latest['data_ultim_pedido']).dt.days
    latest['dies_historial'] = (today_ts - latest['data_primer_pedido']).dt.days

    # Tendència: el share anualitzat dels últims 3 mesos (share_3m_annualized)
    # ha caigut per sota del share_12m * RATIO_EN_RISC ?
    latest['tendencia_negativa'] = (
        (latest['share_3m_annualized'] < latest['share_12m'] * RATIO_EN_RISC)
        & (latest['num_intervals'] >= NUM_INTERVALS_MIN)
    )

    # Aplicar segmentació
    latest['segment'] = latest.apply(segment_client, axis=1)

    # Segment anterior (per context a l'alerta)
    # Si ara és en_risc, quin segment tenia abans? Ho inferim del share_12m
    segment_prev_map = {
        'en_risc': latest['share_12m'].apply(
            lambda s: 'fidel' if s >= SHARE_FIDEL_THR else (
                'promiscu' if s >= SHARE_MARGINAL_THR else 'marginal'
            )
        )
    }
    for seg, prev in segment_prev_map.items():
        latest.loc[latest['segment'] == seg, 'segment_anterior'] = prev

    return latest


# =============================================================================
# 5. GENERACIÓ D'ALERTES
# =============================================================================
def generate_alerts(segments, today, provincia_map=None):
    """Genera alertes prioritzades per cada (client, família) que requereix acció.

    Retorna un DataFrame amb una fila per alerta, ordenat per prioritat desc.
    """
    today_ts = pd.Timestamp(today)
    alerts = []

    # Factors de probabilitat de conversió per segment (README §5.4)
    # Perdut té prob molt baixa: han deixat de comprar, recuperar és difícil
    PROB_CONVERSIO = {
        'fidel': 0.8,
        'promiscu': 0.6,
        'marginal': 0.2,
        'en_risc': 0.9,
        'perdut': 0.05,
        'nou': 0.4,
    }

    def calc_prioritat(gap, dies_retard, cicle_mig, prob):
        """prioritat = gap × urgència × prob (README §5.4)

        urgència_temporal = max(0.1, min(1.0, dies_retard / cicle_mig))
        La urgència es capa a 1.0: un client amb retard ≥ 1 cicle ja té
        la màxima urgència. Més retard no incrementa l'acció immediata.
        """
        if cicle_mig and cicle_mig > 0 and not pd.isna(cicle_mig):
            cicle_segur = max(14, cicle_mig)
            urgencia = max(0.1, min(1.0, dies_retard / cicle_segur))
        else:
            urgencia = 0.5
        return round(gap * urgencia * prob, 2)

    for _, row in segments.iterrows():
        alert = {
            'Id_Cliente': row['Id_Cliente'],
            'Provincia': provincia_map.get(row['Id_Cliente'], '') if provincia_map else '',
            'Familia_Potencial': row['Familia_Potencial'],
            'segment': row['segment'],
            'share_12m': round(row['share_12m'], 3),
            'potencial_anual_eur': round(row[POTENCIAL_COL], 2),
            'euros_12m': round(row['euros_12m'], 2),
            'gap_eur': round(row['gap_eur'], 2),
            'dies_sense_compra': int(row['dies_sense_compra']),
            'data_alerta': today,
        }

        cicle_mig = row['cicle_mig_dies']
        cicle_std = row['cicle_std_dies']
        dies_sense = row['dies_sense_compra']
        segment = row['segment']

        # ── PERDUT ─────────────────────────────────────────────────────
        if segment == 'perdut':
            # Perdut amb potencial molt baix → skip (no val l'esforç)
            impacte = max(alert['gap_eur'], row[POTENCIAL_COL] * 0.5)
            if impacte < 200:
                continue
            alert['tipus_alerta'] = 'perdut'
            alert['urgencia'] = 'baixa'
            alert['canal'] = 'televenda'
            if cicle_mig and not pd.isna(cicle_mig):
                alert['cicle_mig_dies'] = round(cicle_mig, 1)
                alert['dies_retard'] = int(max(0, dies_sense - cicle_mig))
            else:
                alert['cicle_mig_dies'] = None
                alert['dies_retard'] = dies_sense
            alert['prioritat'] = calc_prioritat(
                impacte, alert['dies_retard'],
                cicle_mig if (cicle_mig and not pd.isna(cicle_mig)) else None,
                PROB_CONVERSIO['perdut']
            )
            alert['motiu'] = (
                f"Client sense comprar des de fa {dies_sense} dies. "
                f"Historial previ de {row['dies_historial']:.0f} dies. "
                f"Possible pèrdua de compte. Requereix trucada de reactivació."
            )
            alerts.append(alert)
            continue

        # ── NOU ────────────────────────────────────────────────────────
        if segment == 'nou':
            alert['tipus_alerta'] = 'monitoritzar'
            alert['urgencia'] = 'baixa'
            alert['canal'] = 'televenda'
            alert['cicle_mig_dies'] = round(cicle_mig, 1) if (cicle_mig and not pd.isna(cicle_mig)) else None
            alert['dies_retard'] = 0
            alert['prioritat'] = calc_prioritat(
                alert['gap_eur'], 0, None, PROB_CONVERSIO['nou']
            )
            alert['motiu'] = (
                f"Client NOU ({row['dies_historial']:.0f} dies d'historial). "
                f"Primers pedidos registrats. Fer seguiment de consolidació "
                f"per assegurar fidelització."
            )
            alerts.append(alert)
            continue

        # ── EN RISC ────────────────────────────────────────────────────
        if segment == 'en_risc':
            retard = 0
            z_score = 0
            if cicle_mig and not pd.isna(cicle_mig):
                proper = row['data_ultim_pedido'] + pd.Timedelta(days=cicle_mig)
                retard = max(0, (today_ts - proper).days)
                z_score = retard / cicle_std if (cicle_std and cicle_std > 0) else 0

            alert['tipus_alerta'] = 'risc_fuga'
            alert['dies_retard'] = int(retard)
            alert['z_score'] = round(z_score, 2)
            alert['cicle_mig_dies'] = round(cicle_mig, 1) if (cicle_mig and not pd.isna(cicle_mig)) else None
            alert['prioritat'] = calc_prioritat(
                alert['gap_eur'], retard,
                cicle_mig if (cicle_mig and not pd.isna(cicle_mig)) else None,
                PROB_CONVERSIO['en_risc']
            )

            share_3m = row['share_3m_annualized']
            share_12m = row['share_12m']
            canvi_pct = (share_3m - share_12m) / share_12m * 100 if share_12m > 0 else 0

            alert['urgencia'] = 'alta' if canvi_pct < -30 else 'mitjana'
            alert['canal'] = 'delegat' if alert['urgencia'] == 'alta' else 'televenda'
            alert['motiu'] = (
                f"Client en RISC de fuga ({row.get('segment_anterior', 'actiu')}). "
                f"Share 12m: {share_12m:.0%} → Share últims 3m anualitzat: {share_3m:.0%} "
                f"({canvi_pct:+.0f}%). "
                f"Gap: {alert['gap_eur']:.0f}€/any. "
                f"Tendència negativa clara. Intervenir amb urgència."
            )
            alerts.append(alert)
            continue

        # ── FIDEL / PROMISCU / MARGINAL: cicle de reposició si tenim dades ─
        if cicle_mig is None or pd.isna(cicle_mig):
            if segment in ('fidel', 'promiscu'):
                alert['tipus_alerta'] = 'info'
                alert['urgencia'] = 'baixa'
                alert['canal'] = 'televenda'
                alert['cicle_mig_dies'] = None
                alert['dies_retard'] = 0
                alert['prioritat'] = calc_prioritat(
                    alert['gap_eur'], 0, None, PROB_CONVERSIO[segment]
                )
                alert['motiu'] = (
                    f"Client {segment.upper()}. Sense dades suficients per "
                    f"calcular cicle de reposició. Contacte proactiu recomanat."
                )
                alerts.append(alert)
            elif segment == 'marginal':
                alert['tipus_alerta'] = 'oportunitat_captura'
                alert['urgencia'] = 'baixa'
                alert['canal'] = 'televenda'
                alert['cicle_mig_dies'] = None
                alert['dies_retard'] = 0
                alert['prioritat'] = calc_prioritat(
                    alert['gap_eur'], 0, None, PROB_CONVERSIO['marginal']
                )
                alert['motiu'] = (
                    f"Client MARGINAL ({row['share_12m']:.0%} share). "
                    f"Gap de captura: {alert['gap_eur']:.0f}€/any. "
                    f"Baixa vinculació amb Inibsa. Cal investigar."
                )
                alerts.append(alert)
            continue

        # Tenim cicle calculat
        proper_pedido = row['data_ultim_pedido'] + pd.Timedelta(days=cicle_mig)
        dies_retard = max(0, (today_ts - proper_pedido).days)
        z_score = dies_retard / cicle_std if (cicle_std and cicle_std > 0) else 0

        alert['dies_retard'] = int(dies_retard)
        alert['z_score'] = round(z_score, 2)
        alert['cicle_mig_dies'] = round(cicle_mig, 1)
        alert['proxim_pedido_esperat'] = proper_pedido.strftime('%Y-%m-%d')

        if segment == 'fidel':
            if dies_retard > 0:
                if z_score >= LLINDAR_VERMELL_STD:
                    alert['tipus_alerta'] = 'risc_fuga'
                    alert['urgencia'] = 'alta'
                    alert['canal'] = 'delegat'
                    alert['motiu'] = (
                        f"Client FIDEL d'{row['Familia_Potencial']} amb risc de FUGA. "
                        f"Cicle habitual: {cicle_mig:.0f} dies. Porta {dies_sense} dies "
                        f"sense comprar ({dies_retard} dies de retard, z={z_score:.1f}). "
                        f"Prioritat màxima."
                    )
                elif z_score >= LLINDAR_TARONJA_STD:
                    alert['tipus_alerta'] = 'reposicio_endarrerida'
                    alert['urgencia'] = 'mitjana'
                    alert['canal'] = 'televenda'
                    alert['motiu'] = (
                        f"Client FIDEL d'{row['Familia_Potencial']} amb reposició endarrerida. "
                        f"Cicle habitual: {cicle_mig:.0f} dies. Retard de {dies_retard} dies "
                        f"(z={z_score:.1f}). Contactar per confirmar estat."
                    )
                else:  # groc
                    alert['tipus_alerta'] = 'reposicio_pendent'
                    alert['urgencia'] = 'baixa'
                    alert['canal'] = 'televenda'
                    alert['motiu'] = (
                        f"Client FIDEL d'{row['Familia_Potencial']} amb lleuger retard "
                        f"({dies_retard} dies). Cicle habitual: {cicle_mig:.0f} dies. "
                        f"Seguiment rutina."
                    )
                alert['prioritat'] = calc_prioritat(
                    alert['gap_eur'], dies_retard, cicle_mig, PROB_CONVERSIO['fidel']
                )
                alerts.append(alert)
            # tot normal, no cal alerta

        elif segment == 'promiscu':
            dies_restants = -dies_retard  # negatiu = encara no ha passat el proper pedido
            if abs(dies_restants) <= FINESTRA_CAPTURA_DIES or dies_retard > 0:
                alert['tipus_alerta'] = 'finestra_captura'
                alert['canal'] = 'delegat'
                if dies_retard > 0:
                    alert['urgencia'] = 'alta'
                else:
                    alert['urgencia'] = 'mitjana'
                alert['prioritat'] = calc_prioritat(
                    alert['gap_eur'], dies_retard, cicle_mig, PROB_CONVERSIO['promiscu']
                )
                alert['motiu'] = (
                    f"Client PROMISCU d'{row['Familia_Potencial']} en FINESTRA DE CAPTURA. "
                    f"Cicle: {cicle_mig:.0f} dies. Share: {row['share_12m']:.0%}. "
                    f"Gap: {alert['gap_eur']:.0f}€/any. "
                    f"{'Retard en reposició urgent.' if dies_retard > 0 else 'Moment òptim per contactar.'}"
                )
                alerts.append(alert)

        elif segment == 'marginal':
            alert['tipus_alerta'] = 'oportunitat_captura'
            alert['urgencia'] = 'baixa'
            alert['canal'] = 'televenda'
            alert['dies_retard'] = 0
            alert['z_score'] = 0
            alert['prioritat'] = calc_prioritat(
                alert['gap_eur'], 0, cicle_mig, PROB_CONVERSIO['marginal']
            )
            alert['motiu'] = (
                f"Client MARGINAL d'{row['Familia_Potencial']}. "
                f"Share: {row['share_12m']:.0%}. Gap: {alert['gap_eur']:.0f}€/any. "
                f"Baixa vinculació. Cal investigar."
            )
            alerts.append(alert)

    if not alerts:
        return pd.DataFrame()

    alerts_df = pd.DataFrame(alerts)
    if 'prioritat' in alerts_df.columns:
        alerts_df = alerts_df.sort_values('prioritat', ascending=False).reset_index(drop=True)
    return alerts_df


# =============================================================================
# 6. EXECUCIÓ PRINCIPAL
# =============================================================================
def run(today=None, family=None, output_path=None, verbose=True):
    """Executa el motor complet de commodities.

    Args:
        today: Data de referència (str YYYY-MM-DD o datetime). Per defecte: avui.
        family: Nom de família per filtrar ('Anestesia', 'Bioseguridad') o None (totes).
        output_path: Ruta CSV de sortida. Si None, no guarda.
        verbose: Mostra output per consola.

    Returns:
        DataFrame amb alertes prioritzades.
    """
    if today is None:
        today = datetime.now().strftime('%Y-%m-%d')
    if isinstance(today, datetime):
        today = today.strftime('%Y-%m-%d')

    if verbose:
        print(f"╔═ Motor Commodities ════ Data: {today} {'═' * 30}")
        if family:
            print(f"║  Família: {family}")
        print(f"╚{'═' * 55}")

    # ── 1. Carregar ────────────────────────────────────────────────────────
    if verbose:
        print("📥 Carregant dades...", end=' ')
    raw = load_data(DATA_PATH)

    if family:
        raw = raw[raw['Familia_Potencial'] == family]
        if verbose:
            print(f"({family})", end=' ')

    if verbose:
        print(f"{len(raw):,} línies · {raw['Id_Cliente'].nunique():,} clients")

    # ── 2. Agregació mensual ───────────────────────────────────────────────
    if verbose:
        print("📊 Agregant mensual...", end=' ')
    monthly = build_monthly_aggregate(raw)
    if verbose:
        print(f"{len(monthly):,} files")

    # ── 3. Share of wallet rolling ─────────────────────────────────────────
    if verbose:
        print("💰 Rolling 12m + 3m...", end=' ')
    monthly = calc_rolling_share(monthly)
    monthly = attach_potencial(monthly, raw)
    if verbose:
        print("✓")

    # ── 4. Cicle de reposició ──────────────────────────────────────────────
    if verbose:
        print("🔄 Cicles de reposició...", end=' ')
    cycles = calc_restock_cycle(raw)
    if verbose:
        n_fiable = (cycles['num_intervals'] >= 3).sum()
        print(f"{len(cycles):,} parelles ({n_fiable:,} fiables)")
    # ── 5. Segmentació ─────────────────────────────────────────────────────
    if verbose:
        print("🏷️  Segmentant...", end=' ')
    segments = segment_all(monthly, cycles, today)

    # Guardar províncies per a les alertes
    prov_map = raw[['Id_Cliente', 'Provincia']].drop_duplicates()
    prov_map = prov_map.groupby('Id_Cliente')['Provincia'].first().to_dict()

    if verbose:
        dist = segments['segment'].value_counts()
        print(f"{len(segments):,} parelles")
        for seg in ['fidel', 'promiscu', 'marginal', 'en_risc', 'nou', 'perdut']:
            c = dist.get(seg, 0)
            pct = c / len(segments) * 100
            print(f"   {seg:>12s}: {c:>5d}  ({pct:5.1f}%)")

    # ── 6. Alertes ─────────────────────────────────────────────────────────
    if verbose:
        print("🔔 Alertes...", end=' ')
    alerts = generate_alerts(segments, today, prov_map)
    if verbose:
        print(f"{len(alerts):,} alertes generades")
        if len(alerts) > 0:
            for tipus, count in alerts['tipus_alerta'].value_counts().items():
                print(f"   {tipus:>25s}: {count}")

    # ── Top 10 ─────────────────────────────────────────────────────────────
    if verbose and len(alerts) > 0:
        print(f"\n{'─' * 60}")
        print("TOP 10 ALERTES PRIORITZADES")
        print(f"{'─' * 60}")
        cols = ['Id_Cliente', 'Provincia', 'Familia_Potencial', 'tipus_alerta',
                'urgencia', 'gap_eur', 'prioritat', 'segment']
        display_cols = [c for c in cols if c in alerts.columns]
        for i, (_, a) in enumerate(alerts.head(10).iterrows()):
            print(f"\n{i + 1}. #{a['Id_Cliente']}  |  {a.get('Provincia', '?'):15s}  |  {a['Familia_Potencial']}")
            print(f"   🔸 {a['tipus_alerta']:>25s}  |  {a['urgencia']:>8s}  |  {a['segment']}")
            print(f"   Gap: {a['gap_eur']:>8.0f}€  |  Prioritat: {a['prioritat']:.1f}")
            print(f"   {a['motiu'][:130]}")

    # ── Resum ──────────────────────────────────────────────────────────────
    if verbose:
        gap_total = alerts['gap_eur'].sum() if len(alerts) > 0 else 0
        print(f"\n{'─' * 60}")
        print(f"📊 RESUM: {alerts['Id_Cliente'].nunique() if len(alerts) > 0 else 0} clients amb alerta")
        print(f"   Gap total recuperable: {gap_total:,.0f}€/any")
        if len(alerts) > 0:
            print(f"   Prioritat mitjana: {alerts['prioritat'].mean():.0f}")

    # ── Guardar ────────────────────────────────────────────────────────────
    if output_path and len(alerts) > 0:
        alerts.to_csv(output_path, index=False)
        if verbose:
            print(f"💾 Guardat a {output_path}")

    return alerts


# =============================================================================
# MAIN
# =============================================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Motor Commodities — Smart Demand Signals (Inibsa · Interhack BCN 2026)'
    )
    parser.add_argument('--today', type=str, default=None,
                        help='Data de referència (YYYY-MM-DD). Per defecte: avui.')
    parser.add_argument('--family', type=str, default=None,
                        choices=['Anestesia', 'Bioseguridad'],
                        help='Filtrar per família (per defecte: totes).')
    parser.add_argument('--output', type=str, default=None,
                        help='Fitxer CSV de sortida per a les alertes.')
    args = parser.parse_args()
    run(today=args.today, family=args.family, output_path=args.output)
