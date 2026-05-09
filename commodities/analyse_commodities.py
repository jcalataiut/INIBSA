"""
Anàlisi + Visualització dels resultats del Motor Commodities.
Ús: python commodities/analyse_commodities.py
"""

import pandas as pd
import numpy as np
import sys, os
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", palette="muted")
OUTPUT_DIR = 'commodities/output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from commodities.commodities_engine import run

today = '2025-12-01'
alerts_path = 'commodities/alertes_20251201.csv'

# ── 1. RUN ENGINE ─────────────────────────────────────────────────────────────
print("=" * 65)
print("  ANÀLISI DE RESULTATS — MOTOR COMMODITIES")
print("=" * 65)
alerts, segments = run(today=today, output_path=alerts_path)

if len(alerts) == 0:
    print("⚠️  Cap alerta generada.")
    # Tot i així, tenim segments
    if len(segments) > 0:
        print(f"   Hi ha {len(segments):,} (client, família) segmentats.")
    else:
        sys.exit(0)

# ── 2. ESTADÍSTIQUES ─────────────────────────────────────────────────────────
print(f"\n{'─' * 65}")
print("   RESUM GLOBAL")
print(f"{'─' * 65}")
print(f"   Alertes: {len(alerts):,}  |  Clients: {alerts['Id_Cliente'].nunique():,}  |  Gap total: {alerts['gap_eur'].sum():,.0f}€/any")
print(f"   Gap mitjà: {alerts['gap_eur'].mean():,.0f}€  |  Prioritat mitjana: {alerts['prioritat'].mean():,.0f}")

print(f"\n   Per família:")
for fam, grp in alerts.groupby('Familia_Potencial'):
    print(f"     {fam}: {len(grp)} alertes, {grp['Id_Cliente'].nunique()} clients, gap={grp['gap_eur'].sum():,.0f}€")

print(f"\n   Per tipus d'alerta:")
for tipus, grp in alerts.groupby('tipus_alerta'):
    print(f"     {tipus:>30s}: {len(grp):>5d}  gap={grp['gap_eur'].sum():>8,.0f}€  prio_mig={grp['prioritat'].mean():>7.0f}")

print(f"\n   Per segment (TOTAL, no només alertes):")
# Usar el DataFrame de segments complert (tots els client-família, no només alertes)
for seg in ['fidel','promiscu','marginal','en_risc','nou','perdut']:
    n = (segments['segment'] == seg).sum()
    pct = n / len(segments) * 100
    print(f"     {seg:>12s}: {n:>5d}  ({pct:5.1f}%)")

# ── 3. QUALITAT ───────────────────────────────────────────────────────────────
print(f"\n{'─' * 65}")
print("   QUALITAT")
print(f"{'─' * 65}")
print(f"   Alerta amb prioritat=0:   {(alerts['prioritat']==0).sum()}")
print(f"   Alerta amb gap=0:         {(alerts['gap_eur']<=0).sum()}")
print(f"   Sense cicle reposició:    {alerts['cicle_mig_dies'].isna().sum()} ({alerts['cicle_mig_dies'].isna().sum()/len(alerts)*100:.1f}%)")
print(f"\n   Consistència segment→tipus:")
for seg in ['fidel','promiscu','marginal','en_risc','nou','perdut']:
    sub = alerts[alerts['segment']==seg]
    if len(sub):
        print(f"     {seg:>12s} → {sorted(sub['tipus_alerta'].unique())}")
print(f"\n   Urgència: alta={(alerts['urgencia']=='alta').sum()}  mitjana={(alerts['urgencia']=='mitjana').sum()}  baixa={(alerts['urgencia']=='baixa').sum()}")
print(f"   Canal:    delegat={(alerts['canal']=='delegat').sum()}  televenda={(alerts['canal']=='televenda').sum()}")

# ── 4. TOP 10 ─────────────────────────────────────────────────────────────────
print(f"\n{'─' * 65}")
print("   TOP 10 ALERTES")
print(f"{'─' * 65}")
for i, (_, a) in enumerate(alerts.head(10).iterrows()):
    print(f"   {i+1}. #{a['Id_Cliente']:>10d} | {str(a.get('Provincia',''))[:15]:15s} | {a['Familia_Potencial']:12s} | "
          f"{a['tipus_alerta']:>22s} | {a['segment']:>10s} | gap={a['gap_eur']:>6.0f}€ | prio={a['prioritat']:>6.0f}")

# ── 5. PLOTS ──────────────────────────────────────────────────────────────────
print(f"\n{'─' * 65}")
print("   GENERANT PLOTS...")
print(f"{'─' * 65}")

