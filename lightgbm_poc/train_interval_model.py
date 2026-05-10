"""
Entrenar LightGBM quantile regression: per cada compra, predir dies fins la següent.

Features: rolling windows, cicle, share, etc. al MOMENT de la compra.
Target: interval en dies fins la propera compra (regressió).
Walk-forward CV: split per data de compra (no leakage).

3 models: p25, p50 (median), p75 → interval des de l'última compra.

Usage: python3 train_interval_model.py
"""
import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime, timedelta
import os, json, sys

DATA_PATH    = '../data/master_commodities.csv'
MODEL_DIR    = 'models/interval'
N_FOLDS      = 5

QUANTILES    = [0.25, 0.50, 0.75]
Q_SUFFIX     = {0.25: 'p25', 0.50: 'p50', 0.75: 'p75'}

CAT_FEATS    = ['Familia_Potencial', 'Provincia', 'mes', 'trimestre', 'dia_setmana']

def load_data():
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    print(f"Loaded {len(df)} rows")
    return df

def compute_features_at_purchase(grp, purchase_date, familia, potencial):
    """
    Compute features as of a specific purchase date.
    Returns a dict of features or None if not enough data.
    """
    # Sales up to and including this purchase
    sales_to_date = grp[grp['Fecha'] <= purchase_date].copy()
    if len(sales_to_date) < 2:
        return None

    # Baseline (ex-campaigns) for clean rolling windows
    baseline = sales_to_date[sales_to_date['en_campana'] == 0]
    if len(baseline) == 0:
        return None

    baseline_daily = baseline.groupby('Fecha')['Valores_H'].sum()
    all_daily = sales_to_date.groupby('Fecha')['Valores_H'].sum()

    full_range = pd.date_range(baseline_daily.index.min(), purchase_date, freq='D')
    if purchase_date not in full_range:
        return None

    baseline_daily = baseline_daily.reindex(full_range, fill_value=0)
    all_daily = all_daily.reindex(full_range, fill_value=0)
    idx = full_range.get_loc(purchase_date)

    # Rolling windows (baseline = ex-campaign)
    roll = {}
    for w in [7, 30, 90, 180, 365]:
        roll[f'euros_{w}d'] = float(baseline_daily.rolling(w, min_periods=1).sum().iloc[idx])
        roll[f'n_ped_{w}d'] = float((baseline_daily > 0).astype(float).rolling(w, min_periods=1).sum().iloc[idx])

    # Purchases before this one
    purchase_dates = full_range[all_daily > 0]
    past_purchases = purchase_dates[purchase_dates < purchase_date]

    # Dies desde l'última compra (abans d'aquesta)
    if len(past_purchases) > 0:
        dies_desde = (purchase_date - past_purchases[-1]).days
    else:
        dies_desde = -1

    # Cycle features from ALL purchases before this one
    if len(past_purchases) >= 2:
        s = past_purchases.to_series()
        intervals = s.diff().dt.days.iloc[1:]
        cicle_mean = float(intervals.mean())
        cicle_std  = float(intervals.std()) if len(intervals) > 1 else 0.0
        num_int    = len(intervals)
    else:
        cicle_mean = -1.0
        cicle_std  = -1.0
        num_int    = 0

    # Share of wallet
    e365 = roll['euros_365d']
    e90  = roll['euros_90d']
    share_12m = e365 / potencial if potencial > 0 else 0.0
    share_3m  = (e90 * 4) / potencial if potencial > 0 else 0.0
    gap = max(0.0, potencial - e365)

    # Trends
    e30  = roll['euros_30d']
    avg90m = e90 / 3.0 if e90 > 1 else 0.001
    avg365m= e365/12.0 if e365 > 1 else 0.001
    ratio_30_90  = e30 / avg90m
    ratio_90_365 = avg90m / avg365m

    # Temporal
    provincia = str(sales_to_date['Provincia'].iloc[0]) if pd.notna(sales_to_date['Provincia'].iloc[0]) else 'Unknown'

    return {
        'Familia_Potencial': familia,
        'Provincia': provincia,
        'mes': purchase_date.month,
        'trimestre': (purchase_date.month - 1) // 3 + 1,
        'dia_setmana': purchase_date.weekday(),
        'dia_anyo': purchase_date.timetuple().tm_yday,
        'Potencial_EUR_anual': potencial,
        'euros_7d': roll['euros_7d'], 'euros_30d': e30,
        'euros_90d': e90, 'euros_180d': roll['euros_180d'], 'euros_365d': e365,
        'n_pedidos_7d': roll['n_ped_7d'], 'n_pedidos_30d': roll['n_ped_30d'],
        'n_pedidos_90d': roll['n_ped_90d'], 'n_pedidos_365d': roll['n_ped_365d'],
        'ratio_30d_vs_90d': ratio_30_90,
        'ratio_90d_vs_365d': ratio_90_365,
        'share_wallet_12m': share_12m,
        'gap_eur': gap,
        'dies_desde_ultima_compra': dies_desde,
        'cicle_mig_dies': cicle_mean,
        'cicle_std_dies': cicle_std,
        'num_intervals': num_int,
    }

