"""
Visualitza casos test: interval predit vs interval real.
"""
import pandas as pd, numpy as np, lightgbm as lgb, os, sys, random
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__))
from train_interval_model import load_data, build_training_data, compute_features_at_purchase

MODEL_DIR = 'models/interval'
DATA_PATH = '../data/master_commodities.csv'
CAT_FEATS = ['Familia_Potencial', 'Provincia', 'mes', 'trimestre', 'dia_setmana']
OUTPUT_DIR = 'output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

models = {
    k: lgb.Booster(model_file=os.path.join(MODEL_DIR, f'{k}.txt'))
    for k in ['p25', 'p50', 'p75']
}

# Load + prepare data (use cached)
cache = 'data/interval_training_data.parquet'
if os.path.exists(cache):
    tdf = pd.read_parquet(cache)
else:
    df_raw = load_data()
    tdf = build_training_data(df_raw)
    tdf = tdf[tdf['target_dies'] <= 730]
    tdf.to_parquet(cache)

# Batch predict
drop_cols = ['target_dies', 'Id_Cliente', 'data_compra']
if 'ordinal' in tdf.columns:
    drop_cols.append('ordinal')
X_all = tdf.drop(columns=[c for c in drop_cols if c in tdf.columns])
for c in CAT_FEATS:
    if c in X_all.columns:
        X_all[c] = X_all[c].astype('category')

preds = pd.DataFrame({
    'p25': models['p25'].predict(X_all),
    'p50': models['p50'].predict(X_all),
    'p75': models['p75'].predict(X_all),
    'actual': tdf['target_dies'].values,
    'client_id': tdf['Id_Cliente'].values,
    'familia': tdf['Familia_Potencial'].values if 'Familia_Potencial' in tdf.columns else '',
    'purchase_date': tdf['data_compra'].values,
})
preds['error'] = (preds['actual'] - preds['p50']).abs()
preds['in_window'] = (preds['p25'] <= preds['actual']) & (preds['actual'] <= preds['p75'])

# ── Plot 1: Strip plot of many cases ──
print("Generating strip plot (sample of cases)...")
sample = preds.sample(min(200, len(preds)), random_state=42).copy()
sample = sample.sort_values('actual')

fig, ax = plt.subplots(figsize=(14, 8))
for i, (_, r) in enumerate(sample.iterrows()):
    color = '#10B981' if r['in_window'] else '#EF4444'
    # Predicted interval
    ax.plot([r['p25'], r['p75']], [i, i], color=color, linewidth=2.5, alpha=0.6)
    ax.plot(r['p50'], i, 'D', color='#F59E0B', markersize=5, alpha=0.8)
    # Actual
    ax.plot(r['actual'], i, 'o', color='#1E3A8A', markersize=6, zorder=5)

ax.set_xlabel('Dies des de l\'última compra', fontsize=12, fontweight='bold')
ax.set_ylabel('Casos (ordenats per interval real)', fontsize=12)
ax.set_title('Interval predit (p25-p75) vs Interval real (● blau) — 200 casos',
             fontsize=14, fontweight='bold')
from matplotlib.lines import Line2D as L2
legend_elements = [
    L2([0], [0], color='#10B981', linewidth=3, label='✅ Dins finestra'),
    L2([0], [0], color='#EF4444', linewidth=3, label='❌ Fora finestra'),
    L2([0], [0], marker='D', color='#F59E0B', linestyle='None', markersize=6, label='Mediana predita'),
    L2([0], [0], marker='o', color='#1E3A8A', linestyle='None', markersize=7, label='Interval real'),
]
ax.legend(handles=legend_elements, fontsize=9)
ax.grid(True, alpha=0.2, linestyle=':')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'strip_plot.png'), dpi=130)
print(f"  Saved {OUTPUT_DIR}/strip_plot.png")

# ── Plot 2: Error distribution ──
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
# Histogram of errors
axes[0].hist(preds['error'], bins=60, color='#2563EB', alpha=0.6, edgecolor='white')
axes[0].axvline(preds['error'].median(), color='#EF4444', linewidth=2.5, linestyle='--',
                label=f"Mediana = {preds['error'].median():.0f}d")
axes[0].axvline(preds['error'].mean(), color='#F59E0B', linewidth=2, linestyle=':',
                label=f"Mitjana = {preds['error'].mean():.0f}d")
axes[0].set_xlabel('Error absolut (dies)', fontsize=11)
axes[0].set_ylabel('Freqüència', fontsize=11)
axes[0].set_title('Distribució de l\'error absolut', fontsize=13, fontweight='bold')
axes[0].legend(fontsize=9)
axes[0].grid(True, alpha=0.2, linestyle=':')

