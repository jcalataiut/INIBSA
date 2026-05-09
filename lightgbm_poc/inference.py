"""
Inference: corba de probabilitat + finestra de confiança + alerta.

Per cada (client, família, avui):
  1. Calcula features exactament com a build_dataset.py
  2. Prediu P(comprar) per cada horitzó {7, 14, 30, 60, 90}
  3. Interpola corba acumulada → finestra de confiança
  4. Si avui > límit superior de la finestra → alerta

Ús:
    python3 inference.py                          # mostra exemples
    python3 inference.py --client 1000082665       # client concret
    python3 inference.py --today 2025-06-01        # simular un dia
"""
import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime, timedelta
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from build_dataset import compute_cycle_stats, days_to_next_purchase

MODEL_PATH  = 'models/model.txt'
DATA_PATH   = '../data/master_commodities.csv'
HORIZONS    = [7, 14, 30, 60, 90]
DROP_COLS   = ['Id_Cliente', 'Fecha_ordinal']
CAT_FEATS   = ['Familia_Potencial', 'Provincia', 'mes', 'trimestre', 'dia_setmana']

def load_model():
    return lgb.Booster(model_file=MODEL_PATH)

def load_client_data(client_id, familia=None):
    """Load all sales for a client (optionally filtered by family)."""
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    mask = df['Id_Cliente'] == client_id
    if familia:
        mask &= (df['Familia_Potencial'] == familia)
    grp = df[mask].sort_values('Fecha')
    if len(grp) == 0:
        print(f"  No data for client {client_id}" + (f" / {familia}" if familia else ""))
        return None
    return grp

def compute_features_for_client(grp, today, familia):
    """
    Compute exactly the same feature vector as build_dataset.py
    but for a single (client, family, today) and a single horizon value.
    Returns a DataFrame row ready for prediction (with horitzó_dies set to 0).
    """
    potencial = float(grp['Potencial_EUR_anual'].iloc[0])
    provincia = str(grp['Provincia'].iloc[0]) if pd.notna(grp['Provincia'].iloc[0]) else 'Unknown'

    # Baseline (ex-campaigns) for rolling features
    baseline = grp[grp['en_campana'] == 0]
    baseline_daily = baseline.groupby('Fecha')['Valores_H'].sum()
    all_daily = grp.groupby('Fecha')['Valores_H'].sum()

    if len(baseline_daily) == 0:
        return None

    # Daily range up to today (never use future data)
    full_range = pd.date_range(baseline_daily.index.min(), today, freq='D')
    baseline_daily = baseline_daily.reindex(full_range, fill_value=0)
    all_daily = all_daily.reindex(full_range, fill_value=0)

    # Rolling windows (baseline only)
    roll = {}
    for w in [7, 30, 90, 180, 365]:
        roll[f'euros_{w}d'] = baseline_daily.rolling(w, min_periods=1).sum()
        roll[f'n_ped_{w}d'] = (baseline_daily > 0).astype(np.float32).rolling(w, min_periods=1).sum()

    # Days until next purchase from today forward
    # For inference we don't need this (it's the target), we need features only

    # Today must be in range
    if today not in full_range:
        return None
    idx = full_range.get_loc(today)

    # Past purchases before today
    purchase_dates = full_range[all_daily > 0]
    past_purchases = purchase_dates[purchase_dates < today]
    last_purchase = past_purchases[-1] if len(past_purchases) > 0 else None
    days_since_last = (today - last_purchase).days if last_purchase is not None else -1

    # Cycle
    cicle_mean, cicle_std, num_int = compute_cycle_stats(past_purchases)
    z_retard = days_since_last / cicle_mean if (cicle_mean and cicle_mean > 0 and days_since_last >= 0) else 0.0

    # Rolling values
    e7  = float(roll['euros_7d'].iloc[idx])
    e30 = float(roll['euros_30d'].iloc[idx])
    e90 = float(roll['euros_90d'].iloc[idx])
    e180= float(roll['euros_180d'].iloc[idx])
    e365= float(roll['euros_365d'].iloc[idx])
    n7  = float(roll['n_ped_7d'].iloc[idx])
    n30 = float(roll['n_ped_30d'].iloc[idx])
    n90 = float(roll['n_ped_90d'].iloc[idx])
    n365= float(roll['n_ped_365d'].iloc[idx])

    # Trends
    avg90m = e90 / 3.0 if e90 > 1 else 0.001
    avg365m= e365/12.0 if e365 > 1 else 0.001
    ratio_30_90  = e30 / avg90m
    ratio_90_365 = avg90m / avg365m

    # Share
    share_12m = e365 / potencial if potencial > 0 else 0.0
    share_3m_a = (e90 * 4.0) / potencial if potencial > 0 else 0.0
    gap = max(0.0, potencial - e365)

    # % campaign revenue
    camp_365 = grp[(grp['Fecha'] >= today - timedelta(days=365)) &
                   (grp['Fecha'] < today) &
                   (grp['en_campana'] == 1)]['Valores_H'].sum()
    pct_camp = camp_365 / e365 if e365 > 0 else 0.0

    # These are the same columns in the same order as training
    row = {
        'Familia_Potencial': familia,
        'dia_anyo': today.timetuple().tm_yday,
        'mes': today.month,
        'trimestre': (today.month - 1) // 3 + 1,
        'dia_setmana': today.weekday(),
        'Provincia': provincia,
        'Potencial_EUR_anual': potencial,
        'euros_7d': e7, 'euros_30d': e30, 'euros_90d': e90,
        'euros_180d': e180, 'euros_365d': e365,
        'n_pedidos_7d': n7, 'n_pedidos_30d': n30,
        'n_pedidos_90d': n90, 'n_pedidos_365d': n365,
        'ratio_30d_vs_90d': ratio_30_90,
        'ratio_90d_vs_365d': ratio_90_365,
        'share_wallet_12m': share_12m,
        'share_3m_annualized': share_3m_a,
        'gap_eur': gap,
        'dies_desde_ultim_pedido': days_since_last,
        'cicle_mig_dies': cicle_mean if not np.isnan(cicle_mean) else -1,
        'cicle_std_dies': cicle_std if not np.isnan(cicle_std) else -1,
        'num_intervals': num_int,
        'z_retard': z_retard,
        'pct_ingresos_campanya_365d': pct_camp,
    }

    # Return metadata separately
    meta = {
        'client_id': int(grp['Id_Cliente'].iloc[0]),
        'familia': familia,
        'today': today,
        'potencial': potencial,
        'share_12m': share_12m,
        'gap_eur': gap,
        'dies_sense_compra': days_since_last,
        'cicle_mig_dies': cicle_mean if not np.isnan(cicle_mean) else -1,
        'ultima_compra': last_purchase,
    }

    return row, meta


