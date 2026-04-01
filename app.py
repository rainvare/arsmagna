"""
Ars Magna Scientiarum — Interfaz Conversacional
================================================
Un Motor Luliano para el Descubrimiento de Ciencias.

v2 — Fixes:
- Correct nx.node_link_graph loading for both "links" and "edges" JSON keys
- Reconstruct L0-L2 edges from node ancestor/related data when filtered edges are sparse
"""

import json
import random
import os
from pathlib import Path
from collections import defaultdict

import streamlit as st
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px

from engine import LullianEngine, Hypothesis, Operator, TerritoryClass
from enricher import enriquecer_lote


# ============================================================
# CONFIGURACIÓN
# ============================================================

DATA_DIR = Path(os.environ.get("ARS_DATA_DIR", "data"))
GRAPH_FILE = DATA_DIR / "science_graph_enriched.json"
FALLBACK_GRAPH = DATA_DIR / "science_graph.json"

TERRITORY_COLORS = {
    "established": "#2E7D32",
    "emergent": "#F57F17",
    "niche": "#1565C0",
    "incipient": "#7B1FA2",
    "virgin_territory": "#D32F2F",
    "implausible": "#757575",
    "unknown": "#9E9E9E",
}

TERRITORY_NAMES = {
    "established": "Establecido",
    "emergent": "Emergente",
    "niche": "Nicho",
    "incipient": "Incipiente",
    "virgin_territory": "Territorio Virgen",
    "implausible": "Implausible",
    "unknown": "Desconocido",
}

TERRITORY_ICONS = {
    "established": "🏛️",
    "emergent": "🌱",
    "niche": "🔬",
    "incipient": "💡",
    "virgin_territory": "🗺️",
    "implausible": "⚠️",
}

OPERATOR_DESCRIPTIONS = {
    "combinatio": (
        "**Combinatio** — Fusionar dos disciplinas en pie de igualdad. "
        "Ambas aportan objetos y métodos a una nueva síntesis."
    ),
    "subordinatio": (
        "**Subordinatio** — Aplicar los métodos de una disciplina "
        "a los objetos de otra. Asimétrico: los métodos dominan."
    ),
    "mediatio": (
        "**Mediatio** — Encontrar una tercera disciplina que sirva "
        "de puente entre dos campos distantes."
    ),
    "amplificatio": (
        "**Amplificatio** — Extender un método propio de un campo "
        "estrecho a otros dominios distantes."
    ),
    "quaestio": (
        "**Quaestio** — Transferir las preguntas fundamentales de "
        "una disciplina al dominio de otra."
    ),
    "inversio": (
        "**Inversio** — Invertir la pregunta central de un campo "
        "y aplicar la pregunta invertida a otro."
    ),
}


# ============================================================
# CARGA DE DATOS (v2 — fixed)
# ============================================================

