from sqlalchemy import text
from backend.database import get_engine
import pandas as pd

engine = get_engine()
with engine.connect() as conn:
    df = pd.read_sql("SELECT id_cliente, familia_potencial, fecha, valores_h, potencial_eur_anual FROM ventas", conn)
    df['fecha'] = pd.to_datetime(df['fecha'])
    df['mes'] = df['fecha'].dt.to_period('M').dt.to_timestamp()
    
    # Agrupem per client, familia i mes
    monthly = df.groupby(['id_cliente', 'familia_potencial', 'mes']).agg({
        'valores_h': 'sum',
        'potencial_eur_anual': 'first'
    }).reset_index()
    
    results = []
    for (cid, fam), group in monthly.groupby(['id_cliente', 'familia_potencial']):
        group = group.sort_values('mes')
        potencial = group['potencial_eur_anual'].iloc[0] or 1000
        group['rolling_sales'] = group['valores_h'].rolling(window=12, min_periods=1).sum()
        group['share'] = group['rolling_sales'] / potencial
        
        if len(group) >= 2:
            last = group.iloc[-1]
            prev = group.iloc[-2]
            if last['share'] > prev['share']:
                results.append({
                    'id': cid,
                    'fam': fam,
                    'prev_share': prev['share'],
                    'curr_share': last['share'],
                    'diff': last['share'] - prev['share']
                })

    res_df = pd.DataFrame(results)
    if not res_df.empty:
        print("Clients amb millora de share detectada:")
        print(res_df.sort_values('diff', ascending=False).head(10))
    else:
        print("No s'han trobat clients amb millora de share entre els dos últims mesos.")