# Error vs actual interval
axes[1].scatter(preds['actual'], preds['error'], alpha=0.1, s=5, color='#2563EB')
axes[1].set_xlabel('Interval real (dies)', fontsize=11)
axes[1].set_ylabel('Error absolut (dies)', fontsize=11)
axes[1].set_title('Error per interval real', fontsize=13, fontweight='bold')
axes[1].grid(True, alpha=0.2, linestyle=':')

# Coverage by interval range
bins = [0, 30, 60, 90, 180, 365, 731]
labels = ['<30d', '30-60d', '60-90d', '90-180d', '180-365d', '>365d']
preds['cat'] = pd.cut(preds['actual'], bins=bins, labels=labels)
cov_by_cat = preds.groupby('cat', observed=True)['in_window'].mean()
med_err_by_cat = preds.groupby('cat', observed=True)['error'].median()

ax2 = axes[1].twinx()
ax2.bar(range(len(cov_by_cat)), cov_by_cat.values * 100, alpha=0.15, color='#10B981',
        width=0.5, label='Coverage %')
ax2.set_ylabel('Coverage (%)', fontsize=11, color='#10B981')
for i, (cov, med) in enumerate(zip(cov_by_cat.values, med_err_by_cat.values)):
    axes[1].annotate(f'cov={cov:.0%}\nmae={med:.0f}d',
                     (bins[i] + (bins[i+1]-bins[i])/2, 350),
                     fontsize=7, ha='center', color='#10B981', fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'error_dist.png'), dpi=130)
print(f"  Saved {OUTPUT_DIR}/error_dist.png")

# ── Plot 3: Specific case examples ──
print("\nGenerating specific case examples...")
# Pick good, medium, bad cases
good = preds[preds['in_window']].sort_values('error').head(3)
medium = preds[preds['in_window'] & (preds['error'] > 20)].sort_values('error').head(3)
bad = preds[~preds['in_window']].sort_values('error', ascending=False).head(3)

def plot_case(r, fname, title):
    fig, ax = plt.subplots(figsize=(8, 1.8))
    fig.patch.set_facecolor('#FAFBFC')
    max_x = max(r['p75'] + 30, r['actual'] + 20, 100)
    ax.axhline(0.5, 0, max_x, color='#D1D5DB', linewidth=4, zorder=1)
    ax.axvspan(r['p25'], r['p75'], ymin=0.2, ymax=0.8, alpha=0.3, color='#10B981', zorder=2,
               label=f'Interval predit ({r["p25"]:.0f}-{r["p75"]:.0f}d)')
    ax.plot(r['actual'], 0.5, 'o', color='#1E3A8A', markersize=18, zorder=6,
            label=f'REAL: {r["actual"]:.0f}d')
    ax.plot(r['p50'], 0.5, 'D', color='#F59E0B', markersize=14, zorder=5,
            label=f'Mediana: {r["p50"]:.0f}d')
    ax.set_xlim(-3, max_x)
    ax.set_ylim(0, 1)
    ax.set_xlabel('Dies des de l\'última compra', fontsize=10)
    ax.tick_params(left=False, labelleft=False)
    ax.grid(True, axis='x', alpha=0.2, linestyle=':')
    ax.legend(fontsize=8, loc='upper right', ncol=2)
    ax.set_title(title, fontsize=11, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, fname), dpi=130)
    plt.close()
    print(f"  Saved {OUTPUT_DIR}/{fname}")

for i, (_, r) in enumerate(good.iterrows()):
    plot_case(r, f'case_good_{i}.png',
              f'✅ BONA: real={r["actual"]:.0f}d dins [{r["p25"]:.0f}, {r["p75"]:.0f}]  (error={r["error"]:.0f}d)')

for i, (_, r) in enumerate(medium.iterrows()):
    plot_case(r, f'case_medium_{i}.png',
              f'⚠️ ACCEPTABLE: real={r["actual"]:.0f}d dins [{r["p25"]:.0f}, {r["p75"]:.0f}]  (error={r["error"]:.0f}d)')

for i, (_, r) in enumerate(bad.iterrows()):
    plot_case(r, f'case_bad_{i}.png',
              f'❌ DOLENT: real={r["actual"]:.0f}d FORA de [{r["p25"]:.0f}, {r["p75"]:.0f}]  (error={r["error"]:.0f}d)')

print(f"\n✅ Fet. Revisa {OUTPUT_DIR}/")
print(f"\nMètriques globals:")
print(f"  Coverage (dins p25-p75): {preds['in_window'].mean():.1%}")
print(f"  MedAE: {preds['error'].median():.0f} dies")
print(f"  MAE:  {preds['error'].mean():.0f} dies")
print(f"\n  Coverage per rang:")
for cat, grp in preds.groupby('cat', observed=True):
    print(f"    {cat:>10}: cov={grp['in_window'].mean():.0%}  MedAE={grp['error'].median():.0f}d  n={len(grp)}")
