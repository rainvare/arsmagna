# Ars Magna Scientiarum: A Lullian Engine for the Discovery of Sciences

*R. Indira Valentina Réquiz Molina*
*March 2026*

---

## Abstract

We present Ars Magna Scientiarum, a computational system that applies Ramon Llull's thirteenth-century combinatorial logic to the complete map of human scientific disciplines. By replacing Llull's theological principles with the ~65,000 concepts indexed in OpenAlex and his mystical figures with six typed operators (Combinatio, Subordinatio, Mediatio, Amplificatio, Quaestio, and Inversio), the system generates empirically-grounded hypotheses for new interdisciplinary fields. Each hypothesis is validated against bibliometric data from over 250 million scientific publications and classified as Established, Emergent, Niche, Incipient, or Virgin Territory. The system's plausibility scoring — based on ontological overlap, methodological transferability, and concept distance — provides a novel heuristic for evaluating interdisciplinary fertility. We argue that the space of possible sciences vastly exceeds the space of actual sciences, and that a systematic cartography of this unexplored territory constitutes a meaningful contribution to the science of science.

---

## 1. The Lullian Intuition

In 1305, Ramon Llull completed his *Ars Magna*, a system that proposed to generate all possible truths by combining a finite set of fundamental principles through a defined set of operations. His physical device — concentric rotating wheels inscribed with letters representing divine attributes like Bonitas, Magnitudo, and Aeternitas — was the first known attempt to mechanize reasoning.

Llull's system has been variously interpreted as proto-computation, mystical logic, and combinatorial mathematics. What concerns us here is not its theological content but its formal structure: a finite set of typed primitives, a finite set of typed operators, and the exhaustive generation of all combinations as a method for discovering truths that no single mind could produce unaided.

We propose that this structure, when applied to the map of scientific disciplines rather than to divine attributes, becomes a powerful heuristic engine for identifying unexplored territories of knowledge.

## 2. The Refactoring

The translation from Llull's domain to ours preserves the mechanism while replacing every element of the content.

In the original Ars Magna, the **Principles** are divine attributes (Bonitas, Magnitudo, Aeternitas, Potestas, Sapientia, Voluntas, Virtus, Veritas, Gloria). In our system, the Principles become **scientific disciplines** — not forty, not three hundred, but the complete hierarchy of ~65,000 concepts indexed in OpenAlex, organized in layers from "Physics" and "Biology" down through "Quantum chromodynamics" and "Metagenomics."

Llull's **Figures** — the rotating wheels that mechanically generate combinations — become **six typed operators**, each producing a qualitatively distinct kind of hypothesis. This is a critical point: not all combinations are the same kind of combination. Merging two fields in equal standing (Combinatio) is a fundamentally different intellectual operation from applying the methods of one field to the objects of another (Subordinatio), which is in turn different from inverting a field's core question and redirecting it (Inversio). The six operators are not arbitrary; they correspond to the actual ways in which interdisciplinary fields have historically emerged.

Llull's **Questions** (Utrum? Quid? De quo? Quare? — Whether? What? About what? Why?) become the generative queries that each operator produces when applied to a pair of disciplines. And Llull's goal — the generation of all possible truths — becomes the generation of all possible *disciplines*, with empirical validation replacing divine certainty.

## 3. The Six Operators

### 3.1 Combinatio

The simplest operator: merge two disciplines in equal standing. Both contribute their objects of study and their methods to a new synthesis.

This is how Bioinformatics emerged (Biology + Computer Science), how Biochemistry crystallized (Biology + Chemistry), how Political Economy formed (Politics + Economics). The resulting field is not subordinate to either parent; it synthesizes both.

### 3.2 Subordinatio

An asymmetric operator: apply the characteristic methods of discipline A to the objects of study of discipline B. The methods dominate; the objects receive.

Biophysics is the subordination of physics methods to biological objects. Econometrics is the subordination of statistical methods to economic objects. Mathematical linguistics is the subordination of formal mathematical methods to linguistic objects.

Note the asymmetry: applying biology's methods to physics objects would produce something quite different (and perhaps doesn't exist yet — a territory worth investigating).

