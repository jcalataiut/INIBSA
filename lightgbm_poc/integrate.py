"""
Integració: Segmentació (share of wallet) + LightGBM (timing).

Lògica unificada per TOT client commodity:
  1. LightGBM → corba P(h) → finestra de confiança RELATIVA al màxim assolit
  2. Alerta si avui > p90_rel (límit superior de la finestra)
  3. Segment (fidel/promiscu/...) només pondera PRIORITAT

Output: ranking d'alertes prioritzades, accionable.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from inference import load_model, compute_features_for_client, predict_curve

DATA_PATH = '../data/master_commodities.csv'

SHARE_FIDEL_THR    = 0.70
SHARE_MARGINAL_THR = 0.20

# Pes per segment — només per prioritzar, NO per decidir si alertar
PES_SEGMENT = {
    'PROMISCU': 1.3,   # màxima oportunitat de captura
    'EN_RISC':  1.2,   # recuperar urgent
    'FIDEL':    0.8,   # mantenir
    'MARGINAL': 0.4,   # baixa prioritat
    'NOU':      0.5,
}

def segment_client(grp, today):
    """Share of wallet → segment. Només per ponderar prioritat."""
    baseline    = grp[grp['en_campana'] == 0]
    baseline_daily = baseline.groupby('Fecha')['Valores_H'].sum()
    all_daily   = grp.groupby('Fecha')['Valores_H'].sum()
    potencial   = float(grp['Potencial_EUR_anual'].iloc[0])

    if len(baseline_daily) == 0:
        return None

    full_range = pd.date_range(baseline_daily.index.min(), today, freq='D')
    baseline_daily = baseline_daily.reindex(full_range, fill_value=0)
    all_daily   = all_daily.reindex(full_range, fill_value=0)

    if today not in full_range:
        return None
    idx = full_range.get_loc(today)

    e90  = baseline_daily.rolling(90, min_periods=1).sum().iloc[idx]
    e365 = baseline_daily.rolling(365, min_periods=1).sum().iloc[idx]
    share_12m   = e365 / potencial if potencial > 0 else 0
    share_3m_an = (e90 * 4) / potencial if potencial > 0 else 0

    purchase_dates = full_range[all_daily > 0]
    first_buy = purchase_dates[0] if len(purchase_dates) > 0 else today

    # Segment (strict per share)
    if (today - first_buy).days < 90:
        seg = 'NOU'
    elif share_12m >= SHARE_FIDEL_THR:
        seg = 'FIDEL'
    elif share_12m >= SHARE_MARGINAL_THR:
        seg = 'PROMISCU'
    else:
        seg = 'MARGINAL'

    # Override: si share està caient
    if share_3m_an < share_12m * 0.75 and share_12m > 0.05:
        seg = 'EN_RISC'

    return {
        'segment': seg,
        'share_12m': round(share_12m, 3),
        'share_3m_an': round(share_3m_an, 3),
        'gap_eur': max(0, potencial - e365),
        'potencial': potencial,
    }

def compute_priority(meta, seg_info):
    """
    Prioritat = gap × retard_relatiu × pes_segment

    retard_relatiu: com de lluny de la mediana (cap at 3x)
    """
    gap    = seg_info['gap_eur']
    pes    = PES_SEGMENT.get(seg_info['segment'], 0.5)
    t_p50  = meta['median_day']
    dies   = meta['dies_sense_compra']

    if t_p50 and t_p50 > 0 and t_p50 < 365:
        retard = min(max(0, dies / t_p50), 3.0)  # cap a 3x max
    else:
        retard = 1.0

    return round(gap * retard * pes, 1)

def generar_alerta(client_id, familia, today, seg_info, curve, meta):
    """Alerta unificada: qualsevol client + finestra + motiu."""
    gap     = seg_info['gap_eur']
    seg     = seg_info['segment']
    share   = seg_info['share_12m']
    p_max   = curve['p_max']
    dies    = meta['dies_sense_compra']
    t_p50   = curve['percentiles']['p50']
    t_p75   = curve['percentiles']['p75']
    t_p90   = curve['percentiles']['p90']
    p7      = curve['raw_probs'].get(7, 0)
    p30     = curve['raw_probs'].get(30, 0)
    p90     = curve['raw_probs'].get(90, 0)

    # Explicació segment
    if seg == 'FIDEL':
        desc = f"Client fidel (share {share:.0%})"
    elif seg == 'PROMISCU':
        desc = f"Client promiscu (share {share:.0%}, gap {gap:.0f}€)"
    elif seg == 'EN_RISC':
        desc = f"Client en risc (share 12m:{share:.0%} → 3m:{seg_info['share_3m_an']:.0%})"
    elif seg == 'MARGINAL':
        desc = f"Client marginal (share {share:.0%})"
    else:
        desc = f"Client {seg}"

    # Explicació finestra
    if p_max < 0.2:
        # Client molt esporàdic → finestra ampla
        ex = f"P_max={p_max:.0%} als 90 dies (patró esporàdic). Esperat: ~dia {t_p50}."
    else:
        ex = f"Finestra esperada: {curve['percentiles']['p25']}-{t_p75}d (P50 rel ={t_p50}d)."

    # Determinar si cal alertar
    si_alerta = False
    urgencia = '📊 INFO'
    if t_p90 and t_p90 < 365 and dies > t_p90:
        si_alerta = True
        urgencia  = '🔴 CRÍTIC' if dies > t_p90 * 1.3 else '🟡 RISC'
    elif t_p75 and t_p75 < 365 and dies > t_p75:
        si_alerta = True
        urgencia  = '🟡 RISC'
    elif dies > 365:
        si_alerta = True
        urgencia  = '🔴 CRÍTIC'

    # Motiu complet
    if si_alerta:
        dies_retard = dies - t_p50
        motiu = f"{desc}. Hauria d'haver comprat ~dia {t_p50} i porta {dies_retard}d de retard ({p30:.0%} prob als 30d). Cal contactar."
    else:
        motiu = f"{desc}. {ex} Dins del rang esperat."

    return {
        'client_id': client_id,
        'familia': familia,
        'segment': seg,
        'urgencia': urgencia,
        'prioritat': 0.0,  # es calcula després
        'es_alerta': si_alerta,
        'gap_eur': round(gap, 1),
        'share_wallet': share,
        'p_max': p_max,
        'P(7d)': f"{p7:.0%}",
        'P(30d)': f"{p30:.0%}",
        'P(90d)': f"{p90:.0%}",
        't_p50': t_p50,
        't_p75': t_p75,
        't_p90': t_p90,
        'finestra': f"{curve['percentiles'].get('p25', '?')}-{t_p75}d",
        'dies_sense': dies,
        'motiu': motiu,
        'today': today,
        'median_day': t_p50,
    }


def main():
    model  = load_model()
    df     = pd.read_csv(DATA_PATH, low_memory=False)
    df['Fecha'] = pd.to_datetime(df['Fecha'])

    today = pd.Timestamp('2025-09-15')

    print(f"\n{'='*90}")
    print(f"📋 BRIEFING COMERCIAL · {today.date()}")
    print(f"   Alerta si surt de la finestra (p90_rel). Segment només pondera.")
    print(f"{'='*90}")

    groups = list(df.groupby(['Id_Cliente', 'Familia_Potencial']))
    np.random.RandomState(42).shuffle(groups)

    alertes = []
    n_proc = 0

    for (cid, fam), grp in groups:
        if n_proc >= 500:
            break
        n_proc += 1

        potencial = float(grp['Potencial_EUR_anual'].iloc[0])
        seg_info = segment_client(grp, today)
        if seg_info is None:
            continue

        result = compute_features_for_client(grp, today, fam)
        if result is None:
            continue
        feat_row, meta = result
        meta['dies_sense_compra'] = meta['dies_sense_compra']
        dies = meta['dies_sense_compra']

        curve   = predict_curve(model, feat_row)
        p_max   = curve['p_max']
        p90     = curve['raw_probs'].get(90, 0)

        # Filtre: si porta > 365d sense comprar i prob molt baixa → fugat, no alertar
        if dies > 365 and p_max < 0.15:
            continue
        if dies > 180 and p_max < 0.05:
            continue

        alerta  = generar_alerta(cid, fam, today, seg_info, curve, meta)
        meta_for_priority = {**meta, 'median_day': curve['percentiles']['p50']}
        alerta['prioritat'] = compute_priority(meta_for_priority, seg_info)
        alertes.append(alerta)

    alertes.sort(key=lambda a: a['prioritat'], reverse=True)

    # Stats
    n_alerta = sum(1 for a in alertes if a['es_alerta'])
    seg_c = {}
    urg_c = {}
    for a in alertes:
        seg_c[a['segment']] = seg_c.get(a['segment'], 0) + 1
        urg_c[a['urgencia']] = urg_c.get(a['urgencia'], 0) + 1

    print(f"\n📊 {len(alertes)} clients processats | 🚨 {n_alerta} alertes generades")
    print(f"   Segments:  {seg_c}")
    print(f"   Urgències: {urg_c}")

    # TOP 10
    print(f"\n{'='*90}")
    print("🏆 RANKING ALERTES")
    print(f"{'='*90}")
    h = f"{'Client':>10} {'Família':<14} {'Segm.':<8} {'Urg.':<10} {'Prior.':>7} {'Gap€':>8} {'P30':>5} {'T_p50':>6} {'T_p90':>6} {'Dies':>5} {'Finestra':<10}"
    print(h)
    print('-' * 90)

    for a in alertes[:10]:
        f = f"{a['P(30d)']:>5} {a['t_p50']:>6} {a['t_p90'] if a['t_p90']<365 else '>365':>6} {a['dies_sense']:>5} {a['finestra']:<10}"
        print(f"{a['client_id']:>10} {a['familia']:14} {a['segment']:8} {a['urgencia']:10} {a['prioritat']:7.1f} {a['gap_eur']:8.1f}{f}")

    # Exemples
    print(f"\n{'='*90}")
    print("🔍 EXEMPLES")
    for cat in ['🔴 CRÍTIC', '🟡 RISC', '📊 INFO']:
        exs = [a for a in alertes if a['urgencia'] == cat][:1]
        for a in exs:
            print(f"\n{cat} — Cli.{a['client_id']} {a['familia']} | Segm.:{a['segment']} | Gap:{a['gap_eur']}€")
            print(f"   Corba: P(7d)={a['P(7d)']}  P(30d)={a['P(30d)']}  P(90d)={a['P(90d)']}  P_max={a['p_max']:.0%}")
            print(f"   Finestra: {a['finestra']}  T_p50={a['t_p50']}d  T_p90={a['t_p90']}d  Dies_sense={a['dies_sense']}d")
            print(f"   Motiu: {a['motiu']}")

    print(f"\n{'='*90}")
    print("✅ Fet")

if __name__ == '__main__':
    main()