def build_training_data(df):
    """Build one row per purchase event → target = days until next purchase."""
    rows = []
    groups = list(df.groupby(['Id_Cliente', 'Familia_Potencial']))
    print(f"Processing {len(groups)} (client, family) pairs...")

    for (cid, fam), grp in groups:
        potencial = float(grp['Potencial_EUR_anual'].iloc[0])
        grp = grp.sort_values('Fecha')
        dates = grp['Fecha'].unique()

        if len(dates) < 3:
            continue  # need at least 2 intervals

        for i in range(len(dates) - 1):
            purchase_date = dates[i]
            next_date = dates[i + 1]
            target = (next_date - purchase_date).days

            feats = compute_features_at_purchase(grp, purchase_date, fam, potencial)
            if feats is None:
                continue

            feats['Id_Cliente'] = int(cid)
            feats['target_dies'] = target
            feats['data_compra'] = purchase_date
            rows.append(feats)

    result = pd.DataFrame(rows)
    print(f"  Total rows: {len(result)}")
    print(f"  Target stats: mean={result['target_dies'].mean():.0f}d "
          f"median={result['target_dies'].median():.0f}d "
          f"max={result['target_dies'].max():.0f}d")
    return result

def walk_forward_cv(df):
    """Walk-forward CV by purchase date. No leakage."""
    dates = sorted(df['data_compra'].unique())

    seed_end = int(len(dates) * 0.2)
    val_size = (len(dates) - seed_end) // N_FOLDS

    folds = []
    for fold in range(N_FOLDS):
        val_start = seed_end + fold * val_size
        val_end   = seed_end + (fold + 1) * val_size
        if fold == N_FOLDS - 1:
            val_end = len(dates)

        train_dates = dates[:val_start]
        val_dates   = dates[val_start:val_end]

        train_mask = df['data_compra'].isin(train_dates)
        val_mask   = df['data_compra'].isin(val_dates)

        folds.append({
            'train_mask': train_mask,
            'val_mask': val_mask,
            'n_train': train_mask.sum(),
            'n_val': val_mask.sum(),
        })

    return folds

def train_quantile(X_train, y_train, X_val, y_val, alpha, cat_idxs, model_path):
    """Train one quantile regression model."""
    params = {
        'objective': 'quantile',
        'alpha': alpha,
        'metric': 'quantile',
        'boosting_type': 'gbdt',
        'learning_rate': 0.05,
        'max_depth': 7,
        'num_leaves': 63,
        'subsample': 0.8,
        'colsample_bytree': 0.7,
        'min_child_samples': 20,
        'reg_lambda': 3.0,
        'reg_alpha': 1.0,
        'random_state': 42,
        'verbose': -1,
        'first_metric_only': True,
    }

    train_data = lgb.Dataset(X_train, label=y_train, categorical_feature=cat_idxs)
    val_data   = lgb.Dataset(X_val, label=y_val, categorical_feature=cat_idxs, reference=train_data)

    model = lgb.train(
        params,
        train_data,
        valid_sets=[val_data],
        num_boost_round=1000,
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)],
    )

    model.save_model(model_path)
    return model

def prepare_features(df, mask):
    sub = df[mask].copy()
    y = sub['target_dies'].values
    X = sub.drop(columns=['target_dies', 'Id_Cliente', 'data_compra', 'ordinal'])

    cat_cols = [c for c in CAT_FEATS if c in X.columns]
    for c in cat_cols:
        all_cats = sorted(set(str(x) for x in X[c].unique() if pd.notna(x)))
        X[c] = pd.Categorical(X[c].astype(str), categories=all_cats)

    cat_idxs = [X.columns.get_loc(c) for c in cat_cols]
    return X, y, cat_idxs

