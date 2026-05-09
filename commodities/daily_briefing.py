import streamlit as st
import pandas as pd
import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from commodities.commodities_engine import run

TREATED_PATH = 'commodities/treated_alerts.json'
TODAY = '2025-12-01'
PAGE_SIZE = 50

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
LABEL_TIPUS = {
    'finestra_captura': '🎯 Captura', 'risc_fuga': '🚨 Risc Fuga',
    'reposicio_endarrerida': '⏰ Endarrerit', 'reposicio_preventiva': '📦 Preventiva',
    'reposicio_pendent': '🔄 Pendent', 'oportunitat_captura': '💡 Captura',
    'monitoritzar': '👁️ Monitor', 'info': 'ℹ️ Info', 'fugat': '🚨 Fugat', 'perdut': '❌ Perdut',
}


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

def clean_treated(treated, alerts):
    active_keys = set(key_treated(row) for _, row in alerts.iterrows())
    to_remove = [k for k in treated if k not in active_keys]
    for k in to_remove:
        del treated[k]
    if to_remove:
        save_treated(treated)
    return treated


@st.cache_data(show_spinner='🔄 Calculant alertes...')
def get_alerts(today):
    alerts, segments = run(today=today, verbose=False)
    return alerts, segments


st.sidebar.markdown('# 📋 Daily Briefing')
st.sidebar.markdown('---')

selected_date = st.sidebar.date_input(
    'Data del briefing',
    value=datetime.strptime(TODAY, '%Y-%m-%d'),
    min_value=datetime(2021, 1, 4),
    max_value=datetime(2025, 12, 29),
)
today_str = selected_date.strftime('%Y-%m-%d')

try:
    alerts, segments = get_alerts(today_str)
except Exception as e:
    st.error(f'❌ Error al carregar alertes: {e}')
    st.stop()

treated = load_treated()
treated = clean_treated(treated, alerts)
save_treated(treated)

total_alerts = len(alerts)
total_pendents = sum(1 for _, a in alerts.iterrows() if not is_treated(a, treated))

st.sidebar.markdown('---')
st.sidebar.markdown(f'**📊 Resum General**')
st.sidebar.markdown(f'Alertes: **{total_alerts:,}**')
st.sidebar.markdown(f'Pendents: **{total_pendents:,}**')
st.sidebar.markdown(f'Tractades: **{total_alerts - total_pendents:,}**')
n_auto = len(treated) - (total_alerts - total_pendents)
if n_auto > 0:
    st.sidebar.markdown(f'*({n_auto} tractades en dies anteriors que ja no calen)*')
st.sidebar.markdown('---')
st.sidebar.caption(f'Data: {today_str}')


tab1, tab2 = st.tabs(['📋 Briefing del Dia', '🚨 Fugats ( > 1 any )'])

fugats = alerts[alerts['segment'] == 'fugat'].copy() if len(alerts) > 0 else pd.DataFrame()
no_fugats = alerts[alerts['segment'] != 'fugat'].copy() if len(alerts) > 0 else pd.DataFrame()

fugats['_treated'] = fugats.apply(lambda r: is_treated(r, treated), axis=1)
no_fugats['_treated'] = no_fugats.apply(lambda r: is_treated(r, treated), axis=1)


