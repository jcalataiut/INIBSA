import nbformat as nbf
import os

nb = nbf.v4.new_notebook()

nb['cells'] = [
    nbf.v4.new_markdown_cell("# Data Cleaning and Outlier Analysis\nThis notebook analyzes 'strange cases' in the Inibsa dataset, specifically:\n1. Clients with billing significantly higher than their estimated potential.\n2. Clients with very low transaction frequency."),
    
    nbf.v4.new_code_cell("import pandas as pd\nimport numpy as np\nimport matplotlib.pyplot as plt\nimport seaborn as sns\nimport plotly.express as px\n\n# Settings\nsns.set(style='whitegrid')\n%matplotlib inline"),
    
    nbf.v4.new_markdown_cell("## 1. Loading Data"),
    
    nbf.v4.new_code_cell("df_commodities = pd.read_csv('data/master_commodities.csv', low_memory=False)\ndf_technicals = pd.read_csv('data/master_technicals.csv', low_memory=False)\n\ndf_commodities['Fecha'] = pd.to_datetime(df_commodities['Fecha'])\ndf_technicals['Fecha'] = pd.to_datetime(df_technicals['Fecha'])\n\nprint(f'Commodities: {len(df_commodities)} rows')\nprint(f'Technicals: {len(df_technicals)} rows')"),
    
    nbf.v4.new_markdown_cell("## 2. Billing vs Potential Analysis\nWe compare the annual billing per client and family against the estimated annual potential."),
    
    nbf.v4.new_code_cell("def analyze_billing_vs_potential(df, title):\n    # Aggregate by Client, Year and Family\n    df['anyo'] = df['Fecha'].dt.year\n    annual = df.groupby(['Id_Cliente', 'anyo', 'Familia_Potencial']).agg({\n        'Valores_H': 'sum',\n        'Potencial_EUR': 'first'\n    }).reset_index()\n    \n    # Ratio\n    annual['Ratio'] = annual['Valores_H'] / annual['Potencial_EUR']\n    annual.replace([np.inf, -np.inf], np.nan, inplace=True)\n    \n    # Filter strange cases (e.g., Ratio > 3)\n    strange = annual[annual['Ratio'] > 3]\n    \n    print(f'--- {title} ---')\n    print(f'Total Client-Year-Family records: {len(annual)}')\n    print(f'Records with billing > 3x Potential: {len(strange)}')\n    \n    # Visualization\n    plt.figure(figsize=(10, 6))\n    sns.scatterplot(data=annual, x='Potencial_EUR', y='Valores_H', alpha=0.5)\n    plt.plot([0, annual['Potencial_EUR'].max()], [0, annual['Potencial_EUR'].max()], 'r--', label='Billing = Potential')\n    plt.plot([0, annual['Potencial_EUR'].max()], [0, 3*annual['Potencial_EUR'].max()], 'g--', label='Billing = 3x Potential')\n    plt.title(f'Billing vs Potential ({title})')\n    plt.legend()\n    plt.show()\n    \n    return strange\n\nstrange_comm = analyze_billing_vs_potential(df_commodities, 'Commodities')\nstrange_tech = analyze_billing_vs_potential(df_technicals, 'Technicals')"),
    
    nbf.v4.new_markdown_cell("## 3. Transaction Frequency Analysis\nIdentifying clients with very few invoices over the 5-year period."),
    
    nbf.v4.new_code_cell("def analyze_frequency(df, title):\n    freq = df.groupby('Id_Cliente')['Num.Fact'].nunique().reset_index()\n    freq.columns = ['Id_Cliente', 'Invoice_Count']\n    \n    # Filter low frequency (e.g., < 3 invoices in 5 years)\n    low_freq = freq[freq['Invoice_Count'] < 3]\n    \n    print(f'--- {title} ---')\n    print(f'Total unique clients: {len(freq)}')\n    print(f'Clients with < 3 invoices: {len(low_freq)}')\n    \n    # Visualization\n    plt.figure(figsize=(10, 6))\n    sns.histplot(freq['Invoice_Count'], bins=50, kde=True)\n    plt.axvline(3, color='r', linestyle='--', label='Threshold (< 3)')\n    plt.title(f'Distribution of Invoices per Client ({title})')\n    plt.legend()\n    plt.show()\n    \n    return low_freq\n\nlow_freq_comm = analyze_frequency(df_commodities, 'Commodities')\nlow_freq_tech = analyze_frequency(df_technicals, 'Technicals')"),
    
    nbf.v4.new_markdown_cell("## 4. Cleaning Strategy\nWe will remove:\n1. Clients with annual billing > 5x Potential (extreme outliers).\n2. Clients with < 3 total invoices (insufficient history)."),
    
    nbf.v4.new_code_cell("def clean_dataset(df, strange, low_freq):\n    # Extreme outliers (Ratio > 5)\n    extreme_clients = strange[strange['Ratio'] > 5]['Id_Cliente'].unique()\n    # Low frequency clients\n    low_freq_clients = low_freq['Id_Cliente'].unique()\n    \n    exclude_clients = set(extreme_clients) | set(low_freq_clients)\n    \n    df_clean = df[~df['Id_Cliente'].isin(exclude_clients)].copy()\n    \n    print(f'Original rows: {len(df)}')\n    print(f'Cleaned rows: {len(df_clean)}')\n    print(f'Removed clients: {len(exclude_clients)}')\n    \n    return df_clean\n\ndf_commodities_clean = clean_dataset(df_commodities, strange_comm, low_freq_comm)\ndf_technicals_clean = clean_dataset(df_technicals, strange_tech, low_freq_tech)"),
    
    nbf.v4.new_markdown_cell("## 5. Saving Cleaned Data"),
    
    nbf.v4.new_code_cell("df_commodities_clean.to_csv('data/master_commodities_clean.csv', index=False)\ndf_technicals_clean.to_csv('data/master_technicals_clean.csv', index=False)\nprint('Datasets saved successfully.')")
]

with open('data_cleaning_analysis.ipynb', 'w') as f:
    nbf.write(nb, f)
