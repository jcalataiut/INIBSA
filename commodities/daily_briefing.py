"""
📋 Daily Briefing — Smart Demand Signals
==========================================
UX/UI interactiva que simula el dia a dia de l'equip comercial.
Mostra les alertes prioritzades per avui i permet marcar com a "tractades".
Pestanya separada per a clients FUGATs (> 1 any sense comprar).

Ús: streamlit run commodities/daily_briefing.py
"""

import streamlit as st
import pandas as pd
import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from commodities.commodities_engine import run

TREATED_PATH = 'commodities/treated_alerts.json'
TODAY = '2025-12-01'

st.set_page_config(
    page_title='Daily Briefing — Commodities',
    page_icon='📋',
    layout='wide',
    initial_sidebar_state='expanded',
)

COLOR_SEG = {
    'fidel': '#2ecc71', 'promiscu': '#f1c40f', 'marginal': '#95a5a6',
    'en_risc': '#e67e22', 'nou': '#3498db', 'perdut': '#95a5a6', 'fugat': '#e74c3c',
}


# ── Estat de tractament ────────────────────────────────────────────────────
def load_treated():
    if os.path.exists(TREATED_PATH):
        with open(TREATED_PATH) as f:
            return json.load(f)
    return {}

def save_treated(treated):
    with open(TREATED_PATH, 'w') as f:
        json.dump(treated, f, indent=2)

def key_treated(row):
    return f"{row['Id_Cliente']}_{row['Familia_Potencial']}_{row['tipus_alerta']}"

def is_treated(row, treated):
    return key_treated(row) in treated


# ── Run engine ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner='🔄 Calculant alertes...')
def get_alerts(today):
    alerts, segments = run(today=today, verbose=False)
    return alerts, segments


# ── Sidebar ────────────────────────────────────────────────────────────────
st.sidebar.markdown('# 📋 Daily Briefing')
st.sidebar.markdown('---')

selected_date = st.sidebar.date_input(
    'Data del briefing',
    value=datetime.strptime(TODAY, '%Y-%m-%d'),
    min_value=datetime(2021, 1, 4),
    max_value=datetime(2025, 12, 29),
)
today_str = selected_date.strftime('%Y-%m-%d')

alerts, segments = get_alerts(today_str)
treated = load_treated()

st.sidebar.markdown('---')
st.sidebar.markdown(f'**Alertes:** {len(alerts)}')
st.sidebar.markdown(f'**Pendents:** {sum(1 for _, a in alerts.iterrows() if not is_treated(a, treated))}')
st.sidebar.markdown(f'**Tractades:** {sum(1 for _, a in alerts.iterrows() if is_treated(a, treated))}')

# ── Tabs: Briefing + Fugats ────────────────────────────────────────────────
tab1, tab2 = st.tabs(['📋 Briefing del Dia', '🚨 Fugats ( > 1 any )'])

fugats = alerts[alerts['segment'] == 'fugat'].copy()
no_fugats = alerts[alerts['segment'] != 'fugat'].copy()

