"""
Visualització: corba de probabilitat + finestra relativa + alerta.

Per cada client, mostra:
  - Corba P(comprar en h dies) amb interpolació
  - Llindars relatius (p25, p50, p75, p90 sobre P_max)
  - On és "avui" (dies des de l'última compra)
  - On es dispararia l'alerta
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from inference import load_model, compute_features_for_client, predict_curve
from integrate import segment_client

DATA_PATH = '../data/master_commodities.csv'
os.makedirs('output', exist_ok=True)

def plot_client(client_id, familia, today, model, df):
    """Plot probability curve with thresholds and alert zone."""
    grp_all = df[df['Id_Cliente'] == client_id]
    grp = grp_all[grp_all['Familia_Potencial'] == familia]
    if len(grp) < 2:
        return

    result = compute_features_for_client(grp, today, familia)
    if result is None:
        return
    feat_row, meta = result
    meta['dies_sense_compra'] = meta['dies_sense_compra']
    dies = meta['dies_sense_compra']

    curve = predict_curve(model, feat_row)
    seg_info = segment_client(grp, today)

    h = np.array(curve['curve']['h'])
    p = np.array(curve['curve']['p']) * 100  # → percent
    p_max_pct = curve['p_max'] * 100

    perc = curve['percentiles']
    t_p25 = perc['p25']
    t_p50 = perc['p50']
    t_p75 = perc['p75']
    t_p90 = perc['p90']

    # CHECK: should alert?
    alerta = False
    if t_p90 and t_p90 < 365 and dies > t_p90:
        alerta = True
    elif t_p75 and t_p75 < 365 and dies > t_p75:
        alerta = True
    elif dies > 365:
        alerta = True

    # Filter: churned?
    es_fugat = dies > 365 and curve['p_max'] < 0.15

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    # ── Probability curve ──
    ax.plot(h, p, 'b-', linewidth=2.5, label='P(comprar en h dies)')

    # Shade under the curve
    ax.fill_between(h, p, alpha=0.08, color='blue')

    # ── Relative thresholds on curve ──
    thresholds = [
        (t_p25, 'p25 (25% P_max)', '#2ecc71', '--'),
        (t_p50, 'p50 (50% P_max = mediana)', '#f39c12', '--'),
        (t_p75, 'p75 (75% P_max)', '#e67e22', '--'),
        (t_p90, 'p90 (90% P_max = alerta)', '#e74c3c', '--'),
    ]
    for t, label, color, ls in thresholds:
        if t and t < 360:
            p_at_t = np.interp(t, h, p)
            ax.axvline(t, color=color, linestyle=ls, linewidth=1.5, alpha=0.7)
            ax.plot(t, p_at_t, 'o', color=color, markersize=6)
            ax.annotate(f'  {label}', (t, p_at_t), fontsize=7, color=color,
                        rotation=45, ha='left', va='bottom')

    # ── "Today" marker ──
    if dies < 365:
        y_today = np.interp(dies, h, p)
        ax.axvline(dies, color='red', linewidth=2.5, linestyle='-', alpha=0.8)
        ax.plot(dies, y_today, 'D', color='red', markersize=10, zorder=5)
        ax.annotate(f'← AVUI (+{dies}d)\nP({dies}d)={y_today:.0f}%',
                    (dies, y_today), fontsize=9, color='red',
                    ha='right', va='bottom', fontweight='bold')
    else:
        ax.axvline(min(dies, 365), color='red', linewidth=2, linestyle='-', alpha=0.5)
        ax.annotate(f'AVUI (+{dies}d)', (min(dies, 360), 50),
                    fontsize=9, color='red', ha='right')

    # ── Alert zone ──
    if alerta and not es_fugat:
        start = max(min(t_p90 if t_p90 and t_p90 < 365 else t_p75, dies), 0)
        end = min(max(dies, start + 10), 365)
        ax.axvspan(start, end, alpha=0.12, color='red',
                    label='Zona d\'alerta')
    elif es_fugat:
        ax.axvspan(min(dies, 365), 365, alpha=0.08, color='gray',
                    label='Possible fugat')

    # ── P_max reference line ──
    ax.axhline(p_max_pct, color='gray', linestyle=':', linewidth=1, alpha=0.5)
    ax.annotate(f'P_max = {p_max_pct:.0f}%', (5, p_max_pct + 2),
                fontsize=8, color='gray')

    # ── Segment info ──
    seg = seg_info['segment'] if seg_info else '?'
    share = seg_info['share_12m'] if seg_info else 0
    gap = seg_info['gap_eur'] if seg_info else 0
    potencial = seg_info['potencial'] if seg_info else 0

    title = (
        f"Client {client_id} · {familia}\n"
        f"Segment: {seg} · Share: {share:.0%} · Gap: {gap:.0f}€ · Potencial: {potencial:.0f}€\n"
        f"P_max: {p_max_pct:.0f}% · Finestra: {t_p25}-{t_p75}d · "
        f"{'🚨 ALERTA' if alerta and not es_fugat else '✅ Dins finestra' if not es_fugat else '💤 Possible fugat'}"
    )
    ax.set_title(title, fontsize=11, fontweight='bold')

    # ── Alert state in big text ──
    if es_fugat:
        state = "FUGAT"
        state_color = 'gray'
    elif alerta and p_max_pct >= 20:
        state = "🚨 CONTACTAR"
        state_color = 'red'
    elif alerta and p_max_pct < 20:
        state = "⚠️ MONITORITZAR"
        state_color = 'orange'
    else:
        state = "✅ DINS FINESTRA"
        state_color = 'green'

    ax.text(0.96, 0.92, state, transform=ax.transAxes, fontsize=14,
            fontweight='bold', color=state_color, ha='right', va='top',
            bbox=dict(facecolor='white', alpha=0.8, edgecolor=state_color, boxstyle='round,pad=0.5'))

    # ── Axis ──
    ax.set_xlabel('Horitzó (dies)', fontsize=10)
    ax.set_ylabel('Probabilitat acumulada (%)', fontsize=10)
    ax.set_xlim(-5, 185)
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc='lower right')

    fname = f"output/curve_{client_id}_{familia}_{today.strftime('%Y%m%d')}.png"
    plt.tight_layout()
    plt.savefig(fname, dpi=130)
    print(f"  📊 {fname}")
    plt.close()


def main():
    model = load_model()
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    today = pd.Timestamp('2025-09-15')

    # Various client profiles to show
    profiles = [
        (27995, 'Bioseguridad',  'Compra freqüent (cicle 35d) · sobrepassat potencial'),
        (42432, 'Anestesia',     'Fidel · cicle llarg (~141d)'),
        (1000081914, 'Anestesia','Esporàdic · compra ~1 cop/any'),
        (13822, 'Anestesia',     'Marginal · gap enorme, fa 416d sense comprar'),
        (1000078297, 'Anestesia','En risc · share 11%→0%, gap 6K, porta 144d'),
        (38636, 'Anestesia',     'Promiscu · share 22%, dins finestra'),
        (42755, 'Anestesia',     'En risc · share 15%→0%, P_max=44%'),
        (1000100632, 'Anestesia','En risc · gap 3.2K, 285d silent'),
    ]

    print(f"Generant {len(profiles)} gràfics...")
    for cid, fam, desc in profiles:
        print(f"\n📋 Client {cid} · {fam} — {desc}")
        plot_client(cid, fam, today, model, df)

    print(f"\n✅ Fet. Revisa els gràfics a output/")

if __name__ == '__main__':
    main()
