import pandas as pd
import numpy as np
import pgeocode
from sqlalchemy import text
from backend.database import get_engine
from datetime import datetime

nomi = pgeocode.Nominatim('es')

def run(today=None, verbose=False):
    """
    Genera alertes geogràfiques comparant el share_12m d'un client amb els seus veïns.
    """
    if today is None:
        today = datetime.now().strftime("%Y-%m-%d")
    
    engine = get_engine()
    
    # Obtenir els share_12m de la cache que ja s'ha calculat avui
    query_cache = "SELECT id_cliente, provincia, familia_potencial, share_12m, potencial_anual_eur, euros_12m, gap_eur FROM alertes_cache WHERE data_alerta = :today AND tipus_alerta != 'fugat'"
    df_cache = pd.read_sql(text(query_cache), engine, params={"today": today})
    
    if df_cache.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    # Obtenir els codis postals dels clients
    query_clients = "SELECT id_cliente, MAX(cod_postal) as cod_postal FROM ventas GROUP BY id_cliente"
    df_clients = pd.read_sql(text(query_clients), engine)
    
    df = df_cache.merge(df_clients, on="id_cliente", how="inner")
    
    # Netejar cod_postal
    def clean_cp(x):
        try:
            val = str(x).replace('.0', '')
            # Pad amb 0s si cal
            return val.zfill(5)
        except:
            return None
            
    df['cod_postal_clean'] = df['cod_postal'].apply(clean_cp)
    
    # Obtenir lat / lon
    unique_cps = df['cod_postal_clean'].dropna().unique()
    geo_data = []
    for cp in unique_cps:
        res = nomi.query_postal_code(cp)
        if not pd.isna(res.latitude):
            geo_data.append({'cod_postal_clean': cp, 'lat': res.latitude, 'lon': res.longitude})
            
    df_geo = pd.DataFrame(geo_data)
    if df_geo.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    df = df.merge(df_geo, on="cod_postal_clean", how="inner")
    
    alerts = []
    
    # Calcular per cada familia
    for familia, group in df.groupby("familia_potencial"):
        for _, client in group.iterrows():
            if client['share_12m'] is None:
                continue
            
            client_share = float(client['share_12m'])
            
            # Si el client ja té un share alt, no necessita alerta
            if client_share >= 0.5:
                continue
                
            lat1 = client['lat']
            lon1 = client['lon']
            
            # Distancia simple (euclidiana aproximada)
            group['dist'] = np.sqrt((group['lat'] - lat1)**2 + (group['lon'] - lon1)**2)
            
            # Veïns propers (ex. < 0.1 graus aprox 10km)
            neighbors = group[(group['dist'] < 0.15) & (group['id_cliente'] != client['id_cliente'])]
            
            if len(neighbors) >= 3:
                avg_neighbor_share = neighbors['share_12m'].mean()
                if avg_neighbor_share - client_share >= 0.3: # Diferència significativa
                    alert = {
                        "id_cliente": client['id_cliente'],
                        "provincia": client['provincia'],
                        "familia_potencial": familia,
                        "segment": "lleial" if client_share >= 0.70 else ("promiscu" if client_share >= 0.30 else "fuga"),
                        "segment_anterior": None,
                        "tipus_alerta": "geographical_alert",
                        "urgencia": "mitjana",
                        "canal": "televenda",
                        "share_12m": round(client_share, 3),
                        "potencial_anual_eur": client['potencial_anual_eur'],
                        "euros_12m": client['euros_12m'],
                        "gap_eur": client['gap_eur'],
                        "dies_sense_compra": 0,
                        "num_intervals": 0,
                        "cicle_mig_dies": None,
                        "cicle_std_dies": None,
                        "dies_retard": 0,
                        "z_score": 0.0,
                        "proxim_pedido_esperat": None,
                        "dies_stock": None,
                        "prioritat": round(client['gap_eur'] * 0.4, 2),
                        "motiu": f"Alerta Geogràfica: Aquest client té un Share of Wallet de {client_share*100:.0f}%, mentre que {len(neighbors)} veïns propers tenen una mitjana del {avg_neighbor_share*100:.0f}%. El client podria demanar més producte.",
                        "data_alerta": today
                    }
                    alerts.append(alert)
                    
    alerts_df = pd.DataFrame(alerts)
    
    # Retornem (alerts_df, segments) però per no trencar cap signatura, els segments els enviem buits
    return alerts_df, pd.DataFrame()
