# Smart Demand Signals — Explicació del Sistema

> Sistema diari d'alertes comercials que li diu a l'equip de vendes **a qui trucar avui, per què, i quant impacte econòmic té**.

---

## 1. Què fa aquest sistema?

Cada dia, el sistema analitza **totes les clíniques** i les seves compres dels últims 5 anys, i genera una **llista prioritzada d'alertes** que respon a 3 preguntes:

**A qui contactar avui? Per quina família de producte? Per quin motiu?**

L'output és una llista d'alertes, cadascuna amb:
- Client i província
- Família de producte (Anestèsia, Bioseguretat)
- Tipus d'alerta (què passa)
- Segment del client (qui és)
- Impacte econòmic estimat (quants euros estem perdent)
- Prioritat (per on començar)
- Canal recomanat (delegat o televenda)
- Motiu explicat en text (per què s'ha generat)

---

## 2. Per què NO fem servir Machine Learning?

**Perquè no tenim la variable que voldríem predir.**

Per entrenar un model ML necessites exemples de "fuga" perquè el model aprengui el patró. Però nosaltres **no sabem quins clients han fugit realment**. Sabem quins han deixat de comprar a Inibsa, però no sabem si:
- S'han passat a la competència (fuga real)
- Han reduït activitat (tancat, jubilat, menys pacients)
- Senzillament encara no toca el seu cicle de compra

Si entrenéssim un model amb un target fabricat ("deixa de comprar = fuga"), estaríem aprenent soroll, no senyal real. **El jurat d'un hackathon ho veuria.**

### La solució real: estadística descriptiva + regles de negoci

En lloc de "predir" el futur, el sistema **mesura el present** contra el que seria "normal" per a cada client:
- Quant hauria de consumir basant-se en el seu potencial estimat → **share of wallet**
- Quan hauria de tornar a comprar basant-se en el seu historial → **cicle de reposició**
- Si està comprant menys del normal últimament → **tendència**
- Si porta massa temps sense comprar → **fuga / perdut**

No cal ML per a això. ML afegiria complexitat i opacitat sense guany real en un problema on les regles de negoci són clares i interpretables.

---

## 3. Com funciona? (la lògica en 5 minuts)

El sistema s'executa diàriament i fa aquests passos:

```
1. Carregar vendes, clients, productes, potencial
2. Calcular share of wallet (quants diners del client captem?)
3. Calcular cicle de reposició (cada quants dies compra?)
4. Segmentar cada client-família (qui és?)
5. Generar alertes (què li passa?)
6. Prioritzar (per on comencem?)
```

**Tot es recalcula des de zero cada dia.** Si un client fa una compra gran, l'endemà el sistema ho veu i el reclassifica automàticament. Si un client en risc torna a comprar amb normalitat, l'alerta desapareix sola.

---

## 4. Els dos blocs de negoci

El negoci d'Inibsa té **dues dinàmiques de compra completament diferents**, i cal tractar-les per separat.

### Bloc A — Commodities (Anestèsia + Bioseguretat) ✅ FET

Productes de consum recurrent com anestèsia local, agulles i desinfectants. Tota clínica en necessita, independentment de l'especialitat. És com el paper d'impressora: s'ha de comprar cada X temps.

**El repte aquí no és "si comprarà" sinó "quan comprarà i a qui".** Una clínica pot:
- Comprar-ho TOT a Inibsa → **fidel**
- Repartir entre Inibsa i competència → **promiscu**
- Comprar molt poc (tot i tenir potencial) → **marginal**

**Com ho resolem:** mirem el potencial anual estimat (dada que Inibsa ens dona), mirem quant han comprat a Inibsa els últims 12 mesos, i calculem el % de wallet que captem. Amb això classifiquem el client.

### Bloc B — Productes Tècnics (Biomaterials) ❌ PENDENT

Productes de compra irregular que depenen del tipus de cas clínic (implantologia, regeneració òssia). Un implantòleg pot comprar cada 6 setmanes o cada 6 mesos, depenent de la seva agenda.

Aquí el risc no es detecta per cicle sinó per **desviació del patró individual**: si un client que demanava cada 6 setmanes porta 14 setmanes sense fer-ho, alguna cosa ha canviat.

---

## 5. Com classifiquem cada client?

Per cada (client, família) — per exemple "Clínica Dental ABC + Anestèsia" — el sistema li assigna **un segment**. L'ordre de decisió és:

### 1. `nou` — < 90 dies d'historial
Acaba de començar a comprar. Cal fer seguiment per consolidar-lo.

### 2. `fugat` — > 1 any sense comprar
Ha desaparegut. Requereix trucada de recuperació directa per delegat.
Si torna a comprar, el sistema el reclassifica sol.

### 3. `perdut` — dinàmic segons cicle
- Cicle fiable (≥3 compres): > `max(180, cicle × 2.5)` dies sense comprar
- Cicle poc fiable (1-2 compres): > `max(365, cicle × 3)` dies
- Sense cicle: > 180 dies

Ha deixat de comprar però no fa tant com per ser "fugat".

### 4. `en_risc` — tendència decreixent
Els últims 3 mesos està comprant molt menys que la seva mitjana anual (share_3m anualitzat < share_12m × 0.75). Senyal més primerenca de possible fuga. **Requereix intervenció urgent.**

### 5. `fidel` — share of wallet > 70%
Compra la major part del seu potencial a Inibsa.

### 6. `promiscu` — share entre 20% i 70%
Reparteix la compra entre Inibsa i competència. **Oportunitat de captura.**

### 7. `marginal` — share < 20%
Compra molt per sota del seu potencial. Cal investigar per què.

---

## 6. Com calculem el share of wallet?

```
share_of_wallet = vendes_últims_12_mesos / Potencial_EUR_anual
```

**Exemple:** potencial 4.000€/any, ha comprat 700€ → share = 17.5%. El 82.5% va a la competència.

**Límit:** si el share dona > 100%, el capem a 100%. Si el client compra més del potencial, està crescut.

**Gap (euros no capturats):** `gap = Potencial_anual - vendes_12m` (mai negatiu).

---

## 7. Com calculem el cicle de reposició?

Agafem totes les dates dels seus pedidos, les ordenem, i calculem els intervals entre una compra i la següent.

```
cicle_mig = mitjana(dies entre pedido i pedido)
cicle_std = desviació estàndard
pròxim_pedido = data_últim_pedido + cicle_mig
```

Fiabilitat del cicle segons quants intervals tinguem:

| Intervals | Fiabilitat |
|---|---|
| 0 (1 sol pedido) | ❌ Sense cicle. Llindar permissiu |
| 1-2 | ⚠️ Poc fiable. Llindar 3× el cicle |
| ≥3 | ✅ Fiable. Llindar 2.5× el cicle |

---

## 8. Les 8 alertes

### Alertes del briefing diari (pestanya principal)

| Alerta | Quan surt | Per a qui | Què fer |
|---|---|---|---|
| **finestra_captura** | Client **promiscu** amb proper pedido ara (±3-14 dies segons cicle) o ja en retard | 👤 Delegat | Trucar ara per robar quota a la competència |
| **risc_fuga** | Client **fidel** amb retard crític (z > 2.5σ) o client **en declivi** | 👤 Delegat | Aturada. Si no s'actua, el client marxarà |
| **reposicio_endarrerida** | Client **fidel** amb retard significatiu (1.5σ < z < 2.5σ) | 📞 Televenda | Confirmar estat. Possible inici de fuga |
| **reposicio_preventiva** | Client **fidel** sense retard PERÒ proper pedido en ≤7 dies (stock baixant) | 📞 Televenda | Anticipar reposició |
| **reposicio_pendent** | Client **fidel** amb lleu retard (z < 1.5σ) | 📞 Televenda | Rutina de seguiment |
| **oportunitat_captura** | Client **marginal** (share < 20%) | 📞 Televenda | Investigar per què no compra més |
| **monitoritzar** | Client **nou** (< 90 dies) | 📞 Televenda | Consolidar com a fidel |
| **info** | Sense dades de cicle | 📞 Televenda | Contacte proactiu |

### Pestanya separada: Fugats

| Alerta | Quan surt | Per a qui | Què fer |
|---|---|---|---|
| **fugat** | > 1 any sense comprar | 👤 Delegat | Recuperació directa |

### Alerta de baixa prioritat

| Alerta | Quan surt | Per a qui | Què fer |
|---|---|---|---|
| **perdut** | Entre threshold dinàmic i 365 dies | 📞 Televenda | Reactivació, baixa probabilitat |

---

## 9. Com es prioritza?

Totes les alertes es barregen en una **única llista ordenada per prioritat**:

```
prioritat = impacte_econòmic × urgència × probabilitat_de_conversió
```

### Impacte econòmic
```
impacte = Potencial_anual × (1 - share_of_wallet)
```
Per fugats: potencial × 0.8. Per perduts: potencial × 0.5.

### Urgència temporal
**Per retard:** `max(0.1, min(1, dies_retard / cicle))` — si el retard ≥ 1 cicle, urgència màxima.
**Per stock baix (fidels):** `max(0, 1 - dies_stock / 14)` — si stock = 0, urgència màxima.

L'urgència final = **màxim** entre retard i stock.

### Probabilitat de conversió

| Segment | prob | Per què |
|---|---|---|
| `en_risc` | 0.9 | Si s'actua a temps, encara es pot salvar |
| `fidel` | 0.8 | Ja compra a Inibsa, només cal recordatori |
| `promiscu` | 0.6 | Es pot persuadir |
| `nou` | 0.4 | Incert |
| `marginal` | 0.2 | Difícil de convertir |
| `fugat` | 0.15 | Val la pena intentar |
| `perdut` | 0.05 | Recuperar és molt difícil |

### Exemple real

| Alerta | Gap | Urgència | Prob | Prioritat |
|---|---|---|---|---|
| `finestra_captura` (promiscu, 19k gap) | 19.307€ | 0.1 | 0.6 | **1.158** |
| `reposicio_preventiva` (fidel, stock 2 dies) | 2.481€ | 0.86 | 0.8 | **1.701** |
| `risc_fuga` (fidel, retard 53 dies) | 239€ | 1.0 | 0.8 | **191** |
| `reposicio_pendent` (fidel, lleu retard) | 22€ | 0.3 | 0.8 | **5** |

Un fidel amb stock a punt d'esgotar-se pot tenir més prioritat que un promiscu amb molt gap però poca urgència.

---

## 10. Com funciona a la pràctica?

```bash
# Generar alertes per avui
python3 commodities/commodities_engine.py

# Dashboard interactiu
streamlit run commodities/daily_briefing.py
```

El dashboard mostra:
- **📋 Briefing del Dia**: alertes prioritzades (sense fugats), botó "✅ Tractada"
- **🚨 Fugats**: clients > 1 any sense comprar, botó "✅ Recuperat"

Estat de tractament guardat a `treated_alerts.json` — persisteix entre sessions.

---

## 11. Tecnologia i dependències

- **Python 3.10+**
- Pandas, NumPy (càlculs)
- Streamlit (dashboard)
- Matplotlib, Seaborn (plots)

```bash
pip install pandas numpy streamlit matplotlib seaborn
```

### 3 fitxers .py

| Fitxer | Què fa |
|---|---|
| `commodities/commodities_engine.py` | Tota la lògica: càrrega, càlculs, segmentació, alertes, priorització |
| `commodities/daily_briefing.py` | Dashboard Streamlit per veure i gestionar alertes |
| `commodities/analyse_commodities.py` | Genera 8 plots i estadístiques per debug |

---

## 12. Resum executiu

> **Què hem construït?**
> Un sistema que cada dia analitza automàticament totes les clíniques d'Inibsa i genera una llista prioritzada de "a qui trucar avui" amb el motiu i l'impacte econòmic.
>
> **Per què estadística i no IA?**
> Perquè no sabem quins clients han fugit realment (no veiem la competència). Un model d'IA aprendria soroll. Amb estadística + regles de negoci, tot és explicable i traçable.
>
> **Què fa diferent?**
> 1. Sap quant hauria de consumir cada clínica (potencial) i quant consumeix a Inibsa → **share of wallet**
> 2. Sap cada quants dies compra cada client → **cicle de reposició**
> 3. Detecta canvis de tendència → **avisa abans que el client marxi**
> 4. Prioritza per impacte econòmic × urgència → **saps per on començar**
>
> **Resultats (només commodities):**
> - 2.504 alertes/dia, 365 finestres de captura (oportunitats immediates)
> - Gap total recuperable: **1.159.000 €/any**
> - 1.022 clients fugats identificats per a recuperació directa
>
> **Quant de temps costa?** L'execució diària triga ~20 segons en un portàtil.