fugats['_treated'] = fugats.apply(lambda r: is_treated(r, treated), axis=1)
no_fugats['_treated'] = no_fugats.apply(lambda r: is_treated(r, treated), axis=1)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1: BRIEFING PRINCIPAL (tot excepte fugats)
# ═══════════════════════════════════════════════════════════════════════════
with tab1:
    # Filtres
    col_f1, col_f2, col_f3, col_f4 = st.columns([1, 1, 1, 1])
    with col_f1:
        ftipus = st.multiselect('Tipus', options=sorted(no_fugats['tipus_alerta'].unique()), default=[], key='ftipus')
    with col_f2:
        fseg = st.multiselect('Segment', options=['fidel', 'promiscu', 'marginal', 'en_risc', 'nou', 'perdut'], default=[], key='fseg')
    with col_f3:
        furg = st.multiselect('Urgència', options=['alta', 'mitjana', 'baixa'], default=[], key='furg')
    with col_f4:
        show_tr = st.checkbox('Mostrar tractades', value=False, key='show_tr')

    mask = True
    if ftipus: mask &= no_fugats['tipus_alerta'].isin(ftipus)
    if fseg: mask &= no_fugats['segment'].isin(fseg)
    if furg: mask &= no_fugats['urgencia'].isin(furg)
    if not show_tr: mask &= ~no_fugats['_treated']

    view = no_fugats[mask].copy()

    # Stats
    st.markdown(f'## 📋 {selected_date.strftime("%A, %d de %B de %Y").capitalize()}')
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric('Alertes', f"{len(view):,}", help='Després de filtres')
    with c2: st.metric('Pendents', f"{int((~view['_treated']).sum()):,}")
    with c3: st.metric('Gap', f"{view.loc[~view['_treated'], 'gap_eur'].sum():,.0f}€")
    with c4: st.metric('Alta urgència', f"{int((view['urgencia'] == 'alta').sum())}")
    st.divider()

    if view.empty:
        st.success('✅ Totes les alertes tractades. Bona feina!')
    else:
        for _, a in view.iterrows():
            tr = a['_treated']
            prio = a['prioritat']
            lbl = '🔴 CRÍTICA' if prio >= 500 else ('🟡 IMPORTANT' if prio >= 100 else '🟢 INFO')
            canal = '👤 Delegat' if a['canal'] == 'delegat' else '📞 Televenda'
            bg = '#f0fdf4' if a['tipus_alerta'] == 'finestra_captura' else ('#fef2f2' if a['tipus_alerta'] == 'risc_fuga' else 'white')

            with st.container():
                st.markdown(f'<div style="background:{bg};padding:10px;border-radius:8px;margin-bottom:4px;">', unsafe_allow_html=True)
                cols = st.columns([1.5, 1, 1, 1, 1, 1.2, 0.8, 0.8])
                with cols[0]:
                    st.markdown(f'**#{a["Id_Cliente"]}**<br><span style="font-size:11px;color:#666;">{a.get("Provincia","?")}</span>', unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f'{a["Familia_Potencial"]}<br><span style="font-size:11px;">{a["tipus_alerta"]}</span>', unsafe_allow_html=True)
                with cols[2]:
                    cseg = COLOR_SEG.get(a['segment'], '#999')
                    st.markdown(f'<span style="background:{cseg};color:white;padding:2px 8px;border-radius:8px;font-size:11px;">{a["segment"]}</span><br><span style="font-size:11px;">share {a["share_12m"]:.0%}</span>', unsafe_allow_html=True)
                with cols[3]:
                    st.markdown(f'**{a["gap_eur"]:,.0f}€**<br><span style="font-size:11px;">gap</span>', unsafe_allow_html=True)
                with cols[4]:
                    st.markdown(f'**{a["dies_sense_compra"]}d**<br><span style="font-size:11px;">sense compra</span>', unsafe_allow_html=True)
                with cols[5]:
                    st.markdown(f'**{lbl}**<br><span style="font-size:11px;">prio {a["prioritat"]:,.0f}</span>', unsafe_allow_html=True)
                with cols[6]:
                    st.markdown(f'{canal}<br><span style="font-size:11px;">{a["urgencia"].upper()}</span>', unsafe_allow_html=True)
                with cols[7]:
                    if tr:
                        if st.button(f'↩️', key=f'u_{a.name}', use_container_width=True):
                            k = key_treated(a); del treated[k]; save_treated(treated)
                            st.rerun()
                    else:
                        if st.button(f'✅', key=f't_{a.name}', use_container_width=True):
                            k = key_treated(a); treated[k] = today_str; save_treated(treated)
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

                with st.expander('📝 Motiu'):
                    st.caption(a['motiu'])
                st.markdown('<div style="margin-bottom:8px;"></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2: FUGATS ( > 1 any sense comprar )
# ═══════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('## 🚨 Clients Fugats')
    st.markdown('Porten **més d\'un any** sense comprar. Requereixen recuperació directa per delegat.')

    if fugats.empty:
        st.success('✅ Cap client fugat. Bona feina!')
    else:
        f2_show_tr = st.checkbox('Mostrar tractades', value=False, key='f2_show_tr')
        f2_view = fugats[~fugats['_treated']] if not f2_show_tr else fugats

        st.markdown(f'**{len(f2_view)} fugats** pendents de recuperació')
        st.divider()

        for _, a in f2_view.iterrows():
            tr = a['_treated']
            canal = '👤 Delegat'
            with st.container():
                st.markdown(f'<div style="background:#fef2f2;padding:12px;border-radius:8px;border-left:4px solid #e74c3c;margin-bottom:6px;">', unsafe_allow_html=True)
                cols = st.columns([1.5, 1, 1, 1, 1, 1, 1])
                with cols[0]:
                    st.markdown(f'**🚨 #{a["Id_Cliente"]}**<br><span style="font-size:11px;color:#666;">{a.get("Provincia","?")}</span>', unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f'{a["Familia_Potencial"]}<br><span style="font-size:11px;">{a["dies_sense_compra"]} dies sense comprar</span>', unsafe_allow_html=True)
                with cols[2]:
                    st.markdown(f'**{a["gap_eur"]:,.0f}€**<br><span style="font-size:11px;">gap anual</span>', unsafe_allow_html=True)
                with cols[3]:
                    st.markdown(f'**{a["prioritat"]:,.0f}**<br><span style="font-size:11px;">prioritat</span>', unsafe_allow_html=True)
                with cols[4]:
                    cicle = f'{a["cicle_mig_dies"]:.0f}d' if pd.notna(a.get('cicle_mig_dies')) else '?'
                    st.markdown(f'**{cicle}**<br><span style="font-size:11px;">cicle històric</span>', unsafe_allow_html=True)
                with cols[5]:
                    st.markdown(f'{canal}<br><span style="font-size:11px;">RECUPERACIÓ</span>', unsafe_allow_html=True)
                with cols[6]:
                    if tr:
                        if st.button(f'↩️ Desfer', key=f'fu_{a.name}', use_container_width=True):
                            k = key_treated(a); del treated[k]; save_treated(treated)
                            st.rerun()
                    else:
                        if st.button(f'✅ Recuperat', key=f'ft_{a.name}', use_container_width=True):
                            k = key_treated(a); treated[k] = today_str; save_treated(treated)
                            st.rerun()
                st.markdown(f'<div style="font-size:12px;color:#333;margin-top:4px;">{a["motiu"]}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
