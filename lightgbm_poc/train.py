"""
Walk-Forward CV + LightGBM training for purchase prediction.
Splits by reference_date (no random shuffling).
Each fold: train on past, validate on future → simulates real predictions.
"""
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score, precision_score, recall_score
import json, os, sys

DATA_PATH  = 'data/training_data.parquet'
MODEL_PATH = 'models/model.txt'
N_FOLDS    = 5

# ── Columns to drop before training ──────────────────────────────
DROP_COLS = ['Id_Cliente', 'Fecha_ordinal']  # identifiers, not features

# ── Categorical features for LightGBM ─────────────────────────────
CAT_FEATS = ['Familia_Potencial', 'Provincia', 'mes', 'trimestre', 'dia_setmana']


def load_data():
    df = pd.read_parquet(DATA_PATH)
    print(f"Loaded {len(df)} rows")
    print(f"Target: {df['target'].mean():.4f} positive rate")
    print(f"Horizons: {sorted(df['horitzó_dies'].unique())}")
    return df


def walk_forward_folds(df):
    """
    Create time-based folds ordered by reference_date.
    Returns list of (train_mask, val_mask, fold_name).
    """
    dates = sorted(df['Fecha_ordinal'].unique())
    print(f"\nUnique reference dates: {len(dates)}")
    print(f"Date range: {pd.Timestamp.fromordinal(int(dates[0]))} → {pd.Timestamp.fromordinal(int(dates[-1]))}")

    # Split dates into N_FOLDS roughly equal validation periods
    # First 20% is training seed, remaining 80% is divided into folds
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

        if len(train_dates) == 0 or len(val_dates) == 0:
            continue

        train_mask = df['Fecha_ordinal'].isin(train_dates)
        val_mask   = df['Fecha_ordinal'].isin(val_dates)

        folds.append({
            'fold': fold,
            'train_start': pd.Timestamp.fromordinal(int(train_dates[0])),
            'train_end':   pd.Timestamp.fromordinal(int(train_dates[-1])),
            'val_start':   pd.Timestamp.fromordinal(int(val_dates[0])),
            'val_end':     pd.Timestamp.fromordinal(int(val_dates[-1])),
            'n_train': train_mask.sum(),
            'n_val':   val_mask.sum(),
            'train_mask': train_mask,
            'val_mask':   val_mask,
        })
    return folds


def prepare_features(df, train_mask, val_mask):
    """Split into X, y, and prepare categorical feature indices."""
    train_df = df[train_mask].copy()
    val_df   = df[val_mask].copy()

    y_train = train_df['target'].values
    y_val   = val_df['target'].values

    X_train = train_df.drop(columns=['target'] + DROP_COLS)
    X_val   = val_df.drop(columns=['target'] + DROP_COLS)

    # Convert object columns to category dtype for LightGBM
    cat_cols_present = [c for c in CAT_FEATS if c in X_train.columns]
    for c in cat_cols_present:
        # Use same categories for train and val (handle unseen labels)
        all_cats = list(X_train[c].unique()) + list(X_val[c].unique())
        all_cats = sorted(set(str(x) for x in all_cats if pd.notna(x)))
        X_train[c] = pd.Categorical(X_train[c].astype(str), categories=all_cats)
        X_val[c]   = pd.Categorical(X_val[c].astype(str), categories=all_cats)

    cat_idxs = [X_train.columns.get_loc(c) for c in cat_cols_present]

    return X_train, y_train, X_val, y_val, cat_idxs


