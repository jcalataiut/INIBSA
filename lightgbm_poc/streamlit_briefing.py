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
        import matplotlib.pyplot as plt

        n_compras = len(tdf)
        idx_pred = n_compras  # per defecte: última compra (predicció futura)

        # ── Slider ──
        st.markdown("### ⏱ Simulador: en quina compra estàs?")
        idx_pred = st.slider(
            "Arrossega per canviar de compra",
            min_value=1, max_value=n_compras,
            value=n_compras,  # última per defecte
            format="Compra #%d",
            help="Cada compra mostra la predicció de l'interval fins la següent.",
        )

        r = tdf.iloc[idx_pred - 1]
        d = r['purchase_date']
        p25, p50, p75 = r['p25'], r['p50'], r['p75']
        actual = r['actual']
        in_win = r['in_window']
        is_last = r['es_ultima']

        # ── Single prediction view ──
        st.subheader(f"Compra #{idx_pred}")
        c1, c2, c3 = st.columns([2, 2, 3])
        c1.metric("Data compra", d.strftime('%d/%m/%Y'))
        c2.metric("És l'última?", "✅ Sí" if is_last else "❌ No")

        # Gantt-like visualization for this single purchase
        fig, ax = plt.subplots(figsize=(12, 2.5))
        fig.patch.set_facecolor('#FAFBFC')

        max_x = max(p75 + 30, (actual + 20) if pd.notna(actual) else 150)
        ax.axhline(0.5, 0, max_x, color='#D1D5DB', linewidth=5, zorder=1)

        # Predicted interval
        ax.axvspan(p25, p75, ymin=0.15, ymax=0.85, alpha=0.35, color='#10B981', zorder=2,
                   label=f'Predicció: +{p25:.0f} a +{p75:.0f} dies')

        # Last purchase marker
        ax.plot(0, 0.5, 's', color='#6B7280', markersize=20, zorder=6)
        ax.annotate(f'Compra #{idx_pred}\ndia 0', (0, 0.5), fontsize=10,
                    color='#6B7280', ha='right', va='center', fontweight='bold')

        # p50 marker
        ax.plot(p50, 0.5, 'D', color='#F59E0B', markersize=18, zorder=5)
        ax.annotate(f'Mediana\n+{p50:.0f}d', (p50, 0.6), fontsize=9,
                    color='#F59E0B', ha='center', fontweight='bold')

        # p25/p75 markers
        for t, c, lbl in [(p25, '#10B981', f'p25 +{p25:.0f}d'),
                          (p75, '#F97316', f'p75 +{p75:.0f}d')]:
            ax.plot(t, 0.5, 'o', color=c, markersize=12, zorder=4)
            ax.annotate(lbl, (t, 0.25), fontsize=8, color=c, ha='center', fontweight='bold')

        # Actual next purchase
        if pd.notna(actual):
            actual_color = '#1E3A8A' if in_win else '#DC2626'
            actual_marker = 'o' if in_win else 'X'
            ax.plot(actual, 0.5, actual_marker, color=actual_color, markersize=24, zorder=7)
            status = "✅ CORRECTE" if in_win else "❌ FORA"
            ax.annotate(f'{status}\nReal: +{actual:.0f}d',
                        (actual, 0.35), fontsize=10, color=actual_color,
                        ha='center', va='top', fontweight='bold')
        else:
            ax.plot(0, 0.5, 'D', color='#F59E0B', markersize=20, zorder=6)
            ax.annotate('🔮 PREDICCIÓ\n(sense real encara)', (0, 0.25),
                        fontsize=10, color='#F59E0B', ha='left', fontweight='bold')

        ax.set_xlim(-5, max_x + 10)
        ax.set_ylim(0, 1)
        ax.set_xlabel('Dies des de la compra', fontsize=12, fontweight='bold')
        ax.tick_params(left=False, labelleft=False)
        ax.grid(True, axis='x', alpha=0.2, linestyle=':')
        ax.legend(fontsize=9, loc='upper right')
        ax.set_title(f'Client {selected_id} · {sel_fam} · #{idx_pred}: interval fins la propera compra',
                     fontsize=13, fontweight='bold')
        plt.tight_layout()
        st.pyplot(fig, width='stretch')

        # Stats below
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        if pd.notna(actual):
            col_s1.metric("Interval real", f"+{actual:.0f}d")
            col_s2.metric("Mediana predita", f"+{p50:.0f}d (error {abs(actual-p50):.0f}d)")
            col_s3.metric("Finestra predita", f"[+{p25:.0f}, +{p75:.0f}]")
            col_s4.metric("✅ Dins finestra?", "✅ Sí" if in_win else "❌ No")
        else:
            col_s1.metric("Predicció mediana", f"+{p50:.0f}d")
            col_s2.metric("Finestra", f"[+{p25:.0f}, +{p75:.0f}] dies")
            col_s3.metric("Data estimada", (d + timedelta(days=int(p50))).strftime('%d/%m/%Y'))
            col_s4.metric("Fins", (d + timedelta(days=int(p75))).strftime('%d/%m/%Y'))

        # ── Full timeline (collapsible) ──
        with st.expander("📊 Veure timeline completa de totes les compres", expanded=False):
            import matplotlib.dates as mdates
            fig2, ax2 = plt.subplots(figsize=(14, max(3, n_compras * 0.5)))
            fig2.patch.set_facecolor('#FAFBFC')

            for i2, (_, r2) in enumerate(tdf.iterrows()):
                y2 = i2
                d2 = r2['purchase_date']
                p25_2, p50_2, p75_2 = r2['p25'], r2['p50'], r2['p75']
                actual2 = r2['actual']
                in_win2 = r2['in_window']

                if in_win2 is True:    bar_c = '#10B981'
                elif in_win2 is False: bar_c = '#EF4444'
                else:                  bar_c = '#10B981'

                end2 = d2 + timedelta(days=int(p75_2))
                ax2.plot([d2 + timedelta(days=int(p25_2)), end2], [y2, y2],
                         color=bar_c, linewidth=5, alpha=0.5, zorder=2)
                ax2.plot(d2 + timedelta(days=int(p50_2)), y2, 'D', color='#F59E0B', markersize=8, zorder=4)

                if pd.notna(actual2):
                    act_d = d2 + timedelta(days=int(actual2))
                    c2 = '#1E3A8A' if in_win2 else '#DC2626'
                    ax2.plot(act_d, y2, 'o', color=c2, markersize=10, zorder=5)

                ax2.plot(d2, y2, 'o', color='#6B7280', markersize=6, zorder=3)
                if i2 == idx_pred - 1:
                    ax2.axhline(y2, color='#F59E0B', linewidth=1.5, linestyle=':', alpha=0.8)

            ax2.set_yticks(range(n_compras))
            ax2.set_yticklabels([f"#{r2['n']} {r2['purchase_date'].strftime('%d/%m/%y')}"
                                 for _, r2 in tdf.iterrows()], fontsize=7)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))
            ax2.grid(True, axis='x', alpha=0.2, linestyle=':')
            ax2.set_title('Timeline completa', fontsize=12, fontweight='bold')
            plt.setp(ax2.get_xticklabels(), rotation=30, ha='right', fontsize=7)
            plt.tight_layout()
            st.pyplot(fig2, width='stretch')

        # ── Global stats ──
        completed = tdf[tdf['actual'].notna()]
        n_ok = completed['in_window'].sum()
        n_total = len(completed)
        coverage = n_ok / n_total if n_total > 0 else 0
        mae = completed['actual'].sub(completed['p50']).abs().median()

        st.markdown("---")
        col_g1, col_g2, col_g3 = st.columns(3)
        col_g1.metric("Compres històriques", n_total)
        col_g2.metric("✅ Dins finestra", f"{n_ok}/{n_total} ({coverage:.0%})")
        col_g3.metric("Error mitjà (MedAE)", f"{mae:.0f} dies")
    else:
        st.warning("No es poden predir intervals (calen ≥ 2 compres)")

st.markdown("---")
st.caption(f"LightGBM quantile regression · {MODEL_DIR}/p25/p50/p75.txt · Walk-forward CV")