# ── Plot 1: Segment distribution (TOTAL client-família, no només alertes) ────
fig, ax = plt.subplots(figsize=(10, 5))
seg_order = ['fidel', 'promiscu', 'marginal', 'en_risc', 'nou', 'perdut']
seg_count = segments['segment'].value_counts()
seg_colors = {'fidel':'#2ecc71','promiscu':'#f1c40f','marginal':'#95a5a6',
              'en_risc':'#e67e22','nou':'#3498db','perdut':'#e74c3c'}
bars = ax.bar([s for s in seg_order if s in seg_count],
              [seg_count.get(s, 0) for s in seg_order],
              color=[seg_colors[s] for s in seg_order])
for bar, s in zip(bars, seg_order):
    n = seg_count.get(s, 0)
    pct = n / len(segments) * 100
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height(),
            f'{n:,}  ({pct:.1f}%)', ha='center', va='bottom', fontweight='bold', fontsize=10)
ax.set_title('Distribució per Segment — TOTS els (client, família)', fontsize=14, fontweight='bold')
ax.set_ylabel('Nombre de (client, família)')
ax.spines[['top','right']].set_visible(False)
ax.set_ylim(0, max(seg_count.values) * 1.15)
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/01_segment_dist.png', dpi=120)
plt.close()
print("   ✓ 01_segment_dist.png (distribució REAL, no només alertes)")

# ── Plot 2: Share of wallet distribution per segment (TOTAL) ─────────────────
fig, ax = plt.subplots(figsize=(10, 5))
sns.boxplot(data=segments, x='segment', y='share_12m',
            order=seg_order,
            palette=seg_colors, ax=ax)
ax.set_title('Share of Wallet per Segment — TOTS els (client, família)', fontsize=14, fontweight='bold')
ax.set_ylabel('Share of Wallet (0–100%)')
ax.set_xlabel('')
ax.spines[['top','right']].set_visible(False)
# Afegir nombre de mostres a sota
for i, s in enumerate(seg_order):
    n = seg_count.get(s, 0)
    ax.text(i, -0.08, f'n={n:,}', ha='center', va='top', fontsize=9, transform=ax.get_xaxis_transform())
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/02_share_by_segment.png', dpi=120)
plt.close()
print("   ✓ 02_share_by_segment.png")

# ── Plot 3: Alert type distribution (horizontal) ─────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
alert_order = alerts['tipus_alerta'].value_counts().index
colors_alert = plt.cm.Set2(np.linspace(0, 1, len(alert_order)))
bars = ax.barh(range(len(alert_order)), alerts['tipus_alerta'].value_counts().values, color=colors_alert)
ax.set_yticks(range(len(alert_order)))
ax.set_yticklabels(alert_order)
for bar in bars:
    ax.text(bar.get_width()+2, bar.get_y()+bar.get_height()/2, f'{bar.get_width():,}',
            ha='left', va='center', fontsize=10)
ax.set_title('Alertes per Tipus', fontsize=14, fontweight='bold')
ax.set_xlabel('Nombre d\'alertes')
ax.spines[['top','right']].set_visible(False)
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/03_alert_type.png', dpi=120)
plt.close()
print("   ✓ 03_alert_type.png")

# ── Plot 4: Priority vs Gap scatter ──────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
scatter = ax.scatter(alerts['gap_eur'], alerts['prioritat'],
                     c=[seg_colors.get(s, '#999') for s in alerts['segment']],
                     s=alerts['dies_sense_compra'].clip(0, 200) + 10,
                     alpha=0.5, edgecolors='none')
ax.set_xlabel('Gap (€/any)')
ax.set_ylabel('Prioritat')
ax.set_title('Prioritat vs Gap — cada punt = una alerta (mida = dies sense compra)', fontsize=12)
ax.spines[['top','right']].set_visible(False)
# Llegenda de segments
from matplotlib.lines import Line2D
legend_elements = [Line2D([0],[0], marker='o', color='w', markerfacecolor=seg_colors[s],
                          markersize=8, label=s) for s in seg_order if s in seg_count]
ax.legend(handles=legend_elements, title='Segment')
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/04_priority_vs_gap.png', dpi=120)
plt.close()
print("   ✓ 04_priority_vs_gap.png")

# ── Plot 5: Gap distribution ─────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
# Histograma
axes[0].hist(alerts['gap_eur'], bins=50, color='#2c3e50', alpha=0.7, edgecolor='white')
axes[0].set_xlabel('Gap (€)')
axes[0].set_ylabel('Freqüència')
axes[0].set_title('Distribució del Gap', fontsize=12, fontweight='bold')
axes[0].spines[['top','right']].set_visible(False)
# Boxplot per segment
sns.boxplot(data=alerts, x='segment', y='gap_eur',
            order=['fidel','promiscu','marginal','en_risc','nou','perdut'],
            palette=seg_colors, ax=axes[1])
