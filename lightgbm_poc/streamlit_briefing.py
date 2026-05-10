"""
Streamlit: Timeline de totes les compres d'un client.
Per cada compra: interval predit (p25-p75) vs interval real fins la següent.
L'última compra: mostra predicció cap al futur.
"""
import streamlit as st
import pandas as pd
import numpy as np
import lightgbm as lgb
import os, sys
from datetime import timedelta
from train_interval_model import compute_features_at_purchase

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

st.set_page_config(page_title="Timeline de compres", layout="wide")

MODEL_DIR = os.path.join(SCRIPT_DIR, 'models', 'interval')
DATA_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'master_commodities.csv')
CAT_FEATS = ['Familia_Potencial', 'Provincia', 'mes', 'trimestre', 'dia_setmana']

st.title("📅 Timeline de compres")
st.caption("Per cada compra: interval predit (LightGBM quantile) vs interval real")

@st.cache_resource
def get_models():
    return {k: lgb.Booster(model_file=os.path.join(MODEL_DIR, f'{k}.txt'))
            for k in ['p25', 'p50', 'p75']}

@st.cache_data
def load_all_clients():
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
def predict_all_purchases(client_id, familia):
    """Predict interval after EACH purchase for a (client, family)."""
    models = get_models()
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    grp = df[(df['Id_Cliente'] == client_id) & (df['Familia_Potencial'] == familia)]
    grp = grp.sort_values('Fecha')
    dates = grp['Fecha'].unique()
    if len(dates) < 2:
        return None
    potencial = float(grp['Potencial_EUR_anual'].iloc[0])

    rows = []
    for i, purchase_date in enumerate(dates):
        feats = compute_features_at_purchase(grp, purchase_date, familia, potencial)
        if feats is None:
            continue

        X = pd.DataFrame([feats])
        for c in CAT_FEATS:
            if c in X.columns:
                X[c] = X[c].astype('category')

        p25 = max(1, models['p25'].predict(X)[0])
        p50 = max(1, models['p50'].predict(X)[0])
        p75 = max(1, models['p75'].predict(X)[0])

        # Actual interval to next purchase
        if i < len(dates) - 1:
            actual = (dates[i + 1] - purchase_date).days
            in_window = p25 <= actual <= p75
        else:
            actual = None
            in_window = None  # no ground truth

        rows.append({
            'n': i + 1,
            'purchase_date': purchase_date,
            'p25': p25,
            'p50': p50,
            'p75': p75,
            'actual': actual,
            'in_window': in_window,
            'es_ultima': i == len(dates) - 1,
        })
    return pd.DataFrame(rows)

# ── Sidebar ──
st.sidebar.header("Client")
clients_df = load_all_clients()
client_labels = [str(c) for c in clients_df['Id_Cliente'].tolist()]
sel_client = st.sidebar.selectbox("ID Client", client_labels, index=0)
selected_id = int(sel_client)

cinfo = clients_df[clients_df['Id_Cliente'] == selected_id].iloc[0]
families = cinfo['families']
sel_fam = st.sidebar.radio("Família", families, horizontal=True)

# ── Main ──
st.subheader(f"Client **{selected_id}** · {sel_fam}")
c1, c2, c3 = st.columns(3)
c1.metric("Total compres", cinfo['n_compres'])
c2.metric("Última compra", cinfo['ultima_compra'].strftime('%d/%m/%Y'))
c3.metric("Família", sel_fam)

