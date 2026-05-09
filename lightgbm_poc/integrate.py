"""
Integració: Segmentació (share of wallet) + LightGBM (timing).
 
QUI → Segment (FIDEL/PROMISCU/MARGINAL/EN_RISC) basat en share_of_wallet
QUAN → Corba de probabilitat LightGBM → finestra de confiança
 
Output: alertes combinades amb prioritat final.
"""
import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from build_dataset import compute_cycle_stats
from inference import load_model, compute_features_for_client, predict_curve

DATA_PATH = '../data/master_commodities.csv'
MODEL_PATH = 'models/model.txt'
HORIZONS = [7, 14, 30, 60, 90]

SHARE_FIDEL_THR     = 0.70
SHARE_MARGINAL_THR  = 0.20
RATIO_EN_RISC       = 0.75  # share_3m / share_12m < 0.75 → declining

# Pesos per segment — quant importa actuar-hi
SEGMENT_WEIGHT = {
    'FIDEL':     0.8,   # mantenir, no perdre'ls
    'PROMISCU':  1.0,   # oportunitat de captura
    'MARGINAL':  0.3,   # baixa prioritat
    'EN_RISC':   1.2,   # màxima urgència
    'NOU':       0.5,
}

def segment_client(grp, today, potencial):
    """Compute share-of-wallet and segment for a (client, family)."""
    baseline = grp[grp['en_campana'] == 0]
    baseline_daily = baseline.groupby('Fecha')['Valores_H'].sum()
    all_daily = grp.groupby('Fecha')['Valores_H'].sum()

    if len(baseline_daily) == 0:
        return None

    full_range = pd.date_range(baseline_daily.index.min(), today, freq='D')
    baseline_daily = baseline_daily.reindex(full_range, fill_value=0)
    all_daily = all_daily.reindex(full_range, fill_value=0)

    if today not in full_range:
        return None
    idx = full_range.get_loc(today)

    # Rolling windows
    e90  = baseline_daily.rolling(90, min_periods=1).sum().iloc[idx]
    e365 = baseline_daily.rolling(365, min_periods=1).sum().iloc[idx]

    share_12m = e365 / potencial if potencial > 0 else 0
    share_3m_an = (e90 * 4) / potencial if potencial > 0 else 0

    # Segment
    purchase_dates = full_range[all_daily > 0]
    first_buy = purchase_dates[0] if len(purchase_dates) > 0 else today

    if (today - first_buy).days < 90:
        segment = 'NOU'
    elif share_12m >= SHARE_FIDEL_THR:
        segment = 'FIDEL' if share_3m_an >= share_12m * RATIO_EN_RISC else 'EN_RISC'
    elif share_12m >= SHARE_MARGINAL_THR:
        segment = 'PROMISCU' if share_3m_an >= share_12m * RATIO_EN_RISC else 'EN_RISC'
    else:
        segment = 'MARGINAL' if share_3m_an >= share_12m * RATIO_EN_RISC else 'EN_RISC'

    return {
        'segment': segment,
        'share_12m': share_12m,
        'share_3m_an': share_3m_an,
        'gap_eur': max(0, potencial - e365),
    }

def compute_priority(meta, curve, segment_info):
    """
    Priority = gap × segment_weight × timing_factor
    
    timing_factor:
      - High when purchase is probable but not imminent
      - Low when purchase is imminent (they'll buy anyway)
      - Low when purchase is very far (no urgency)
    
    sweet_spot = P(30d) is high AND P(7d) is not too high
    """
    p7  = curve['raw_probs'].get(7, 0)
    p30 = curve['raw_probs'].get(30, 0)
    t50 = curve['percentiles'].get('p50', 365)
    gap = segment_info['gap_eur']
    seg = segment_info['segment']

    # Sweet spot: likely to buy in 30d but not this week
    timing = p30 * (1 - p7) * (30 / max(t50, 1))
    # Clamp: if t50 is very large, timing should be low
    if t50 > 180:
        timing *= 0.3
    elif t50 > 90:
        timing *= 0.6

    weight = SEGMENT_WEIGHT.get(seg, 0.5)
    priority = gap * weight * timing

    return priority