axes[1].set_title('Gap per Segment', fontsize=12, fontweight='bold')
axes[1].set_ylabel('Gap (€)')
axes[1].set_xlabel('')
axes[1].spines[['top','right']].set_visible(False)
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/05_gap_distribution.png', dpi=120)
plt.close()
print("   ✓ 05_gap_distribution.png")

# ── Plot 6: Top provinces by gap ─────────────────────────────────────────────
prov_gap = alerts.groupby('Provincia').agg(
    n=('Id_Cliente','count'), gap=('gap_eur','sum')
).sort_values('gap', ascending=False).head(15)
fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.barh(range(len(prov_gap)), prov_gap['gap'].values, color='#3498db')
ax.set_yticks(range(len(prov_gap)))
ax.set_yticklabels(prov_gap.index)
for i, (_, r) in enumerate(prov_gap.iterrows()):
    ax.text(r['gap']+200, i, f'{r["n"]} alert.  {r["gap"]:,.0f}€', va='center', fontsize=9)
ax.set_title('Top 15 Províncies per Gap Total', fontsize=13, fontweight='bold')
ax.set_xlabel('Gap (€/any)')
ax.spines[['top','right']].set_visible(False)
ax.invert_yaxis()
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/06_top_provinces.png', dpi=120)
plt.close()
print("   ✓ 06_top_provinces.png")

# ── Plot 7: Urgency + Canal pie ──────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
urg_counts = alerts['urgencia'].value_counts()
axes[0].pie(urg_counts.values, labels=urg_counts.index, autopct='%1.0f%%',
            colors=['#e74c3c','#f39c12','#3498db'], startangle=90)
axes[0].set_title('Urgència', fontweight='bold')
canal_counts = alerts['canal'].value_counts()
axes[1].pie(canal_counts.values, labels=canal_counts.index, autopct='%1.0f%%',
            colors=['#2ecc71','#9b59b6'], startangle=90)
axes[1].set_title('Canal Recomanat', fontweight='bold')
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/07_urgency_canal.png', dpi=120)
plt.close()
print("   ✓ 07_urgency_canal.png")

# ── Plot 8: Rolling share evolution (need to reload raw data) ───────────────
print("\n   📊 Calculant evolució temporal del share of wallet...")
df = pd.read_csv('data/master_commodities_clean.csv', low_memory=False)
df = df[df['es_devolucion'] == 0].copy()
df['Fecha'] = pd.to_datetime(df['Fecha'])
df['any_mes'] = df['Fecha'].dt.to_period('M').astype(str)
pot = df[['Id_Cliente', 'Familia_Potencial', 'Potencial_EUR']].drop_duplicates()

monthly = df.groupby(['Familia_Potencial', 'any_mes'], as_index=False).agg(
    euros=('Valores_H', 'sum'),
    clients=('Id_Cliente', 'nunique'),
    pedidos=('Num.Fact', 'nunique'),
)
monthly['any_mes'] = pd.to_datetime(monthly['any_mes'].str[:7] + '-01')

fig, ax1 = plt.subplots(figsize=(12, 5))
for fam in monthly['Familia_Potencial'].unique():
    sub = monthly[monthly['Familia_Potencial']==fam].sort_values('any_mes')
    ax1.plot(sub['any_mes'], sub['euros']/1000, label=fam, linewidth=2)
ax1.set_ylabel('Euros (k€/mes)', color='#2c3e50')
ax1.set_title('Evolució Vendes Commodities (2021–2025)', fontsize=14, fontweight='bold')
ax1.legend()
ax1.spines[['top','right']].set_visible(False)

ax2 = ax1.twinx()
sub_all = monthly.groupby('any_mes')['clients'].sum().reset_index()
ax2.plot(sub_all['any_mes'], sub_all['clients'], color='#e74c3c', linewidth=1.5, alpha=0.6, linestyle='--')
ax2.set_ylabel('Clients actius/mes', color='#e74c3c')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/08_monthly_evolution.png', dpi=120)
plt.close()
print("   ✓ 08_monthly_evolution.png")

# ── SUMMARY ───────────────────────────────────────────────────────────────────
print(f"\n{'=' * 65}")
print("   SUMMARY")
print(f"{'=' * 65}")
print(f"   {len(alerts):,} alertes | {alerts['Id_Cliente'].nunique():,} clients | {alerts['Familia_Potencial'].nunique()} famílies")
print(f"   Gap recuperable: {alerts['gap_eur'].sum():,.0f}€/any")
print(f"   Plots guardats a {OUTPUT_DIR}/")
