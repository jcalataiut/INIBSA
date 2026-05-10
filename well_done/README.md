# Smart Demand Signals — Inibsa · Interhack BCN 2026

> Predicció de necessitat de compra i detecció primerenca de risc d'abandonament en clíniques dentals.

---

## 1. Context i problema de negoci

**Inibsa** és una empresa farmacèutica de producció local (Barcelona) especialitzada en productes odontològics. Opera amb una base aproximada de **7.000 clíniques dentals** a Espanya i disposa d'un historial de més de cinc anys de vendes a nivell de client, producte i data.

L'equip comercial d'Inibsa es divideix en **delegats** (visites presencials) i **televendedors** (contacte telefònic). Avui en dia, l'activitat comercial és majoritàriament **reactiva**: es contacta el client quan ell truca, quan es detecta que ha deixat de comprar del tot, o en base a intuïció del delegat. No hi ha cap sistema que digui proactivament *"avui has d'anar a aquesta clínica, per aquest motiu, en aquest moment"*.

Això genera tres problemes concrets:

1. **Pèrdua de demanda no capturada**: una clínica que consumeix 4.000€/any d'anestèsia i només compra 800€ a Inibsa s'està abastint majoritàriament amb la competència. Sense un sistema de detecció, mai es sap.
2. **Reacció tardana a fugues**: quan es detecta que un client ha deixat de comprar, normalment ja ha estat mesos comprant exclusivament a un competidor i la relació és difícil de recuperar.
3. **Temps comercial mal distribuït**: els delegats i televendedors dediquen esforç a clíniques que no necessiten atenció immediata, mentre clíniques amb risc real de fuga no reben cap contacte.

### L'objectiu del sistema

Dissenyar una solució analítica que cada dia generi una **llista prioritzada d'alertes comercials** a nivell de `(client, família de producte, motiu)`, de manera que l'equip comercial sàpiga exactament:

- A qui contactar avui
- Per quin producte / família
- Per quin motiu (reposició, risc de fuga, oportunitat de captura)
- Per quin canal (delegat, televenda, màrqueting automatitzat)
- Quin impacte econòmic té la intervenció

---

## 2. Dos blocs analítics ben diferenciats

El negoci té dues dinàmiques de compra radicalment diferents que **requereixen motors analítics separats**.

### Bloc A — Commodities (Anestèsia + Bioseguretat)

Productes de consum **recurrent i predecible**. Tota clínica dental, independentment de la seva especialitat, consumeix anestèsia local i material de bioseguretat (agulles, desinfectants) de forma regular, com si fos paper d'impressora.

El repte aquí no és "si comprarà" sinó **"quan comprarà i a qui"**. Una clínica pot repartir la compra entre Inibsa i la competència (client promiscu), pot concentrar-la tota amb Inibsa (client fidel), o pot tenir un volum de compra molt per sota del seu potencial estimat (demanda no capturada).

Les preguntes clau:
- Quin % del wallet d'aquesta clínica estem capturant?
- Quan toca el proper pedido? (cicle de reposició)
- La tendència de compra és estable, creixent o decreixent?
- Hi ha una finestra d'oportunitat per capturar demanda que avui va a la competència?

### Bloc B — Productes Tècnics (Biomaterials)

Productes de compra **irregular i dependent del cas clínic**. Un implantòleg o cirurgià oral utilitza biomaterials (membranes de col·lagen, materials de regeneració òssia) quan té un cas que ho requereix. No és un consum setmanal, pot ser mensual, bimensual, o fins i tot trimestral depenent de l'agenda de la clínica.

Aquí el risc no és predictible per cicle sinó per **desviació del patró individual**. Si un client que historicament demanava cada 6 setmanes porta 14 setmanes sense demanar, alguna cosa ha canviat: potser ha reduït activitat, potser ha canviat de proveïdor.

Les preguntes clau:
- Quin és el patró de compra "normal" d'aquest client concret?
- El silenci actual és compatible amb la seva variabilitat natural, o és una senyal d'alarma?
- Quan va ser l'últim pedido i quant temps fa en relació al seu cicle habitual?

---

## 3. Datasets disponibles

### 3.1 `Ventas.csv` — 162.546 línies de venda (2021–2025)

**El dataset central.** Cada fila és una línia d'una factura: un producte venut a una clínica en una data concreta.