@st.cache_resource
def load_graph():
    """
    Carga el grafo de conocimiento, filtrado a L0-L2 para rendimiento.
    
    v2 fixes:
    - Handles both "links" and "edges" JSON keys (nx 2.x vs 3.x compat)
    - Reconstructs edges from node-level ancestor/related data when
      the edge filter leaves the graph too sparse
    """
    graph_path = GRAPH_FILE if GRAPH_FILE.exists() else FALLBACK_GRAPH
    if not graph_path.exists():
        st.error(
            f"No se encontró el grafo en {GRAPH_FILE} ni {FALLBACK_GRAPH}. "
            "Ejecutá `python spike_openalex.py` primero."
        )
        st.stop()

    with open(graph_path) as f:
        data = json.load(f)

    # ---- Step 1: Filter nodes to L0-L2 ----
    keep_layers = {"L0:Navigation", "L1:Discipline", "L2:Subdiscipline"}
    keep_ids = set()
    filtered_nodes = []
    # Keep a map of node data for edge reconstruction
    node_data_map = {}

    for node in data.get("nodes", []):
        if node.get("layer") in keep_layers:
            node_id = node.get("id", "")
            keep_ids.add(node_id)
            filtered_nodes.append(node)
            node_data_map[node_id] = node

    # ---- Step 2: Filter edges (handle both "links" and "edges" keys) ----
    raw_links = data.get("links", data.get("edges", []))
    
    filtered_links = []
    for link in raw_links:
        src = link.get("source", "")
        tgt = link.get("target", "")
        if src in keep_ids and tgt in keep_ids:
            filtered_links.append(link)

    # ---- Step 3: Build the graph ----
    # We build manually instead of using node_link_graph to avoid
    # the "links" vs "edges" key issue across networkx versions
    G = nx.DiGraph()

    for node in filtered_nodes:
        node_id = node.pop("id")  # remove id from attrs
        G.add_node(node_id, **node)
        node["id"] = node_id  # restore for later use

    for link in filtered_links:
        src = link.get("source", "")
        tgt = link.get("target", "")
        edge_attrs = {k: v for k, v in link.items()
                      if k not in ("source", "target")}
        G.add_edge(src, tgt, **edge_attrs)

    edges_from_json = G.number_of_edges()

    # ---- Step 4: Reconstruct edges from node-level ancestor data ----
    # OpenAlex nodes store their ancestors as a list within each concept.
    # When spike_openalex.py built the graph, it created edges for these,
    # but many point to L3+ nodes that got filtered out.
    # However, the ancestor LIST inside each node still contains L0/L1 refs.
    # We can reconstruct those edges here.
    #
    # Also reconstruct related_concepts edges between L0-L2 nodes.
    
    reconstructed = 0

    for node in filtered_nodes:
        node_id = node.get("id", "")
        
        # Reconstruct ancestor edges (child → parent hierarchy)
        ancestors = node.get("ancestors", [])
        if isinstance(ancestors, list):
            for anc in ancestors:
                if isinstance(anc, dict):
                    anc_id = anc.get("id", "").replace("https://openalex.org/", "")
                elif isinstance(anc, str):
                    anc_id = anc.replace("https://openalex.org/", "")
                else:
                    continue
                    
                if anc_id in keep_ids and anc_id != node_id:
                    if not G.has_edge(node_id, anc_id):
                        G.add_edge(node_id, anc_id, type="is_subconcept_of")
                        reconstructed += 1

        # Reconstruct related_concepts edges
        related = node.get("related_concepts", [])
        if isinstance(related, list):
            for rel in related:
                if isinstance(rel, dict):
                    rel_id = rel.get("id", "").replace("https://openalex.org/", "")
                    score = rel.get("score", 0)
                elif isinstance(rel, str):
                    rel_id = rel.replace("https://openalex.org/", "")
                    score = 0
                else:
                    continue
                    
                if rel_id in keep_ids and rel_id != node_id:
                    if not G.has_edge(node_id, rel_id):
                        G.add_edge(node_id, rel_id,
                                   type="related_to", score=score)
                        reconstructed += 1

    # Log the reconstruction stats
    total_edges = G.number_of_edges()
    print(f"[Ars Magna] Graph loaded: {G.number_of_nodes()} nodes")
    print(f"[Ars Magna] Edges from JSON: {edges_from_json}")
    print(f"[Ars Magna] Edges reconstructed from node data: {reconstructed}")
    print(f"[Ars Magna] Total edges: {total_edges}")

    # Count connected components
    undirected = G.to_undirected()
    n_components = nx.number_connected_components(undirected)
    largest_cc = max(nx.connected_components(undirected), key=len)
    print(f"[Ars Magna] Connected components: {n_components}")
    print(f"[Ars Magna] Largest component: {len(largest_cc)} nodes")

    return G


@st.cache_resource
def get_engine(_graph):
    return LullianEngine(_graph)


def get_disciplines(G, layers=None):
    if layers is None:
        layers = {"L0:Navigation"}
    return sorted(
        [(nid, d["name"]) for nid, d in G.nodes(data=True)
         if d.get("layer") in layers],
        key=lambda x: x[1]
    )


# ============================================================
# VISUALIZACIÓN
# ============================================================

