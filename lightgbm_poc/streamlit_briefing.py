"""
Streamlit: Interval entre compres — LightGBM Quantile Regression.

Selecciona client → mostra interval predit (p25-p75) per la propera compra.
"""
import streamlit as st
import pandas as pd
import numpy as np
import lightgbm as lgb
import os, sys
from datetime import timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

st.set_page_config(page_title="Interval entre compres", layout="wide")

MODEL_DIR   = os.path.join(SCRIPT_DIR, 'models', 'interval')
DATA_PATH   = os.path.join(SCRIPT_DIR, '..', 'data', 'master_commodities.csv')

CAT_FEATS   = ['Familia_Potencial', 'Provincia', 'mes', 'trimestre', 'dia_setmana']

st.title("📅 Interval entre compres")
st.caption("Predicció de la propera compra des de l'última, amb LightGBM quantile regression")

@st.cache_resource
def get_models():
    return {
        k: lgb.Booster(model_file=os.path.join(MODEL_DIR, f'{k}.txt'))
        for k in ['p25', 'p50', 'p75']
    }

@st.cache_data
def load_clients():
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    clients = df.groupby('Id_Cliente').agg(
        ultima_compra=('Fecha', 'max'),
        n_compres=('Fecha', 'nunique'),
        families=('Familia_Potencial', lambda x: list(x.unique())),
    ).reset_index()
    clients = clients[clients['n_compres'] >= 2]
    return clients.sort_values('ultima_compra', ascending=False)

@st.cache_data
def predict_interval(client_id, familia):
    from train_interval_model import compute_features_at_purchase
    models = get_models()
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    grp = df[(df['Id_Cliente'] == client_id) & (df['Familia_Potencial'] == familia)]
    grp = grp.sort_values('Fecha')
    if len(grp) < 2:
        return None

    last_date = grp['Fecha'].max()
    potencial = float(grp['Potencial_EUR_anual'].iloc[0])
    feats = compute_features_at_purchase(grp, last_date, familia, potencial)
    if feats is None:
        return None

    X = pd.DataFrame([feats])
    for c in CAT_FEATS:
        if c in X.columns:
            X[c] = X[c].astype('category')

    p25, p50, p75 = [models[k].predict(X)[0] for k in ['p25', 'p50', 'p75']]

    return {
        'last_date': last_date,
        'p25': max(1, p25),
        'p50': max(1, p50),
        'p75': max(1, p75),
        'n_compres': len(grp),
        'potencial': potencial,
    }

# ── Sidebar ──
st.sidebar.header("Client")
clients_df = load_clients()

client_ids = clients_df['Id_Cliente'].tolist()
client_labels = [str(c) for c in client_ids]

sel_client = st.sidebar.selectbox(
    "ID Client (més recents primer)",
    client_labels,
    index=0,
    help="Selecciona un client. Ordenats per última compra (més recent primer).",
)

selected_id = int(sel_client)

# ── Main ──
if selected_id:
    cinfo = clients_df[clients_df['Id_Cliente'] == selected_id].iloc[0]
    families = cinfo['families']

    st.subheader(f"Client **{selected_id}**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Última compra", cinfo['ultima_compra'].strftime('%d/%m/%Y'))
    c2.metric("Compres totals", cinfo['n_compres'])
    c3.metric("Familia", " / ".join(families))

    sel_fam = st.radio("Família", families, horizontal=True)

    if sel_fam:
        with st.spinner("Predint interval..."):
            pred = predict_interval(selected_id, sel_fam)

        if pred:
            p25, p50, p75 = pred['p25'], pred['p50'], pred['p75']
            last_date = pred['last_date']
            p25_date = last_date + timedelta(days=int(p25))
            p50_date = last_date + timedelta(days=int(p50))
            p75_date = last_date + timedelta(days=int(p75))

            st.markdown("---")
            st.subheader("📐 Interval predit per la propera compra")

            # ── Gantt-like plot ──
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(10, 2.5))
            fig.patch.set_facecolor('#FAFBFC')

            max_x = max(p75 + 40, 150)
            ax.axhline(0.5, 0, max_x, color='#D1D5DB', linewidth=4, zorder=1)

            # Window
            ax.axvspan(p25, p75, ymin=0.2, ymax=0.8, alpha=0.3, color='#10B981', zorder=2,
                       label=f'Pròxima compra esperada (+{p25:.0f} a +{p75:.0f} dies)')

            # Markers
            for t, c, lbl, marker, size in [
                (0, '#10B981', f'Última compra\ndia 0', 's', 18),
                (p50, '#F59E0B', f'Mediana +{p50:.0f}d', 'D', 16),
                (p25, '#10B981', f'p25 +{p25:.0f}d', 'o', 10),
                (p75, '#F97316', f'p75 +{p75:.0f}d', 'o', 10),
            ]:
                ax.plot(t, 0.5, marker, color=c, markersize=size, zorder=5)
                ax.annotate(lbl, (t, 0.35 if marker == 'o' else 0.55),
                            fontsize=8, color=c, ha='center', fontweight='bold')

            ax.set_xlim(-5, max_x)
            ax.set_ylim(0, 1)
            ax.set_xlabel('Dies des de l\'última compra', fontsize=11, fontweight='bold')
            ax.tick_params(left=False, labelleft=False)
            ax.grid(True, axis='x', alpha=0.2, linestyle=':')
            ax.legend(fontsize=9, loc='upper right')
            plt.tight_layout()
            st.pyplot(fig, width='stretch')

            # ── Info table ──
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("🟢 Última compra", last_date.strftime('%d/%m/%Y'))
            col_b.metric("📅 Inici (p25)", f"+{p25:.0f}d → {p25_date.strftime('%d/%m/%Y')}")
            col_c.metric("🎯 Mediana (p50)", f"+{p50:.0f}d → {p50_date.strftime('%d/%m/%Y')}")
            col_d.metric("🔚 Fi (p75)", f"+{p75:.0f}d → {p75_date.strftime('%d/%m/%Y')}")

            st.success(
                f"**Predicció**: la propera compra es produirà entre **+{p25:.0f} i +{p75:.0f} dies** "
                f"després de l'última (mediana **+{p50:.0f} dies**). "
                f"Basat en {pred['n_compres']} compres històriques."
            )

            with st.expander("📊 Validació del model"):
                st.markdown(f"""
                **LightGBM Quantile Regression** — 3 models (p25, p50, p75)

                - **Entrenament**: {pred['n_compres']} compres per client × 8470 parelles (client, família)
                - **Walk-forward CV**: 5 folds, sense leakage temporal
                - **Coverage** (real dins p25-p75): **46.6%** (esperat: 50%)
                - **Error mitjà** (MedAE): **31 dies**
                - Millor rendiment en intervals 30-180d: coverage 61-65%, error 16-27d

                **Top features**: n_pedidos_365d, n_pedidos_90d, dies_desde_ultima_compra,
                cicle_mig_dies, ratio_90d_vs_365d (rolling windows + cicle + tendència)
                """)
        else:
            st.warning("No es pot predir (calen ≥ 2 compres)")

else:
    st.info("Selecciona un client de la llista per veure la predicció d'interval.")

# ── Footer ──
st.markdown("---")
st.caption(
    f"Models: {MODEL_DIR}/p25.txt, p50.txt, p75.txt · "
    f"Dataset: {DATA_PATH} · "
    f"Entrenat amb walk-forward CV, LightGBM quantile regression"
)