def generate_alert(client_id, familia, today, segment_info, curve, priority):
    """Generate the combined alert with explanation."""
    gap = segment_info['gap_eur']
    seg = segment_info['segment']
    p7  = curve['raw_probs'].get(7, 0)
    p30 = curve['raw_probs'].get(30, 0)
    p90 = curve['raw_probs'].get(90, 0)
    t50 = curve['percentiles'].get('p50', 365)
    t75 = curve['percentiles'].get('p75', 365)
    dies_sense = segment_info.get('dies_sense_compra', 0)

    # Build explanation based on segment + timing
    parts = []
    if seg == 'FIDEL':
        parts.append(f"Client fidel (share {segment_info['share_12m']:.0%})")
    elif seg == 'PROMISCU':
        parts.append(f"Client promiscu (share {segment_info['share_12m']:.0%}, gap {gap:.0f}€)")
    elif seg == 'EN_RISC':
        parts.append(f"Client en risc (share 12m: {segment_info['share_12m']:.0%} → 3m: {segment_info['share_3m_an']:.0%})")
    elif seg == 'MARGINAL':
        parts.append(f"Client marginal (share {segment_info['share_12m']:.0%})")

    # Timing info
    if t50 < 14:
        parts.append(f"comprarà aviat (mediana {t50}d)")
    elif t50 < 30:
        parts.append(f"finestra de captura: mediana {t50}d")
    elif t50 < 90:
        parts.append(f"pot comprar els pròxims mesos (mediana {t50}d)")
    else:
        parts.append(f"no es preveu compra imminent (mediana >90d)")

    # Alert urgency
    if dies_sense > t75 and t75 < 365:
        urgency = '🔴 CRÍTIC' if dies_sense > t75 * 1.5 else '🟡 RISC'
    elif seg == 'EN_RISC':
        urgency = '🟡 RISC'
    elif seg == 'PROMISCU' and p30 > 0.5:
        urgency = '🟡 OPORTUNITAT'
    else:
        urgency = '📊 INFO'

    return {
        'client_id': client_id,
        'familia': familia,
        'segment': seg,
        'urgency': urgency,
        'priority': round(priority, 1),
        'gap_eur': round(gap, 2),
        'share_wallet': round(segment_info['share_12m'], 3),
        'prob_7d': f"{p7:.0%}",
        'prob_30d': f"{p30:.0%}",
        'prob_90d': f"{p90:.0%}",
        'median_day': t50,
        'window_iqr': f"{curve['percentiles']['p25']}-{curve['percentiles']['p75']}d",
        'explanation': '. '.join(parts) + '.',
    }

def main():
    model = load_model()
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df['Fecha'] = pd.to_datetime(df['Fecha'])

    today = pd.Timestamp('2025-09-15')  # could be any day

    print(f"\n{'='*80}")
    print(f"📋 BRIEFING COMERCIAL · {today.date()}")
    print(f"   Segmentació (share of wallet) + Timing (LightGBM)")
    print(f"{'='*80}")

    # Process each (client, family) — for POC, sample a subset
    groups = list(df.groupby(['Id_Cliente', 'Familia_Potencial']))
    rng = np.random.RandomState(42)
    rng.shuffle(groups)  # shuffle to show diversity

    alerts = []
    n_processed = 0

    # For the POC, process a limited number of groups
    for (cid, fam), grp in groups:
        if n_processed >= 500:
            break
        n_processed += 1

        potencial = float(grp['Potencial_EUR_anual'].iloc[0])
        seg_info = segment_client(grp, today, potencial)
        if seg_info is None:
            continue

        # Get LightGBM curve
        result = compute_features_for_client(grp, today, fam)
        if result is None:
            continue
        feat_row, meta = result
        meta['dies_sense_compra'] = meta['dies_sense_compra']
        seg_info['dies_sense_compra'] = meta['dies_sense_compra']

        curve = predict_curve(model, feat_row)
        priority = compute_priority(meta, curve, seg_info)
        alert = generate_alert(cid, fam, today, seg_info, curve, priority)

        alerts.append(alert)

    # Rank by priority
    alerts.sort(key=lambda a: a['priority'], reverse=True)

    # Print summary stats
    seg_counts = {}
    urg_counts = {}
    for a in alerts:
        seg_counts[a['segment']] = seg_counts.get(a['segment'], 0) + 1
        urg_counts[a['urgency']] = urg_counts.get(a['urgency'], 0) + 1

    print(f"\n📊 Resum: {len(alerts)} alertes generades (mostra de 500 clients)")
    print(f"   Segments: {seg_counts}")
    print(f"   Urgències: {urg_counts}")

    # Show top 10
    print(f"\n{'='*80}")
    print("🏆 TOP 10 ALERTES PRIORITZADES")
    print(f"{'='*80}")
    print(f"{'Client':>10} {'Família':<15} {'Segment':<12} {'Urgència':<18} {'Prioritat':>9} {'Gap':>8} {'P(30d)':>7} {'Mediana':>7} {'Finestra':<10}")
    print(f"{'-'*10} {'-'*15} {'-'*12} {'-'*18} {'-'*9} {'-'*8} {'-'*7} {'-'*7} {'-'*10}")

    for a in alerts[:10]:
        print(f"{a['client_id']:>10} {a['familia']:<15} {a['segment']:<12} {a['urgency']:<18} {a['priority']:>9.1f} {a['gap_eur']:>8.1f} {a['prob_30d']:>7} {a['median_day']:>7} {a['window_iqr']:<10}")

    # Show 3 detailed examples
    print(f"\n{'='*80}")
    print("🔍 EXEMPLES DETALLATS")
    print(f"{'='*80}")

    top_urgency = ['🔴 CRÍTIC', '🟡 RISC', '🟡 OPORTUNITAT']
    for urg in top_urgency:
        examples = [a for a in alerts if a['urgency'] == urg]
        if examples:
            ex = examples[0]
            print(f"\n{ex['urgency']} — Client {ex['client_id']} · {ex['familia']}")
            print(f"   Segment: {ex['segment']} | Share: {ex['share_wallet']:.0%} | Gap: {ex['gap_eur']}€")
            print(f"   Corba: P(7d)={ex['prob_7d']}  P(30d)={ex['prob_30d']}  P(90d)={ex['prob_90d']}")
            print(f"   Finestra (IQR): {ex['window_iqr']} | Mediana: dia {ex['median_day']}")
            print(f"   Motiu: {ex['explanation']}")

    print(f"\n{'='*80}")
    print("✅ Fet. Per generar briefing complet: augmentar mostra a tots els clients")

if __name__ == '__main__':
    main()
