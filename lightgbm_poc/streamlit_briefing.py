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
    grp = grp[grp['es_devolucion'] == 0]  # només compres reals, no devolucions
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

        amount = grp[grp['Fecha'] == purchase_date]['Valores_H'].sum()

        rows.append({
            'n': i + 1,
            'purchase_date': purchase_date,
            'amount': amount,
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
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        n_compras = len(tdf)

        # ── Slider ──
        st.markdown("### ⏱ Simulador: en quina compra estàs?")
        idx_pred = st.slider(
            "Arrossega per canviar de compra",
            min_value=1, max_value=n_compras, value=n_compras,
            format="Compra #%d",
            help="Selecciona des de quina compra vols predir la següent.",
        )

        # Historial + predicció: només una línia de temps
        subset = tdf.iloc[:idx_pred].copy()
        r_current = subset.iloc[-1]
        d_current = r_current['purchase_date']
        p25, p50, p75 = r_current['p25'], r_current['p50'], r_current['p75']
        actual = r_current['actual']
        in_win = r_current['in_window']
        is_last = r_current['es_ultima']

        # ── Timeline vertical lines ──
        fig, ax = plt.subplots(figsize=(14, 3))
        fig.patch.set_facecolor('#FAFBFC')

        min_date = subset['purchase_date'].min()
        max_date = d_current + timedelta(days=int(p75) + 40)
        if pd.notna(actual):
            max_date = max(max_date, d_current + timedelta(days=int(actual) + 20))

        # Bar heights = purchase amount (euros)
        amounts = []
        for i2, (_, r2) in enumerate(subset.iterrows()):
            d2 = r2['purchase_date']
            amt = r2['amount']
            amounts.append(amt)
            is_current = i2 == len(subset) - 1

            color = '#1E3A8A' if is_current else '#3B82F6'
            alpha_val = 1.0 if is_current else 0.5 + 0.3 * (i2 / max(1, len(subset) - 1))

            # Vertical bar = import comprat
            ax.vlines(d2, 0, amt, color=color, linewidth=4 if is_current else 2.5,
                      alpha=alpha_val, zorder=4)
            ax.plot(d2, amt, 'o', color=color, markersize=4 if is_current else 2,
                    alpha=alpha_val, zorder=4)

            # Label
            lbl = f"#{r2['n']}"
            ax.annotate(lbl, (d2, amt + amt * 0.05), fontsize=8,
                        color=color, ha='center', va='bottom',
                        fontweight='bold' if is_current else 'normal',
                        alpha=alpha_val)

            # Connection between consecutive buys
            if i2 > 0:
                prev_d = subset.iloc[i2 - 1]['purchase_date']
                ax.plot([prev_d, d2], [amt * 0.02, amt * 0.02], color='#9CA3AF',
                        linewidth=1, linestyle=':', alpha=0.3, zorder=1)

        y_max = max(amounts) * 1.3

        # ARA marker
        ax.annotate('← ARA', (d_current, amounts[-1] * 1.15), fontsize=11,
                    color='#1E3A8A', ha='center', fontweight='bold')

        # ── Prediction bar (only from current purchase, below baseline) ──
        p25_date = d_current + timedelta(days=int(p25))
        p75_date = d_current + timedelta(days=int(p75))
        p50_date = d_current + timedelta(days=int(p50))

        # Green window below baseline
        ax.axvspan(p25_date, p75_date, ymin=0, ymax=0.08, alpha=0.25,
                   color='#10B981', zorder=2)
        ax.plot([d_current, p75_date], [0, 0], color='#10B981', linewidth=10,
                alpha=0.4, zorder=2)
        ax.plot(p50_date, 0, 'D', color='#F59E0B', markersize=16, zorder=6)

        # Prediction annotations
        ax.annotate(f'Mediana +{p50:.0f}d', (p50_date, -y_max * 0.08), fontsize=10,
                    color='#F59E0B', ha='center', fontweight='bold')
        ax.annotate(f'[{p25:.0f} – {p75:.0f}] dies', (p75_date, -y_max * 0.14), fontsize=9,
                    color='#10B981', ha='center', fontweight='bold')

        # Actual next purchase
        if pd.notna(actual):
            act_d = d_current + timedelta(days=int(actual))
            color_act = '#1E3A8A' if in_win else '#DC2626'
            ax.plot(act_d, 0, 'o' if in_win else 'X', color=color_act, markersize=18, zorder=7)
            ax.annotate(f'Real +{actual:.0f}d {"✅" if in_win else "❌"}',
                        (act_d, -y_max * 0.06), fontsize=9, color=color_act,
                        ha='center', fontweight='bold')

        ax.set_xlim(min_date - timedelta(days=20), max_date)
        ax.set_ylim(-y_max * 0.3, y_max)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax.get_xticklabels(), rotation=30, ha='right', fontsize=9)
        ax.tick_params(left=False, labelleft=False, right=False, labelright=False)
        ax.set_xlabel('Temps real', fontsize=11, fontweight='bold')
        ax.grid(True, axis='x', alpha=0.15, linestyle=':')
        ax.set_title(f'Client {selected_id} · {sel_fam} — Compra #{idx_pred} → predicció de la següent',
                     fontsize=13, fontweight='bold', pad=10)

        # Divider line at 0
        ax.axhline(0, color='#6B7280', linewidth=1, alpha=0.2, zorder=1)

        # Vertical line at current purchase
        ax.vlines(d_current, -y_max * 0.05, amounts[-1], color='#1E3A8A', linewidth=1.5,
                  linestyle='--', alpha=0.3, zorder=1)

        plt.tight_layout()
        st.pyplot(fig, width='stretch')

        # ── Stats ──
        st.subheader(f"📐 Des de compra #{idx_pred}")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.metric("Data compra", d_current.strftime('%d/%m/%Y'))
        p50_est_date = d_current + timedelta(days=int(p50))
        col_s2.metric("Mediana", f"+{p50:.0f} dies → {p50_est_date.strftime('%d/%m/%Y')}")
        col_s3.metric("Finestra", f"[+{p25:.0f}, +{p75:.0f}] dies")
        col_s4.metric("És l'última?", "✅ Sí" if is_last else "❌ No (hi ha dades reals)")

        if pd.notna(actual):
            st.success(f"**Resultat**: la següent compra va ser **+{actual:.0f} dies** després. "
                       f"{'✅ Dins la finestra predita.' if in_win else '❌ Fora de la finestra.'} "
                       f"Error: {abs(actual-p50):.0f} dies.")

        # ── Global stats ──
        completed = tdf[tdf['actual'].notna()]
        n_ok = completed['in_window'].sum()
        n_total = len(completed)
        coverage = n_ok / n_total if n_total > 0 else 0
        mae = completed['actual'].sub(completed['p50']).abs().median()

        st.markdown("---")
        col_g1, col_g2, col_g3 = st.columns(3)
        col_g1.metric("Compres amb real", n_total)
        col_g2.metric("✅ Dins finestra", f"{n_ok}/{n_total} ({coverage:.0%})")
        col_g3.metric("Error mitjà (MedAE)", f"{mae:.0f} dies")
    else:
        st.warning("No es poden predir intervals (calen ≥ 2 compres)")

st.markdown("---")
st.caption(f"LightGBM quantile regression · {MODEL_DIR}/p25/p50/p75.txt · Walk-forward CV")
