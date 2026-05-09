import pandas as pd
import numpy as np

# =============================================================================
# BUILD MASTER DATASET
# Une ventas con productos, clientes, potencial y campañas en una sola tabla.
# Output: master_with_ids.csv  (162.546 filas, una por línea de venta)
#
# COLUMNAS QUE SON IDs — dropear antes de meter en cualquier modelo:
#   Num.Fact    → ID de factura (agrupa líneas de un mismo pedido)
#   Id_Cliente  → ID de la clínica dental
#   Id_Producto → ID del producto
#   Fecha       → fecha exacta (usar en su lugar las features de tiempo:
#                 anyo, mes, trimestre, dia_semana, dia_anyo)
# =============================================================================

print("📦 Loading raw data...")
ventas    = pd.read_csv('/mnt/user-data/uploads/Datasets_xlsx_-_Ventas.csv', low_memory=False)
clientes  = pd.read_csv('/mnt/user-data/uploads/Datasets_xlsx_-_Clientes.csv')
productos = pd.read_csv('/mnt/user-data/uploads/Datasets_xlsx_-_Productos.csv')
potencial = pd.read_csv('/mnt/user-data/uploads/Datasets_xlsx_-_Potencial.csv')
campanas  = pd.read_csv('/mnt/user-data/uploads/Datasets_xlsx_-_Campañas.csv')

# ── 1. PARSEO Y LIMPIEZA DE COLUMNAS RAW ────────────────────────────────────

# Números con formato español (1.234,56 → 1234.56)
def parse_es_float(s):
    if pd.isna(s):
        return np.nan
    return float(str(s).replace('.', '').replace(',', '.'))

ventas['Valores_H']      = ventas['Valores_H'].apply(parse_es_float)
potencial['Potencial_H'] = potencial['Potencial_H'].apply(parse_es_float)

# Fechas
ventas['Fecha']          = pd.to_datetime(ventas['Fecha'],          format='%m/%d/%Y')
campanas['Fecha inicio'] = pd.to_datetime(campanas['Fecha inicio'], format='%m/%d/%Y')
campanas['Fecha fin']    = pd.to_datetime(campanas['Fecha fin'],    format='%m/%d/%Y')

# Renombrar columnas con espacios/puntos/caracteres raros a snake_case limpio
ventas    = ventas.rename(columns={'Id. Cliente': 'Id_Cliente', 'Id. Producto': 'Id_Producto'})
clientes  = clientes.rename(columns={'Id. Cliente': 'Id_Cliente', 'Unnamed: 1': 'Cod_Postal'})
productos = productos.rename(columns={'Id.Prod': 'Id_Producto', 'Bloque analítico': 'Bloque_Analitico'})
potencial = potencial.rename(columns={'Id.Cliente': 'Id_Cliente', 'Categoria Productos': 'Categoria_Potencial'})

# ── 2. FLAG: DEVOLUCIONES ────────────────────────────────────────────────────
# Unidades negativas = devolución. Hay 1.951 sobre 162.546 líneas.
# Se mantienen en el dataset marcadas — filtrar según el análisis que se haga.
ventas['es_devolucion'] = (ventas['Unidades'] < 0).astype(int)
print(f"  Devoluciones: {ventas['es_devolucion'].sum():,} filas")

# ── 3. FLAG: EN CAMPAÑA ──────────────────────────────────────────────────────
# Hay 10 campañas entre 2021 y 2025 (duración 1-12 días cada una).
# Las ventas durante campaña tienen picos artificiales → excluir del baseline
# de consumo normal en los modelos de frecuencia/ciclo de reposición.
campana_intervals = list(zip(campanas['Fecha inicio'], campanas['Fecha fin']))

def in_campaign(fecha):
    for inicio, fin in campana_intervals:
        if inicio <= fecha <= fin:
            return 1
    return 0

print("  Calculando flag en_campana...")
ventas['en_campana'] = ventas['Fecha'].apply(in_campaign)
print(f"  Ventas en campaña: {ventas['en_campana'].sum():,} filas")

# ── 4. JOIN PRODUCTOS ────────────────────────────────────────────────────────
# Añade Bloque_Analitico, Categoria_H, Familia_H a cada línea de venta.
# 25 productos en catálogo, 0 unmatched.
df = ventas.merge(productos, on='Id_Producto', how='left')
assert df['Bloque_Analitico'].isna().sum() == 0, "Hay productos sin match!"

# Commodity vs Técnico como binario (útil para filtrar sin depender del string)
df['es_commodity'] = (df['Bloque_Analitico'] == 'Commodities').astype(int)

# ── 5. JOIN CLIENTES ─────────────────────────────────────────────────────────
# El maestro de clientes tiene 37 IDs duplicados:
#   - La mayoría son filas exactamente iguales (bug de exportación)
#   - 7 tienen CP diferente (misma clínica, dos sedes o error de datos)
#   - 1 caso aparece en dos provincias distintas (Cádiz y Sevilla)
# Estrategia: drop_duplicates exactos primero, luego keep='first' para conflictos.
clientes_clean = clientes.drop_duplicates()
clientes_clean = clientes_clean.drop_duplicates(subset='Id_Cliente', keep='first')
n_dups = len(clientes) - len(clientes_clean)
print(f"  Clientes deduplicados: {n_dups} filas eliminadas del maestro")

