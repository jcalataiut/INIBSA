"""
Valida la detecció de caiguda de volum en productes tècnics.

Ús:
    python scratch/validate_volum_drop.py

Simula 3 casos:
  1. Client amb caiguda de volum clara (ratio 0.3), silenci dins del normal
  2. Client sense caiguda (ratio ~1.0), mateix patró temporal
  3. Client amb poques dades (no s'ha de detectar res)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from backend.engine.technicals_engine import calc_individual_pattern, classify_all, generate_alerts, calc_sow_and_gap

TODAY = "2026-01-15"
REF = pd.Timestamp("2025-01-01")

def make_fake_sales(client_id, family, orders):
    rows = []
    for i, (dia, valor) in enumerate(orders):
        rows.append({
            "id_cliente": client_id,
            "familia_potencial": family,
            "num_fact": f"F{client_id}_{i}",
            "fecha": REF + pd.Timedelta(days=dia),
            "valores_h": valor,
            "es_commodity": False,
            "es_devolucion": False,
            "en_campana": False,
            "potencial_eur_anual": 100000,
            "id_producto": 1,
            "cod_postal": "08001",
            "provincia": "Barcelona",
        })
    return pd.DataFrame(rows)

def test_volume_drop():
    print("╔══ Test: Detecció de Caiguda de Volum ══╗\n")

    # ── Cas 1: Client amb caiguda de volum ──────────────
    # 5 comandes, cada ~60 dies. La darrera fa 10 dies (silenci normal).
    # Últimes 2 comandes: volum ~ 1/3 de l'històric → cal detectar caiguda de volum
    orders_1 = [
        (0,   3000),
        (60,  3200),
        (120, 3100),
        (240, 1000),  # ← baix
        (360, 900),   # ← baix (ara fa 10 dies, silence=10, freq≈90)
    ]
    df1 = make_fake_sales(1, "Biomateriales", orders_1)

    patterns1 = calc_individual_pattern(df1)
    sow1 = calc_sow_and_gap(df1, TODAY)
    classified1 = classify_all(patterns1, sow1, TODAY)
    alerts1 = generate_alerts(classified1, TODAY, {1: "Barcelona"})

    vol_ratio1 = patterns1["vol_ratio"].values[0] if len(patterns1) > 0 else None
    print("── Cas 1: Caiguda de volum (ratio ~0.3, silenci dins del normal) ──")
    print(f"  vol_ratio: {vol_ratio1}")
    print(f"  segment: {classified1['segment'].values[0] if len(classified1) > 0 else 'N/A'}")
    ok1 = len(alerts1) > 0 and alerts1["tipus_alerta"].values[0] == "caiguda_volum"
    if ok1:
        print(f"  ✅ caiguda_volum generada: {alerts1['motiu'].values[0][:120]}")
    else:
        tipus = alerts1["tipus_alerta"].values[0] if len(alerts1) > 0 else "cap"
        print(f"  ❌ Alerta incorrecta: {tipus}")

    # ── Cas 2: Client sense caiguda ──────────────────
    orders_2 = [
        (0,   3000),
        (60,  3200),
        (120, 3100),
        (240, 2900),
        (360, 3050),
    ]
    df2 = make_fake_sales(2, "Biomateriales", orders_2)

    patterns2 = calc_individual_pattern(df2)
    sow2 = calc_sow_and_gap(df2, TODAY)
    classified2 = classify_all(patterns2, sow2, TODAY)
    alerts2 = generate_alerts(classified2, TODAY, {2: "Madrid"})

    vol_ratio2 = patterns2["vol_ratio"].values[0] if len(patterns2) > 0 else None
    print("\n── Cas 2: Sense caiguda (ratio ~1.0) ──")
    print(f"  vol_ratio: {vol_ratio2}")
    ok2 = len(alerts2) == 0
    if ok2:
        print("  ✅ Sense alerta (correcte: volum estable i silenci dins del normal)")
    else:
        print(f"  ❌ Alerta inesperada: {alerts2['tipus_alerta'].values[0]}")

    # ── Cas 3: Poques dades ──────────────────────────────
    orders_3 = [(0, 3000), (200, 2500)]
    df3 = make_fake_sales(3, "Biomateriales", orders_3)
    patterns3 = calc_individual_pattern(df3)
    sow3 = calc_sow_and_gap(df3, TODAY)
    classified3 = classify_all(patterns3, sow3, TODAY)
    alerts3 = generate_alerts(classified3, TODAY, {3: "València"})

    vol_ratio3 = patterns3["vol_ratio"].values[0] if len(patterns3) > 0 else None
    n_int3 = patterns3["num_intervals"].values[0] if len(patterns3) > 0 else 0
    print(f"\n── Cas 3: Poques dades (2 ordres, intervals=1) ──")
    print(f"  vol_ratio: {vol_ratio3}, intervals: {n_int3}")
    ok3 = len(alerts3) == 0
    if ok3:
        print("  ✅ Sense alerta (correcte: num_intervals < 3, no es pot detectar tendència)")
    else:
        print(f"  ❌ Alerta inesperada: {alerts3['tipus_alerta'].values[0] if len(alerts3) > 0 else 'N/A'}")

    # ── Resum ─────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    all_ok = ok1 and ok2 and ok3
    print(f"{'✅ TOTS ELS TESTS PASSEN' if all_ok else '❌ ALGUN TEST HA FALLAT'}")
    return all_ok

if __name__ == "__main__":
    test_volume_drop()
