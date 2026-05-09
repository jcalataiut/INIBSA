"""
Build training dataset for LightGBM POC.
One row per (client, family, reference_date, horizon).
Features computed using only data BEFORE reference_date (no leakage).
Target: 1 if any purchase in (reference_date, reference_date + horizon].
"""
import pandas as pd
import numpy as np
from datetime import timedelta
import os

DATA_PATH   = '../data/master_commodities.csv'
OUTPUT_PATH = 'data/training_data.parquet'
SAMPLE_EVERY_N_DAYS = 15
MIN_HISTORY_DAYS    = 60
HORIZONS = [7, 14, 30, 60, 90]
MIN_SALES_FOR_CYCLE = 2


def load_and_prepare():
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    return df

def days_to_next_purchase(daily_series):
    """For each day, how many days until next purchase (>0)."""
    vals = daily_series.values
    n = len(vals)
    result = np.full(n, np.iinfo(np.int32).max, dtype=np.int32)
    next_day = np.iinfo(np.int32).max
    for i in range(n - 1, -1, -1):
        result[i] = next_day
        if vals[i] > 0:
            next_day = 0
        if next_day < np.iinfo(np.int32).max:
            next_day += 1
    return pd.Series(result, index=daily_series.index)

def compute_cycle_stats(purchase_dates):
    if len(purchase_dates) < MIN_SALES_FOR_CYCLE:
        return np.nan, np.nan, 0
    s = purchase_dates.to_series()
    intervals = s.diff().dt.days.iloc[1:]
    if len(intervals) < 1:
        return np.nan, np.nan, 0
    return intervals.mean(), intervals.std(), len(intervals)

def process_group(grp, client_id, familia):
    """Process one (client, family) group.
    Returns list of dicts — one row per (ref_date × horizon).
    """
    if len(grp) < 2:
        return []

    potencial = float(grp['Potencial_EUR_anual'].iloc[0])
    provincia = str(grp['Provincia'].iloc[0]) if pd.notna(grp['Provincia'].iloc[0]) else 'Unknown'

    # Baseline = exclude campaign sales for clean rolling windows
    baseline = grp[grp['en_campana'] == 0].copy()

    # Daily aggregation
    baseline_daily = baseline.groupby('Fecha')['Valores_H'].sum()
    all_daily = grp.groupby('Fecha')['Valores_H'].sum()

    if len(baseline_daily) < 2:
        return []

    full_range = pd.date_range(baseline_daily.index.min(), baseline_daily.index.max(), freq='D')
    baseline_daily = baseline_daily.reindex(full_range, fill_value=0)
    all_daily = all_daily.reindex(full_range, fill_value=0)

    # Rolling windows (baseline only — no campaign contamination)
    roll = {}
    for w in [7, 30, 90, 180, 365]:
        roll[f'euros_{w}d'] = baseline_daily.rolling(w, min_periods=1).sum()
        roll[f'n_ped_{w}d'] = (baseline_daily > 0).astype(np.float32).rolling(w, min_periods=1).sum()

    # Days until next purchase (all sales, including campaigns — target)
    dtn = days_to_next_purchase(all_daily)
    purchase_dates = full_range[all_daily > 0]

    # Reference dates
    min_ref = full_range[0] + timedelta(days=MIN_HISTORY_DAYS)
    max_ref = full_range[-1]
    if min_ref >= max_ref:
        return []
    ref_dates = pd.date_range(min_ref, max_ref, freq=f'{SAMPLE_EVERY_N_DAYS}D')

    rows = []
    for ref_date in ref_dates:
        try:
            idx = full_range.get_loc(ref_date)
        except KeyError:
            continue

        # Past purchases
        past_purchases = purchase_dates[purchase_dates < ref_date]
        last_purchase = past_purchases[-1] if len(past_purchases) > 0 else None
        days_since_last = (ref_date - last_purchase).days if last_purchase is not None else -1

        # Cycle
        cicle_mean, cicle_std, num_int = compute_cycle_stats(past_purchases)
        z_retard = days_since_last / cicle_mean if (cicle_mean and cicle_mean > 0 and days_since_last >= 0) else 0.0

        # Rolling values at ref_date
        e7  = float(roll['euros_7d'].iloc[idx])
        e30 = float(roll['euros_30d'].iloc[idx])
        e90 = float(roll['euros_90d'].iloc[idx])
        e180= float(roll['euros_180d'].iloc[idx])
        e365= float(roll['euros_365d'].iloc[idx])

        n7  = float(roll['n_ped_7d'].iloc[idx])
        n30 = float(roll['n_ped_30d'].iloc[idx])
        n90 = float(roll['n_ped_90d'].iloc[idx])
        n365= float(roll['n_ped_365d'].iloc[idx])

        # Trends (avoid div by 0)
        avg90m = e90 / 3.0 if e90 > 1 else 0.001
        avg365m= e365/12.0 if e365 > 1 else 0.001
        ratio_30_90  = e30 / avg90m
        ratio_90_365 = avg90m / avg365m

        # Share
        share_12m = e365 / potencial if potencial > 0 else 0.0
        share_3m_a = (e90 * 4.0) / potencial if potencial > 0 else 0.0
        gap = max(0.0, potencial - e365)

        # % campaign revenue in last 365d
        camp_365 = grp[(grp['Fecha'] >= ref_date - timedelta(days=365)) &
                       (grp['Fecha'] < ref_date) &
                       (grp['en_campana'] == 1)]['Valores_H'].sum()
        pct_camp = camp_365 / e365 if e365 > 0 else 0.0

        # Common features (don't depend on horizon)
        base = {
            'Id_Cliente': int(client_id),
            'Familia_Potencial': familia,
            'Fecha_ordinal': ref_date.toordinal(),
            'dia_anyo': ref_date.timetuple().tm_yday,
            'mes': ref_date.month,
            'trimestre': (ref_date.month - 1) // 3 + 1,
            'dia_setmana': ref_date.weekday(),
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

        # Targets for each horizon
        days_to_target = dtn.iloc[idx]
        for h in HORIZONS:
            row = base.copy()
            row['horitzó_dies'] = h
            row['target'] = 1 if days_to_target <= h + 1 else 0
            rows.append(row)

    return rows

def main():
    os.makedirs('data', exist_ok=True)
    df = load_and_prepare()
    print(f"Loaded {len(df)} rows, {df['Id_Cliente'].nunique()} clients")

    groups = list(df.groupby(['Id_Cliente', 'Familia_Potencial']))
    print(f"Processing {len(groups)} (client, family) pairs...")

    all_rows = []
    n_skipped = 0

    for i, ((cid, fam), grp) in enumerate(groups):
        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(groups)}] rows so far: {len(all_rows)}")

        rows = process_group(grp, cid, fam)
        if len(rows) == 0:
            n_skipped += 1
            continue
        all_rows.extend(rows)

    df_final = pd.DataFrame(all_rows)
    df_final.to_parquet(OUTPUT_PATH, index=False)
    print(f"\nDone! Saved {len(df_final)} rows to {OUTPUT_PATH}")
    print(f"Skipped {n_skipped} pairs (insufficient data)")
    print(f"Target distribution:\n{df_final['target'].value_counts().to_dict()}")

if __name__ == '__main__':
    main()