if sel_fam:
    with st.spinner("Predint intervals per totes les compres..."):
        tdf = predict_all_purchases(selected_id, sel_fam)

    if tdf is not None and len(tdf) > 0:
        # ── Timeline plot ──
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        fig, ax = plt.subplots(figsize=(14, max(3, len(tdf) * 0.6)))
        fig.patch.set_facecolor('#FAFBFC')

        for i, (_, r) in enumerate(tdf.iterrows()):
            y = i
            d = r['purchase_date']
            p25, p50, p75 = r['p25'], r['p50'], r['p75']
            actual = r['actual']
            in_win = r['in_window']
            is_last = r['es_ultima']

            # Predicted interval bar
            end_date = d + timedelta(days=int(p75))
            if in_win is True:
                bar_color = '#10B981'  # green - correct
            elif in_win is False:
                bar_color = '#EF4444'  # red - miss
            else:
                bar_color = '#10B981'  # green - last purchase (no ground truth)

            # Bar: p25 to p75
            ax.plot([d + timedelta(days=int(p25)), end_date], [y, y],
                    color=bar_color, linewidth=6, alpha=0.5, zorder=2)
            # p50 marker
            ax.plot(d + timedelta(days=int(p50)), y, 'D', color='#F59E0B',
                    markersize=10, zorder=4)

            # Actual next purchase (if exists)
            if pd.notna(actual):
                actual_date = d + timedelta(days=int(actual))
                color = '#1E3A8A' if in_win else '#DC2626'
                ax.plot(actual_date, y, 'o', color=color, markersize=12, zorder=5)
                status = "✅ OK" if in_win else "❌ Fora"
                label = f"{status} (real={actual:.0f}d, predit [{p25:.0f}-{p75:.0f}])"
                ax.annotate(label, (actual_date, y), fontsize=7, color=color,
                            ha='left', va='center', fontweight='bold')
            else:
                # Last purchase: prediction only
                ax.plot(d, y, 's', color='#F59E0B', markersize=14, zorder=5)
                ax.annotate(f"🟡 Predicció: +{p50:.0f}d [{p25:.0f}-{p75:.0f}]",
                            (d, y), fontsize=7, color='#F59E0B',
                            ha='right', va='center', fontweight='bold')

            # Purchase marker
            ax.plot(d, y, 'o', color='#6B7280', markersize=8, zorder=3)

        ax.set_xlabel('Data', fontsize=11)
        ax.set_ylabel('Compra #', fontsize=11)
        ax.set_yticks(range(len(tdf)))
        ax.set_yticklabels([f"#{r['n']} {r['purchase_date'].strftime('%d/%m/%y')}"
                           for _, r in tdf.iterrows()], fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax.get_xticklabels(), rotation=30, ha='right', fontsize=8)
        ax.grid(True, axis='x', alpha=0.2, linestyle=':')
        ax.set_title(f'Compres {selected_id} · {sel_fam} — Interval predit vs real',
                     fontsize=13, fontweight='bold')
        plt.tight_layout()
        st.pyplot(fig, width='stretch')

        # ── Stats ──
        completed = tdf[tdf['actual'].notna()]
        n_ok = completed['in_window'].sum()
        n_total = len(completed)
        coverage = n_ok / n_total if n_total > 0 else 0
        mae = completed['actual'].sub(completed['p50']).abs().median()

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Compres històriques", n_total)
        col_b.metric("✅ Dins finestra", f"{n_ok}/{n_total} ({coverage:.0%})")
        col_c.metric("Error mitjà (MedAE)", f"{mae:.0f} dies")
        col_d.metric("Última → Predicció", f"+{tdf.iloc[-1]['p50']:.0f}d [{tdf.iloc[-1]['p25']:.0f}-{tdf.iloc[-1]['p75']:.0f}]")

        # ── Table ──
        with st.expander("📊 Taula de totes les compres", expanded=False):
            display = tdf.copy()
            display['Data'] = display['purchase_date'].dt.strftime('%d/%m/%Y')
            display['Interval predit'] = display.apply(
                lambda r: f"[{r['p25']:.0f}-{r['p75']:.0f}] med={r['p50']:.0f}d", axis=1)
            display['Real (dies)'] = display['actual'].apply(
                lambda x: f"{x:.0f}d" if pd.notna(x) else "—")
            display['✅?'] = display['in_window'].apply(
                lambda x: '✅' if x is True else ('❌' if x is False else '🟡 (futur)'))
            st.dataframe(
                display[['Data', 'Interval predit', 'Real (dies)', '✅?']],
                width='stretch', hide_index=True,
            )
    else:
        st.warning("No es poden predir intervals (calen ≥ 2 compres)")

st.markdown("---")
st.caption(f"LightGBM quantile regression · {MODEL_DIR}/p25/p50/p75.txt · Walk-forward CV")