def predict_curve(model, base_features):
    """
    Predict P(purchase within h days) for all horizons.
    Returns dict: {horizon: probability}
    + interpolated curve
    """
    probs = {}
    for h in HORIZONS:
        row = base_features.copy()
        row['horitzó_dies'] = h
        df_pred = pd.DataFrame([row])

        # Ensure same column order and category dtypes as training
        cat_cols_present = [c for c in CAT_FEATS if c in df_pred.columns]
        for c in cat_cols_present:
            df_pred[c] = df_pred[c].astype('category')

        prob = model.predict(df_pred)[0]
        probs[h] = float(prob)

    # Build smooth curve via interpolation
    points = sorted(probs.items())  # [(h, p), ...]
    h_vals = np.array([0] + [p[0] for p in points])
    p_vals = np.array([0.0] + [p[1] for p in points])

    # Linear interpolation (conservative)
    fine_h = np.arange(0, 366, 1)
    fine_p = np.interp(fine_h, h_vals, p_vals, left=0, right=p_vals[-1])

    # Clamp to [0, 1] and enforce monotonicity
    fine_p = np.clip(fine_p, 0, 1)
    fine_p = np.maximum.accumulate(fine_p)  # ensure non-decreasing

    # Find thresholds — RELATIVE to max probability achieved
    p_max = max(fine_p[-1], 0.01)  # max P in 0-365 days

    def first_where(condition, default=365):
        idxs = np.where(condition)[0]
        return int(idxs[0]) if len(idxs) > 0 else default

    t_p10  = first_where(fine_p >= 0.10 * p_max)
    t_p25  = first_where(fine_p >= 0.25 * p_max)
    t_p50  = first_where(fine_p >= 0.50 * p_max)
    t_p75  = first_where(fine_p >= 0.75 * p_max)
    t_p90  = first_where(fine_p >= 0.90 * p_max)

    return {
        'raw_probs': probs,
        'curve': {'h': fine_h.tolist(), 'p': fine_p.tolist()},
        'p_max': round(p_max, 4),
        'percentiles': {
            'p10': t_p10,   # 10% of max P → lower bound
            'p25': t_p25,   # 25% of max P
            'p50': t_p50,   # 50% of max P → median-like
            'p75': t_p75,   # 75% of max P
            'p90': t_p90,   # 90% of max P → alert threshold
        },
        'window_medio': (t_p25, t_p75),  # central 50% of probability mass
        'window_alerta': (t_p10, t_p90), # 80% window → alert if past p90
    }


