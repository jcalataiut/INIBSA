# INIBSA - Hackathon Smart Demand Signals

## 🦷 El contexto: Qué está pasando en el negocio
Inibsa es una farmacéutica que vende productos dentales (anestesia, agujas, biomateriales, implantes...) a ~7.000 clínicas dentales en España. Su equipo comercial tiene delegados y televendedores que visitan/llaman a estas clínicas. 
El problema: no saben cuándo llamar, a quién llamar, ni por qué un cliente ha dejado de comprar. Todo es reactivo.

Lo que quieren es un sistema tipo "CRM inteligente" que cada mañana les diga: "Hoy llama a estas 20 clínicas, por este motivo, con esta urgencia." El objetivo es anticiparse, prever cuándo un cliente se va a ir o deteriorar, y actuar de forma proactiva.

## 📊 Los datos
1. **Ventas.csv** — el corazón del sistema
   - 162.545 líneas, ventas desde enero 2022 hasta septiembre 2025.
   - Tiene unidades (negativas = devoluciones), valores anonimizados, ID de cliente y producto.
   - La fecha es la variable principal para construir el comportamiento temporal.
2. **Productos.csv** — catálogo
   - 25 productos clave divididos en 2 grandes bloques analíticos: Commodities (8) vs Productos Técnicos (17).
   - **Commodities:** (Anestesia, agujas) Se consumen de forma predecible y constante.
   - **Técnicos:** (Biomateriales, implantes) Se usan esporádicamente por casos clínicos concretos. Son más caros e irregulares.
3. **Clientes.csv** — maestro de clientes
   - ~11.000 clínicas dentales con geografía (Provincia, Código Postal).
4. **Potencial.csv** — el más valioso
   - Gasto potencial estimado de cada clínica en cada familia.
   - Permite calcular la **tasa de captura** (`ventas reales / potencial = % del wallet`).
5. **Campañas.csv**
   - 10 campañas cortas (1-12 días). Generan picos artificiales que deben considerarse ruido para los modelos predictivos.

## 🎯 Qué queremos construir
Dos modelos distintos bien justificados:

### Motor 1: Commodities (Anestesia, Bioseguridad)
- **El problema de la competencia invisible:** La competencia no se observa directamente. Hay que inferirla de forma razonable a partir del patrón de compra observado y del potencial relativo del cliente.
- **Objetivo 1 - Clasificación:** El sistema debe distinguir entre clientes **leales** (compran mayormente a Inibsa) y clientes **promiscuos** (reparten su demanda con la competencia o compran a Inibsa a través de distribuidores/depósitos alternativos).
- **Objetivo 2 - Solución accionable (Lo que debe permitir):**
  1. Detectar demanda no capturada en clientes promiscuos.
  2. Estimar el momento óptimo de contacto (retraso en el ciclo de reposición).
  3. Identificar señales tempranas de deterioro en clientes estables/leales antes de que se vayan.

### Motor 2: Productos Técnicos (Biomateriales, Implantes)
- **Qué puede pasar:** Algunos clientes muestran recurrencia suficiente para detectar desviaciones.
- **Qué no debe asumirse:** Esa regularidad no está garantizada y no debe leerse de forma rígida.
- **Qué debe hacer la solución:** Distinguir entre variabilidad normal, desplazamiento temporal y deterioro real.
- **Detectar (puntos extra):**
  - Caída de frecuencia
  - Caída de volumen
  - Ausencia de compra
  - Actividad anómala

## 🔧 Workflow Pipeline / Features (build_dataset.py)
1. Parseo de formatos (comas por puntos decimales).
2. Limpieza de devoluciones.
3. Marcar ventas durante campañas para aislarlas.
4. Joins de productos, clientes y potencial.
5. Se generan 2 archivos listos para modelar:
   - `data/master_commodities.csv`
   - `data/master_technicals.csv`
(Recuerda hacer drop de `Num.Fact`, `Fecha`, `Id_Cliente`, `Id_Producto` antes de entrenar, como se avisa en el output).