"""
Ars Magna Scientiarum — LLM Enrichment Pipeline (Groq)
======================================================
Uses Groq (Llama 3.3 70B) to generate structured properties
for each discipline node in the science graph.

Properties generated:
- objects_of_study
- characteristic_methods
- ontological_assumptions
- fundamental_questions

Run after spike_openalex.py has generated the base graph:
    pip install groq networkx tqdm --break-system-packages
    export GROQ_API_KEY="your-api-key-from-console.groq.com"
    python enrich_nodes.py

Groq free tier: 30 req/min, 14,400 req/day, 6,000 tokens/min.
Llama 3.3 70B at ~750 tokens/sec on Groq's LPU hardware.
For ~4,500 L0-L2 nodes this takes ~3-4 hours with caching.
"""

import json
import os
import time
from pathlib import Path

from groq import Groq, RateLimitError
import networkx as nx
from tqdm import tqdm


# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = Path(os.environ.get("ARS_DATA_DIR", "data"))
GRAPH_FILE = DATA_DIR / "science_graph.json"
ENRICHED_FILE = DATA_DIR / "science_graph_enriched.json"
ENRICHMENT_CACHE = DATA_DIR / "enrichment_cache.json"

# Target layers for enrichment
TARGET_LAYERS = {"L0:Navigation", "L1:Discipline", "L2:Subdiscipline"}

# Groq config
MODEL = "llama-3.3-70b-versatile"
# Free tier: 30 req/min → 1 req every 2 seconds to stay safe
REQUEST_DELAY = 2.1
MAX_RETRIES = 5
RETRY_BACKOFF = 10  # seconds to wait after rate limit hit

ENRICHMENT_PROMPT = """You are a philosopher of science and epistemologist.
For the scientific discipline "{name}" (described as: {description}),
provide a structured analysis in JSON format with EXACTLY these keys:

{{
  "objects_of_study": ["list of 3-7 primary objects or phenomena this discipline studies"],
  "characteristic_methods": ["list of 3-7 methods distinctive to this discipline"],
  "ontological_assumptions": ["list of 3-5 fundamental assumptions about what exists and what counts as explanation in this discipline"],
  "fundamental_questions": ["list of 3-5 core questions that define this discipline's research agenda"]
}}

Be precise and specific. For objects, use concrete nouns (not vague descriptions).
For methods, name actual research methods (not meta-descriptions like "scientific method").
For ontological assumptions, state what kinds of entities the discipline assumes exist
and what types of causation it accepts.
For questions, phrase them as actual research questions a practitioner would ask.

Return ONLY valid JSON, no markdown, no explanation, no preamble."""


# ============================================================
# GROQ CLIENT
# ============================================================

