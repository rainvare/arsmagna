
# 🔮 Ars Magna Scientiarum

*Cartografiando los territorios desconocidos del conocimiento humano.*

Un motor lulliano para el descubrimiento sistemático de nuevas ciencias. Basado en el *Ars Magna* (1305) de Ramon Llull, refactorizado para operar sobre el mapa completo de disciplinas científicas usando datos bibliométricos reales de OpenAlex.

---


## 🧠 ¿Qué hace?

**Ars Magna Scientiarum** es un motor de descubrimiento científico que:

1. **Mapea todas las ciencias conocidas**  
   Ingiere la jerarquía completa de conceptos de OpenAlex (~65.000 disciplinas)

2. **Aplica operadores combinatorios lullianos**  
   Genera hipótesis de nuevas disciplinas interdisciplinarias

3. **Valida contra datos reales**  
   Analiza co-ocurrencia en más de 250M publicaciones científicas

4. **Clasifica territorios científicos**  
   - Established  
   - Emergent  
   - Niche  
   - Incipient  
   - Virgin Territory

5. **Calcula plausibilidad**  
   Basado en:
   - Superposición ontológica  
   - Transferibilidad metodológica  
   - Distancia en el grafo  

---

## ⚙️ Estado actual del proyecto

✅ Pipeline funcional de ingestión y enriquecimiento  
✅ Motor de operadores lullianos implementado  
✅ Sistema de scoring de plausibilidad  
✅ Cache de respuestas LLM para eficiencia  
✅ Interfaz conversacional con Streamlit  
✅ Demo desplegada en Hugging Face Spaces  

👉 Demo: https://huggingface.co/spaces/Rainvare/ars-magna-scientiarum  

---

## 🧩 Los 6 operadores lullianos

| Operador | Acción | Ejemplo |
|---|---|---|
| **Combinatio** | Combina disciplinas en igualdad | Biología + Computación → Bioinformática |
| **Subordinatio** | Aplica métodos de A a B | Física → Biología → Biofísica |
| **Mediatio** | Encuentra disciplina puente | Economía ↔ Neurociencia → Neuroeconomía |
| **Amplificatio** | Expande un método | Cladística → Lingüística → Lingüística filogenética |
| **Quaestio** | Transfiere preguntas fundamentales | Simetrías → Redes sociales → Física de redes |
| **Inversio** | Invierte preguntas | Adaptación → Diseño biofílico |

---

## 🏗️ Arquitectura

```

spike_openalex.py     → Descarga TODOS los conceptos de OpenAlex
enrich_nodes.py       → Enriquecimiento semántico con LLM
core/engine.py        → Operadores + scoring de plausibilidad
app.py                → Interfaz conversacional (Streamlit)

data/
science_graph.json
science_graph_enriched.json
enrichment_cache.json
spike_report.md

````

---

## 🔄 Pipeline de datos

1. **OpenAlex → Grafo base**  
   ~65K conceptos con jerarquía y relaciones

2. **LLM → Grafo enriquecido**  
   Cada disciplina incluye:
   - objetos de estudio  
   - métodos  
   - supuestos ontológicos  
   - preguntas fundamentales  

3. **Co-ocurrencia → Evidencia empírica**  
   Relación entre disciplinas en publicaciones reales

4. **Engine → Generación de hipótesis**  
   Nuevas ciencias con ranking y evidencia

---

## 🚀 Setup

```bash
# Clonar repositorio
git clone https://github.com/rainvare/ars-magna-scientiarum.git
cd ars-magna-scientiarum

# Instalar dependencias
pip install -r requirements.txt

# 1. Descargar mapa de ciencias
python spike_openalex.py

# 2. Enriquecer nodos (requiere API key de Groq)
export GROQ_API_KEY="your-key"
python enrich_nodes.py

# 3. Ejecutar app
streamlit run app.py
````


---

## 🔭 Visión

Una máquina de pensamiento capaz de:

* Explorar el espacio completo de las ciencias posibles
* Detectar campos emergentes antes de que existan
* Servir como copiloto para investigación, estrategia e innovación

---

**Built by Rainvare** | 2026
*A thinking machine navigating the graph of human knowledge.*

-----------------------------------------------------



## 🧠 What It Does

**Ars Magna Scientiarum** is a scientific discovery engine that:

1. **Maps all known sciences**
   Ingests the full OpenAlex concept graph (~65,000 disciplines)

2. **Applies Lullian combinatorial operators**
   Generates hypotheses for new interdisciplinary fields

3. **Validates against real data**
   Uses co-occurrence across 250M+ publications

4. **Classifies scientific territories**

   * Established
   * Emergent
   * Niche
   * Incipient
   * Virgin Territory

5. **Scores plausibility**
   Based on:

   * Ontological overlap
   * Methodological transferability
   * Graph distance

---

## ⚙️ Current Status

✅ End-to-end data pipeline working
✅ Lullian operator engine implemented
✅ Plausibility scoring system
✅ LLM enrichment with caching
✅ Streamlit conversational interface
✅ Live demo on Hugging Face Spaces

👉 Demo: [https://huggingface.co/spaces/Rainvare/ars-magna-scientiarum](https://huggingface.co/spaces/Rainvare/ars-magna-scientiarum)

---

## 🧩 The Six Operators

| Operator         | Action                         | Example                                             |
| ---------------- | ------------------------------ | --------------------------------------------------- |
| **Combinatio**   | Merge disciplines equally      | Biology + Computation → Bioinformatics              |
| **Subordinatio** | Apply methods of A to B        | Physics → Biology → Biophysics                      |
| **Mediatio**     | Find bridging discipline       | Economics ↔ Neuroscience → Neuroeconomics           |
| **Amplificatio** | Extend a method                | Cladistics → Linguistics → Phylogenetic Linguistics |
| **Quaestio**     | Transfer fundamental questions | Symmetry → Social networks → Network Physics        |
| **Inversio**     | Invert questions               | Adaptation → Biophilic Design                       |

---

## 🏗️ Architecture

```
spike_openalex.py     → Downloads all OpenAlex concepts
enrich_nodes.py       → LLM semantic enrichment
core/engine.py        → Operators + plausibility scoring
app.py                → Streamlit conversational UI

data/
  science_graph.json
  science_graph_enriched.json
  enrichment_cache.json
  spike_report.md
```

---

## 🔄 Data Pipeline

1. **OpenAlex → Base Graph**
   ~65K concepts with hierarchy & relations

2. **LLM → Enriched Graph**
   Each node includes:

   * objects of study
   * methods
   * ontological assumptions
   * fundamental questions

3. **Co-occurrence → Empirical Evidence**
   Links disciplines via publications

4. **Engine → Hypothesis Generation**
   Ranked, evidence-backed new sciences

---

## 🚀 Setup

```bash
git clone https://github.com/rainvare/ars-magna-scientiarum.git
cd ars-magna-scientiarum

pip install -r requirements.txt

python spike_openalex.py

export GROQ_API_KEY="your-key"
python enrich_nodes.py

streamlit run app.py
```

---

## 🧠 Theoretical Foundation


* Computational refactoring of Ars Magna
* Scientific plausibility model
* Ontology of disciplines
* Links to knowledge systems & agentic architectures

---

## 🔭 Vision

A thinking system that:

* Explores the full space of possible sciences
* Detects emerging fields before they exist
* Acts as a co-pilot for research, strategy, and innovation

---

**Built by Rainvare** | 2026
*A thinking machine navigating the graph of human knowledge.*

```
