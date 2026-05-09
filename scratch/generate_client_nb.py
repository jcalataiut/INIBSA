import nbformat as nbf

nb = nbf.v4.new_notebook()

nb['cells'] = [
    nbf.v4.new_markdown_cell("# Client-Product Annual Behavior Analysis\nThis notebook allows you to explore how specific clients purchase specific products year over year."),
    
    nbf.v4.new_code_cell("import pandas as pd\nimport numpy as np\nimport plotly.express as px\nimport ipywidgets as widgets\nfrom IPython.display import display\n\n# Load Data\ndf = pd.read_csv('data/master_commodities_clean.csv', low_memory=False)\ndf['Fecha'] = pd.to_datetime(df['Fecha'])\ndf['Año'] = df['Fecha'].dt.year\n\nprint(f'Dataset loaded with {len(df)} rows.')"),
    
    nbf.v4.new_markdown_cell("## 1. Data Aggregation\nWe aggregate the data by Client, Product, and Year."),
    
    nbf.v4.new_code_cell("df_annual = df.groupby(['Id_Cliente', 'Id_Producto', 'Año']).agg({\n    'Unidades': 'sum',\n    'Valores_H': 'sum',\n    'Num.Fact': 'nunique'\n}).reset_index()\ndf_annual.columns = ['Id_Cliente', 'Id_Producto', 'Año', 'Total_Unidades', 'Total_Valor', 'Num_Pedidos']\n\n# Get lists for selectors\nclients = sorted(df_annual['Id_Cliente'].unique())\n\nprint('Aggregation complete.')"),
    
    nbf.v4.new_markdown_cell("## 2. Interactive Visualization\nUse the dropdowns to select a Client and a Product."),
    
    nbf.v4.new_code_cell("client_dropdown = widgets.Dropdown(options=clients, description='Client ID:')\nproduct_dropdown = widgets.Dropdown(description='Product ID:')\n\ndef update_products(*args):\n    client_id = client_dropdown.value\n    products = sorted(df_annual[df_annual['Id_Cliente'] == client_id]['Id_Producto'].unique())\n    product_dropdown.options = products\n\nclient_dropdown.observe(update_products, 'value')\nupdate_products() # Initialize\n\n@widgets.interact(client_id=client_dropdown, product_id=product_dropdown)\ndef plot_behavior(client_id, product_id):\n    subset = df_annual[(df_annual['Id_Cliente'] == client_id) & (df_annual['Id_Producto'] == product_id)]\n    \n    if subset.empty:\n        print('No data found for this selection.')\n        return\n    \n    # Ensure all years are present for a better timeline\n    all_years = pd.DataFrame({'Año': range(df_annual['Año'].min(), df_annual['Año'].max() + 1)})\n    subset = all_years.merge(subset, on='Año', how='left').fillna(0)\n\n    fig = px.bar(subset, x='Año', y='Total_Unidades', \n                 title=f'Annual Units: Client {client_id} - Product {product_id}',\n                 labels={'Total_Unidades': 'Units Sold'},\n                 text='Total_Unidades',\n                 color_discrete_sequence=['#636EFA'])\n    \n    fig.update_traces(textposition='outside')\n    fig.update_layout(xaxis_type='category')\n    fig.show()\n    \n    fig_val = px.line(subset, x='Año', y='Total_Valor', markers=True,\n                      title=f'Annual Value (€): Client {client_id} - Product {product_id}',\n                      labels={'Total_Valor': 'Value (€)'},\n                      color_discrete_sequence=['#EF553B'])\n    fig_val.update_layout(xaxis_type='category')\n    fig_val.show()\n    \n    display(subset[['Año', 'Total_Unidades', 'Total_Valor', 'Num_Pedidos']])")
]

with open('client_product_annual_behavior.ipynb', 'w') as f:
    nbf.write(nb, f)
