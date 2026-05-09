import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Configuración de página
st.set_page_config(page_title="Inibsa - EDA Smart Demand Signals", layout="wide")

st.title("🦷 Explorador de Datos Reactivo: INIBSA Hackathon")

@st.cache_data
def load_data(dataset_type):
    file_path = f"data/master_{dataset_type.lower()}.csv"
    df = pd.read_csv(file_path, parse_dates=['Fecha'])
    return df

# --- SIDEBAR ---
st.sidebar.header("Filtros Globales")
dataset_choice = st.sidebar.radio("Tipo de Producto", ["Commodities", "Technicals"])

# Cargar dataset
df = load_data(dataset_choice)

# Filtro extra por familia
familias = df['Familia_Potencial'].dropna().unique().tolist()
selected_familia = st.sidebar.multiselect("Familia de Producto", familias, default=familias)

if selected_familia:
    df = df[df['Familia_Potencial'].isin(selected_familia)]

# Modo de análisis
analisis_mode = st.sidebar.radio("Vista de Análisis", ["Visión Global", "Deep Dive por Cliente"])

# --- VISTA GLOBAL ---
if analisis_mode == "Visión Global":
    st.header(f"Visión Global: {dataset_choice}")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Ventas (€)", f"€ {df['Valores_H'].sum():,.2f}")
    col2.metric("Total Transacciones", f"{len(df):,}")
    col3.metric("Clientes Únicos", f"{df['Id_Cliente'].nunique():,}")
    col4.metric("Devoluciones", f"{df['es_devolucion'].sum():,}")

    st.subheader("Evolución Temporal de Ventas")
    # Agrupar por Mes/Año
    df['Mes_Año'] = df['Fecha'].dt.to_period('M').astype(str)
    ventas_mes = df.groupby('Mes_Año')['Valores_H'].sum().reset_index()
    fig_line = px.line(ventas_mes, x='Mes_Año', y='Valores_H', markers=True, title="Ventas Mensuales (€)")
    st.plotly_chart(fig_line, use_container_width=True)

    colA, colB = st.columns(2)
    with colA:
        st.subheader("Top Provincias por Facturación")
        prov_ventas = df.groupby('Provincia')['Valores_H'].sum().nlargest(10).reset_index()
        fig_prov = px.bar(prov_ventas, x='Provincia', y='Valores_H', title="Top 10 Provincias")
        st.plotly_chart(fig_prov, use_container_width=True)

    with colB:
        st.subheader("Potencial vs. Ventas Reales (Top 50 Clientes)")
        ventas_cliente = df.groupby(['Id_Cliente', 'Familia_Potencial']).agg(
            Ventas_Reales=('Valores_H', 'sum'),
            Potencial_EUR=('Potencial_EUR', 'first')
        ).reset_index()
        
        # Filtrar a los top 50 por ventas
        top_50 = ventas_cliente.nlargest(50, 'Ventas_Reales')
        
        fig_scatter = px.scatter(top_50, x='Potencial_EUR', y='Ventas_Reales', color='Familia_Potencial',
                                 hover_data=['Id_Cliente'], title="Captura vs Potencial (Puntos bajo la diagonal indican potencial no capturado)")
        
        # Añadir línea y=x (diagonal donde Ventas = Potencial)
        max_val = top_50[['Potencial_EUR', 'Ventas_Reales']].max().max()
        fig_scatter.add_shape(type='line', line=dict(dash='dash'), x0=0, x1=max_val, y0=0, y1=max_val)
        st.plotly_chart(fig_scatter, use_container_width=True)


# --- DEEP DIVE POR CLIENTE ---
elif analisis_mode == "Deep Dive por Cliente":
    st.header(f"🕵️ Deep Dive: Historial del Cliente ({dataset_choice})")
    
    top_clientes = df.groupby('Id_Cliente')['Valores_H'].sum().nlargest(100).index.tolist()
    cliente_selected = st.sidebar.selectbox("Selecciona un Cliente (Top 100 por defecto o busca ID)", df['Id_Cliente'].unique(), index=0)
    
    df_cliente = df[df['Id_Cliente'] == cliente_selected].sort_values('Fecha')
    
    if df_cliente.empty:
        st.warning("No hay datos para este cliente en los filtros actuales.")
    else:
        # Metricas Clave
        provincia = df_cliente['Provincia'].iloc[0]
        st.subheader(f"Cliente ID: {cliente_selected} | Provincia: {provincia}")
        
        c1, c2, c3, c4 = st.columns(4)
        total_spent = df_cliente['Valores_H'].sum()
        potencial_estimado = df_cliente['Potencial_EUR'].max()
        capture_rate = (total_spent / potencial_estimado) * 100 if potencial_estimado > 0 else 0
        
        c1.metric("Gasto Total Acumulado", f"€ {total_spent:,.2f}")
        c2.metric("Potencial Anual", f"€ {potencial_estimado:,.2f}" if not pd.isna(potencial_estimado) else "Desconocido")
        c3.metric("Tasa de Captura (Histórica)", f"{capture_rate:.1f}%")
        
        # Calcular patrón de compra
        fechas_compra = df_cliente[df_cliente['es_devolucion'] == 0]['Fecha'].drop_duplicates().sort_values()
        dias_entre_compras = fechas_compra.diff().dt.days.dropna()
        frecuencia_media = dias_entre_compras.mean() if len(dias_entre_compras) > 0 else np.nan
        dias_desde_ultima = (pd.to_datetime("2025-09-30") - fechas_compra.max()).days # Suponiendo corte a Sept 2025
        
        c4.metric("Días desde última compra", f"{dias_desde_ultima} días")
        
        st.markdown(f"**Patrón de Ciclo de Reposición:** Pide media una vez cada **{frecuencia_media:.1f} días** (Varianza: {dias_entre_compras.std():.1f} días).")

        # Gráfico temporal
        st.subheader("Timeline de Transacciones del Cliente")
        fig_time = px.scatter(df_cliente, x='Fecha', y='Valores_H', color='Familia_Potencial',
                              size=df_cliente['Valores_H'].abs().clip(lower=10),
                              hover_data=['Id_Producto', 'Unidades', 'en_campana', 'es_devolucion'],
                              title="Historial de pedidos en el tiempo (Puntos negativos = Devoluciones)")
        
        # Marcar devoluciones en distinto simbolo si se desea o dejar tamaño
        st.plotly_chart(fig_time, use_container_width=True)
        
        st.write("Datos en crudo del cliente:")
        cols_to_show = ['Fecha', 'Id_Producto', 'Familia_Potencial', 'Unidades', 'Valores_H', 'en_campana', 'es_devolucion']
        st.dataframe(df_cliente[cols_to_show])