| Columna | Tipus | Descripció |
|---|---|---|
| `Num.Fact` | string | ID de factura. Una factura pot tenir múltiples línies (un mateix pedido agrupa diversos productes). **Identificador, no usar en models.** |
| `Fecha` | date | Data de la venda. Granularitat diària. Rang: **4 gen 2021 → 29 des 2025**. |
| `Id. Cliente` | int | ID de la clínica dental compradora. **8.095 clíniques úniques** han fet almenys una compra. |
| `Id. Producto` | int | ID del producte venut. **25 productes únics** al catàleg. |
| `Unidades` | int | Quantitat venuda. ⚠️ **Pot ser negativa** (1.951 casos = devolucions). Filtrar o marcar abans de qualsevol anàlisi. |
| `Valores_H` | float | Import en euros d'aquesta línia. Anonimitzat en escala (sufixe `_H` = hashed), però els valors relatius entre clients i productes són reals i comparables. |

**Notes importants:**
- Les **devolucions** (Unidades < 0) representen l'1,2% de les línies. Distorsionen el càlcul de volum si no es tracten.
- El format original del CSV utilitza punt com a separador de milers i coma com a decimal (`2.223,12`), amb els valors entre cometes per evitar conflictes amb el separador CSV. El pipeline de dades ho gestiona automàticament.

---

### 3.2 `Productos.csv` — Catàleg de 25 productes

Taula de dimensió petita però estratègicament crítica: és la que permet separar els dos blocs analítics.

| Columna | Tipus | Descripció |
|---|---|---|
| `Id.Prod` | int | ID del producte. Clau de join amb `Ventas.csv`. |
| `Bloque analítico` | string | **La variable més important del catàleg.** Dos valors: `Commodities` (8 productes) o `Productos Técnicos` (17 productes). Determina quin motor analític s'aplica. |
| `Categoria_H` | string | Categoria anonimitzada: `Categoria C1`, `Categoria C2`, `Categoria T1`. |
| `Familia_H` | string | Família anonimitzada: `Familia C1`, `Familia C2`, `Familia T1`, `Familia T2`. |

**Estructura del catàleg per família:**

| Família | Bloc | Família real (inferida) | Productes |
|---|---|---|---|
| Familia C1 | Commodities | Anestèsia | 6 productes |
| Familia C2 | Commodities | Bioseguretat (agulles, desinfecció) | 2 productes |
| Familia T1 | Productes Tècnics | Biomaterials (subfamília principal) | 10 productes |
| Familia T2 | Productes Tècnics | Biomaterials (subfamília secundària) | 7 productes |

---

### 3.3 `Clientes.csv` — Maestro de 11.031 clíniques