def format_alerts(meta, curve):
    """Generate alerts based on how overdue the client is."""
    today = meta['today']
    t_50 = curve['percentiles']['p50']
    t_95 = curve['percentiles']['p95']
    dies_sense = meta['dies_sense_compra']

    alerts = []
    # Alert: past median → overdue
    if dies_sense >= t_50 and t_50 > 0:
        days_over = dies_sense - t_50
        severity = '🔴 CRÍTIC' if dies_sense >= t_95 else '🟡 RISC'
        alerts.append({
            'severity': severity,
            'message': (
                f"Esperàvem compra cap al dia {t_50} (mediana). "
                f"Porta {dies_sense} dies sense comprar ({days_over} dies de retard). "
                f"95% de confiança: hauria d'haver comprat abans del dia {t_95}."
            ),
            'priority_score': meta['gap_eur'] * (dies_sense / max(t_50, 1)),
        })

    # Alert: general info
    alerts.append({
        'severity': '📊 INFO',
        'message': (
            f"Probabilitat de compra: "
            f"{curve['raw_probs'][7]:.0%} (7d), "
            f"{curve['raw_probs'][14]:.0%} (14d), "
            f"{curve['raw_probs'][30]:.0%} (30d), "
            f"{curve['raw_probs'][60]:.0%} (60d)"
        ),
    })

    return sorted(alerts, key=lambda x: x.get('priority_score', 0), reverse=True)


def print_report(client_id, familia, today_str, meta, curve, alerts):
    print(f"\n{'='*65}")
    print(f"📋 CLIENT {client_id} · {meta['familia']}")
    print(f"   Avui: {today_str}")
    print(f"{'='*65}")
    print(f"   Potencial anual:     {meta['potencial']:>8.2f} €")
    print(f"   Share of wallet 12m: {meta['share_12m']:>7.1%}")
    print(f"   Gap no capturat:     {meta['gap_eur']:>8.2f} €")
    print(f"   Dies sense comprar:  {meta['dies_sense_compra']}")
    print(f"   Cicle mig:           {meta['cicle_mig_dies']:.0f} dies" if meta['cicle_mig_dies'] > 0 else "   Cicle mig:           N/A")

    print(f"\n   📈 Corba de probabilitat acumulada:")
    print(f"      P(comprar en 7 dies):   {curve['raw_probs'][7]:>7.1%}")
    print(f"      P(comprar en 14 dies):  {curve['raw_probs'][14]:>7.1%}")
    print(f"      P(comprar en 30 dies):  {curve['raw_probs'][30]:>7.1%}")
    print(f"      P(comprar en 60 dies):  {curve['raw_probs'][60]:>7.1%}")
    print(f"      P(comprar en 90 dies):  {curve['raw_probs'][90]:>7.1%}")

    print(f"\n   🎯 Finestres de confiança:")
    print(f"      50% confiança (IQR):     dia {curve['percentiles']['p25']} → dia {curve['percentiles']['p75']}")
    print(f"      90% confiança:           dia {curve['percentiles']['p5']} → dia {curve['percentiles']['p95']}")
    print(f"      Mediana (dia esperat):   dia {curve['percentiles']['p50']}")

    print(f"\n   ⚠️ Alertes:")
    for a in alerts:
        print(f"      {a['severity']}: {a['message']}")