### 3.3 Mediatio

Find a third discipline that serves as a bridge between two distant fields. The mediator shares conceptual, methodological, or ontological ground with both fields, providing a path where none existed directly.

Neuroeconomics required cognitive psychology as a mediator between neuroscience and economics. Computational social science required computer science as a mediator between the social sciences and formal modeling. In each case, the mediating discipline provided the conceptual vocabulary that allowed the two distant fields to communicate.

### 3.4 Amplificatio

Take a method native to a narrow, specialized field and extend it to broader or distant domains.

Cladistics originated in biological systematics as a method for reconstructing phylogenetic trees. Its amplification to linguistics produced phylogenetic linguistics — the reconstruction of language family trees using the same branching algorithms. Its amplification to manuscript studies produced stemmatology. The method was the same; the domain was new.

### 3.5 Quaestio

Transfer the fundamental question of one discipline to another. Not the methods, not the objects — the *question itself*.

Physics asks: "What symmetries govern this system?" Applied to social networks, this question generates the physics of networks. Evolutionary biology asks: "What selective pressures shaped this trait?" Applied to algorithms, this question generates evolutionary computation. The question acts as a lens that reveals structures in the target domain that its native practitioners never asked about.

### 3.6 Inversio

The most creative operator. Take the fundamental question of one discipline, invert its direction or subject-object relationship, and apply the inverted question to another field.

Biology asks: "How do organisms adapt to their environments?" Inversion: "How do environments adapt to organisms?" Applied to architecture, this generates biophilic design — the design of built environments that adapt to human biological needs rather than requiring humans to adapt to buildings.

Ecology asks: "How do ecosystems reach equilibrium?" Inversion: "How does equilibrium break down in ecosystems?" Applied to organizations, this generates the study of organizational collapse — a field that is, not coincidentally, the domain of our parallel project Seldon Corporate.

Inversio is the operator most likely to produce genuinely novel research questions because it reverses the direction of inquiry that each discipline takes for granted.

## 4. Plausibility and the Problem of Vacuity

Not all combinations are fertile. Combining "Mathematics" with "Culinary Arts" through Combinatio produces... what? Perhaps something, perhaps nothing. The system must distinguish plausible combinations from vacuous ones.

We propose a plausibility criterion based on **partial ontological overlap**. Every scientific discipline makes implicit assumptions about what kinds of entities exist (its ontology) and what kinds of causation it recognizes. These assumptions define the discipline's conceptual territory.

Two disciplines are most fertile when they share *some* ontological ground but not all of it. Full overlap means they are already the same discipline or close neighbors. Zero overlap means there is no shared conceptual surface on which methods can operate or questions can land. Partial overlap — sharing some assumptions about entities and causation while diverging on others — creates the productive tension from which new fields emerge.

This is not metaphor. Biophysics was possible because biology and physics both deal with material entities subject to physical forces, but biology adds the dimensions of evolution, function, and information that physics alone does not address. The partial overlap in ontological assumptions provided the foundation; the non-overlapping dimensions provided the novelty.

## 5. Bibliometric Validation

A hypothesis about a possible new field is only useful if we can assess whether anyone has already explored it. The system uses OpenAlex — a free, open index of over 250 million scientific publications — to classify every generated combination into one of five territory classes.

**Established** fields have tens of thousands of co-occurring publications. They are not discoveries; they are confirmations that the system's logic matches reality. **Emergent** fields have hundreds to low thousands of publications with a strong recent growth trend. These are the most immediately actionable for researchers seeking to join a rising tide. **Niche** fields have modest publication counts without growth — stable but small. **Incipient** fields have a handful of publications — someone has been there, but it's barely explored. And **Virgin Territories** have zero co-occurring publications: discipline pairs where the methods of one have never been applied to the objects of the other, where the questions of one have never been asked in the domain of the other.

It is in this last category that the system makes its most interesting contribution. Virgin territories that score high on plausibility represent the genuinely unexplored frontiers of human knowledge — places where the combination is not absurd but simply untried.

## 6. The System as a Knowledge Harness