def render_hypothesis_card(h: Hypothesis, index: int):
    icon = TERRITORY_ICONS.get(h.territory_class, "❓")
    color = TERRITORY_COLORS.get(h.territory_class, "#9E9E9E")
    territory_name = TERRITORY_NAMES.get(h.territory_class, h.territory_class)

    with st.expander(
        f"{icon} **{h.suggested_name}** — "
        f"_{h.operator.upper()}_ "
        f"(plausibilidad: {h.plausibility_score:.2f})",
        expanded=(index == 0)
    ):
        st.markdown(
            f'<span style="background-color:{color};color:white;'
            f'padding:2px 10px;border-radius:12px;font-size:0.85em;">'
            f'{territory_name}</span>',
            unsafe_allow_html=True
        )

        st.markdown(f"\n{h.description}")

        if h.mediator_name:
            st.info(f"🔗 **Mediador:** {h.mediator_name}")

        st.caption(h.justification)

        # ----- ENRIQUECIMIENTO GROQ -----
        gd = getattr(h, "groq_data", {})
        if gd:
            st.divider()
            st.markdown("**🧠 Análisis Groq / Llama 3.3**")

            if gd.get("hipotesis_formal"):
                st.info(f"📐 **Hipótesis formal:** {gd['hipotesis_formal']}")

            if gd.get("mecanismo"):
                st.markdown(f"⚙️ **Mecanismo:** {gd['mecanismo']}")

            col_q, col_r = st.columns([3, 1])
            with col_q:
                if gd.get("pregunta_empirica"):
                    st.markdown(
                        f"❓ **Pregunta empírica:** {gd['pregunta_empirica']}"
                    )
            with col_r:
                if gd.get("score_originalidad"):
                    st.metric("Originalidad", f"{gd['score_originalidad']}/10")

            if gd.get("keywords_busqueda"):
                kw_str = "  ".join(
                    f"`{k}`" for k in gd["keywords_busqueda"]
                )
                st.markdown(f"🔍 **Keywords:** {kw_str}")

            if gd.get("disciplinas_auxiliares"):
                st.markdown(
                    "🔗 **Disciplinas auxiliares sugeridas:** "
                    + ", ".join(gd["disciplinas_auxiliares"])
                )

            if gd.get("riesgo_principal"):
                st.warning(f"⚠️ **Riesgo principal:** {gd['riesgo_principal']}")

        # --------------------------------

        if h.research_questions:
            st.markdown("**Preguntas de investigación que genera esta combinación:**")
            for q in h.research_questions:
                st.markdown(f"- {q}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Publicaciones", f"{h.co_occurrence_total:,}")
        with col2:
            st.metric("Recientes (5 años)", f"{h.co_occurrence_recent:,}")
        with col3:
            st.metric("Plausibilidad", f"{h.plausibility_score:.3f}")


def render_territory_map(hypotheses: list[Hypothesis]):
    if not hypotheses:
        return

    data = []
    for h in hypotheses:
        novelty = 1.0 if h.co_occurrence_total == 0 else max(
            0, 1 - h.co_occurrence_total / 100000)
        data.append({
            "nombre": h.suggested_name,
            "plausibilidad": h.plausibility_score,
            "novedad": novelty,
            "territorio": TERRITORY_NAMES.get(h.territory_class, h.territory_class),
            "operador": h.operator,
            "publicaciones": h.co_occurrence_total,
        })

    fig = px.scatter(
        data,
        x="plausibilidad",
        y="novedad",
        color="territorio",
        hover_name="nombre",
        hover_data=["operador", "publicaciones"],
        color_discrete_map={
            TERRITORY_NAMES[v]: TERRITORY_COLORS[v]
            for v in TERRITORY_COLORS if v in TERRITORY_NAMES
        },
        labels={
            "plausibilidad": "Plausibilidad",
            "novedad": "Novedad",
        },
        title="Mapa de Territorios: Plausibilidad × Novedad",
    )
    fig.update_layout(
        height=400,
        template="plotly_dark",
        font=dict(size=12),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_discipline_network(G, selected_nodes=None, depth=1):
    if not selected_nodes:
        return

    nodes_to_show = set(selected_nodes)
    undirected = G.to_undirected()
    for node in selected_nodes:
        if node in undirected:
            for _ in range(depth):
                new_nodes = set()
                for n in nodes_to_show:
                    if n in undirected:
                        new_nodes.update(undirected.neighbors(n))
                nodes_to_show.update(new_nodes)

    nodes_to_show = {
        n for n in nodes_to_show
        if G.nodes[n].get("layer") in (
            "L0:Navigation", "L1:Discipline", "L2:Subdiscipline")
    }

    if len(nodes_to_show) > 200:
        nodes_to_show = {
            n for n in nodes_to_show
            if G.nodes[n].get("layer") in ("L0:Navigation", "L1:Discipline")
        }

    subG = G.subgraph(nodes_to_show)

    try:
        pos = nx.spring_layout(subG.to_undirected(), k=2, iterations=50, seed=42)
    except Exception:
        pos = nx.random_layout(subG)

    edge_x, edge_y = [], []
    for u, v in subG.edges():
        if u in pos and v in pos:
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color="#444"),
        hoverinfo="none", mode="lines"
    )

    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    for node in subG.nodes():
        if node in pos:
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(G.nodes[node].get("name", node))
            layer = G.nodes[node].get("layer", "")

            if node in selected_nodes:
                node_color.append("#FF5722")
                node_size.append(20)
            elif layer == "L0:Navigation":
                node_color.append("#2196F3")
                node_size.append(15)
            elif layer == "L1:Discipline":
                node_color.append("#4CAF50")
                node_size.append(10)
            else:
                node_color.append("#9E9E9E")
                node_size.append(6)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=node_text, textposition="top center",
        textfont=dict(size=8, color="#ddd"),
        hoverinfo="text",
        marker=dict(size=node_size, color=node_color,
                    line=dict(width=1, color="#222"))
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title="Vecindario de Disciplinas",
            showlegend=False, template="plotly_dark", height=500,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        )
    )
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# APP PRINCIPAL
# ============================================================

