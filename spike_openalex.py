"""
Ars Magna Scientiarum — Sprint 0: Technical Spike
===================================================
This script validates the OpenAlex API and ingests the complete concept hierarchy.

Run this on your machine (requires internet access):
    pip install requests networkx tqdm --break-system-packages
    python spike_openalex.py

It will:
1. Download ALL concepts from OpenAlex (all levels, ~65K)
2. Build the complete hierarchy as a NetworkX graph
3. Compute co-occurrence data for L1 discipline pairs
4. Generate a spike report with data quality metrics
5. Save the raw graph as science_graph.json
"""

import json
import time
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import requests
import networkx as nx
from tqdm import tqdm


# ============================================================
# CONFIGURATION
# ============================================================

OPENALEX_BASE = "https://api.openalex.org"
POLITE_EMAIL = "your-email@example.com"  # Replace with your email for polite pool
PER_PAGE = 200  # Max allowed by OpenAlex
OUTPUT_DIR = Path(os.environ.get("ARS_DATA_DIR", "data"))
GRAPH_FILE = OUTPUT_DIR / "science_graph.json"
REPORT_FILE = OUTPUT_DIR / "spike_report.md"
CO_OCCURRENCE_SAMPLE_SIZE = 50  # Number of L1 pairs to test co-occurrence

# Rate limiting: OpenAlex allows 10 req/sec for polite pool
REQUEST_DELAY = 0.11  # seconds between requests


# ============================================================
# 1. DOWNLOAD ALL CONCEPTS
# ============================================================

def get_headers():
    """Headers for polite pool access."""
    return {"User-Agent": f"ArsMagnaScientiarum/0.1 (mailto:{POLITE_EMAIL})"}


