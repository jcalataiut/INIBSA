import nbformat as nbf

nb = nbf.v4.new_notebook()

# --- Section 1: Intro ---
nb.cells.append(nbf.v4.new_markdown_cell("""
# Detección Avanzada y Explicativa del "Momento Óptimo"
Este notebook explora soluciones estadísticas para detectar el momento ideal de intervención comercial. 
El enfoque de este notebook es **EXPLICATIVO**: cada modelo no solo detecta el momento, sino que provee una explicación visual y cuantitativa para que el equipo de negocio confíe en la alerta.

## Perfiles:
1. **Clientes Leales**: Anticipar reposición (Stock, Monte Carlo, Gamma).
2. **Clientes Promiscuos**: Capturar ventana de compra (Velocidad de Share).
3. **Clientes en Riesgo**: Detectar deterioro (CUSUM, Control de Shewhart).
"""))

# --- Section 2: Setup ---
nb.cells.append(nbf.v4.new_code_cell("""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from datetime import datetime, timedelta

# Configuración visual
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['figure.figsize'] = (12, 6)

# Carga de datos
df = pd.read_csv('data/master_commodities.csv')
df['Fecha'] = pd.to_datetime(df['Fecha'])
df = df[df['es_devolucion'] == 0] # Solo ventas netas

print(f"Dataset cargado: {len(df):,} transacciones")
"""))

# --- Section 3: CLIENTES LEALES ---
nb.cells.append(nbf.v4.new_markdown_cell("""
# 1. Clientes Leales: Anticipando la Reposición
El objetivo aquí es contactar al cliente *justo antes* de que se quede sin stock o cuando entra en su ventana de compra habitual.
"""))

# 3.1 Gamma Wait-Time
nb.cells.append(nbf.v4.new_markdown_cell("""
## 1.1 Modelado Probabilístico del Tiempo de Espera (Gamma)
**Lógica**: Modela los días entre compras. Calcula qué porcentaje de las veces el cliente ha comprado antes de X días.
**Explicación para negocio**: "El 80% de las veces, este cliente compra antes de 30 días. Hoy lleva 32 días, la probabilidad de que esté listo para comprar es muy alta."
"""))

nb.cells.append(nbf.v4.new_code_cell("""
def explainer_gamma_wait_time(client_id, family='Anestesia'):
    client_df = df[(df['Id_Cliente'] == client_id) & (df['Familia_Potencial'] == family)]
    dates = client_df['Fecha'].sort_values().unique()
    
    if len(dates) < 4:
        return "Datos insuficientes para modelar."
    
    intervals = np.diff(dates.astype('datetime64[D]')).astype(float)
    alpha, loc, beta = stats.gamma.fit(intervals)
    
    today = df['Fecha'].max() # Simulamos que 'hoy' es el último día del dataset
    last_date = dates[-1]
    days_since = (today - last_date).days
    
    # Calcular percentil 80 (Umbral óptimo)
    optimal_day = stats.gamma.ppf(0.8, alpha, loc, beta)
    prob_today = stats.gamma.cdf(days_since, alpha, loc, beta)
    
    # Visualización
    x = np.linspace(0, max(intervals) * 1.5, 100)
    pdf = stats.gamma.pdf(x, alpha, loc, beta)
    cdf = stats.gamma.cdf(x, alpha, loc, beta)
    
    fig, ax1 = plt.subplots()
    ax1.plot(x, pdf, 'b-', label='Densidad (Frecuencia histórica)')
    ax1.set_xlabel('Días entre compras')
    ax1.set_ylabel('Densidad', color='b')
    
    ax2 = ax1.twinx()
    ax2.plot(x, cdf, 'r--', label='Prob. Acumulada')
    ax2.axhline(0.8, color='orange', linestyle=':', label='Umbral 80%')
    ax2.axvline(optimal_day, color='green', lw=2, label=f'Día Óptimo ({optimal_day:.0f})')
    ax2.axvline(days_since, color='purple', linestyle='-.', lw=2, label=f'Días Hoy ({days_since})')
    ax2.set_ylabel('Probabilidad de haber comprado', color='r')
    
    plt.title(f"Explicación Gamma - Cliente {client_id}")
    fig.legend(loc='center right', bbox_to_anchor=(0.9, 0.5))
    plt.show()
    
    # Mensaje Explicativo
    mensaje = (f" EXPLICACIÓN PARA NEGOCIO:\\n"
               f" - Históricamente, el 80% de las veces este cliente reposiciona antes de {optimal_day:.0f} días.\\n"
               f" - Actualmente lleva {days_since} días sin comprar.\\n"
               f" - La probabilidad de que su stock esté listo para reposición es del {prob_today:.1%}.\\n"
               f" - ACCIÓN: {'Llamar YA' if days_since >= optimal_day else 'Esperar'}")
    print(mensaje)

# Ejemplo cliente leal
explainer_gamma_wait_time(4767)
"""))

