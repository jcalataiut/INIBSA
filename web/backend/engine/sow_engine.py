import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import text
from backend.database import get_engine

def run(today=None, verbose=False, **kwargs):
    if today is None:
        today = datetime.now().strftime("%Y-%m-%d")
    
    engine = get_engine()
    # Carreguem totes les vendes per calcular el share real per família
    query = "SELECT id_cliente, fecha, familia_potencial, valores_h, potencial_eur_anual FROM ventas WHERE es_devolucion = false"
    df = pd.read_sql(text(query), engine)
    df["fecha"] = pd.to_datetime(df["fecha"])
    
    alerts = []
    
    # Agrupem per client i família
    for (client_id, familia), group in df.groupby(["id_cliente", "familia_potencial"]):
        potencial = group["potencial_eur_anual"].max()
        if not potencial or potencial <= 0:
            continue
            
        # Resum mensual
        monthly = group.set_index("fecha").resample("MS")["valores_h"].sum().reset_index()
        
        # Reindexem per assegurar que tenim tots els mesos (per al rolling 12m)
        all_months = pd.date_range(monthly["fecha"].min(), today, freq="MS")
        monthly = monthly.set_index("fecha").reindex(all_months).fillna(0).reset_index()
        monthly.columns = ["mes", "euros"]
        
        # Càlcul del share rolling 12m
        monthly["rolling_12m"] = monthly["euros"].rolling(12, min_periods=1).sum()
        monthly["share"] = (monthly["rolling_12m"] / potencial).clip(0, 1)
        
        if len(monthly) < 2:
            continue
            
        # Ignorem el mes actual si no té dades suficients o estem a principi de mes
        # Per a un anàlisi real, mirem l'últim mes complet tancat vs l'anterior
        complete_months = monthly[monthly["mes"] < pd.to_datetime(today).replace(day=1)]
        if len(complete_months) < 2:
            continue
            
        current_share = complete_months.iloc[-1]["share"]
        prev_share = complete_months.iloc[-2]["share"]
        last_complete_month = complete_months.iloc[-1]["mes"]
        
        # Funcions auxiliars per segments
        def get_seg(s):
            if s >= 0.70: return "lleial"
            if s >= 0.30: return "promiscu"
            return "fuga"
        # Càlcul del Gap (només si estem per sota del 70%)
        # El gap és el que ens falta per arribar al 70% del seu potencial
        gap = max(0, (0.7 - current_share) * potencial)
        
        pre_seg = get_seg(prev_share)
        cur_seg = get_seg(current_share)
        
        if cur_seg != pre_seg:
            tipus = f"sow_{pre_seg}_{cur_seg}"
            motiu = ""
        # Mètriques de periodicitat
        df_c = group.sort_values('fecha')
        dies_sense = 0
        cicle_mig = None
        if not df_c.empty:
            last_date = df_c['fecha'].max()
            dies_sense = (pd.to_datetime(today) - last_date).days
            if len(df_c) > 1:
                cicle_mig = df_c['fecha'].diff().dt.days.mean()

        tipus = None
        motiu = ""
        prioritat = 50
            
        if pre_seg == cur_seg:
            continue

        if cur_seg == "fuga":
            tipus = "sow_promiscu_fuga"
            prioritat = 90
            motiu = f"RISC: Risc de pèrdua imminent a {familia}. El share ha caigut per sota del 30% (actual: {current_share*100:.0f}%)."
        elif pre_seg == "lleial" and cur_seg == "promiscu":
            tipus = "sow_lleial_promiscu"
            prioritat = 70
            motiu = f"CAIGUDA: El client ha passat de Lleial a Promiscu a {familia} (share: {current_share*100:.0f}%)."
        elif pre_seg == "fuga" and cur_seg == "promiscu":
            tipus = "sow_fuga_promiscu"
            prioritat = 60
            motiu = f"RECUPERACIÓ: El client torna a comprar {familia} (share: {current_share*100:.0f}%)."
        elif pre_seg == "promiscu" and cur_seg == "lleial":
            tipus = "sow_promiscu_lleial"
            prioritat = 50
            motiu = f"ÈXIT: El client ja és Lleial a {familia} (share: {current_share*100:.0f}%). Objectiu de fidelització assolit."
        
        if tipus:
            alerts.append({
                "id_cliente": int(client_id),
                "familia_potencial": familia,
                "tipus_alerta": tipus,
                "prioritat": prioritat,
                "urgencia": "critica" if "fuga" in tipus else ("alta" if "promiscu" in tipus and "lleial" in tipus else "mitjana"),
                "canal": "delegat" if "fuga" in tipus else "televenda",
                "segment": cur_seg,
                "segment_anterior": pre_seg,
                "motiu": motiu,
                "share_12m": current_share,
                "gap_eur": potencial - monthly.iloc[-1]["rolling_12m"],
                "dies_sense_compra": int(dies_sense),
                "cicle_mig_dies": float(cicle_mig) if cicle_mig else None,
                "data_alerta": today
            })
            
    return pd.DataFrame(alerts), None