df = df.merge(clientes_clean, on='Id_Cliente', how='left')
# 623 clientes en ventas no están en el maestro (dados de baja o errores)
print(f"  Clientes sin match en maestro: {df['Provincia'].isna().sum()}")
assert len(df) == len(ventas), f"Join clientes multiplicó filas: {len(df)} vs {len(ventas)}"

# ── 6. JOIN POTENCIAL ────────────────────────────────────────────────────────
# Potencial tiene una fila por (cliente, familia_real).
# Familias reales en potencial: Anestesia, Biomateriales, Bioseguridad
# Familias anonimizadas en productos: Familia C1, C2, T1, T2
#
# Mapeo por dominio (confirmado por estructura del negocio):
#   Familia C1 → Anestesia      (commodities, anestesia local)
#   Familia C2 → Bioseguridad   (commodities, agujas y desinfección)
#   Familia T1 → Biomateriales  (técnicos, regeneración ósea)
#   Familia T2 → Biomateriales  (técnicos, otra subfamilia de biomateriales)
familia_map = {
    'Familia C1': 'Anestesia',
    'Familia C2': 'Bioseguridad',
    'Familia T1': 'Biomateriales',
    'Familia T2': 'Biomateriales',
}
df['Familia_Potencial'] = df['Familia_H'].map(familia_map)

potencial_slim = potencial[['Id_Cliente', 'Familia', 'Potencial_H']].rename(
    columns={'Familia': 'Familia_Potencial', 'Potencial_H': 'Potencial_EUR'}
)

df = df.merge(potencial_slim, on=['Id_Cliente', 'Familia_Potencial'], how='left')
print(f"  Cobertura potencial: {df['Potencial_EUR'].notna().sum():,} / {len(df):,} filas")
assert len(df) == len(ventas), f"Join potencial multiplicó filas: {len(df)} vs {len(ventas)}"

# ── 7. FEATURES TEMPORALES ───────────────────────────────────────────────────
# Extraídas de Fecha. Usar estas en modelos, no la fecha raw.
df['anyo']       = df['Fecha'].dt.year
df['mes']        = df['Fecha'].dt.month
df['trimestre']  = df['Fecha'].dt.quarter
df['dia_semana'] = df['Fecha'].dt.dayofweek  # 0 = lunes, 6 = domingo
df['dia_anyo']   = df['Fecha'].dt.dayofyear

# ── 8. ORDEN FINAL DE COLUMNAS ────────────────────────────────────────────────
df = df[[
    # ── IDs — dropear antes de cualquier modelo ──────────────────────────────
    'Num.Fact',          # ID de factura (agrupa líneas del mismo pedido)
    'Fecha',             # fecha exacta — usar features de tiempo en su lugar
    'Id_Cliente',        # ID clínica dental
    'Id_Producto',       # ID producto
    # ── Info producto ────────────────────────────────────────────────────────
    'Bloque_Analitico',  # 'Commodities' | 'Productos Técnicos'
    'Categoria_H',       # categoría anonimizada: C1, C2, T1
    'Familia_H',         # familia anonimizada: C1, C2, T1, T2
    'Familia_Potencial', # familia real mapeada: Anestesia | Bioseguridad | Biomateriales
    'es_commodity',      # 1 = commodity, 0 = técnico
    # ── Info cliente ─────────────────────────────────────────────────────────
    'Cod_Postal',        # código postal (NaN en 623 clientes no encontrados en maestro)
    'Provincia',         # provincia española
    # ── Transacción ──────────────────────────────────────────────────────────
    'Unidades',          # cantidad (negativo = devolución)
    'Valores_H',         # importe EUR (anonimizado en escala pero real)
    'es_devolucion',     # 1 si Unidades < 0
    'en_campana',        # 1 si la venta cae dentro de una campaña promocional
    # ── Potencial de mercado ─────────────────────────────────────────────────
    'Potencial_EUR',     # gasto estimado anual de la clínica en esa familia
    # ── Features temporales — usar estas en modelo, no Fecha ─────────────────
    'anyo',
    'mes',
    'trimestre',
    'dia_semana',        # 0 = lunes
    'dia_anyo',
]]

# ── 9. SAVE ───────────────────────────────────────────────────────────────────
output_path = '/mnt/user-data/outputs/master_with_ids.csv'
df.to_csv(output_path, index=False)

print(f"\n✅ DONE — {df.shape[0]:,} filas × {df.shape[1]} columnas → master_with_ids.csv")
print(f"\n  Para modelo: df.drop(columns=['Num.Fact', 'Fecha', 'Id_Cliente', 'Id_Producto'])")
print(f"\n{df.dtypes}")
