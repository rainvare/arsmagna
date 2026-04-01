"""
Ars Magna Scientiarum — Combinatorial Engine
=============================================
Implements the 6 Lullian operators for generating hypotheses
about new interdisciplinary fields.

Operators:
1. Combinatio — merge two disciplines equally
2. Subordinatio — apply methods of A to objects of B
3. Mediatio — find a bridging discipline between A and B
4. Amplificatio — extend a narrow method to broader domains
5. Quaestio — transfer fundamental questions across disciplines
6. Inversio — invert a discipline's question and apply to another

v2 — Fixes:
- Derive ontological overlap from actual ancestor data (Jaccard)
- Derive methodological proxy from related_concepts overlap
- Penalize infinite graph distance properly
- surprise_me() filters to connected component + distance range
"""

import json
import math
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum

import networkx as nx


# ============================================================
# DATA MODELS
# ============================================================

class Operator(Enum):
    COMBINATIO = "combinatio"
    SUBORDINATIO = "subordinatio"
    MEDIATIO = "mediatio"
    AMPLIFICATIO = "amplificatio"
    QUAESTIO = "quaestio"
    INVERSIO = "inversio"


class TerritoryClass(Enum):
    ESTABLISHED = "established"
    EMERGENT = "emergent"
    NICHE = "niche"
    INCIPIENT = "incipient"
    VIRGIN = "virgin_territory"
    IMPLAUSIBLE = "implausible"


@dataclass
class Hypothesis:
    """A generated hypothesis for a new or existing interdisciplinary field."""
    operator: str
    discipline_a: str
    discipline_b: str
    discipline_a_name: str
    discipline_b_name: str
    suggested_name: str
    description: str
    justification: str
    research_questions: list[str]
    territory_class: str = "unknown"
    plausibility_score: float = 0.0
    co_occurrence_total: int = 0
    co_occurrence_recent: int = 0
    mediator: Optional[str] = None
    mediator_name: Optional[str] = None
    groq_data: dict = field(default_factory=dict)


# ============================================================
# HELPER: EXTRACT ANCESTORS FROM GRAPH STRUCTURE
# ============================================================

def _get_ancestors_from_graph(G: nx.DiGraph, node_id: str) -> set[str]:
    """
    Get the set of ancestor node IDs by following 'is_subconcept_of' edges.
    This uses the actual graph hierarchy instead of the empty
    'ontological_assumptions' field.
    """
    ancestors = set()
    for _, target, data in G.out_edges(node_id, data=True):
        if data.get("type") == "is_subconcept_of":
            ancestors.add(target)
    return ancestors


def _get_related_from_graph(G: nx.DiGraph, node_id: str) -> set[str]:
    """
    Get the set of related concept IDs by following 'related_to' edges.
    Used as a proxy for methodological/conceptual affinity.
    """
    related = set()
    for _, target, data in G.out_edges(node_id, data=True):
        if data.get("type") == "related_to":
            related.add(target)
    # Also check incoming related_to edges
    for source, _, data in G.in_edges(node_id, data=True):
        if data.get("type") == "related_to":
            related.add(source)
    return related


# ============================================================
# PLAUSIBILITY SCORING (v2 — uses real graph data)
# ============================================================

def compute_ontological_overlap(node_a: dict, node_b: dict,
                                 ancestors_a: set = None,
                                 ancestors_b: set = None) -> float:
    """
    Compute ontological overlap between two disciplines.
    
    v2: Uses actual ancestor sets from graph hierarchy (Jaccard index).
    Falls back to the old field-based approach only if ancestors are
    explicitly provided as empty AND the node has ontological_assumptions.
    """
    # Primary: use graph-derived ancestors
    if ancestors_a is not None and ancestors_b is not None:
        if ancestors_a or ancestors_b:  # at least one has ancestors
            union = len(ancestors_a | ancestors_b)
            if union == 0:
                return 0.0
            intersection = len(ancestors_a & ancestors_b)
            return intersection / union

    # Fallback: use enriched ontological_assumptions if they exist
    assumptions_a = set(node_a.get("ontological_assumptions", []))
    assumptions_b = set(node_b.get("ontological_assumptions", []))

    if assumptions_a and assumptions_b:
        intersection = len(assumptions_a & assumptions_b)
        union = len(assumptions_a | assumptions_b)
        if union == 0:
            return 0.0
        return intersection / union

    # Last resort: no data at all → return a low-confidence neutral
    # BUT mark it clearly as uninformative (0.3 instead of the old 0.5
    # which was landing in the "optimal" zone and inflating scores)
    return 0.3


