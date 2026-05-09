import pandas as pd
import numpy as np
import json
from datetime import timedelta

class CommoditiesEngine:
    """
    Motor estadístic per a la família de Commodities (Anestèsia, Bioseguretat).
    Calcula Share of Wallet, cicles de reposició i genera alertes estructurades.
    """
    
    def __init__(self, data_path='../data/master_commodities.csv'):
        self.data_path = data_path
        self.df = None
        
    def load_data(self):
        print("📥 Carregant dades de commodities...")
        self.df = pd.read_csv(self.data_path)
        self.df['Fecha'] = pd.to_datetime(self.df['Fecha'])
        
    def process_client_family(self, df_cf, avui):
        """
        Processa les dades d'un sol client i família per generar segmentació i alertes.
        """
        if df_cf.empty:
            return None
            
        # Potencial anual (agafem el primer valor, ja que és el mateix per tota la sèrie d'aquesta família-client)
        potencial = df_cf['Potencial_EUR_anual'].iloc[0]
        if pd.isna(potencial) or potencial == 0:
            potencial = 1# Evitar divisió per zero si hi ha errors a les dades
            
        # Netejem vendes de campanyes i devolucions per fer els càlculs de baseline fiables
        df_net = df_cf[(df_cf['es_devolucion'] == 0) & (df_cf['en_campana'] == 0)].copy()
        df_net = df_net.sort_values('Fecha')
        
        if df_net.empty:
            return None
            
        primera_compra = df_net['Fecha'].min()
        ultima_compra = df_net['Fecha'].max()
        dies_desde_ultim = (avui - ultima_compra).days
        dies_antiguitat = (avui - primera_compra).days
        
        # Filtrem per finestres temporals vs "avui"
        vendes_12m_df = df_net[df_net['Fecha'] >= (avui - timedelta(days=365))]
        vendes_3m_df = df_net[df_net['Fecha'] >= (avui - timedelta(days=90))]
        
        vendes_12m = vendes_12m_df['Valores_H'].sum()
        vendes_3m = vendes_3m_df['Valores_H'].sum()
        
        # Share of Wallet
        share_12m = vendes_12m / potencial
        share_3m_anualitzat = (vendes_3m * 4) / potencial
        
        # 1. Segmentació
        segment = 'marginal'
        
        if dies_antiguitat < 90:
            segment = 'nou'
        elif dies_desde_ultim > 90 and df_net.shape[0] > 1:
            segment = 'perdut'
        else:
            if share_12m > 0.75:
                segment = 'fidel'
            elif 0.25 <= share_12m <= 0.75:
                segment = 'promiscu'
            else:
                segment = 'marginal'
                
            # Regla d'empitjorament (Risc de fuga)
            if segment in ['fidel', 'promiscu'] and share_3m_anualitzat < (0.8 * share_12m):
                segment = 'en_risc'
                
        # 2. Cicle de Reposició (Per fidels, promiscus, o en risc)
        cicle_mig = None
        cicle_std = None
        dies_retard = None
        z_score = None
        
        # Obtenir les dates de pedidos únics per calcular el cicle
        dates_pedidos = df_net.drop_duplicates(subset=['Num.Fact'])['Fecha'].sort_values()
        
        if len(dates_pedidos) >= 3 and segment in ['fidel', 'promiscu', 'en_risc']:
            intervals = dates_pedidos.diff().dt.days.dropna()
            cicle_mig = intervals.mean()
            cicle_std = intervals.std()
            
            # Necessitem una mínima std per evitar divisió per 0 en clients extremadament rutinaris
            if pd.isna(cicle_std) or cicle_std < 1: 
                cicle_std = 1.0 
                
            if pd.notna(cicle_mig) and cicle_mig > 0:
                dies_retard = max(0, dies_desde_ultim - cicle_mig)
                z_score = (dies_desde_ultim - cicle_mig) / cicle_std
        
        # 3. Generació d'Alerta
        tipus_alerta = None
        urgencia = None
        impacte_recuperable = (potencial * (1 - share_12m)) if share_12m < 1 else 0
        
        # Si tenim z_score, podem generar alertes de reposició o fuga pel cicle
        if z_score is not None:
            if segment == 'fidel' and z_score > 1.5:
                tipus_alerta = 'risc_fuga'
                urgencia = 'alta' if z_score > 2.5 else 'mitja'
            elif segment == 'promiscu' and abs(dies_desde_ultim - cicle_mig) <= 3:
                # El pedido toca EXACTAMENT ara (± 3 dies)
                tipus_alerta = 'finestra_captura'
                urgencia = 'alta'
            elif segment == 'promiscu' and z_score > 0:
                # S'ha saltat el cicle, potser ja ha comprat a la competència 
                # (però seguim tractant d'alertar-lo)
                tipus_alerta = 'reposicio_endarrerida'
                urgencia = 'mitja'
            elif segment == 'en_risc':
                tipus_alerta = 'caiguda_share'
                urgencia = 'alta' if z_score > 1.0 else 'mitja'
                
        # Construcció del record d'alerta (si n'hi ha) o al menys l'estat actual per reporting
        data = {
            'id_client': int(df_cf['Id_Cliente'].iloc[0]),
            'provincia': df_cf['Provincia'].iloc[0] if 'Provincia' in df_cf else 'Desconeguda',
            'familia': str(df_cf['Familia_Potencial'].iloc[0]),
            'segment_client': segment,
            'share_of_wallet_12m': round(share_12m, 3),
            'dies_sense_compra': int(dies_desde_ultim),
            'cicle_habitual_dies': round(cicle_mig, 1) if cicle_mig else None,
            'potencial_anual_eur': round(potencial, 2),
            'z_score_retard': round(z_score, 2) if z_score else None
        }
        
        if tipus_alerta:
            data.update({
                'genera_alerta': True,
                'tipus_alerta': tipus_alerta,
                'impacte_recuperable_eur': round(impacte_recuperable, 2),
                'urgencia': urgencia
            })
            
            # Text explicatiu
            motiu = f"Client {segment} de {data['familia']} (Share 12m: {share_12m*100:.0f}%). "
            if cicle_mig is not None:
                motiu += f"El seu cicle de compra és de {cicle_mig:.0f} dies. Porta {dies_desde_ultim} dies sense comprar "
                motiu += f"({(dies_desde_ultim - cicle_mig):.0f} dies de coll). "
            
            if tipus_alerta == 'risc_fuga':
                motiu += "Possible inici de fuga."
            elif tipus_alerta == 'finestra_captura':
                motiu += "S'obre la seva finestra de reposició ara. Oportunitat per robar share a la competència."
            elif tipus_alerta == 'caiguda_share':
                motiu += "Tenia share alt, però en els últims 3 mesos ha caigut substancialment."
                
            data['motiu_explicat'] = motiu
        else:
            data['genera_alerta'] = False
            
        return data

    def run(self, data_ref=None):
        if self.df is None:
            self.load_data()
            
        avui = pd.to_datetime(data_ref) if data_ref else self.df['Fecha'].max()
        print(f"⏱️ Executant motor commodities a data de referència: {avui.strftime('%Y-%m-%d')}")
        
        results = []
        
        # Agrupar per Client i Família
        grups = self.df.groupby(['Id_Cliente', 'Familia_Potencial'])
        
        n_clients = len(self.df['Id_Cliente'].unique())
        print(f"🔄 Processant {n_clients} clients i les seves famílies de commodities...")
        
        for name, group in grups:
            res = self.process_client_family(group, avui)
            if res:
                results.append(res)
                
        df_results = pd.DataFrame(results)
        
        # Filtrar només els que generen alerta
        alertes = df_results[df_results['genera_alerta'] == True].copy()
        
        # Priorització d'alertes
        if not alertes.empty:
            # Una fòrmula senzilla per prioritat: impacte_economic (en milers d'euros) * pes urgencia
            urgencia_map = {'alta': 2.0, 'mitja': 1.0, 'baixa': 0.5}
            alertes['score_urgencia'] = alertes['urgencia'].map(urgencia_map)
            
            alertes['score_prioritat'] = (alertes['impacte_recuperable_eur'] / 1000) * alertes['score_urgencia']
            
            # Donar un extra boost a les alertes de fuga perquè són les més dolorses de perdre
            alertes.loc[alertes['tipus_alerta'] == 'risc_fuga', 'score_prioritat'] *= 1.5
            
            alertes = alertes.sort_values(by='score_prioritat', ascending=False)
            
        print(f"✅ Anàlisi complet. Generades {len(alertes) if not alertes.empty else 0} alertes.")
        return df_results, alertes

if __name__ == "__main__":
    import os
    
    engine = CommoditiesEngine(data_path='data/master_commodities.csv')
    df_all, df_alerts = engine.run()
    
    # Desa resultats
    output_dir = 'commodities/output'
    os.makedirs(output_dir, exist_ok=True)
    
    if not df_alerts.empty:
        # Exportem les alertes prioritzades
        alertes_path = os.path.join(output_dir, 'alertes_diaries_commodities.csv')
        df_alerts.drop(columns=['genera_alerta', 'score_urgencia']).to_csv(alertes_path, index=False)
        print(f"📁 Alertes exportades a {alertes_path}")
        
    # Exportem estat complert (incloses no alertes, útil pel dashboard/reporting)
    all_path = os.path.join(output_dir, 'estat_clients_commodities.csv')
    df_all.to_csv(all_path, index=False)
    print(f"📁 Estat complet exportat a {all_path}")
    
    # Genera exemple d'alerta
    if not df_alerts.empty:
        print("\n🔍 EXEMPLE DE TOP ALERTA:")
        top = df_alerts.iloc[0].to_dict()
        print(json.dumps(top, indent=2, ensure_ascii=False))