def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    print("=" * 60)
    print("BUILD TRAINING DATA: purchase events → days_to_next")
    print("=" * 60)
    df_raw = load_data()
    tdf = build_training_data(df_raw)

    # Cap target at reasonable values
    tdf = tdf[tdf['target_dies'] <= 730].copy()  # max 2 years
    tdf['ordinal'] = tdf['data_compra'].map(pd.Timestamp.toordinal)
    print(f"  After capping at 730d: {len(tdf)} rows")

    # Walk-forward CV
    folds = walk_forward_cv(tdf)
    print(f"\n{'='*60}")
    print("WALK-FORWARD CROSS-VALIDATION")
    print(f"{'='*60}")
    for i, f in enumerate(folds):
        print(f"  Fold {i}: train={f['n_train']}, val={f['n_val']}")

    # Train quantile models
    print(f"\n{'='*60}")
    print("TRAINING QUANTILE MODELS")
    print(f"{'='*60}")

    all_results = {}
    for alpha in QUANTILES:
        suffix = Q_SUFFIX[alpha]
        print(f"\n── Quantile {alpha:.2f} ({suffix}) ──")

        # Walk-forward CV
        cv_metrics = []
        best_model = None
        best_val_loss = float('inf')

        for fold_idx, f in enumerate(folds):
            Xtr, ytr, cat_idxs = prepare_features(tdf, f['train_mask'])
            Xva, yva, _         = prepare_features(tdf, f['val_mask'])

            model = train_quantile(
                Xtr, ytr, Xva, yva, alpha, cat_idxs,
                f"{MODEL_DIR}/fold{fold_idx}_{suffix}.txt"
            )

            y_pred = model.predict(Xva)
            # Pinball loss
            err = yva - y_pred
            pinball = np.mean(np.maximum(alpha * err, (alpha - 1) * err))
            cv_metrics.append(pinball)

            print(f"  Fold {fold_idx}: pinball_loss={pinball:.1f}, best_iter={model.best_iteration}")

            if pinball < best_val_loss:
                best_val_loss = pinball
                best_model = model

        # Train final model on ALL data
        print(f"  → Training final model on all data...")
        Xall, yall, cat_idxs_all = prepare_features(tdf, pd.Series(True, index=tdf.index))

        train_data = lgb.Dataset(Xall, label=yall, categorical_feature=cat_idxs_all)
        final_model = lgb.train(
            {
                'objective': 'quantile', 'alpha': alpha,
                'boosting_type': 'gbdt', 'learning_rate': 0.05,
                'max_depth': 7, 'num_leaves': 63,
                'subsample': 0.8, 'colsample_bytree': 0.7,
                'min_child_samples': 20, 'reg_lambda': 3.0, 'reg_alpha': 1.0,
                'random_state': 42, 'verbose': -1,
            },
            train_data,
            num_boost_round=best_model.best_iteration,
        )
        final_model.save_model(f"{MODEL_DIR}/{suffix}.txt")

        # Feature importance
        imp = pd.DataFrame({
            'feature': Xall.columns,
            'gain': final_model.feature_importance(importance_type='gain'),
        }).sort_values('gain', ascending=False).head(10)

        all_results[suffix] = {
            'cv_loss': np.mean(cv_metrics),
            'cv_std': np.std(cv_metrics),
            'best_iter': best_model.best_iteration,
            'top_features': imp.to_dict('records'),
        }
        print(f"  CV pinball loss: {np.mean(cv_metrics):.1f} ± {np.std(cv_metrics):.1f}")
        print(f"  Top features: {imp['feature'].head(5).tolist()}")

    # Summary
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    for q, suffix in Q_SUFFIX.items():
        r = all_results[suffix]
        print(f"  {suffix} (α={q:.2f}): CV loss={r['cv_loss']:.1f}±{r['cv_std']:.1f}, "
              f"iter={r['best_iter']}")

    # Save config
    with open(f"{MODEL_DIR}/config.json", 'w') as f:
        json.dump({'features': Xall.columns.tolist(), 'quantiles': QUANTILES,
                    'cat_feats': CAT_FEATS}, f, indent=2)

    print(f"\n✅ Models saved to {MODEL_DIR}/")
    print(f"   Files: {', '.join(f'{suffix}.txt' for suffix in Q_SUFFIX.values())}")

if __name__ == '__main__':
    main()