def show_probability_curve(curve, meta, title="Probabilitat de compra acumulada"):
    """Print an ASCII visualization of the probability curve."""
    try:
        import matplotlib.pyplot as plt
        h = np.array(curve['curve']['h'])
        p = np.array(curve['curve']['p'])
        today = meta['today']

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Left: probability curve
        ax = axes[0]
        ax.plot(h, p * 100, 'b-', linewidth=2, label='P(comprar en h dies)')
        dsc = min(meta['dies_sense_compra'], 360)
        ax.axvline(dsc, color='red', linestyle='--',
                   label=f"Avui (+{dsc} dies sense comprar)")
        for pct, color, ls in [(50, 'green', ':'), (75, 'orange', ':')]:
            t = curve['percentiles'].get(f'p{pct}', 365)
            if t and t < 360:
                ax.axvline(t, color=color, linestyle=ls,
                           label=f"P{pct} = dia {t}")
        ax.set_xlabel("Horitzó (dies)")
        ax.set_ylabel("Probabilitat acumulada (%)")
        ax.set_title(title)
        ax.legend(fontsize=8)
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)

        # Right: probability density (derivative of cumulative)
        ax2 = axes[1]
        dp = np.diff(p)
        dh = np.diff(h)
        density = dp / dh * 100
        mid_h = (np.array(h[:-1]) + np.array(h[1:])) / 2
        ax2.bar(mid_h, density, width=dh, alpha=0.6, color='blue')
        dsc = max(min(meta['dies_sense_compra'], 360), 0)
        ax2.axvline(dsc, color='red', linestyle='--',
                    label=f"Avui (+{dsc}d)")
        ax2.set_xlabel("Dies")
        ax2.set_ylabel("Densitat de probabilitat (%/dia)")
        ax2.set_title("Quan esperem la compra (densitat)")
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        os.makedirs('output', exist_ok=True)
        fname = f"output/curve_{meta['client_id']}_{today.strftime('%Y%m%d')}.png"
        plt.savefig(fname, dpi=120)
        print(f"   📊 Gràfic guardat: {fname}")
        plt.close()
    except ImportError:
        print("   (instal·la matplotlib per veure gràfics)")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--client', type=int, default=None,
                        help='Client ID (default: mostra exemples)')
    parser.add_argument('--today', type=str, default=None,
                        help='Data avui (YYYY-MM-DD, default: avui real)')
    parser.add_argument('--familia', type=str, default=None,
                        help='Família (Anestesia o Bioseguridad, default: ambdues)')
    args = parser.parse_args()

    today = datetime.strptime(args.today, '%Y-%m-%d').date() if args.today else datetime.now().date()
    today = pd.Timestamp(today)

    print(f"📅 Simulant avui = {today.date()}")
    model = load_model()
    print(f"✅ Model carregat de {MODEL_PATH}\n")

    # Deterministic behavior: seed for reproducibility
    rng = np.random.RandomState(42)

    if args.client:
        clients_to_show = [args.client]
    else:
        # Pick a few representative clients
        df_ref = pd.read_csv(DATA_PATH, low_memory=False)
        df_ref['Fecha'] = pd.to_datetime(df_ref['Fecha'])

        # One loyal, one promiscuous, one marginal, one long-silent
        last_purchase = df_ref.groupby('Id_Cliente')['Fecha'].max().reset_index()
        last_purchase['dies_sense'] = (today - last_purchase['Fecha']).dt.days
        active = last_purchase[last_purchase['dies_sense'] < 60]
        silent = last_purchase[(last_purchase['dies_sense'] > 90) & (last_purchase['dies_sense'] < 365)]

        clients_to_show = []
        # Active high-volume client
        if len(active) > 0:
            vol = df_ref[df_ref['Id_Cliente'].isin(active['Id_Cliente'])]
            vol = vol.groupby('Id_Cliente')['Valores_H'].sum()
            clients_to_show.append(vol.sort_values(ascending=False).index[0])
        # Active medium client
        if len(active) > 1:
            vol = vol.sort_values()
            middle_idx = len(vol) // 2
            clients_to_show.append(vol.index[middle_idx])
        # Silent client (potential churn)
        if len(silent) > 0:
            clients_to_show.append(silent.sample(1, random_state=42)['Id_Cliente'].iloc[0])

        clients_to_show = list(set(clients_to_show))[:3]

    for cid in clients_to_show:
        grp_all = load_client_data(cid)
        if grp_all is None:
            continue

        families = [args.familia] if args.familia else grp_all['Familia_Potencial'].unique()
        for fam in families:
            grp = grp_all[grp_all['Familia_Potencial'] == fam]
            if len(grp) < 2:
                continue

            result = compute_features_for_client(grp, today, fam)
            if result is None:
                continue
            feat_row, meta = result

            curve = predict_curve(model, feat_row)
            alerts = format_alerts(meta, curve)
            print_report(cid, fam, str(today.date()), meta, curve, alerts)
            show_probability_curve(curve, meta)

    print(f"\n{'='*65}")
    print("✅ INFERENCE COMPLETE")
    print("   Per usar: python3 inference.py --client 1000082665 --today 2025-06-01")


if __name__ == '__main__':
    main()