def compute_methodological_transferability(node_a: dict, node_b: dict,
                                            related_a: set = None,
                                            related_b: set = None) -> float:
    """
    Estimate how transferable methods are between disciplines.
    
    v2: Uses related_concepts overlap as a proxy when
    characteristic_methods is empty (which is the common case).
    """
    # Primary: use enriched characteristic_methods if available
    methods_a = set(node_a.get("characteristic_methods", []))
    methods_b = set(node_b.get("characteristic_methods", []))

    if methods_a and methods_b:
        shared = len(methods_a & methods_b)
        total = len(methods_a | methods_b)
        if total == 0:
            return 0.0
        ratio = shared / total
        return 1.0 - abs(ratio - 0.35) * 2

    # Proxy: use related_concepts overlap (from graph edges)
    if related_a is not None and related_b is not None:
        if related_a or related_b:
            union = len(related_a | related_b)
            if union == 0:
                return 0.3
            shared = len(related_a & related_b)
            ratio = shared / union
            # Optimal transferability when ~15-40% concepts overlap
            # (lower threshold than methods because related_concepts
            # is a broader, noisier signal)
            return max(0.0, min(1.0, 1.0 - abs(ratio - 0.25) * 2.5))

    # No data at all
    return 0.3


def compute_plausibility(node_a: dict, node_b: dict,
                          graph_distance: float,
                          co_occurrence: int,
                          ancestors_a: set = None,
                          ancestors_b: set = None,
                          related_a: set = None,
                          related_b: set = None) -> float:
    """
    Compute overall plausibility score for a discipline combination.

    v2 changes:
    - Accepts pre-computed ancestor/related sets for real overlap
    - Infinite distance now strongly penalizes (0.05 instead of 0.4)
    - Overall scoring is more discriminating
    """
    onto_overlap = compute_ontological_overlap(
        node_a, node_b, ancestors_a, ancestors_b)
    method_transfer = compute_methodological_transferability(
        node_a, node_b, related_a, related_b)

    # Graph distance component: moderate distance is most interesting
    # v2: infinite distance is HEAVILY penalized — it means the nodes
    # are in different components and likely have nothing in common
    if graph_distance == float("inf"):
        distance_score = 0.05  # was 0.4 — this was the main inflation bug
    elif graph_distance == 0:
        distance_score = 0.0
    elif graph_distance <= 2:
        distance_score = 0.3
    elif graph_distance <= 5:
        distance_score = 1.0
    elif graph_distance <= 8:
        distance_score = 0.7
    else:
        distance_score = 0.4

    # Ontological overlap component: partial overlap is best
    if onto_overlap < 0.05:
        onto_score = 0.1  # essentially unrelated
    elif onto_overlap < 0.15:
        onto_score = 0.5  # distant but some shared ground
    elif onto_overlap < 0.35:
        onto_score = 1.0  # sweet spot — enough overlap to be meaningful
    elif onto_overlap < 0.6:
        onto_score = 0.8  # good overlap
    elif onto_overlap < 0.8:
        onto_score = 0.4  # getting redundant
    else:
        onto_score = 0.2  # too similar

    # Novelty component: less co-occurrence = more novel
    if co_occurrence == 0:
        novelty_score = 1.0
    elif co_occurrence < 100:
        novelty_score = 0.9
    elif co_occurrence < 1000:
        novelty_score = 0.7
    elif co_occurrence < 10000:
        novelty_score = 0.4
    else:
        novelty_score = 0.1

    # Weighted combination
    score = (
        onto_score * 0.30 +
        method_transfer * 0.25 +
        distance_score * 0.20 +
        novelty_score * 0.25
    )

    return round(score, 3)


