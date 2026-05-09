"""
Anàlisi i visualització dels resultats del Motor Commodities.
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from commodities.commodities_engine import run

# ── 1. EXECUTAR ENGINE ───────────────────────────────────────────────────────
print("=" * 65)
print("  ANÀLISI DE RESULTATS — MOTOR COMMODITIES")
print("=" * 65)

today = '2025-12-01'
alerts = run(today=today, output_path='commodities/alertes_20251201.csv')

if len(alerts) == 0:
    print("⚠️  Cap alerta generada. No hi ha res per analitzar.")
    sys.exit(0)

# ── 2. ESTADÍSTIQUES GLOBALS ─────────────────────────────────────────────────
print(f"\n{'─' * 65}")
print("   ESTADÍSTIQUES GLOBALS")
print(f"{'─' * 65}")

print(f"\n   Total alertes: {len(alerts)}")
print(f"   Clients únics: {alerts['Id_Cliente'].nunique()}")
print(f"   Famílies: {alerts['Familia_Potencial'].nunique()}")

print(f"\n   Per família:")
for fam, grp in alerts.groupby('Familia_Potencial'):
    print(f"     {fam}: {len(grp)} alertes, {grp['Id_Cliente'].nunique()} clients")

gap_total = alerts['gap_eur'].sum()
print(f"\n   Gap total recuperable: {gap_total:,.0f} €/any")
print(f"   Gap mitjà per alerta: {alerts['gap_eur'].mean():,.0f} €")
print(f"   Prioritat mitjana: {alerts['prioritat'].mean():,.0f}")

# ── 3. DISTRIBUCIÓ PER TIPUS D'ALERTA ────────────────────────────────────────
print(f"\n{'─' * 65}")
print("   DISTRIBUCIÓ PER TIPUS D'ALERTA")
print(f"{'─' * 65}")
for tipus, grp in alerts.groupby('tipus_alerta'):
    n = len(grp)
    pct = n / len(alerts) * 100
    gap = grp['gap_eur'].sum()
    prio_med = grp['prioritat'].median()
    print(f"   {tipus:>30s}: {n:>5d} ({pct:5.1f}%)  gap={gap:>8,.0f}€  prio_med={prio_med:>8,.0f}")

# ── 4. DISTRIBUCIÓ PER SEGMENT ────────────────────────────────────────────────
print(f"\n{'─' * 65}")
print("   DISTRIBUCIÓ PER SEGMENT")
print(f"{'─' * 65}")
for seg, grp in alerts.groupby('segment'):
    n = len(grp)
    pct = n / len(alerts) * 100
    gap = grp['gap_eur'].sum()
    print(f"   {seg:>15s}: {n:>5d} ({pct:5.1f}%)  gap={gap:>8,.0f}€")

# ── 5. PERFIL D'ALERTES PER SEGMENT ──────────────────────────────────────────
print(f"\n{'─' * 65}")
print("   PERFIL D'ALERTES PER SEGMENT (share, gap, retard mitjà)")
print(f"{'─' * 65}")
seg_profile = alerts.groupby('segment').agg(
    n=('Id_Cliente', 'count'),
    share_mig=('share_12m', 'mean'),
    gap_mig=('gap_eur', 'mean'),
    dies_sense_mig=('dies_sense_compra', 'mean'),
    prioritat_mig=('prioritat', 'mean'),
).round(2)
print(seg_profile.to_string())

# ── 6. TOP 10 ALERTES (ja surten a l'engine, aquí en format compacte) ───────
print(f"\n{'─' * 65}")
print("   TOP 10 PER PRIORITAT (format compacte)")
print(f"{'─' * 65}")
cols = ['Id_Cliente', 'Provincia', 'Familia_Potencial', 'tipus_alerta',
        'segment', 'gap_eur', 'prioritat', 'dies_sense_compra']
for i, (_, a) in enumerate(alerts.head(10).iterrows()):
    print(f"   #{a['Id_Cliente']:>12d} | {str(a.get('Provincia', '?')):15s} | {a['Familia_Potencial']:12s} | "
          f"{a['tipus_alerta']:>22s} | {a['segment']:>10s} | gap={a['gap_eur']:>6.0f}€ | "
          f"prio={a['prioritat']:>8.0f}")

# ── 7. COMPROVACIÓ DE QUALITAT ──────────────────────────────────────────────
print(f"\n{'─' * 65}")
print("   QUALITAT I VALIDACIONS")
print(f"{'─' * 65}")

# 7a. Alerta amb prioritat 0 (possible anomalia)
zero_prio = alerts[alerts['prioritat'] == 0]
print(f"\n   Alertes amb prioritat = 0: {len(zero_prio)}")
if len(zero_prio) > 0:
    print(f"     Motiu: gap=0? {(zero_prio['gap_eur'] == 0).sum()} | sense cicle? {(zero_prio['dies_sense_compra'] == 0).sum()}")

# 7b. Gap = 0 (share = 100% o més)
gap_zero = alerts[alerts['gap_eur'] <= 0]
print(f"   Alertes amb gap ≤ 0 (share ≥ 100%): {len(gap_zero)}")
if len(gap_zero) > 0:
    print(f"     Segments: {gap_zero['segment'].value_counts().to_dict()}")

# 7c. Sense cicle de reposició
no_cicle = alerts[alerts['cicle_mig_dies'].isna()]
print(f"   Alertes sense cicle de reposició: {len(no_cicle)} ({len(no_cicle)/len(alerts)*100:.1f}%)")

# 7d. Verificar que tots els segments tenen alertes consistents
print(f"\n   Consistència segment → tipus_alerta:")
for seg in ['fidel', 'promiscu', 'marginal', 'en_risc', 'nou', 'perdut']:
    subset = alerts[alerts['segment'] == seg]
    if len(subset) > 0:
        tipus = subset['tipus_alerta'].unique()
        print(f"     {seg:>12s} → {sorted(tipus)}")

# 7e. Distribució per urgència
print(f"\n   Distribució per urgència:")
for urg, grp in alerts.groupby('urgencia'):
    print(f"     {urg:>10s}: {len(grp):>5d} ({len(grp)/len(alerts)*100:.1f}%)")

# 7f. Canal recomanat
print(f"\n   Distribució per canal recomanat:")
for can, grp in alerts.groupby('canal'):
    print(f"     {can:>10s}: {len(grp):>5d} ({len(grp)/len(alerts)*100:.1f}%)")

# ── 8. ANÀLISI GEOGRÀFICA ────────────────────────────────────────────────────
if 'Provincia' in alerts.columns:
    print(f"\n{'─' * 65}")
    print("   TOP 10 PROVÍNCIES PER GAP TOTAL")
    print(f"{'─' * 65}")
    for prov, grp in alerts.groupby('Provincia'):
        prov_str = str(prov) if pd.notna(prov) else 'SENSE_PROV'
        print(f"   {prov_str[:20]:20s}: {len(grp):>5d} alertes, gap={grp['gap_eur'].sum():>8,.0f}€, "
              f"prio_mig={grp['prioritat'].mean():>8,.0f}")

# ── 9. SUMMARY FINAL PER AL LLM/HACKATHON ────────────────────────────────────
print(f"\n{'=' * 65}")
print("   RESUM EXECUTIU PER AL HACKATHON")
print(f"{'=' * 65}")
seg_actual = alerts.groupby('segment').size().to_dict()
print(f"\n   📊 {len(alerts):,} alertes prioritzades ({alerts['Id_Cliente'].nunique():,} clients únics)")
print(f"   💰 Gap total recuperable: {gap_total:,.0f} €/any")
print(f"   🏷️  Segments: {seg_actual}")
print(f"   ⚠️  Alertes d\'alta urgència: {(alerts['urgencia'] == 'alta').sum()} ({sum(v for k,v in alerts['tipus_alerta'].value_counts().items() if k in ('risc_fuga', 'finestra_captura'))}) operatives")
print(f"\n   Les alertes \"finestra_captura\" sobre promiscus representen oportunitats immediates")
print(f"   de captura de demanda que actualment va a la competència.")
print(f"   Les alertes \"risc_fuga\" indiquen clients amb tendència negativa que requereixen")
print(f"   intervenció prioritària de l'equip de delegats.")
