"""
Dashboard HTML v1 — Alertes Commodities
========================================
Genera un dashboard HTML autònom amb les alertes prioritzades,
filtrable per tipus, segment, urgència i província.

Ús: python commodities/dashboard_v1.py
Output: commodities/output/dashboard.html (obre'l al navegador)
"""

import pandas as pd
import os
from datetime import datetime

ALERTS_PATH = 'commodities/alertes_20251201.csv'
OUTPUT_PATH = 'commodities/output/dashboard.html'
TODAY = '2025-12-01'


def load_alerts():
    df = pd.read_csv(ALERTS_PATH)
    df['data_alerta'] = TODAY
    return df


def build_html(df):
    n = len(df)
    n_clients = df['Id_Cliente'].nunique()
    gap_total = df['gap_eur'].sum()

    # Alertes per tipus (per comptes ràpids)
    tipus_counts = df['tipus_alerta'].value_counts().to_dict()

    # Taula d'alertes
    rows_html = ''
    for i, (_, a) in enumerate(df.iterrows()):
        prio_class = 'prio-high' if a['prioritat'] >= 500 else ('prio-med' if a['prioritat'] >= 100 else 'prio-low')
        urg_class = f"urg-{a['urgencia']}"
        rows_html += f'''
        <tr class="{prio_class}">
            <td class="num">{i+1}</td>
            <td><strong>#{a['Id_Cliente']}</strong><br><span class="prov">{a.get('Provincia', '?')}</span></td>
            <td>{a['Familia_Potencial']}</td>
            <td><span class="badge badge-{a['tipus_alerta']}">{a['tipus_alerta']}</span></td>
            <td><span class="badge badge-seg {a['segment']}">{a['segment']}</span></td>
            <td class="num">{a['gap_eur']:,.0f}€</td>
            <td class="num">{a['share_12m']:.0%}</td>
            <td class="num">{a['dies_sense_compra']}d</td>
            <td><span class="urg {urg_class}">{a['urgencia']}</span></td>
            <td class="num">{a['prioritat']:,.0f}</td>
            <td><span class="badge badge-canal">{a['canal']}</span></td>
            <td class="motiu" title="{a['motiu']}">{a['motiu'][:80]}…</td>
        </tr>'''

    # Opcions de filtre dinàmic (JS)
    tipus_opts = ''.join(f'<option value="{t}">{t} ({c})</option>' for t, c in sorted(tipus_counts.items()))
    seg_opts = ''.join(f'<option value="{s}">{s}</option>' for s in ['fidel', 'promiscu', 'marginal', 'en_risc', 'nou', 'perdut'])

    html = f'''<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smart Demand Signals — Dashboard v1</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #f5f7fa; color: #1a1a2e; padding: 20px; }}
.header {{ max-width: 1400px; margin: 0 auto 20px; display: flex; justify-content: space-between; align-items: center; }}
.header h1 {{ font-size: 22px; color: #1a1a2e; }}
.header h1 span {{ color: #3498db; }}
.stats {{ display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 20px; }}
.stat-card {{ background: white; border-radius: 10px; padding: 15px 20px; flex: 1; min-width: 150px;
             box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
.stat-card .label {{ font-size: 11px; text-transform: uppercase; color: #7f8c8d; letter-spacing: 0.5px; }}
.stat-card .value {{ font-size: 24px; font-weight: 700; margin-top: 4px; }}
.filters {{ display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }}
.filters select, .filters input {{ padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;
                                   font-size: 13px; background: white; }}
.filters select:focus, .filters input:focus {{ outline: none; border-color: #3498db; }}
.filters label {{ font-size: 12px; color: #555; align-self: center; }}
table {{ width: 100%; max-width: 1400px; margin: 0 auto; border-collapse: collapse;
        background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
th {{ background: #1a1a2e; color: white; padding: 10px 8px; font-size: 11px; text-transform: uppercase;
     letter-spacing: 0.5px; text-align: left; white-space: nowrap; cursor: pointer; }}
th:hover {{ background: #2d2d5e; }}
td {{ padding: 10px 8px; font-size: 13px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
tr:hover {{ background: #f8f9ff; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.motiu {{ max-width: 200px; font-size: 11px; color: #555; }}
.prov {{ font-size: 11px; color: #7f8c8d; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
.badge-finestra_captura {{ background: #d4edda; color: #155724; }}
.badge-risc_fuga {{ background: #f8d7da; color: #721c24; }}
.badge-reposicio_endarrerida {{ background: #fff3cd; color: #856404; }}
.badge-reposicio_pendent {{ background: #e2e3f5; color: #383d41; }}
.badge-oportunitat_captura {{ background: #d1ecf1; color: #0c5460; }}
.badge-monitoritzar {{ background: #e2e3f5; color: #383d41; }}
.badge-perdut {{ background: #f5f5f5; color: #999; }}
.badge-info {{ background: #e2e3f5; color: #383d41; }}
.badge-seg.fidel {{ background: #2ecc71; color: white; }}
.badge-seg.promiscu {{ background: #f1c40f; color: #333; }}
.badge-seg.marginal {{ background: #95a5a6; color: white; }}
.badge-seg.en_risc {{ background: #e67e22; color: white; }}
.badge-seg.nou {{ background: #3498db; color: white; }}
.badge-seg.perdut {{ background: #e74c3c; color: white; }}
.badge-canal {{ background: #1a1a2e; color: white; font-size: 10px; }}
.urg {{ padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
.urg-alta {{ background: #f8d7da; color: #721c24; }}
.urg-mitjana {{ background: #fff3cd; color: #856404; }}
.urg-baixa {{ background: #e2e3f5; color: #383d41; }}
.prio-high {{ border-left: 3px solid #e74c3c; }}
.prio-med {{ border-left: 3px solid #f39c12; }}
.prio-low {{ border-left: 3px solid #bdc3c7; }}
.empty {{ text-align: center; padding: 40px; color: #999; font-size: 16px; }}
#counter {{ font-size: 13px; color: #555; margin-bottom: 10px; }}
footer {{ text-align: center; margin-top: 20px; color: #999; font-size: 12px; }}
</style>
</head>
<body>

<div class="header">
    <h1>🔔 <span>Smart Demand Signals</span> — Commodities</h1>
    <div style="font-size:13px;color:#555;">{TODAY} · v1</div>
</div>

<div class="stats">
    <div class="stat-card"><div class="label">Alertes</div><div class="value">{n:,}</div></div>
    <div class="stat-card"><div class="label">Clients</div><div class="value">{n_clients:,}</div></div>
    <div class="stat-card"><div class="label">Gap Total</div><div class="value">{gap_total:,.0f}€</div></div>
    <div class="stat-card"><div class="label">Per tipus</div><div class="value" style="font-size:14px;">
        {" · ".join(f'{t}: {c}' for t,c in sorted(tipus_counts.items()))}
    </div></div>
</div>

<div class="filters">
    <label>🔍 Tipus:</label>
    <select id="filter-tipus" onchange="filtra()">
        <option value="">Tots</option>
        {tipus_opts}
    </select>
    <label>Segment:</label>
    <select id="filter-seg" onchange="filtra()">
        <option value="">Tots</option>
        {seg_opts}
    </select>
    <label>Urgència:</label>
    <select id="filter-urg" onchange="filtra()">
        <option value="">Totes</option>
        <option value="alta">Alta</option>
        <option value="mitjana">Mitjana</option>
        <option value="baixa">Baixa</option>
    </select>
    <label>Província:</label>
    <input type="text" id="filter-prov" placeholder="Escriu..." onkeyup="filtra()">
    <label>Prioritat mín:</label>
    <input type="number" id="filter-prio" value="0" min="0" onkeyup="filtra()" style="width:70px;">
</div>

<div id="counter">Mostrant totes les {n:,} alertes</div>

<table>
<thead>
<tr>
    <th>#</th><th>Client</th><th>Família</th><th>Alerta</th><th>Segment</th>
    <th>Gap</th><th>Share</th><th>Sense</th><th>Urg.</th><th>Prioritat</th><th>Canal</th><th>Motiu</th>
</tr>
</thead>
<tbody id="tbody">
{rows_html}
</tbody>
</table>

<footer>Smart Demand Signals · Inibsa · Interhack BCN 2026 · Executat: {datetime.now().strftime('%Y-%m-%d %H:%M')}</footer>

<script>
function filtra() {{
    const tipus = document.getElementById('filter-tipus').value.toLowerCase();
    const seg = document.getElementById('filter-seg').value.toLowerCase();
    const urg = document.getElementById('filter-urg').value.toLowerCase();
    const prov = document.getElementById('filter-prov').value.toLowerCase();
    const prioMin = parseFloat(document.getElementById('filter-prio').value) || 0;
    const rows = document.querySelectorAll('#tbody tr');
    let visibles = 0;
    rows.forEach(r => {{
        const t = r.cells[3].innerText.toLowerCase();
        const s = r.cells[4].innerText.toLowerCase();
        const u = r.cells[8].innerText.toLowerCase();
        const p = r.cells[1].innerText.toLowerCase();
        const prio = parseFloat(r.cells[9].innerText.replace(/,/g,'')) || 0;
        const match = (!tipus || t.includes(tipus)) && (!seg || s.includes(seg))
                   && (!urg || u.includes(urg)) && (!prov || p.includes(prov))
                   && prio >= prioMin;
        r.style.display = match ? '' : 'none';
        if (match) visibles++;
    }});
    document.getElementById('counter').innerText = 'Mostrant ' + visibles + ' de {n:,} alertes';
}}
</script>
</body>
</html>'''
    return html


if __name__ == '__main__':
    print("📊 Generant dashboard v1...")
    df = load_alerts()
    html = build_html(df)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        f.write(html)
    print(f"✅ Dashboard generat: {OUTPUT_PATH}")
    print(f"   Obre'l al navegador: file://{os.path.abspath(OUTPUT_PATH)}")
