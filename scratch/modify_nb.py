import nbformat as nbf

nb_path = '/home/jcalatay/Desktop/INTERHACK/INIBSA/client_product_annual_behavior.ipynb'

with open(nb_path, 'r', encoding='utf-8') as f:
    nb = nbf.read(f, as_version=4)

# Improved interactive visualization code
new_code = """client_dropdown = widgets.Dropdown(options=clients, description='Client ID:')
product_dropdown = widgets.Dropdown(description='Product ID:')

def update_products(*args):
    client_id = client_dropdown.value
    products = sorted(df_annual[df_annual['Id_Cliente'] == client_id]['Id_Producto'].unique())
    product_dropdown.options = products

client_dropdown.observe(update_products, 'value')
update_products() # Initialize

@widgets.interact(client_id=client_dropdown, product_id=product_dropdown)
def plot_behavior(client_id, product_id):
    # 1. Filter detailed daily data
    detailed_subset = df[(df['Id_Cliente'] == client_id) & (df['Id_Producto'] == product_id)].copy()
    
    if detailed_subset.empty:
        print('No data found for this selection.')
        return
    
    # 2. Prepare aligned X-axis for yearly comparison
    # We use a dummy year (2000) to align the months and days across all years
    detailed_subset['Fecha_Aliniada'] = detailed_subset['Fecha'].apply(lambda x: x.replace(year=2000))
    detailed_subset['Año_Str'] = detailed_subset['Año'].astype(str)
    
    # 3. Faceted Bar Chart (One below the other per year)
    # This allows comparing the same dates across different years easily
    fig = px.bar(detailed_subset.sort_values('Fecha'), 
                 x='Fecha_Aliniada', 
                 y='Unidades', 
                 facet_row='Año_Str',
                 color='Año_Str',
                 title=f'Daily Activity by Year (Comparative): Client {client_id} - Product {product_id}',
                 hover_data={'Fecha': '|%d %B %Y', 'Unidades': True, 'Num.Fact': True, 'Fecha_Aliniada': False, 'Año_Str': False},
                 labels={'Unidades': 'Units', 'Fecha_Aliniada': 'Month', 'Año_Str': 'Year'},
                 category_orders={"Año_Str": sorted(detailed_subset['Año_Str'].unique(), reverse=True)})
    
    # Adjust layout for better readability
    fig.update_layout(
        height=250 * len(detailed_subset['Año'].unique()), 
        showlegend=False,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    # Fix X-axis to show months correctly and align all plots
    fig.update_xaxes(tickformat='%b', dtick='M1', title='Time of Year')
    
    # Clean up facet labels
    fig.for_each_annotation(lambda a: a.update(text=f"Year {a.text.split('=')[-1]}"))
    
    fig.show()
    
    # 4. Annual summary table
    subset_annual = df_annual[(df_annual['Id_Cliente'] == client_id) & (df_annual['Id_Producto'] == product_id)]
    print("\\nAnnual Summary:")
    display(subset_annual[['Año', 'Total_Unidades', 'Total_Valor', 'Num_Pedidos']].sort_values('Año'))"""

nb.cells[-1].source = new_code

with open(nb_path, 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print("Notebook updated with faceted yearly plots.")
