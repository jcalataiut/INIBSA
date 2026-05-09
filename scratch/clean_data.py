import pandas as pd
import numpy as np

def clean_data(file_path, output_path):
    df = pd.read_csv(file_path, low_memory=False)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df['anyo'] = df['Fecha'].dt.year
    
    # Frequency filter: < 3 invoices
    freq = df.groupby('Id_Cliente')['Num.Fact'].nunique()
    low_freq_clients = freq[freq < 3].index
    
    # Billing vs Potential filter
    annual = df.groupby(['Id_Cliente', 'anyo', 'Familia_Potencial']).agg({
        'Valores_H': 'sum',
        'Potencial_EUR': 'first'
    }).reset_index()
    annual['Ratio'] = annual['Valores_H'] / annual['Potencial_EUR']
    extreme_billing_clients = annual[annual['Ratio'] > 5]['Id_Cliente'].unique()
    
    exclude_clients = set(low_freq_clients) | set(extreme_billing_clients)
    
    df_clean = df[~df['Id_Cliente'].isin(exclude_clients)].copy()
    df_clean.to_csv(output_path, index=False)
    
    print(f'Processed {file_path}:')
    print(f'  Original Clients: {df.Id_Cliente.nunique()}')
    print(f'  Cleaned Clients: {df_clean.Id_Cliente.nunique()}')
    print(f'  Removed: {len(exclude_clients)}')

clean_data('data/master_commodities.csv', 'data/master_commodities_clean.csv')
clean_data('data/master_technicals.csv', 'data/master_technicals_clean.csv')