def train_fold(X_train, y_train, X_val, y_val, cat_idxs, fold_name):
    """Train LightGBM with early stopping on validation set."""
    # Compute class weight (handle imbalance)
    pos = y_train.sum()
    neg = len(y_train) - pos
    scale_pos_weight = neg / max(pos, 1)

    params = {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'learning_rate': 0.05,
        'max_depth': 7,
        'num_leaves': 63,
        'subsample': 0.8,
        'colsample_bytree': 0.7,
        'min_child_samples': 20,
        'reg_lambda': 3.0,
        'reg_alpha': 1.0,
        'scale_pos_weight': scale_pos_weight,
        'random_state': 42,
        'verbose': -1,
    }

    train_data = lgb.Dataset(
        X_train, label=y_train,
        categorical_feature=cat_idxs,
        free_raw_data=False,
    )
    val_data = lgb.Dataset(
        X_val, label=y_val,
        categorical_feature=cat_idxs,
        reference=train_data,
        free_raw_data=False,
    )

    model = lgb.train(
        params,
        train_data,
        valid_sets=[val_data],
        num_boost_round=1000,
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)],
    )

    y_pred = model.predict(X_val)
    auc  = roc_auc_score(y_val, y_pred)
    ap   = average_precision_score(y_val, y_pred)

    # Precision@K: top 10%, 20% of validation set
    n_k = len(y_val)
    for pct in [0.05, 0.10, 0.20]:
        k = max(1, int(n_k * pct))
        top_k_idx = np.argsort(y_pred)[-k:]
        prec_at_k = y_val[top_k_idx].mean()
        recall_at_k = y_val[top_k_idx].sum() / max(y_val.sum(), 1)
        print(f"    P@{pct*100:.0f}%: {prec_at_k:.4f}, R@{pct*100:.0f}%: {recall_at_k:.4f}")

    print(f"  AUC={auc:.4f}, AP={ap:.4f}, best_iter={model.best_iteration}")

    return {
        'model': model,
        'auc': auc,
        'avg_precision': ap,
        'best_iter': model.best_iteration,
        'y_pred': y_pred,
    }


def main():
    os.makedirs('models', exist_ok=True)
    df = load_data()

    # Walk-forward CV
    folds = walk_forward_folds(df)
    print(f"\n{'='*60}")
    print("WALK-FORWARD CROSS-VALIDATION")
    print(f"{'='*60}")
    for f in folds:
        print(f"  Fold {f['fold']}: train {f['train_start'].date()} → {f['train_end'].date()} "
              f"({f['n_train']} rows) | val {f['val_start'].date()} → {f['val_end'].date()} "
              f"({f['n_val']} rows)")

    results = []
    best_auc = 0
    best_model = None

    for f in folds:
        print(f"\n── Fold {f['fold']} ──")
        X_train, y_train, X_val, y_val, cat_idxs = prepare_features(
            df, f['train_mask'], f['val_mask']
        )

        print(f"  Train: {X_train.shape}, Val: {X_val.shape}")
        print(f"  Val target rate: {y_val.mean():.4f}")
        print(f"  Cat features at indices: {cat_idxs}")

        result = train_fold(X_train, y_train, X_val, y_val, cat_idxs, f"fold_{f['fold']}")

        results.append({
            'fold': f['fold'],
            'auc': result['auc'],
            'avg_precision': result['avg_precision'],
            'best_iter': result['best_iter'],
            'n_train': f['n_train'],
            'n_val': f['n_val'],
        })

        if result['auc'] > best_auc:
            best_auc = result['auc']
            best_model = result['model']

    # Summary
    print(f"\n{'='*60}")
    print("CV RESULTS SUMMARY")
    print(f"{'='*60}")
    results_df = pd.DataFrame(results)
    print(results_df[['fold', 'auc', 'avg_precision', 'best_iter']].to_string(index=False))
    print(f"\nMean AUC: {results_df['auc'].mean():.4f} ± {results_df['auc'].std():.4f}")
    print(f"Mean AP:  {results_df['avg_precision'].mean():.4f} ± {results_df['avg_precision'].std():.4f}")

    # Train final model on all data
    print(f"\n{'='*60}")
    print("TRAINING FINAL MODEL ON ALL DATA")
    print(f"{'='*60}")
    # Use best_iter from CV as estimate for final training
    avg_best_iter = int(results_df['best_iter'].mean())
    print(f"Using ~{avg_best_iter} iterations (avg from CV)")

    # Prepare all data
    all_mask = pd.Series(True, index=df.index)
    X_all, y_all, _, _, cat_idxs_all = prepare_features(df, all_mask, ~all_mask)

    params_final = {
        'objective': 'binary',
        'metric': 'auc',
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
    }

    train_data_all = lgb.Dataset(
        X_all, label=y_all,
        categorical_feature=cat_idxs_all,
        free_raw_data=False,
    )

    final_model = lgb.train(
        params_final,
        train_data_all,
        num_boost_round=avg_best_iter,
        callbacks=[lgb.log_evaluation(0)],
    )

    final_model.save_model(MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")

    # Feature importance
    print(f"\n{'='*60}")
    print("FEATURE IMPORTANCE (top 20)")
    print(f"{'='*60}")
    importances = pd.DataFrame({
        'feature': X_all.columns,
        'gain': final_model.feature_importance(importance_type='gain'),
        'split': final_model.feature_importance(importance_type='split'),
    }).sort_values('gain', ascending=False)

    print(importances.head(20).to_string(index=False))

    return final_model, results_df, importances


if __name__ == '__main__':
    main()