# 3.2 Simulación Monte Carlo
nb.cells.append(nbf.v4.new_markdown_cell("""
## 1.2 Simulación Monte Carlo de Consumo
**Lógica**: Simula miles de escenarios de consumo diario basados en el historial para ver cuándo es probable que el stock llegue a 0.
**Explicación para negocio**: "En el 90% de nuestras simulaciones basadas en su consumo histórico, el stock de su último pedido se agotará el día X."
"""))

nb.cells.append(nbf.v4.new_code_cell("""
def explainer_monte_carlo_stock(client_id, family='Anestesia'):
    client_df = df[(df['Id_Cliente'] == client_id) & (df['Familia_Potencial'] == family)]
    dates = client_df['Fecha'].sort_values().unique()
    
    if len(dates) < 2: return "Datos insuficientes."
    
    # Calcular consumo medio diario histórico
    total_units = client_df['Unidades'].sum()
    total_days = (dates[-1] - dates[0]).days
    if total_days == 0: return "Días = 0"
    
    mean_burn_rate = total_units / total_days
    std_burn_rate = mean_burn_rate * 0.3 # Asumimos 30% de variabilidad para la simulación
    
    last_units = client_df[client_df['Fecha'] == dates[-1]]['Unidades'].sum()
    
    # Simular 5000 trayectorias de consumo
    n_sims = 5000
    n_days_sim = int(last_units / mean_burn_rate * 2) # Proyectar el doble de días esperados
    
    simulations = np.random.normal(mean_burn_rate, std_burn_rate, (n_sims, n_days_sim))
    simulations = np.clip(simulations, 0, None) # No consumos negativos
    cumulative_consumption = np.cumsum(simulations, axis=1)
    
    # Días hasta cruzar el stock disponible (last_units)
    days_to_depletion = np.argmax(cumulative_consumption >= last_units, axis=1)
    # Ignorar simulaciones que no se agotan en el tiempo proyectado
    days_to_depletion = days_to_depletion[days_to_depletion > 0]
    
    if len(days_to_depletion) == 0: return "No se agota en la simulación."
    
    pct_10 = np.percentile(days_to_depletion, 10) # 10% de las veces se agota antes de este día (Riesgo alto de rotura)
    pct_50 = np.median(days_to_depletion)
    
    plt.figure(figsize=(10,5))
    sns.histplot(days_to_depletion, bins=30, kde=True, color='skyblue')
    plt.axvline(pct_10, color='red', linestyle='--', label=f'Riesgo Rotura 10% (Día {pct_10:.0f})')
    plt.axvline(pct_50, color='green', linestyle='--', label=f'Mediana Esperada (Día {pct_50:.0f})')
    plt.title(f"Simulación Monte Carlo de Agotamiento de Stock - Cliente {client_id}")
    plt.xlabel('Días hasta agotar el último pedido')
    plt.ylabel('Frecuencia en Simulación')
    plt.legend()
    plt.show()
    
    mensaje = (f" EXPLICACIÓN PARA NEGOCIO:\\n"
               f" - Basado en 5,000 simulaciones de su consumo diario (Media: {mean_burn_rate:.1f} u/día):\\n"
               f" - Lo más probable es que agote las {last_units} unidades en {pct_50:.0f} días.\\n"
               f" - Sin embargo, hay un 10% de riesgo de que las agote rápido, en solo {pct_10:.0f} días.\\n"
               f" - ACCIÓN RECOMENDADA: Contactar el día {pct_10:.0f} desde su último pedido para asegurar stock.")
    print(mensaje)

explainer_monte_carlo_stock(36095)
"""))


# --- Section 4: CLIENTES EN RIESGO ---
nb.cells.append(nbf.v4.new_markdown_cell("""
# 2. Clientes en Riesgo: Detectando el Deterioro
Identificar cuándo el cliente se desvía de su propio patrón de normalidad.
"""))

# 4.1 Shewhart Control Chart
nb.cells.append(nbf.v4.new_markdown_cell("""
## 2.1 Control Estadístico (Shewhart)
**Lógica**: Dibuja la media histórica y bandas de control (Media ± 2 Desviaciones Estándar). 
**Explicación**: "Sus ventas de este mes han caído por debajo de la banda verde de normalidad. Es un comportamiento estadísticamente inusual."
"""))