with tab1:
    col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns([1.2, 1, 1, 1, 1])
    with col_f1:
        ftipus = st.multiselect('Tipus', options=sorted(no_fugats['tipus_alerta'].unique()) if len(no_fugats) > 0 else [], default=[], key='ftipus')
    with col_f2:
        fseg = st.multiselect('Segment', options=['fidel', 'promiscu', 'marginal', 'en_risc', 'nou', 'perdut'], default=[], key='fseg')
    with col_f3:
        furg = st.multiselect('Urgència', options=['alta', 'mitjana', 'baixa'], default=[], key='furg')
    with col_f4:
        search_id = st.text_input('🔍 Cerca ID Client', placeholder='Ex: 30870', key='search_id')
    with col_f5:
        show_tr = st.checkbox('Mostrar tractades', value=False, key='show_tr')

    mask = pd.Series(True, index=no_fugats.index) if len(no_fugats) > 0 else pd.Series(dtype=bool)
    if ftipus and len(no_fugats) > 0: mask &= no_fugats['tipus_alerta'].isin(ftipus)
    if fseg and len(no_fugats) > 0: mask &= no_fugats['segment'].isin(fseg)
    if furg and len(no_fugats) > 0: mask &= no_fugats['urgencia'].isin(furg)
    if not show_tr and len(no_fugats) > 0: mask &= ~no_fugats['_treated']
    if search_id and len(no_fugats) > 0:
        try:
            id_num = int(search_id)
            mask &= no_fugats['Id_Cliente'] == id_num
        except ValueError:
            pass

    view = no_fugats[mask].copy() if len(no_fugats) > 0 else pd.DataFrame()

    st.markdown(f'## 📋 {selected_date.strftime("%A, %d de %B de %Y").capitalize()}')
    c1, c2, c3, c4 = st.columns(4)
    total_visible = len(view)
    total_pendents_view = int((~view['_treated']).sum()) if total_visible > 0 else 0
    total_gap = view.loc[~view['_treated'], 'gap_eur'].sum() if total_visible > 0 else 0
    total_alta = int((view['urgencia'] == 'alta').sum()) if total_visible > 0 else 0
    with c1: st.metric('Alertes', f"{total_visible:,}", help=f'{total_alerts:,} alertes totals · {total_visible:,} després de filtres')
    with c2: st.metric('Pendents', f"{total_pendents_view:,}", help=f'{total_pendents:,} pendents totals')
    with c3: st.metric('Gap Total', f"{total_gap:,.0f}€")
    with c4: st.metric('Alta Urgència', f"{total_alta}")
    st.divider()

    if total_visible == 0:
        if search_id:
            st.warning(f'🔍 Cap alerta per al client #{search_id}')
        elif not show_tr:
            st.success('✅ Totes les alertes tractades. Bona feina!')
        else:
            st.info('📭 Cap alerta amb els filtres seleccionats')
    else:
        view_sorted = view.sort_values('prioritat', ascending=False).reset_index(drop=True)

        total_pages = max(1, (len(view_sorted) + PAGE_SIZE - 1) // PAGE_SIZE)
        if 'page' not in st.session_state:
            st.session_state.page = 0
        if st.session_state.page >= total_pages:
            st.session_state.page = 0

        page = st.session_state.page
        start = page * PAGE_SIZE
        end = min(start + PAGE_SIZE, len(view_sorted))
        page_view = view_sorted.iloc[start:end]

        col_pag, col_info = st.columns([1, 3])
        with col_pag:
            pag_cols = st.columns([0.5, 1, 0.5, 1, 0.5])
            with pag_cols[0]:
                if st.button('◀', disabled=page == 0, use_container_width=True, key='pag_prev'):
                    st.session_state.page -= 1
                    st.rerun()
            with pag_cols[1]:
                st.markdown(f'<div style="text-align:center;padding-top:6px;">Pàg {page+1}/{total_pages}</div>', unsafe_allow_html=True)
            with pag_cols[2]:
                if st.button('▶', disabled=page >= total_pages - 1, use_container_width=True, key='pag_next'):
                    st.session_state.page += 1
                    st.rerun()
            with pag_cols[3]:
                st.markdown(f'<div style="text-align:center;padding-top:6px;">{start+1}-{end} de {len(view_sorted)}</div>', unsafe_allow_html=True)
            with pag_cols[4]:
                if st.button('↻', use_container_width=True, key='refresh'):
                    st.cache_data.clear()
                    st.rerun()
        with col_info:
            st.markdown(f'<div style="text-align:right;color:#666;padding-top:6px;font-size:13px;">Prioritat: crítica ≥ 500 · important ≥ 100 · info &lt; 100</div>', unsafe_allow_html=True)

        for _, a in page_view.iterrows():
            tr = a['_treated']
            prio = a['prioritat']

            if prio >= 500:
                badge = '🔴 CRÍTICA'
                badge_color = '#e74c3c'
            elif prio >= 100:
                badge = '🟡 IMPORTANT'
                badge_color = '#f39c12'
            else:
                badge = '🟢 INFO'
                badge_color = '#27ae60'

            canal = '👤 Delegat' if a['canal'] == 'delegat' else '📞 Televenda'

            if a['tipus_alerta'] == 'finestra_captura':
                bg = '#f0fdf4'
                border = '#2ecc71'
            elif a['tipus_alerta'] == 'risc_fuga':
                bg = '#fef2f2'
                border = '#e74c3c'
            elif tr:
                bg = '#f9f9f9'
                border = '#bbb'
            else:
                bg = 'white'
                border = '#e0e0e0'

            with st.container():
                st.markdown(f'<div style="background:{bg};padding:12px 16px;border-radius:10px;border-left:5px solid {border};margin-bottom:8px;{"opacity:0.6;" if tr else ""}">', unsafe_allow_html=True)

                hcols = st.columns([2, 1.5, 1.2, 1.2, 1.2, 1.5, 0.6])
                with hcols[0]:
                    st.markdown(f'**#{a["Id_Cliente"]}** · {a.get("Provincia","?")}<br><span style="font-size:11px;color:#666;">{a["Familia_Potencial"]}</span>', unsafe_allow_html=True)
                with hcols[1]:
                    cseg = COLOR_SEG.get(a['segment'], '#999')
                    share_pct = f'{a["share_12m"]:.0%}' if pd.notna(a.get('share_12m')) else '?'
                    cicle_str = f'{a["cicle_mig_dies"]:.0f}d' if pd.notna(a.get('cicle_mig_dies')) else '?'
                    st.markdown(f'<span style="background:{cseg};color:white;padding:2px 10px;border-radius:10px;font-size:11px;font-weight:600;">{a["segment"]}</span><br><span style="font-size:11px;">share {share_pct} · cicle {cicle_str}</span>', unsafe_allow_html=True)
                with hcols[2]:
                    st.markdown(f'**{a["gap_eur"]:,.0f}€**<br><span style="font-size:11px;color:#666;">gap</span>', unsafe_allow_html=True)
                with hcols[3]:
                    dies_str = f'{a["dies_sense_compra"]}d' if pd.notna(a.get('dies_sense_compra')) else '?'
                    retard_str = f'{a["dies_retard"]}d retard' if pd.notna(a.get('dies_retard')) and a.get('dies_retard', 0) > 0 else 'al dia'
                    st.markdown(f'**{dies_str}**<br><span style="font-size:11px;color:#666;">{retard_str}</span>', unsafe_allow_html=True)
                with hcols[4]:
                    label = LABEL_TIPUS.get(a['tipus_alerta'], a['tipus_alerta'])
                    st.markdown(f'**{label}**<br><span style="font-size:11px;color:#666;">{a["urgencia"].upper()}</span>', unsafe_allow_html=True)
                with hcols[5]:
                    st.markdown(f'<span style="font-size:13px;font-weight:700;color:{badge_color};">{badge}</span><br><span style="font-size:11px;">prio {a["prioritat"]:,.0f}</span>', unsafe_allow_html=True)
                with hcols[6]:
                    if tr:
                        if st.button(f'↩️', key=f'u_{a.name}', use_container_width=True):
                            k = key_treated(a); del treated[k]; save_treated(treated)
                            st.rerun()
                    else:
                        if st.button(f'✅', key=f't_{a.name}', use_container_width=True):
                            k = key_treated(a); treated[k] = today_str; save_treated(treated)
                            st.rerun()

                with st.expander('📝 Motiu', expanded=False):
                    st.markdown(f'<div style="font-size:13px;color:#333;line-height:1.5;">{a["motiu"]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="font-size:11px;color:#999;margin-top:4px;">{canal} · {a["urgencia"].upper()}</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

            if tr:
                st.markdown('<div style="margin-top:-6px;margin-bottom:4px;padding-left:16px;"><span style="font-size:11px;color:#999;">✅ Tractada</span></div>', unsafe_allow_html=True)


with tab2:
    st.markdown('## 🚨 Clients Fugats')
    st.markdown('Porten **més d\'un any** sense comprar. Requereixen recuperació directa per delegat.')

    if len(fugats) == 0:
        st.success('✅ Cap client fugat. Bona feina!')
    else:
        f2_show_tr = st.checkbox('Mostrar tractades', value=False, key='f2_show_tr')
        f2_view = fugats[~fugats['_treated']] if not f2_show_tr else fugats

        st.markdown(f'**{len(f2_view)} fugats** pendents de recuperació')

        f2_view_sorted = f2_view.sort_values('prioritat', ascending=False).reset_index(drop=True)

        f2_total_pages = max(1, (len(f2_view_sorted) + PAGE_SIZE - 1) // PAGE_SIZE)
        if 'f2_page' not in st.session_state:
            st.session_state.f2_page = 0
        if st.session_state.f2_page >= f2_total_pages:
            st.session_state.f2_page = 0

        f2_page = st.session_state.f2_page
        f2_start = f2_page * PAGE_SIZE
        f2_end = min(f2_start + PAGE_SIZE, len(f2_view_sorted))
        f2_page_view = f2_view_sorted.iloc[f2_start:f2_end]

        col_pag2, _ = st.columns([2, 4])
        with col_pag2:
            pag2 = st.columns([0.5, 1, 0.5])
            with pag2[0]:
                if st.button('◀', disabled=f2_page == 0, use_container_width=True, key='f2_prev'):
                    st.session_state.f2_page -= 1
                    st.rerun()
            with pag2[1]:
                st.markdown(f'<div style="text-align:center;padding-top:6px;">Pàg {f2_page+1}/{f2_total_pages} ({len(f2_view_sorted)} fugats)</div>', unsafe_allow_html=True)
            with pag2[2]:
                if st.button('▶', disabled=f2_page >= f2_total_pages - 1, use_container_width=True, key='f2_next'):
                    st.session_state.f2_page += 1
                    st.rerun()

        st.divider()

        for _, a in f2_page_view.iterrows():
            tr = a['_treated']
            canal = '👤 Delegat'
            with st.container():
                st.markdown(f'<div style="background:#fef2f2;padding:12px 16px;border-radius:10px;border-left:5px solid #e74c3c;margin-bottom:8px;{"opacity:0.6;" if tr else ""}">', unsafe_allow_html=True)
                cols = st.columns([1.5, 1, 1, 1, 1, 1, 0.6])
                with cols[0]:
                    st.markdown(f'**🚨 #{a["Id_Cliente"]}**<br><span style="font-size:11px;color:#666;">{a.get("Provincia","?")}</span>', unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f'{a["Familia_Potencial"]}<br><span style="font-size:11px;">{a["dies_sense_compra"]} dies sense comprar</span>', unsafe_allow_html=True)
                with cols[2]:
                    st.markdown(f'**{a["gap_eur"]:,.0f}€**<br><span style="font-size:11px;color:#666;">gap anual</span>', unsafe_allow_html=True)
                with cols[3]:
                    st.markdown(f'**{a["prioritat"]:,.0f}**<br><span style="font-size:11px;color:#666;">prioritat</span>', unsafe_allow_html=True)
                with cols[4]:
                    cicle = f'{a["cicle_mig_dies"]:.0f}d' if pd.notna(a.get('cicle_mig_dies')) else '?'
                    st.markdown(f'**{cicle}**<br><span style="font-size:11px;color:#666;">cicle històric</span>', unsafe_allow_html=True)
                with cols[5]:
                    st.markdown(f'{canal}<br><span style="font-size:11px;color:#666;">RECUPERACIÓ</span>', unsafe_allow_html=True)
                with cols[6]:
                    if tr:
                        if st.button(f'↩️', key=f'fu_{a.name}', use_container_width=True):
                            k = key_treated(a); del treated[k]; save_treated(treated)
                            st.rerun()
                    else:
                        if st.button(f'✅', key=f'ft_{a.name}', use_container_width=True):
                            k = key_treated(a); treated[k] = today_str; save_treated(treated)
                            st.rerun()
                st.markdown(f'<div style="font-size:12px;color:#333;margin-top:6px;">{a["motiu"]}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