def fetch_all_concepts():
    """
    Download every concept from OpenAlex.
    Uses cursor-based pagination to get all ~65K concepts.
    """
    concepts = []
    cursor = "*"
    page = 0

    print("=== Downloading ALL OpenAlex concepts ===")

    while cursor:
        url = (
            f"{OPENALEX_BASE}/concepts"
            f"?per_page={PER_PAGE}"
            f"&cursor={cursor}"
            f"&select=id,display_name,level,description,works_count,"
            f"cited_by_count,ancestors,related_concepts"
        )

        try:
            resp = requests.get(url, headers=get_headers(), timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  Error on page {page}: {e}. Retrying in 5s...")
            time.sleep(5)
            continue

        results = data.get("results", [])
        if not results:
            break

        concepts.extend(results)
        page += 1

        # Get next cursor
        meta = data.get("meta", {})
        cursor = meta.get("next_cursor")

        if page % 10 == 0:
            print(f"  Page {page}: {len(concepts)} concepts so far...")

        time.sleep(REQUEST_DELAY)

    print(f"  TOTAL: {len(concepts)} concepts downloaded.")
    return concepts


# ============================================================
# 2. BUILD THE KNOWLEDGE GRAPH
# ============================================================

def build_graph(concepts):
    """
    Build a NetworkX DiGraph from OpenAlex concepts.
    Nodes = concepts, Edges = ancestor relationships.
    """
    G = nx.DiGraph()

    print("\n=== Building knowledge graph ===")

    for c in tqdm(concepts, desc="Adding nodes"):
        concept_id = c["id"].replace("https://openalex.org/", "")
        G.add_node(concept_id, **{
            "name": c["display_name"],
            "level": c["level"],
            "description": c.get("description", ""),
            "works_count": c.get("works_count", 0),
            "cited_by_count": c.get("cited_by_count", 0),
            # These will be enriched later by LLM:
            "objects_of_study": [],
            "characteristic_methods": [],
            "ontological_assumptions": [],
            "fundamental_questions": [],
            # Layer classification
            "layer": classify_layer(c["level"]),
        })

        # Add hierarchy edges (child → parent)
        for ancestor in (c.get("ancestors") or []):
            ancestor_id = ancestor["id"].replace("https://openalex.org/", "")
            G.add_edge(concept_id, ancestor_id, type="is_subconcept_of")

        # Add related concept edges
        for related in (c.get("related_concepts") or []):
            related_id = related["id"].replace("https://openalex.org/", "")
            G.add_edge(concept_id, related_id, type="related_to",
                       score=related.get("score", 0))

    print(f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def classify_layer(level):
    """Map OpenAlex concept level to our layer system."""
    if level == 0:
        return "L0:Navigation"
    elif level in (1, 2):
        return "L1:Discipline"
    elif level == 3:
        return "L2:Subdiscipline"
    else:
        return "L3:Concept"


# ============================================================
# 3. CO-OCCURRENCE ANALYSIS
# ============================================================

def get_l1_concepts(G):
    """Get all L1:Discipline level concepts."""
    return [n for n, d in G.nodes(data=True)
            if d.get("layer") in ("L0:Navigation", "L1:Discipline")]


def measure_co_occurrence(concept_a_id, concept_b_id):
    """
    Query OpenAlex for works tagged with BOTH concepts.
    Returns total count and recent (last 5 years) count.
    """
    # Full IDs for API
    full_a = f"https://openalex.org/{concept_a_id}"
    full_b = f"https://openalex.org/{concept_b_id}"

    current_year = datetime.now().year

    # Total co-occurrence
    url_total = (
        f"{OPENALEX_BASE}/works"
        f"?filter=concepts.id:{full_a},concepts.id:{full_b}"
        f"&per_page=1"
    )

    # Recent co-occurrence (last 5 years)
    url_recent = (
        f"{OPENALEX_BASE}/works"
        f"?filter=concepts.id:{full_a},concepts.id:{full_b},"
        f"publication_year:{current_year-5}-{current_year}"
        f"&per_page=1"
    )

    total_count = 0
    recent_count = 0

    try:
        resp = requests.get(url_total, headers=get_headers(), timeout=30)
        if resp.ok:
            total_count = resp.json().get("meta", {}).get("count", 0)
        time.sleep(REQUEST_DELAY)

        resp = requests.get(url_recent, headers=get_headers(), timeout=30)
        if resp.ok:
            recent_count = resp.json().get("meta", {}).get("count", 0)
        time.sleep(REQUEST_DELAY)

    except Exception as e:
        print(f"    Error querying co-occurrence: {e}")

    return total_count, recent_count


def classify_intersection(total, recent, threshold_established=10000,
                          threshold_emergent=100):
    """
    Classify a discipline intersection based on publication counts.
    """
    if total >= threshold_established:
        return "ESTABLISHED"
    elif total >= threshold_emergent:
        if recent > 0 and (recent / max(total, 1)) > 0.3:
            return "EMERGENT"
        return "NICHE"
    elif total > 0:
        return "INCIPIENT"
    else:
        return "VIRGIN_TERRITORY"


def sample_co_occurrences(G, n_pairs=50):
    """
    Sample co-occurrence data for L1 concept pairs.
    Focuses on a mix of close and distant pairs.
    """
    l1_concepts = get_l1_concepts(G)
    print(f"\n=== Sampling co-occurrences for {n_pairs} L1 pairs ===")
    print(f"  Total L1 concepts: {len(l1_concepts)}")

    if len(l1_concepts) < 2:
        print("  Not enough L1 concepts for co-occurrence analysis.")
        return []

    # Select pairs: mix of related and random
    import random
    random.seed(42)

    pairs = []
    # First, get some pairs that are related in the graph
    for n in l1_concepts[:20]:
        neighbors = [nbr for nbr in G.neighbors(n)
                     if G.nodes[nbr].get("layer") in ("L0:Navigation", "L1:Discipline")]
        for nbr in neighbors[:2]:
            if (n, nbr) not in pairs and (nbr, n) not in pairs:
                pairs.append((n, nbr))

    # Then add random pairs for diversity
    while len(pairs) < n_pairs and len(l1_concepts) > 1:
        a, b = random.sample(l1_concepts, 2)
        if (a, b) not in pairs and (b, a) not in pairs:
            pairs.append((a, b))

    pairs = pairs[:n_pairs]

    results = []
    for a, b in tqdm(pairs, desc="Querying co-occurrences"):
        name_a = G.nodes[a].get("name", a)
        name_b = G.nodes[b].get("name", b)
        total, recent = measure_co_occurrence(a, b)
        classification = classify_intersection(total, recent)

        results.append({
            "concept_a": a,
            "concept_b": b,
            "name_a": name_a,
            "name_b": name_b,
            "total_co_occurrence": total,
            "recent_5yr_co_occurrence": recent,
            "classification": classification,
        })

        # Add co-occurrence edge to graph
        if total > 0:
            G.add_edge(a, b, type="co_occurrence",
                       total=total, recent=recent,
                       classification=classification)

    return results


# ============================================================
# 4. SAVE & REPORT
# ============================================================

def save_graph(G, filepath):
    """Save graph as JSON (node-link format)."""
    data = nx.node_link_data(G)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  Graph saved to {filepath}")
    print(f"  File size: {filepath.stat().st_size / 1024 / 1024:.1f} MB")


def generate_report(G, co_occurrence_results, filepath):
    """Generate spike report with data quality metrics."""

    # Compute statistics
    levels = defaultdict(int)
    layers = defaultdict(int)
    total_works = 0
    for _, d in G.nodes(data=True):
        levels[d.get("level", -1)] += 1
        layers[d.get("layer", "unknown")] += 1
        total_works += d.get("works_count", 0)

    co_occ_classes = defaultdict(int)
    for r in co_occurrence_results:
        co_occ_classes[r["classification"]] += 1

    report = f"""# Ars Magna Scientiarum — Spike Report
**Generated:** {datetime.now().isoformat()}

## 1. OpenAlex Concept Coverage

| Metric | Value |
|---|---|
| Total concepts | {G.number_of_nodes():,} |
| Total edges (hierarchy + related) | {G.number_of_edges():,} |
| Total works referenced | {total_works:,} |

### By Level
| Level | Count | Layer |
|---|---|---|
"""
    for level in sorted(levels.keys()):
        layer = classify_layer(level)
        report += f"| {level} | {levels[level]:,} | {layer} |\n"

    report += f"""
### By Layer
| Layer | Count |
|---|---|
"""
    for layer in sorted(layers.keys()):
        report += f"| {layer} | {layers[layer]:,} |\n"

    report += f"""
## 2. Co-occurrence Sampling ({len(co_occurrence_results)} pairs tested)

### Classification Distribution
| Classification | Count |
|---|---|
"""
    for cls in ["ESTABLISHED", "EMERGENT", "NICHE", "INCIPIENT", "VIRGIN_TERRITORY"]:
        report += f"| {cls} | {co_occ_classes.get(cls, 0)} |\n"

    report += "\n### Sample Results\n"
    report += "| Discipline A | Discipline B | Total | Recent 5yr | Classification |\n"
    report += "|---|---|---|---|---|\n"

    for r in sorted(co_occurrence_results,
                    key=lambda x: x["total_co_occurrence"], reverse=True)[:30]:
        report += (
            f"| {r['name_a']} | {r['name_b']} | "
            f"{r['total_co_occurrence']:,} | {r['recent_5yr_co_occurrence']:,} | "
            f"{r['classification']} |\n"
        )

    # Highlight virgin territories
    virgin = [r for r in co_occurrence_results if r["classification"] == "VIRGIN_TERRITORY"]
    if virgin:
        report += "\n### 🗺️ Virgin Territories Found\n"
        report += "These discipline pairs have ZERO co-occurring publications:\n\n"
        for r in virgin:
            report += f"- **{r['name_a']}** × **{r['name_b']}**\n"

    report += f"""
## 3. Data Quality Assessment

### Strengths
- Complete hierarchical coverage of all scientific disciplines
- Works count provides quantitative grounding for each concept
- Related concepts provide lateral connections beyond hierarchy
- Co-occurrence queries enable empirical validation of combinations

### Limitations
- OpenAlex concept tagging is algorithmic (not human-curated) — some noise expected
- Co-occurrence measures publication overlap, not true methodological integration
- Concepts at levels 4-5 may be too granular for meaningful combination
- Some social sciences and humanities may be underrepresented

### Recommendations for Sprint 1
1. Use L0-L2 concepts (~4,500) as the primary operating set
2. Compute full co-occurrence matrix for L1 (~300×300 = 90K pairs)
3. Enrich L1 nodes with LLM-generated properties (objects, methods, ontology)
4. Build distance metric combining: graph distance + co-occurrence inverse + ontological similarity
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  Report saved to {filepath}")


# ============================================================
# 5. MAIN
# ============================================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("╔══════════════════════════════════════════╗")
    print("║  ARS MAGNA SCIENTIARUM — Technical Spike  ║")
    print("╚══════════════════════════════════════════╝\n")

    # Step 1: Download all concepts
    concepts_file = OUTPUT_DIR / "openalex_concepts_raw.json"
    if concepts_file.exists():
        print(f"Loading cached concepts from {concepts_file}...")
        with open(concepts_file) as f:
            concepts = json.load(f)
    else:
        concepts = fetch_all_concepts()
        with open(concepts_file, "w", encoding="utf-8") as f:
            json.dump(concepts, f, ensure_ascii=False, indent=2)
        print(f"  Cached to {concepts_file}")

    # Step 2: Build graph
    G = build_graph(concepts)

    # Step 3: Sample co-occurrences
    co_results = sample_co_occurrences(G, n_pairs=CO_OCCURRENCE_SAMPLE_SIZE)

    # Step 4: Save
    save_graph(G, GRAPH_FILE)
    generate_report(G, co_results, REPORT_FILE)

    print("\n✅ Spike complete!")
    print(f"   Graph: {GRAPH_FILE}")
    print(f"   Report: {REPORT_FILE}")
    print(f"\nNext: Review the report, then proceed to Sprint 1.")


if __name__ == "__main__":
    main()
