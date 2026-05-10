"""
Validate interval model: coverage, error by range.
"""
import pandas as pd, numpy as np, lightgbm as lgb, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from train_interval_model import load_data, build_training_data, compute_features_at_purchase

MODEL_DIR = 'models/interval'
DATA_PATH = '../data/master_commodities.csv'
CAT_FEATS = ['Familia_Potencial', 'Provincia', 'mes', 'trimestre', 'dia_setmana']

def prepare_row(row):
    """Convert a single row dict into a DataFrame ready for prediction."""
    X = pd.DataFrame([row])
    for c in CAT_FEATS:
        if c in X.columns:
            X[c] = X[c].astype('category')
    return X

def main():
    models = {
        'p25': lgb.Booster(model_file=os.path.join(MODEL_DIR, 'p25.txt')),
        'p50': lgb.Booster(model_file=os.path.join(MODEL_DIR, 'p50.txt')),
        'p75': lgb.Booster(model_file=os.path.join(MODEL_DIR, 'p75.txt')),
    }

    df_raw = load_data()
    tdf = build_training_data(df_raw)
    tdf = tdf[tdf['target_dies'] <= 730].copy()

    # Batch predict
    drop_cols = ['target_dies', 'Id_Cliente', 'data_compra']
    if 'ordinal' in tdf.columns:
        drop_cols.append('ordinal')
    X_all = tdf.drop(columns=drop_cols)
    for c in CAT_FEATS:
        if c in X_all.columns:
            X_all[c] = X_all[c].astype('category')

    preds = {
        'p25': models['p25'].predict(X_all),
        'p50': models['p50'].predict(X_all),
        'p75': models['p75'].predict(X_all),
    }

    results = pd.DataFrame({
        'actual': tdf['target_dies'].values,
        'p25': preds['p25'], 'p50': preds['p50'], 'p75': preds['p75'],
    })
    results['error'] = (results['actual'] - results['p50']).abs()
    results['in_window'] = (results['p25'] <= results['actual']) & (results['actual'] <= results['p75'])

    rdf = pd.DataFrame(results)
    print(f"\n{'='*60}")
    print("VALIDACIÓ: Interval model")
    print(f"{'='*60}")
    print(f"  Mostra: {len(rdf)} compres")
    print(f"  Coverage (dins p25-p75): {rdf['in_window'].mean():.1%}")
    print(f"  MAE (dies): {rdf['error'].mean():.0f}")
    print(f"  MedAE (dies): {rdf['error'].median():.0f}")

    print(f"\n  📊 Per rang d'interval real:")
    bins = [0, 30, 60, 90, 180, 365, 731]
    labels = ['<30d', '30-60d', '60-90d', '90-180d', '180-365d', '>365d']
    rdf['cat'] = pd.cut(rdf['actual'], bins=bins, labels=labels)
    for cat, grp in rdf.groupby('cat', observed=True):
        cov = grp['in_window'].mean()
        mae = grp['error'].median()
        print(f"    {cat:>10}: n={len(grp):5d}  cov={cov:.0%}  MedAE={mae:.0f}d")

    print(f"\n  📊 Error per quantil predit:")
    for q in [0.25, 0.50, 0.75]:
        col = f"p{q*100:.0f}"
        actual_col = 'actual'
        err = (rdf[actual_col] - rdf[col]).abs()
        print(f"    {col}: error mig={err.mean():.0f}d, median={err.median():.0f}d")

if __name__ == '__main__':
    main()