def setup_groq():
    """Configure Groq client."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "Set GROQ_API_KEY environment variable.\n"
            "Get a free key at https://console.groq.com/keys\n"
            "No credit card required."
        )
    return Groq(api_key=api_key)


def enrich_node(client: Groq, name: str, description: str) -> dict:
    """
    Query Groq (Llama 3.3 70B) to generate structured properties
    for a discipline.
    """
    prompt = ENRICHMENT_PROMPT.format(
        name=name,
        description=description or name
    )

    for attempt in range(MAX_RETRIES):
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert epistemologist. "
                            "Always respond with valid JSON only. "
                            "No markdown, no explanation, no preamble."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=MODEL,
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"},  # Groq supports JSON mode
            )

            text = chat_completion.choices[0].message.content.strip()

            # Clean common artifacts just in case
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)

            # Validate structure
            required_keys = {
                "objects_of_study", "characteristic_methods",
                "ontological_assumptions", "fundamental_questions"
            }
            if not required_keys.issubset(data.keys()):
                missing = required_keys - data.keys()
                print(f"  WARNING: Missing keys for '{name}': {missing}")
                for k in missing:
                    data[k] = []

            return data

        except RateLimitError as e:
            wait_time = RETRY_BACKOFF * (attempt + 1)
            print(f"  Rate limited on '{name}'. Waiting {wait_time}s "
                  f"(attempt {attempt + 1}/{MAX_RETRIES})...")
            time.sleep(wait_time)

        except json.JSONDecodeError as e:
            print(f"  ERROR parsing JSON for '{name}': {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(REQUEST_DELAY)
                continue
            return {
                "objects_of_study": [],
                "characteristic_methods": [],
                "ontological_assumptions": [],
                "fundamental_questions": [],
            }

        except Exception as e:
            print(f"  ERROR enriching '{name}': {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(REQUEST_DELAY * 2)
                continue
            return None

    print(f"  FAILED after {MAX_RETRIES} retries: '{name}'")
    return None


# ============================================================
# CACHE MANAGEMENT
# ============================================================

def load_cache(cache_file: Path) -> dict:
    """Load enrichment cache to avoid re-querying."""
    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict, cache_file: Path):
    """Save enrichment cache."""
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# ============================================================
# MAIN
# ============================================================

def main():
    print("╔════════════════════════════════════════════════╗")
    print("║  ARS MAGNA SCIENTIARUM — LLM Enrichment (Groq) ║")
    print("╚════════════════════════════════════════════════╝\n")

    # Load graph
    if not GRAPH_FILE.exists():
        print(f"ERROR: {GRAPH_FILE} not found. Run spike_openalex.py first.")
        return

    print(f"Loading graph from {GRAPH_FILE}...")
    with open(GRAPH_FILE) as f:
        graph_data = json.load(f)
    G = nx.node_link_graph(graph_data)

    # Identify nodes to enrich
    to_enrich = [
        (nid, d) for nid, d in G.nodes(data=True)
        if d.get("layer") in TARGET_LAYERS
    ]
    print(f"Nodes to enrich: {len(to_enrich)}")

    # Load cache
    cache = load_cache(ENRICHMENT_CACHE)
    cached_count = sum(1 for nid, _ in to_enrich if nid in cache)
    print(f"Already cached: {cached_count}")
    print(f"Remaining: {len(to_enrich) - cached_count}")

    # Estimate time
    remaining = len(to_enrich) - cached_count
    est_minutes = remaining * REQUEST_DELAY / 60
    est_hours = est_minutes / 60
    print(f"Estimated time: ~{est_hours:.1f} hours "
          f"({est_minutes:.0f} minutes) at {REQUEST_DELAY}s/request")
    print(f"Daily limit: 14,400 requests (you need {remaining})\n")

    if remaining > 14400:
        print("⚠️  More nodes than daily limit. Will need multiple days.")
        print("   Cache persists between runs — just re-run tomorrow.\n")

    # Setup Groq client
    client = setup_groq()

    # Test connection
    print("Testing Groq connection...")
    try:
        test = client.chat.completions.create(
            messages=[{"role": "user", "content": "Say 'OK' in JSON: {\"status\": \"ok\"}"}],
            model=MODEL,
            max_tokens=20,
            response_format={"type": "json_object"},
        )
        print(f"  ✅ Connected. Model: {MODEL}")
        print(f"  Response: {test.choices[0].message.content.strip()}\n")
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        return

    # Enrich
    enriched_count = 0
    errors = 0
    skipped = 0

    for nid, node_data in tqdm(to_enrich, desc="Enriching nodes"):
        if nid in cache:
            # Apply cached enrichment
            for key, value in cache[nid].items():
                G.nodes[nid][key] = value
            skipped += 1
            continue

        name = node_data.get("name", nid)
        description = node_data.get("description", "")

        result = enrich_node(client, name, description)

        if result:
            # Apply enrichment to graph
            for key, value in result.items():
                G.nodes[nid][key] = value

            # Cache result
            cache[nid] = result
            enriched_count += 1

            # Save cache periodically
            if enriched_count % 25 == 0:
                save_cache(cache, ENRICHMENT_CACHE)
                tqdm.write(f"  💾 Cache saved ({enriched_count} new enrichments, "
                           f"{skipped + enriched_count}/{len(to_enrich)} total)")
        else:
            errors += 1

        time.sleep(REQUEST_DELAY)

    # Final save
    save_cache(cache, ENRICHMENT_CACHE)

    # Save enriched graph
    graph_data = nx.node_link_data(G)
    with open(ENRICHED_FILE, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"✅ Enrichment complete!")
    print(f"   New enrichments: {enriched_count}")
    print(f"   Cached (reused): {skipped}")
    print(f"   Errors: {errors}")
    print(f"   Total processed: {skipped + enriched_count + errors}/{len(to_enrich)}")
    print(f"   Enriched graph: {ENRICHED_FILE}")

    if errors > 0:
        print(f"\n   ⚠️ {errors} nodes failed. Re-run to retry (cache preserves progress).")

    remaining_after = len(to_enrich) - skipped - enriched_count - errors
    if remaining_after > 0:
        print(f"   📋 {remaining_after} nodes still need enrichment.")
        print(f"   Just run again — cache ensures no duplicate work.")


if __name__ == "__main__":
    main()