def main():
    st.set_page_config(
        page_title="Ars Magna Scientiarum",
        page_icon="🔮",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.markdown("""
    <style>
    :root {
      --latte:       #FFF8E7;
      --latte-dark:  #F0E8D0;
      --sangria:     #930500;
      --cornflower:  #95BBEA;
      --corn-dark:   #5A8EC4;
      --corn-pale:   #EAF1FB;
    }
    .stApp                        { background-color: var(--latte) !important; }
    section[data-testid="stSidebar"] > div { background-color: #F5EDD8 !important; }
    
    /* Títulos */
    h1                            { color: var(--sangria) !important; font-family: 'Georgia', serif; }
    h2, h3                        { color: #5A1A1A !important; }
    
    /* Botón primario */
    .stButton > button            { background: var(--sangria) !important; color: var(--latte) !important;
                                    border: none !important; border-radius: 8px !important; }
    .stButton > button:hover      { background: #C41500 !important; }
    
    /* Selectboxes */
    .stSelectbox > div > div      { background: white !important; border-color: rgba(147,5,0,0.25) !important; }
    
    /* Métricas */
    div[data-testid="stMetricValue"] { color: var(--sangria) !important; font-size: 1.2rem; }
    
    /* Bloque Groq */
    .groq-block                   { background: var(--corn-pale); border: 1px solid rgba(149,187,234,0.4);
                                    border-radius: 8px; padding: 12px; }
    
    /* Expanders */
    .stExpander                   { border-color: rgba(147,5,0,0.15) !important;
                                    background: white !important; border-radius: 10px !important; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab"]              { color: #8A7A7A; }
    .stTabs [aria-selected="true"]            { color: var(--sangria) !important;
                                                border-bottom-color: var(--sangria) !important; }
    </style>
    """, unsafe_allow_html=True)

    st.title("🔮 Ars Magna Scientiarum")
    st.caption(
        "*Cartografiando los territorios desconocidos del conocimiento humano* \n"
        "Un motor luliano para el descubrimiento sistemático de nuevas ciencias."
    )

    G = load_graph()
    engine = get_engine(G)

    # ----- SIDEBAR -----
    with st.sidebar:
        st.header("📊 Grafo de Conocimiento")
        total_nodes = G.number_of_nodes()
        total_edges = G.number_of_edges()
        layers = defaultdict(int)
        for _, d in G.nodes(data=True):
            layers[d.get("layer", "unknown")] += 1

        st.metric("Conceptos totales", f"{total_nodes:,}")
        st.metric("Relaciones totales", f"{total_edges:,}")

        st.markdown("**Por capa:**")
        for layer in sorted(layers.keys()):
            st.text(f"  {layer}: {layers[layer]:,}")

        # Show connectivity info
        undirected = G.to_undirected()
        n_components = nx.number_connected_components(undirected)
        largest_cc = max(nx.connected_components(undirected), key=len)
        st.markdown("**Conectividad:**")
        st.text(f"  Componentes: {n_components:,}")
        st.text(f"  Mayor componente: {len(largest_cc):,} nodos")

        st.divider()

        nivel = st.radio(
            "Nivel de disciplinas",
            ["L0 — Campos principales", "L0 + L1 — Con subdisciplinas"],
            index=0,
            help="L0 muestra ~20 grandes campos. L0+L1 suma cientos de disciplinas."
        )
        layers_sel = (
            {"L0:Navigation"}
            if "L0 —" in nivel
            else {"L0:Navigation", "L1:Discipline"}
        )

        st.divider()

        graph_path = GRAPH_FILE if GRAPH_FILE.exists() else FALLBACK_GRAPH
        if graph_path.exists():
            with open(graph_path, "rb") as f:
                st.download_button(
                    label="💾 Descargar grafo JSON",
                    data=f,
                    file_name="science_graph.json",
                    mime="application/json",
                )

        st.divider()

        st.header("📖 Los Seis Operadores")
        for op, desc in OPERATOR_DESCRIPTIONS.items():
            st.markdown(desc, unsafe_allow_html=True)
            st.text("")

    # ----- PESTAÑAS -----
    disciplines = get_disciplines(G, layers=layers_sel)
    tab_explore, tab_surprise, tab_virgin, tab_graph, tab_about = st.tabs([
        "🔍 Explorar", "🎲 Sorpréndeme", "🗺️ Territorios Vírgenes",
        "🕸️ Grafo", "ℹ️ Acerca de"
    ])

    # ----- EXPLORAR -----
    with tab_explore:
        st.header("Explorar Combinaciones")
        st.markdown(
            "Seleccioná dos disciplinas y un operador para generar "
            "hipótesis sobre posibles nuevos campos."
        )

        col1, col2 = st.columns(2)
        disc_options = [(name, nid) for nid, name in disciplines]

        with col1:
            name_a = st.selectbox(
                "Disciplina A",
                options=[name for name, _ in disc_options],
                index=0, key="disc_a"
            )
            id_a = next(nid for name, nid in disc_options if name == name_a)

        with col2:
            name_b = st.selectbox(
                "Disciplina B",
                options=[name for name, _ in disc_options],
                index=min(1, len(disc_options) - 1), key="disc_b"
            )
            id_b = next(nid for name, nid in disc_options if name == name_b)

        operator_choice = st.selectbox(
            "Operador",
            options=["Todos los operadores"] + [op.value.title() for op in Operator],
            index=0,
        )

        if st.button("🔮 Generar Hipótesis", type="primary", use_container_width=True):
            if id_a == id_b:
                st.warning("Seleccioná dos disciplinas diferentes.")
            else:
                with st.spinner("Aplicando combinatoria luliana..."):
                    if operator_choice == "Todos los operadores":
                        hypotheses = engine.explore(id_a, id_b)
                    else:
                        op_name = operator_choice.lower()
                        if op_name == "combinatio":
                            hypotheses = [engine.combinatio(id_a, id_b)]
                        elif op_name == "subordinatio":
                            hypotheses = [
                                engine.subordinatio(id_a, id_b),
                                engine.subordinatio(id_b, id_a)
                            ]
                        elif op_name == "mediatio":
                            hypotheses = engine.mediatio(id_a, id_b)
                        elif op_name == "amplificatio":
                            hypotheses = engine.amplificatio(id_a)
                        elif op_name == "quaestio":
                            hypotheses = [
                                engine.quaestio(id_a, id_b),
                                engine.quaestio(id_b, id_a)
                            ]
                        elif op_name == "inversio":
                            hypotheses = [
                                engine.inversio(id_a, id_b),
                                engine.inversio(id_b, id_a)
                            ]
                        else:
                            hypotheses = engine.explore(id_a, id_b)

                if hypotheses:
                    with st.spinner("✨ Enriqueciendo con Groq..."):
                        hypotheses = enriquecer_lote(hypotheses, max_enrichments=6)
                    st.success(f"Se generaron {len(hypotheses)} hipótesis.")
                    render_territory_map(hypotheses)
                    for i, h in enumerate(hypotheses):
                        render_hypothesis_card(h, i)
                else:
                    st.info("No se generaron hipótesis para esta combinación.")

    # ----- SORPRÉNDEME -----
    with tab_surprise:
        st.header("🎲 Motor de Serendipia")
        st.markdown(
            "Dejá que el Ars Magna te sorprenda con combinaciones "
            "inesperadas y de alta plausibilidad de todo el mapa de ciencias."
        )

        n_surprises = st.slider("Cantidad de sugerencias", 5, 30, 10)

        if st.button("🎲 ¡Sorpréndeme!", type="primary", use_container_width=True):
            with st.spinner("Buscando combinaciones fortuitas..."):
                hypotheses = engine.surprise_me(n=n_surprises)

            if hypotheses:
                with st.spinner("✨ Enriqueciendo con Groq..."):
                    hypotheses = enriquecer_lote(hypotheses, max_enrichments=5)
                st.success(f"¡Se encontraron {len(hypotheses)} combinaciones interesantes!")
                render_territory_map(hypotheses)
                for i, h in enumerate(hypotheses):
                    render_hypothesis_card(h, i)
            else:
                st.info(
                    "No se encontraron combinaciones de alta plausibilidad. "
                    "Probá aumentando la cantidad."
                )

    # ----- TERRITORIOS VÍRGENES -----
    with tab_virgin:
        st.header("🗺️ Territorios Vírgenes")
        st.markdown(
            "Pares de disciplinas con **cero publicaciones** en su intersección — "
            "las fronteras inexploradas del conocimiento humano. "
            "Filtrado por plausibilidad para excluir combinaciones vacuas."
        )

        if st.button("🗺️ Escanear Territorios Vírgenes", type="primary",
                      use_container_width=True):
            with st.spinner("Escaneando el mapa completo..."):
                virgin = engine.virgin_territories(limit=50)

            if virgin:
                st.success(f"¡Se encontraron {len(virgin)} territorios vírgenes plausibles!")

                for i, h in enumerate(virgin[:30]):
                    with st.expander(
                        f"🗺️ **{h.discipline_a_name}** × **{h.discipline_b_name}** "
                        f"(plausibilidad: {h.plausibility_score:.2f})",
                        expanded=(i < 3)
                    ):
                        st.markdown(
                            f"No existen publicaciones en la intersección de "
                            f"**{h.discipline_a_name}** y **{h.discipline_b_name}**. "
                            f"El análisis de plausibilidad sugiere que podría ser "
                            f"un territorio fértil inexplorado."
                        )
                        st.markdown(f"*Plausibilidad: {h.plausibility_score:.3f}*")
            else:
                st.info("No se encontraron territorios vírgenes con plausibilidad suficiente.")

    # ----- GRAFO -----
    with tab_graph:
        st.header("🕸️ Explorador del Grafo")
        st.markdown("Visualizá el vecindario de las disciplinas seleccionadas.")

        selected = st.multiselect(
            "Seleccioná disciplinas para visualizar",
            options=[name for name, _ in disc_options],
            default=[disc_options[0][0]] if disc_options else [],
            max_selections=5,
        )

        selected_ids = [nid for name, nid in disc_options if name in selected]
        depth = st.slider("Profundidad del vecindario", 1, 3, 1)

        if selected_ids:
            render_discipline_network(G, selected_ids, depth)
        else:
            st.info("Seleccioná al menos una disciplina para visualizar su vecindario.")

    # ----- ACERCA DE -----
    with tab_about:
        st.header("Acerca de Ars Magna Scientiarum")

        st.markdown("""
### La Tradición Luliana

Ramon Llull (1232-1316) creó el *Ars Magna*, un sistema de lógica combinatoria
que proponía que todas las verdades podían generarse combinando sistemáticamente
principios fundamentales mediante operadores definidos. Usando ruedas concéntricas
giratorias, la máquina de Llull fue el primer intento de razonamiento mecanizado.

### Este Sistema

**Ars Magna Scientiarum** refactoriza el motor combinatorio de Llull para un nuevo
dominio: el mapa completo de las ciencias humanas. En lugar de principios teológicos,
combinamos disciplinas científicas. En lugar de buscar la verdad divina, buscamos
**territorios inexplorados del conocimiento**.

El sistema usa:
- Datos de **OpenAlex** que cubren más de 65,000 conceptos científicos y 250M+ publicaciones
- **Seis operadores** (Combinatio, Subordinatio, Mediatio, Amplificatio, Quaestio, Inversio)
  que generan hipótesis cualitativamente distintas
- **Validación bibliométrica** para clasificar intersecciones como Establecida, Emergente,
  Nicho, Incipiente o Territorio Virgen
- **Puntuación de plausibilidad** basada en superposición ontológica, transferibilidad
  metodológica y distancia en el grafo

### Qué Es y Qué No Es

Es una **herramienta heurística para la creatividad científica** — una forma
sistemática de explorar el espacio de las disciplinas posibles e identificar
dónde nadie ha mirado todavía.

**No es** un reemplazo del método científico. Una combinación sugerida puede
ser plausible pero finalmente estéril. El sistema genera hipótesis;
los humanos deben validarlas.

### Origen

*"Al final, sería la culminación del sueño luliano: una máquina de pensar
que, en lugar de girar círculos de madera, navega por el grafo del
conocimiento humano y nos dice: 'Mirá, acá hay una combinación que nadie
ha probado todavía; quizás ahí crezca una nueva ciencia.'"*

---
**Construido por Rainvare** | 2026
        """)


if __name__ == "__main__":
    main()
