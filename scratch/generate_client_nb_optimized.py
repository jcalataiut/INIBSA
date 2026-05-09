import nbformat as nbf

nb = nbf.v4.new_notebook()

nb['cells'] = [
    nbf.v4.new_markdown_cell("# Optimized Client-Product Annual Behavior Analysis\nThis version is optimized for speed and uses pre-calculated indices."),
    
    nbf.v4.new_code_cell("import pandas as pd\nimport numpy as np\nimport plotly.express as px\nimport ipywidgets as widgets\nfrom IPython.display import display, clear_output\n\n# Load Data\ndf = pd.read_csv('data/master_commodities_clean.csv', low_memory=False)\ndf['Año'] = pd.to_datetime(df['Fecha']).dt.year\n\n# Pre-aggregate data to a very small dataframe\ndf_annual = df.groupby(['Id_Cliente', 'Id_Producto', 'Año']).agg({\n    'Unidades': 'sum',\n    'Valores_H': 'sum',\n    'Num.Fact': 'nunique'\n}).reset_index()\n\n# Create a dictionary for super fast lookup: {client_id: {product_id: dataframe}}\n# This avoids repeated filtering of the main dataframe\nlookup = {}\nfor (cid, pid), group in df_annual.groupby(['Id_Cliente', 'Id_Producto']):\n    if cid not in lookup:\n        lookup[cid] = {}\n    lookup[cid][pid] = group.sort_values('Año')\n\nclients = sorted(lookup.keys())\nprint(f'Ready! Optimized lookup for {len(clients)} clients.')"),
    
    nbf.v4.new_markdown_cell("## Interactive Exploration"),
    
    nbf.v4.new_code_cell("output = widgets.Output()\nclient_select = widgets.Dropdown(options=clients, description='Client ID:')\nproduct_select = widgets.Dropdown(description='Product ID:')\n\ndef on_client_change(change):\n    cid = change['new']\n    pids = sorted(lookup[cid].keys())\n    product_select.options = pids\n    if pids:\n        product_select.value = pids[0]\n\ndef on_selection_change(b=None):\n    with output:\n        clear_output(wait=True)\n        cid = client_select.value\n        pid = product_select.value\n        \n        if cid not in lookup or pid not in lookup[cid]:\n            print('No data found.')\n            return\n            \n        subset = lookup[cid][pid]\n        \n        fig = px.bar(subset, x='Año', y='Unidades', title=f'Annual Units: Client {cid} - Product {pid}', text_auto=True)\n        fig.update_layout(xaxis_type='category', height=400)\n        fig.show()\n        \n        fig_val = px.line(subset, x='Año', y='Valores_H', markers=True, title=f'Annual Value (€)')\n        fig_val.update_layout(xaxis_type='category', height=400)\n        fig_val.show()\n        \n        display(subset)\n\nclient_select.observe(on_client_change, names='value')\nproduct_select.observe(lambda x: on_selection_change(), names='value')\n\n# Initialize\non_client_change({'new': clients[0]})\ndisplay(widgets.VBox([client_select, product_select, output]))\non_selection_change()")
]

with open('client_product_annual_behavior.ipynb', 'w') as f:
    nbf.write(nb, f)