nb.cells.append(nbf.v4.new_code_cell("""
def explainer_shewhart(client_id, family='Anestesia'):
    client_df = df[(df['Id_Cliente'] == client_id) & (df['Familia_Potencial'] == family)]
    monthly_sales = client_df.groupby('Fecha')['Valores_H'].sum().resample('ME').sum().fillna(0)
    
    if len(monthly_sales) < 12: return "Historial mensual insuficiente."
    
    # Calcular baseline con los primeros N-3 meses para ver si los últimos 3 meses son atípicos
    baseline = monthly_sales[:-3]
    recent = monthly_sales[-3:]
    
    mu = baseline.mean()
    sigma = baseline.std()
    lower_control_limit = max(0, mu - 2*sigma) # Límite inferior (2 sigmas)
    
    plt.figure(figsize=(12,4))
    plt.plot(monthly_sales.index, monthly_sales.values, marker='o', label='Ventas Mensuales')
    plt.axhline(mu, color='green', linestyle='-', label='Media Histórica')
    plt.axhline(lower_control_limit, color='red', linestyle='--', label='Límite Control Inferior (-2σ)')
    
    # Marcar alertas
    alerts = recent[recent < lower_control_limit]
    if len(alerts) > 0:
        plt.scatter(alerts.index, alerts.values, color='red', s=100, zorder=5, label='Alerta Deterioro')
        
    plt.title(f"Gráfico de Control (Shewhart) - Cliente {client_id}")
    plt.ylabel("Ventas (€)")
    plt.legend()
    plt.show()
    
    mensaje = (f" EXPLICACIÓN PARA NEGOCIO:\\n"
               f" - El consumo normal del cliente ronda los {mu:.0f}€ mensuales.\\n"
               f" - El límite de 'alarma' está configurado en {lower_control_limit:.0f}€ (caída extrema).\\n")
    if len(alerts) > 0:
        mensaje += f" - ¡ALERTA! Las ventas recientes han roto este límite hacia abajo. Investigar motivos inmediatamente."
    else:
        mensaje += f" - Actualmente el cliente se mantiene dentro de los límites normales de variabilidad."
    print(mensaje)

explainer_shewhart(96)
"""))


# --- Section 5: CLIENTES PROMISCUOS ---
nb.cells.append(nbf.v4.new_markdown_cell("""
# 3. Clientes Promiscuos: Identificando Oportunidades
Para clientes que dividen su compra, el momento óptimo es cuando vemos que su *Share of Wallet* comienza a acelerar positivamente (momento de fidelizar) o negativamente (riesgo inminente).
"""))

nb.cells.append(nbf.v4.new_code_cell("""
def explainer_share_velocity(client_id, family='Anestesia'):
    client_df = df[(df['Id_Cliente'] == client_id) & (df['Familia_Potencial'] == family)]
    
    if len(client_df) < 5: return "Datos insuficientes"
    
    # Agregación mensual
    monthly = client_df.groupby('Fecha')['Valores_H'].sum().resample('ME').sum().fillna(0).reset_index()
    
    # Necesitamos el potencial para el share. Asumiremos el potencial que tenga en el df
    potencial = df[(df['Id_Cliente'] == client_id) & (df['Familia_Potencial'] == family)]['Potencial_EUR_anual'].iloc[0]
    
    # Calcular rolling 12m sales para calcular share
    monthly['rolling_12m'] = monthly['Valores_H'].rolling(12, min_periods=1).sum()
    monthly['share'] = (monthly['rolling_12m'] / potencial).clip(0, 1)
    
    # Calcular VELOCIDAD (Primera derivada: cambio de share respecto al mes anterior)
    monthly['share_velocity'] = monthly['share'].diff()
    
    plt.figure(figsize=(12, 5))
    
    ax1 = plt.gca()
    ax1.plot(monthly['Fecha'], monthly['share'], 'b-', marker='o', label='Share of Wallet (12m)')
    ax1.set_ylabel('Share of Wallet (%)', color='b')
    ax1.set_ylim(0, 1.1)
    
    ax2 = ax1.twinx()
    # Color rojo si velocidad es negativa, verde si es positiva
    colors = ['red' if v < 0 else 'green' for v in monthly['share_velocity']]
    ax2.bar(monthly['Fecha'], monthly['share_velocity'], width=20, color=colors, alpha=0.5, label='Velocidad del Share')
    ax2.axhline(0, color='gray', linestyle='-')
    ax2.set_ylabel('Cambio de Share', color='k')
    
    plt.title(f"Dinámica de Share of Wallet - Cliente {client_id}")
    fig = plt.gcf()
    fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.9))
    plt.show()
    
    ult_vel = monthly['share_velocity'].iloc[-1]
    mensaje = (f" EXPLICACIÓN PARA NEGOCIO:\\n"
               f" - El gráfico azul muestra el % de compras que hace con nosotros (Share).\\n"
               f" - Las barras muestran el momentum: si son rojas, estamos perdiendo terreno rápidamente; si son verdes, estamos ganando.\\n"
               f" - Momentum actual: {ult_vel:.2%} mensual.\\n"
               f" - ACCIÓN: {'Fuerte caída, llamar con oferta agresiva' if ult_vel < -0.05 else ('Buen momentum, intentar cross-sell' if ult_vel > 0.05 else 'Mantener seguimiento')}")
    print(mensaje)

# Probamos con un cliente que parezca promiscuo o en riesgo
explainer_share_velocity(30)
"""))


# Guardar el notebook
with open('momento_optimo_explicativo.ipynb', 'w') as f:
    nbf.write(nb, f)
print("Notebook explicativo generado con éxito: momento_optimo_explicativo.ipynb")