| Columna | Tipus | Descripció |
|---|---|---|
| `Id. Cliente` | int | ID de la clínica. Clau de join amb `Ventas.csv`. **10.994 IDs únics** (37 duplicats eliminats en el pipeline — errors d'exportació). |
| `Cod_Postal` | int | Codi postal de la clínica. Permet anàlisi geogràfica i agregació per zona. |
| `Provincia` | string | Província espanyola. **53 províncies** cobertes. Top 5: Madrid (1.814), Barcelona (1.197), València (753), Sevilla (480), Alacant (398). |

**Limitació important:** el maestro de clients és molt espartà. No inclou tipus de clínica, especialitat, nombre de cadires, ni cap atribut qualitatiu. Tota la segmentació de comportament s'ha d'inferir de les dades transaccionals i del potencial.

**Nota sobre duplicats:** 37 clients apareixien dues vegades al maestro (alguns amb el mateix codi postal, altres amb codis postals lleugerament diferents — probablement multi-seu o error de migració de CRM). El pipeline elimina els duplicats conservant la primera fila disponible.

---

### 3.4 `Potencial.csv` — 33.093 files · **El dataset més valuós per al repte**

Conté l'estimació del **gasto anual potencial** de cada clínica en cada família de producte. Probablement calculat per Inibsa a partir de factors com nombre de cadires, tipus de clínica, zona geogràfica i benchmarks del sector.

| Columna | Tipus | Descripció |
|---|---|---|
| `Id.Cliente` | int | ID de la clínica. **11.031 clíniques úniques** (totes les del maestro). |
| `Familia` | string | Família de producte en text real (no anonimitzat): `Anestesia`, `Biomateriales`, `Bioseguridad`. |
| `Categoria Productos` | string | Categoria: `Categoria C1`, `Categoria C2`, `Categoria T1`. |
| `Potencial_EUR_anual` | float | **Gasto anual estimat en euros** d'aquesta clínica en aquesta família. Rang: 0 → 208.065€. Mitjana: 3.180€. |

**Per què és tan valuós:** permet calcular el **share of wallet** (quota de mercat dins el client):

```
share_of_wallet = vendes_reals_ultims_12m / potencial_EUR_anual
```

Si una clínica té potencial de 4.000€/any en anestèsia i ens ha comprat 700€ els últims 12 mesos → share of wallet = 17,5%. Això vol dir que el 82,5% del seu consum va a la competència. Sense aquest dataset, aquesta inferència seria impossible.

**Mapeo família potencial ↔ família productes (anonimitzada):**

| Familia (Potencial) | Familia_H (Productos) | Bloc |
|---|---|---|
| Anestesia | Familia C1 | Commodities |
| Bioseguridad | Familia C2 | Commodities |
| Biomateriales | Familia T1 + Familia T2 | Productes Tècnics |

---

### 3.5 `Campañas.csv` — 10 campanyes promocionals (2021–2025)

| Columna | Descripció |
|---|---|
| `Campaña` | ID de campanya (format `ANY_N`, ex: `2024_1`) |
| `Fecha inicio` | Inici de la campanya |
| `Fecha fin` | Final de la campanya |

Les 10 campanyes registrades:

| Campanya | Inici | Fi | Dies |
|---|---|---|---|
| 2021_1 | 24/11/2021 | 26/11/2021 | 3 |
| 2022_1 | 14/03/2022 | 26/03/2022 | 13 |
| 2022_2 | 24/11/2022 | 25/11/2022 | 2 |
| 2023_1 | 12/09/2023 | 15/09/2023 | 4 |
| 2023_2 | 24/11/2023 | 24/11/2023 | 1 |
| 2024_1 | 04/03/2024 | 16/03/2024 | 13 |
| 2024_2 | 07/06/2024 | 09/06/2024 | 3 |
| 2024_3 | 12/09/2024 | 15/09/2024 | 4 |
| 2024_4 | 28/11/2024 | 29/11/2024 | 2 |
| 2025_1 | 28/11/2025 | 28/11/2025 | 1 |

**Per què importa:** durant campanyes, les vendes presenten **pics artificials** (descomptes, agrupació de demanda, compres anticipades). Si s'utilitzen aquestes dates per calcular el cicle de reposició o el baseline de consum, els models quedaran contaminats. El pipeline marca totes les línies de venda amb el flag `en_campana` per poder excloure-les del baseline quan calgui.

---

## 4. Master datasets (`master_commodities.csv` + `master_technicals.csv`)

El pipeline `build_dataset.py` unifica tots els datasets i separa per bloc analític:
- **`data/master_commodities.csv`** — productes de consum recurrent (Anestèsia + Bioseguretat)
- **`data/master_technicals.csv`** — productes tècnics (Biomaterials)

Cada dataset té **162.546 files × 21 columnes** en total, una per línia de venda.

### Columnes i descripció

```
# ── IDs — ELIMINAR ABANS DE QUALSEVOL MODEL ──────────────────────
Num.Fact          # ID de factura (agrupa línies del mateix pedido)
Fecha             # Data exacta — usar les features temporals en lloc d'això
Id_Cliente        # ID clínica dental
Id_Producto       # ID producte

# ── Info producte ────────────────────────────────────────────────
Bloque_Analitico  # 'Commodities' | 'Productos Técnicos'
Categoria_H       # Categoria anonimitzada: Categoria C1, C2, T1
Familia_H         # Família anonimitzada: Familia C1, C2, T1, T2
Familia_Potencial # Família real mapeada: Anestesia | Bioseguridad | Biomateriales
es_commodity      # 1 = commodity, 0 = tècnic

# ── Info client ──────────────────────────────────────────────────
Cod_Postal        # Codi postal (NaN en 623 clients no trobats al maestro)
Provincia         # Província espanyola

# ── Transacció ───────────────────────────────────────────────────
Unidades          # Quantitat (negatiu = devolució)
Valores_H         # Import en EUR (anonimitzat en escala però real)
es_devolucion     # 1 si Unidades < 0
en_campana        # 1 si la venda cau dins d'una campanya promocional

# ── Potencial de mercat ──────────────────────────────────────────
Potencial_EUR_anual  # Gasto anual estimat de la clínica en aquesta família

# ── Features temporals — usar aquestes en model, no Fecha ────────
anyo              # Any de la venda
mes               # Mes (1-12)
trimestre         # Trimestre (1-4)
dia_semana        # Dia de la setmana (0=dilluns, 6=diumenge)
dia_anyo          # Dia de l'any (1-365)
```

### Per usar en un model

```python
import pandas as pd

df = pd.read_csv('data/master_commodities.csv')

# Eliminar IDs i data raw
X = df.drop(columns=['Num.Fact', 'Fecha', 'Id_Cliente', 'Id_Producto'])
```

---

## 5. Lògica analítica proposada

### 5.1 Mètrica base: agregació mensual per (client, família)

Tota l'analítica s'ha de construir sobre una vista agregada:

```
per cada (Id_Cliente, Familia_Potencial, any-mes):
    - euros_venuts = sum(Valores_H) excloent devolucions i campanyes
    - num_pedidos = count(Num.Fact únics)
    - unitats = sum(Unidades)
```

### 5.2 Motor Commodities — Segmentació i cicle de reposició

**Step 1: Calcular share of wallet per client-família**
```
share_of_wallet_12m = sum(Valores_H últims 12m) / Potencial_EUR_anual
```

**Step 2: Classificar el client**

| Segment | Criteri |
|---|---|
| `fidel` | share > 70%, compra regular |
| `promiscu` | share entre 20-70%, compra regular però parcial |
| `marginal` | share < 20%, compra molt per sota del potencial |
| `en_risc` | era fidel o promiscu, però tendència decreixent els últims 3 mesos |
| `nou` | menys de 3 mesos d'historial |
| `perdut` | sense compra els últims 90 dies, tenia historial previ |

**Step 3: Calcular cicle de reposició (només per fidels i promiscus)**
```
cicle_mig_dies = mitjana(dies entre pedidos consecutius)
desviació_std = std(dies entre pedidos)
próxim_pedido_esperat = data_últim_pedido + cicle_mig_dies
```

**Step 4: Generar alerta**
- Si avui > `próxim_pedido_esperat` → **alerta de reposició**
- Si avui > `próxim_pedido_esperat + 1.5 * desviació_std` → **alerta de risc de fuga**
- Si client és promiscu i `próxim_pedido_esperat` és avui ± 3 dies → **finestra de captura**

### 5.3 Motor Tècnics — Detecció d'anomalia

**Step 1: Calcular patró individual**
```
freq_mig_dies = mitjana(dies entre pedidos) — excloent campanyes
vol_mig_eur = mitjana(euros per pedido)
std_freq = desviació estàndard de la freqüència
```

**Step 2: Classificar el client tècnic**
- `actiu_regular`: ≥ 4 pedidos en els últims 12m
- `actiu_esporàdic`: 1-3 pedidos en els últims 12m (patró vàlid, no alarmar fàcilment)
- `inactiu_recent`: sense pedido els últims X dies (X > `freq_mig + 2*std_freq`)

**Step 3: Generar alerta**
- Silenci > `freq_mig + 1*std` → **alerta groga** (vigilar)
- Silenci > `freq_mig + 2*std` → **alerta vermella** (risc real de pèrdua)
- Per a esporàdics: llindar més permissiu (`freq_mig + 3*std`)

### 5.4 Priorització d'alertes

Cada alerta porta una puntuació de prioritat:

```
prioritat = impacte_economic_potencial × urgència_temporal × probabilitat_conversió
```

On:
- `impacte_economic_potencial` = `Potencial_EUR_anual × (1 - share_of_wallet)` (euros recuperables)
- `urgència_temporal` = dies de retard / cicle_mig (quant s'ha passat del moment òptim)
- `probabilitat_conversió` = funció del segment i historial de conversions passades

### 5.5 Output d'una alerta (format mínim)

```json
{
  "id_client": 4523,
  "provincia": "Barcelona",
  "familia": "Anestesia",
  "tipus_alerta": "risc_fuga",
  "segment_client": "fidel",
  "dies_sense_compra": 42,
  "cicle_habitual_dies": 28,
  "share_of_wallet_12m": 0.84,
  "potencial_anual_eur": 3410.04,
  "impacte_recuperable_eur": 546.0,
  "urgencia": "alta",
  "canal_recomanat": "delegat",
  "motiu_explicat": "Client fidel d'Anestèsia. El seu cicle habitual és de 28 dies. Porta 42 dies sense comprar (14 dies de retard). Share of wallet els últims 12m: 84%. Possible inici de fuga.",
  "data_alerta": "2025-10-15"
}
```

---

## 6. Pipeline de dades (`build_dataset.py`)

El script `build_dataset.py` executa tots els passos de neteja i unió:

1. **Parseja formats numèrics** espanyols (`2.223,12` → `2223.12`)
2. **Converteix dates** al format estàndard pandas
3. **Marca devolucions** (`es_devolucion = 1` si Unidades < 0)
4. **Marca períodes de campanya** (`en_campana = 1`) per poder excloure'ls del baseline
5. **Join productes** → afegeix Bloque_Analitico, Categoria_H, Familia_H, es_commodity
6. **Deduplicació del maestro de clients** (37 IDs duplicats eliminats, keep='first')
7. **Join clients** → afegeix Cod_Postal, Provincia
8. **Mapeja famílies** (Familia_H anonimitzada → Familia_Potencial en text real)
9. **Join potencial** → afegeix Potencial_EUR_anual
10. **Extreu features temporals** → anyo, mes, trimestre, dia_semana, dia_anyo
11. **Assertions de qualitat**: comprova que cap join ha multiplicat files

### Execució

```bash
python3 build_dataset.py
# Output: data/master_commodities.csv + data/master_technicals.csv
```

### Dependències

```bash
pip install pandas numpy
```

---

## 7. Requisits funcionals del sistema final

- **Periodicitat diària**: recalcular totes les alertes cada dia
- **Unitat de decisió**: `(client, família, data)` — una alerta per combinació rellevant
- **Lògica diferenciada**: dos motors separats (Commodities vs Tècnics)
- **Alertes interpretables**: cada alerta inclou el motiu en text llegible
- **Priorització**: ordenar per impacte econòmic × urgència
- **Canal adaptatiu**: delegat / televenda / automatització de màrqueting (HubSpot)
- **Arquitectura standalone**: operable sense CRM, integrable en el futur
- **Escalabilitat geogràfica**: dissenyat per Espanya, extensible a Portugal i altres

---

## 8. Mètriques d'èxit del sistema

- **Taxa de conversió d'alertes**: % d'alertes que acaben en compra
- **Taxa de recuperació**: % de clients en risc que recuperen el seu patró de compra
- **Reducció de falsos positius**: alertes generades sense necessitat real
- **Millora progressiva**: el sistema aprèn dels resultats registrant alerta → acció → resultat

---

## 9. Estructura de fitxers del projecte

```text
/
├── README.md                                  # Aquest document
├── build_dataset.py                           # Pipeline inicial de dades
├── eda_dashboard.py                           # Dashboard d'Anàlisi Exploratori de Dades
├── data_cleaning_analysis.ipynb               # Notebook de neteja i anàlisi de dades
├── client_product_annual_behavior.ipynb       # Anàlisi de comportament anual per client
├── data/
│   ├── master_commodities.csv                 # Dades de productes commodity (sortida build_dataset.py)
│   ├── master_technicals.csv                  # Dades de productes tècnics (sortida build_dataset.py)
│   └── raw/                                   # Fitxers originals exportats
│       ├── Datasets.xlsx - Campañas.csv
│       ├── Datasets.xlsx - Clientes.csv
│       ├── Datasets.xlsx - Potencial.csv
│       ├── Datasets.xlsx - Productos.csv
│       └── Datasets.xlsx - Ventas.csv
├── info/                                      # Informació i documentació addicional
└── scratch/                                   # Scripts de proves i experiments
    ├── clean_data.py
    ├── generate_client_nb.py
    ├── generate_client_nb_optimized.py
    └── generate_nb.py
```