Architecturally, Ars Magna Scientiarum is a domain-specific instance of a more general pattern we call a Knowledge Harness — a system that structures, connects, and navigates knowledge within a defined domain through typed nodes, scored relationships, and agent-mediated exploration.

The science graph is a typed-node graph where each node (discipline) carries structured properties: objects of study, methods, ontological assumptions, fundamental questions. The operators are agents that traverse this graph, generating hypotheses by combining node properties according to specific rules. The bibliometric validation layer provides evidence accumulation. The plausibility scoring provides a quality metric analogous to the NM_graph stability metric we use in other contexts.

This pattern is general. A Knowledge Harness for scientific disciplines uses OpenAlex as its data source and Lullian operators as its agents. A Knowledge Harness for organizational knowledge uses internal documents and extraction agents. A Knowledge Harness for brand contexts uses structured brand descriptions and compatibility agents. The architecture is the same; the domain defines the content.

## 7. Implications for the Agentic Economy

In the emerging economy of autonomous AI agents, a Lullian engine for scientific discovery is not merely an academic curiosity. It is a prototype of what agents will do at scale: navigate knowledge graphs, identify structural opportunities, generate hypotheses, and validate them against empirical data.

Consider a research funding agency that deploys an agent equipped with the Ars Magna to scan for high-plausibility virgin territories. The agent identifies that no one has applied network ecology methods to the dynamics of urban gentrification. It generates a research proposal outline, identifies potential collaborators from publication records, estimates the likelihood of productive outcomes based on analogous historical combinations, and presents the entire package to a human program officer for review.

This is not science fiction. Every component of this workflow exists today. What is missing is the systematic, exhaustive, validated combinatorial engine that generates the initial hypothesis — and that is precisely what the Ars Magna Scientiarum provides.

The broader thesis is that the bottleneck to agentic intelligence is not model capability but organizational infrastructure. Agents need structured knowledge graphs to navigate, typed operators to apply, and validation mechanisms to ground their outputs. The Ars Magna is one implementation of this infrastructure for one domain. The pattern generalizes.

## 8. Limitations and Honest Assessment

The system generates hypotheses, not validated scientific findings. A high plausibility score does not guarantee that a proposed combination will be productive. Science is not purely combinatorial; it requires empirical validation, theoretical coherence, and often the right person asking the right question at the right time.

The ontological enrichment of discipline nodes relies on LLM-generated properties, which introduces a layer of imprecision. While the objects-of-study and methods can be validated against publication abstracts, the ontological assumptions are more interpretive and may reflect the LLM's biases rather than the discipline's actual philosophical commitments.

The co-occurrence metric in OpenAlex measures publication overlap, not genuine methodological integration. Two concepts may co-occur in a paper's keyword tags without the paper actually combining the disciplines in any deep sense. Conversely, genuinely interdisciplinary work may not be tagged with both parent disciplines.

Finally, the system inherits the biases of its data source. OpenAlex, like all bibliometric databases, overrepresents English-language publications, STEM fields, and institutionally well-funded disciplines. The humanities, indigenous knowledge systems, and non-Western scientific traditions are underrepresented. A truly complete map of human knowledge would need to account for these gaps.

## 9. Conclusion: Cartographing the Unknown

The space of possible sciences is vastly larger than the space of actual sciences. Every time a new interdisciplinary field emerges — from biochemistry to neuroeconomics to computational social science — it is proof that a productive combination existed but had not yet been attempted.

The Ars Magna Scientiarum is a machine for making these latent possibilities visible. It does not replace the creative act of doing science; it augments it by showing where no one has looked. It is, in Llull's terms, a *machina inventiva* — a machine for invention — applied to the map of knowledge itself.

In the end, it fulfills the Lullian dream in a way Llull could not have imagined: a thinking machine that, instead of rotating wooden circles inscribed with divine attributes, navigates the graph of human knowledge and says: *Look, here is a combination no one has tried yet; perhaps a new science will grow there.*

---

*This work is part of the Agentic Economy framework. For the working system, see the Ars Magna Scientiarum repository at github.com/rainvare/ars-magna-scientiarum.*