# ============================================================
# THE SIX OPERATORS
# ============================================================

class LullianEngine:
    """
    The combinatorial engine that applies Lullian operators
    to the graph of sciences.
    """

    def __init__(self, graph: nx.DiGraph):
        self.G = graph
        self._distance_cache = {}
        self._ancestor_cache = {}
        self._related_cache = {}
        # Pre-compute connected components for fast filtering
        self._undirected = graph.to_undirected()
        self._components = {}
        for i, comp in enumerate(nx.connected_components(self._undirected)):
            for node in comp:
                self._components[node] = i

    def _get_ancestors(self, node_id: str) -> set:
        """Cached ancestor lookup."""
        if node_id not in self._ancestor_cache:
            self._ancestor_cache[node_id] = _get_ancestors_from_graph(
                self.G, node_id)
        return self._ancestor_cache[node_id]

    def _get_related(self, node_id: str) -> set:
        """Cached related concepts lookup."""
        if node_id not in self._related_cache:
            self._related_cache[node_id] = _get_related_from_graph(
                self.G, node_id)
        return self._related_cache[node_id]

    def _same_component(self, a: str, b: str) -> bool:
        """Check if two nodes are in the same connected component."""
        return self._components.get(a) == self._components.get(b)

    def get_node(self, concept_id: str) -> dict:
        """Get node data, raising clear error if not found."""
        if concept_id not in self.G:
            raise ValueError(f"Concept '{concept_id}' not found in graph.")
        return self.G.nodes[concept_id]

    def graph_distance(self, a: str, b: str) -> float:
        """Compute shortest path distance in the undirected graph."""
        cache_key = (min(a, b), max(a, b))
        if cache_key in self._distance_cache:
            return self._distance_cache[cache_key]

        # Fast check: different components → infinite
        if not self._same_component(a, b):
            self._distance_cache[cache_key] = float("inf")
            return float("inf")

        try:
            dist = nx.shortest_path_length(self._undirected, a, b)
        except nx.NetworkXNoPath:
            dist = float("inf")

        self._distance_cache[cache_key] = dist
        return dist

    def get_co_occurrence(self, a: str, b: str) -> tuple[int, int]:
        """Get co-occurrence data from graph edges if available."""
        edge_data = self.G.get_edge_data(a, b) or self.G.get_edge_data(b, a) or {}
        return (
            edge_data.get("total", 0),
            edge_data.get("recent", 0)
        )

    def _compute_pair_plausibility(self, a: str, b: str,
                                    node_a: dict, node_b: dict) -> tuple:
        """
        Compute plausibility for a pair, returning
        (plausibility, distance, total_co, recent_co).
        Centralizes the ancestor/related lookup.
        """
        total_co, recent_co = self.get_co_occurrence(a, b)
        dist = self.graph_distance(a, b)
        ancestors_a = self._get_ancestors(a)
        ancestors_b = self._get_ancestors(b)
        related_a = self._get_related(a)
        related_b = self._get_related(b)

        plausibility = compute_plausibility(
            node_a, node_b, dist, total_co,
            ancestors_a, ancestors_b,
            related_a, related_b
        )
        return plausibility, dist, total_co, recent_co

    def classify_territory(self, total: int, recent: int) -> str:
        """Classify intersection based on bibliometric data."""
        if total >= 10000:
            return TerritoryClass.ESTABLISHED.value
        elif total >= 100:
            if recent > 0 and (recent / max(total, 1)) > 0.3:
                return TerritoryClass.EMERGENT.value
            return TerritoryClass.NICHE.value
        elif total > 0:
            return TerritoryClass.INCIPIENT.value
        else:
            return TerritoryClass.VIRGIN.value

    # ----- OPERATOR 1: COMBINATIO -----

    def combinatio(self, a: str, b: str) -> Hypothesis:
        """
        Merge two disciplines in equal standing.
        The resulting field combines objects and methods from both.
        """
        node_a = self.get_node(a)
        node_b = self.get_node(b)
        name_a = node_a["name"]
        name_b = node_b["name"]

        plausibility, dist, total_co, recent_co = \
            self._compute_pair_plausibility(a, b, node_a, node_b)

        onto_overlap = compute_ontological_overlap(
            node_a, node_b, self._get_ancestors(a), self._get_ancestors(b))

        suggested = f"{name_a}-{name_b} Synthesis"

        objects_a = node_a.get("objects_of_study", [name_a + " phenomena"])
        objects_b = node_b.get("objects_of_study", [name_b + " phenomena"])
        questions = []
        for oa in objects_a[:2]:
            for ob in objects_b[:2]:
                questions.append(
                    f"What happens when we study {ob} through the combined "
                    f"lens of {name_a} and {name_b}?"
                )

        return Hypothesis(
            operator=Operator.COMBINATIO.value,
            discipline_a=a,
            discipline_b=b,
            discipline_a_name=name_a,
            discipline_b_name=name_b,
            suggested_name=suggested,
            description=(
                f"A field that merges {name_a} and {name_b} in equal standing, "
                f"combining their objects of study and methodological toolkits "
                f"into an integrated discipline."
            ),
            justification=(
                f"Ontological overlap: {onto_overlap:.2f}. "
                f"Graph distance: {dist}. "
                f"Co-occurrence: {total_co:,} publications."
            ),
            research_questions=questions[:4],
            territory_class=self.classify_territory(total_co, recent_co),
            plausibility_score=plausibility,
            co_occurrence_total=total_co,
            co_occurrence_recent=recent_co,
        )

    # ----- OPERATOR 2: SUBORDINATIO -----

    def subordinatio(self, method_source: str, object_target: str) -> Hypothesis:
        """
        Apply the methods of discipline A to the objects of discipline B.
        Asymmetric: the method source dominates.
        """
        node_a = self.get_node(method_source)
        node_b = self.get_node(object_target)
        name_a = node_a["name"]
        name_b = node_b["name"]

        plausibility, dist, total_co, recent_co = \
            self._compute_pair_plausibility(method_source, object_target,
                                            node_a, node_b)

        method_transfer = compute_methodological_transferability(
            node_a, node_b,
            self._get_related(method_source),
            self._get_related(object_target))

        methods = node_a.get("characteristic_methods", [f"{name_a} methods"])
        objects = node_b.get("objects_of_study", [f"{name_b} phenomena"])

        suggested = f"{name_a}-informed {name_b}"

        questions = []
        for m in methods[:3]:
            for o in objects[:2]:
                questions.append(
                    f"What do we learn by applying {m} to the study of {o}?"
                )

        return Hypothesis(
            operator=Operator.SUBORDINATIO.value,
            discipline_a=method_source,
            discipline_b=object_target,
            discipline_a_name=name_a,
            discipline_b_name=name_b,
            suggested_name=suggested,
            description=(
                f"A field that applies the methods of {name_a} "
                f"({', '.join(methods[:3])}) to the objects of study of "
                f"{name_b} ({', '.join(objects[:3])})."
            ),
            justification=(
                f"Method transfer from {name_a} to {name_b}. "
                f"Transferability score: {method_transfer:.2f}. "
                f"Graph distance: {dist}."
            ),
            research_questions=questions[:4],
            territory_class=self.classify_territory(total_co, recent_co),
            plausibility_score=plausibility,
            co_occurrence_total=total_co,
            co_occurrence_recent=recent_co,
        )

    # ----- OPERATOR 3: MEDIATIO -----

    def mediatio(self, a: str, b: str, max_mediators: int = 5) -> list[Hypothesis]:
        """
        Find disciplines that can bridge two distant fields.
        A mediator shares edges with both A and B.
        """
        node_a = self.get_node(a)
        node_b = self.get_node(b)
        name_a = node_a["name"]
        name_b = node_b["name"]

        neighbors_a = set(self._undirected.neighbors(a)) if a in self._undirected else set()
        neighbors_b = set(self._undirected.neighbors(b)) if b in self._undirected else set()

        common_neighbors = neighbors_a & neighbors_b
        if not common_neighbors:
            # Expand to 2-hop neighbors
            neighbors_a_2 = set()
            for n in neighbors_a:
                neighbors_a_2.update(self._undirected.neighbors(n))
            common_neighbors = neighbors_a_2 & neighbors_b

        hypotheses = []
        for mediator_id in list(common_neighbors)[:max_mediators]:
            if mediator_id in (a, b):
                continue

            node_m = self.get_node(mediator_id)
            name_m = node_m["name"]

            plausibility, dist, total_co, recent_co = \
                self._compute_pair_plausibility(a, b, node_a, node_b)

            # Boost plausibility for good mediators
            dist_am = self.graph_distance(a, mediator_id)
            dist_bm = self.graph_distance(b, mediator_id)
            if dist_am < dist and dist_bm < dist:
                plausibility = min(plausibility * 1.2, 1.0)

            hypotheses.append(Hypothesis(
                operator=Operator.MEDIATIO.value,
                discipline_a=a,
                discipline_b=b,
                discipline_a_name=name_a,
                discipline_b_name=name_b,
                suggested_name=f"{name_a}-{name_b} (via {name_m})",
                description=(
                    f"A bridge between {name_a} and {name_b}, mediated by "
                    f"{name_m}. The mediator provides shared concepts, methods, "
                    f"or ontological ground that connects these distant fields."
                ),
                justification=(
                    f"{name_m} is connected to both {name_a} (distance {dist_am}) "
                    f"and {name_b} (distance {dist_bm}), while {name_a} and "
                    f"{name_b} are at distance {dist}."
                ),
                research_questions=[
                    f"How does {name_m} translate insights from {name_a} "
                    f"into the domain of {name_b}?",
                    f"What concepts in {name_m} serve as bridges between "
                    f"the objects of {name_a} and {name_b}?",
                ],
                territory_class=self.classify_territory(total_co, recent_co),
                plausibility_score=plausibility,
                co_occurrence_total=total_co,
                co_occurrence_recent=recent_co,
                mediator=mediator_id,
                mediator_name=name_m,
            ))

        return sorted(hypotheses, key=lambda h: h.plausibility_score, reverse=True)

    # ----- OPERATOR 4: AMPLIFICATIO -----

    def amplificatio(self, source: str, max_targets: int = 10) -> list[Hypothesis]:
        """
        Take a method native to a narrow field and suggest its application
        to other, distant fields.
        """
        node_s = self.get_node(source)
        name_s = node_s["name"]
        methods = node_s.get("characteristic_methods", [])

        if not methods:
            methods = [f"{name_s} analytical framework"]

        # Find distant disciplines (high graph distance)
        l1_nodes = [
            (n, d) for n, d in self.G.nodes(data=True)
            if d.get("layer") in ("L0:Navigation", "L1:Discipline")
            and n != source
        ]

        candidates = []
        for n, d in l1_nodes:
            dist = self.graph_distance(source, n)
            if 3 <= dist < float("inf"):  # v2: exclude infinite distance
                candidates.append((n, d, dist))

        # Sort by distance (farther = more novel)
        candidates.sort(key=lambda x: x[2], reverse=True)

        hypotheses = []
        for target_id, target_data, dist in candidates[:max_targets]:
            name_t = target_data["name"]
            plausibility, _, total_co, recent_co = \
                self._compute_pair_plausibility(source, target_id,
                                                node_s, target_data)

            hypotheses.append(Hypothesis(
                operator=Operator.AMPLIFICATIO.value,
                discipline_a=source,
                discipline_b=target_id,
                discipline_a_name=name_s,
                discipline_b_name=name_t,
                suggested_name=f"{methods[0].title()} applied to {name_t}",
                description=(
                    f"Extending the methods of {name_s} "
                    f"({', '.join(methods[:3])}) beyond their native domain "
                    f"into {name_t}, which has never used these approaches."
                ),
                justification=(
                    f"Graph distance: {dist} (high — novel territory). "
                    f"Co-occurrence: {total_co} publications. "
                    f"Method '{methods[0]}' may reveal unseen patterns in "
                    f"{name_t}."
                ),
                research_questions=[
                    f"What would {name_t} look like analyzed through "
                    f"{methods[0]}?",
                    f"Are there hidden structures in {name_t} that only "
                    f"{name_s} methods can reveal?",
                ],
                territory_class=self.classify_territory(total_co, recent_co),
                plausibility_score=plausibility,
                co_occurrence_total=total_co,
                co_occurrence_recent=recent_co,
            ))

        return sorted(hypotheses, key=lambda h: h.plausibility_score, reverse=True)

    # ----- OPERATOR 5: QUAESTIO -----

    def quaestio(self, question_source: str, target: str) -> Hypothesis:
        """
        Transfer the fundamental questions of discipline A to discipline B.
        Generates novel research questions.
        """
        node_a = self.get_node(question_source)
        node_b = self.get_node(target)
        name_a = node_a["name"]
        name_b = node_b["name"]

        questions_a = node_a.get("fundamental_questions",
                                  [f"What is the nature of {name_a} phenomena?"])
        objects_b = node_b.get("objects_of_study", [f"{name_b} entities"])

        plausibility, dist, total_co, recent_co = \
            self._compute_pair_plausibility(question_source, target,
                                            node_a, node_b)

        # Transfer questions
        transferred = []
        for q in questions_a[:3]:
            for o in objects_b[:2]:
                transferred.append(
                    f"[From {name_a}] Applying '{q}' to {o} in {name_b}"
                )

        return Hypothesis(
            operator=Operator.QUAESTIO.value,
            discipline_a=question_source,
            discipline_b=target,
            discipline_a_name=name_a,
            discipline_b_name=name_b,
            suggested_name=f"{name_a} Questions in {name_b}",
            description=(
                f"Transplanting the fundamental questions of {name_a} into "
                f"the domain of {name_b}. What {name_a} asks about its "
                f"objects, we now ask about {name_b}'s objects."
            ),
            justification=(
                f"The questions of {name_a} have never been systematically "
                f"applied to {name_b}. Graph distance: {dist}. "
                f"This could reframe {name_b}'s research agenda."
            ),
            research_questions=transferred[:5],
            territory_class=self.classify_territory(total_co, recent_co),
            plausibility_score=plausibility,
            co_occurrence_total=total_co,
            co_occurrence_recent=recent_co,
        )

    # ----- OPERATOR 6: INVERSIO -----

    def inversio(self, source: str, target: str) -> Hypothesis:
        """
        Invert the fundamental question of discipline A and apply to B.
        """
        node_a = self.get_node(source)
        node_b = self.get_node(target)
        name_a = node_a["name"]
        name_b = node_b["name"]

        questions_a = node_a.get("fundamental_questions",
                                  [f"How does {name_a} work?"])
        objects_b = node_b.get("objects_of_study", [f"{name_b} entities"])

        plausibility, dist, total_co, recent_co = \
            self._compute_pair_plausibility(source, target, node_a, node_b)

        # Invert questions
        inverted = []
        for q in questions_a[:3]:
            inv_q = self._invert_question(q)
            for o in objects_b[:2]:
                inverted.append(
                    f"[Inverted from {name_a}] '{inv_q}' — applied to {o}"
                )

        return Hypothesis(
            operator=Operator.INVERSIO.value,
            discipline_a=source,
            discipline_b=target,
            discipline_a_name=name_a,
            discipline_b_name=name_b,
            suggested_name=f"Inverse {name_a} in {name_b}",
            description=(
                f"Taking the core question of {name_a}, inverting its "
                f"direction or subject-object relationship, and applying "
                f"that inverted question to {name_b}."
            ),
            justification=(
                f"Inversio is the most creative operator — it doesn't just "
                f"transfer, it *reverses*. What {name_a} takes as the agent "
                f"becomes the patient, and vice versa. Applied to {name_b}, "
                f"this generates questions no one is asking."
            ),
            research_questions=inverted[:4],
            territory_class=self.classify_territory(total_co, recent_co),
            plausibility_score=plausibility,
            co_occurrence_total=total_co,
            co_occurrence_recent=recent_co,
        )

    @staticmethod
    def _invert_question(question: str) -> str:
        """
        Simple heuristic to invert a question.
        In production, this would use an LLM for semantic inversion.
        """
        inversions = {
            "how do": "how do ... fail to",
            "what causes": "what prevents",
            "why does": "why doesn't",
            "how does": "how does the inverse of",
            "what is": "what is the absence of",
            "how can": "how can we prevent",
            "what drives": "what inhibits",
            "how do organisms adapt to environments":
                "how do environments adapt to organisms",
        }
        q_lower = question.lower().strip("?")
        for pattern, replacement in inversions.items():
            if q_lower.startswith(pattern):
                return question.replace(
                    question[:len(pattern)],
                    replacement.capitalize(),
                    1
                ) + "?"
        return f"What is the opposite of: {question}"

    # ----- COMPOSITE OPERATIONS -----

    def explore(self, a: str, b: str) -> list[Hypothesis]:
        """
        Apply ALL operators to a pair of disciplines.
        Returns a ranked list of hypotheses.
        """
        hypotheses = []

        # Combinatio
        hypotheses.append(self.combinatio(a, b))

        # Subordinatio (both directions)
        hypotheses.append(self.subordinatio(a, b))
        hypotheses.append(self.subordinatio(b, a))

        # Mediatio
        hypotheses.extend(self.mediatio(a, b, max_mediators=3))

        # Amplificatio (both directions)
        amp_a = self.amplificatio(a, max_targets=3)
        amp_b = self.amplificatio(b, max_targets=3)
        hypotheses.extend([h for h in amp_a if h.discipline_b == b])
        hypotheses.extend([h for h in amp_b if h.discipline_b == a])

        # Quaestio (both directions)
        hypotheses.append(self.quaestio(a, b))
        hypotheses.append(self.quaestio(b, a))

        # Inversio (both directions)
        hypotheses.append(self.inversio(a, b))
        hypotheses.append(self.inversio(b, a))

        # Rank by plausibility
        hypotheses.sort(key=lambda h: h.plausibility_score, reverse=True)
        return hypotheses

    def surprise_me(self, n: int = 10, layer: str = "L1:Discipline",
                     min_works: int = 50000) -> list[Hypothesis]:
        """
        Generate random, high-plausibility combinations from distant disciplines.
        The 'serendipity engine'.

        v3 fixes:
        - Filter to substantive disciplines (works_count >= min_works)
        - Only pairs in the same connected component (finite distance)
        - Prefer distance 2-6 (the fertile zone)
        - Two-tier strategy: first try pairs WITH co-occurrence data,
          then fill remaining slots with virgin territory pairs
        """
        import random

        # Filter to substantive disciplines only
        # This removes granular concepts like "Isotopes of chromium"
        # and keeps real disciplines like "Ecology", "Genetics", etc.
        nodes = [
            (nid, d) for nid, d in self.G.nodes(data=True)
            if d.get("layer") == layer
            and d.get("works_count", 0) >= min_works
        ]

        if len(nodes) < 2:
            # Fallback: relax threshold
            nodes = [
                (nid, d) for nid, d in self.G.nodes(data=True)
                if d.get("layer") == layer
                and d.get("works_count", 0) >= 10000
            ]

        if len(nodes) < 2:
            return []

        # Group nodes by connected component for efficient sampling
        comp_groups = {}
        for nid, d in nodes:
            comp_id = self._components.get(nid)
            if comp_id is not None:
                comp_groups.setdefault(comp_id, []).append((nid, d))

        # Only consider components with at least 2 nodes
        viable_comps = [
            group for group in comp_groups.values()
            if len(group) >= 2
        ]

        if not viable_comps:
            return []

        # Collect pairs that have co-occurrence edges for quick lookup
        co_occurrence_pairs = set()
        for u, v, data in self.G.edges(data=True):
            if data.get("type") == "co_occurrence":
                co_occurrence_pairs.add((min(u, v), max(u, v)))

        hypotheses = []
        seen_pairs = set()
        attempts = 0
        max_attempts = n * 30

        while len(hypotheses) < n and attempts < max_attempts:
            attempts += 1

            # Pick a random component (weighted by size)
            weights = [len(g) for g in viable_comps]
            comp = random.choices(viable_comps, weights=weights, k=1)[0]

            (a, _), (b, _) = random.sample(comp, 2)

            # Avoid duplicate pairs
            pair_key = (min(a, b), max(a, b))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Check distance is in the interesting range
            dist = self.graph_distance(a, b)
            if dist < 2 or dist == float("inf"):
                continue

            h = self.combinatio(a, b)

            # Accept if plausible enough
            if h.plausibility_score > 0.3:
                # Boost priority for pairs with real co-occurrence data
                if pair_key in co_occurrence_pairs:
                    h.plausibility_score = min(h.plausibility_score + 0.05, 1.0)
                hypotheses.append(h)

        hypotheses.sort(key=lambda h: h.plausibility_score, reverse=True)
        return hypotheses[:n]

    def virgin_territories(self, layer: str = "L1:Discipline",
                            limit: int = 50) -> list[Hypothesis]:
        """
        Systematically scan for discipline pairs with ZERO co-occurrence.
        These are the unexplored frontiers.
        
        v2: Only considers pairs with finite graph distance.
        """
        nodes = [
            (nid, d) for nid, d in self.G.nodes(data=True)
            if d.get("layer") == layer
        ]

        virgin = []
        for i, (a, da) in enumerate(nodes):
            for b, db in nodes[i+1:]:
                total, recent = self.get_co_occurrence(a, b)
                if total == 0:
                    dist = self.graph_distance(a, b)
                    # v2: skip disconnected pairs
                    if dist == float("inf"):
                        continue
                    plausibility = compute_plausibility(
                        da, db, dist, 0,
                        self._get_ancestors(a), self._get_ancestors(b),
                        self._get_related(a), self._get_related(b))
                    if plausibility > 0.4:
                        virgin.append(Hypothesis(
                            operator="scan",
                            discipline_a=a,
                            discipline_b=b,
                            discipline_a_name=da["name"],
                            discipline_b_name=db["name"],
                            suggested_name=f"{da['name']} × {db['name']}",
                            description="Unexplored intersection — no publications found.",
                            justification=(
                                f"Plausibility: {plausibility:.2f}. "
                                f"Graph distance: {dist}."
                            ),
                            research_questions=[],
                            territory_class=TerritoryClass.VIRGIN.value,
                            plausibility_score=plausibility,
                        ))

        virgin.sort(key=lambda h: h.plausibility_score, reverse=True)
        return virgin[:limit]


# ============================================================
# SERIALIZATION
# ============================================================

def hypothesis_to_dict(h: Hypothesis) -> dict:
    return asdict(h)


def hypotheses_to_json(hypotheses: list[Hypothesis]) -> str:
    return json.dumps([hypothesis_to_dict(h) for h in hypotheses],
                      ensure_ascii=False, indent=2)
