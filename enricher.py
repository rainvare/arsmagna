"""
Ars Magna Scientiarum — Enriquecedor Groq
==========================================
Enriquece hipótesis generadas por el motor luliano usando Groq/Llama 3.3 70B.
Cada operador tiene su propio prompt y temperatura calibrada.

Uso:
    from enricher import enriquecer_hipotesis
    groq_data = enriquecer_hipotesis(h)
    h.groq_data = groq_data
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

# Configuración por operador: (descripción del rol, temperatura)
OPERATOR_CONFIG = {
    "combinatio":   ("fusión igualitaria entre dos disciplinas", 0.4),
    "subordinatio": ("aplicación asimétrica de métodos de A sobre objetos de B", 0.4),
    "mediatio":     ("disciplina puente que conecta dos campos distantes", 0.5),
    "amplificatio": ("extensión de métodos estrechos a dominios amplios y distantes", 0.6),
    "quaestio":     ("transferencia de preguntas fundamentales de un campo a otro", 0.5),
    "inversio":     ("hipótesis contraintuitiva que invierte la relación esperada", 0.8),
    "scan":         ("intersección inexplorada identificada bibliométricamente", 0.5),
}

SYSTEM_PROMPT = """Eres un científico experto en interdisciplinariedad y bibliometría.
Recibes hipótesis generadas combinatoriamente y debes enriquecerlas con análisis crítico.
Responde EXCLUSIVAMENTE con JSON válido. Sin markdown, sin texto extra, sin backticks."""

ENRICHMENT_TEMPLATE = """Hipótesis interdisciplinaria ({role}):

Nombre sugerido: {name}
Descripción: {description}
Disciplina A: {disc_a}
Disciplina B: {disc_b}
Operador: {operator}
Plausibilidad calculada: {plausibility:.3f}
Publicaciones en intersección: {co_occurrence:,}

Devuelve exactamente este JSON (sin modificar las claves):
{{
  "hipotesis_formal": "Hipótesis falseable en formato Si [condición medible], entonces [resultado específico] porque [mecanismo causal]. Sin generalidades.",
  "mecanismo": "Mecanismo causal o analógico que justifica la combinación. 2-3 oraciones concretas.",
  "keywords_busqueda": ["término1", "término2", "término3", "término4", "término5"],
  "pregunta_empirica": "Una pregunta de investigación concreta y operacionalizable derivada de esta hipótesis.",
  "disciplinas_auxiliares": ["disciplina que aportaría metodología o datos clave"],
  "score_originalidad": 7,
  "riesgo_principal": "Principal obstáculo epistemológico o metodológico para esta combinación."
}}"""


def enriquecer_hipotesis(h) -> dict:
    """
    Enriquece un objeto Hypothesis con análisis Groq.
    
    Params:
        h: objeto Hypothesis con campos .suggested_name, .description,
           .operator, .discipline_a_name, .discipline_b_name,
           .plausibility_score, .co_occurrence_total
    
    Returns:
        dict con campos de enriquecimiento, o {} si hay error.
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        logger.warning("GROQ_API_KEY no encontrada — enriquecimiento deshabilitado.")
        return {}

    role, temperature = OPERATOR_CONFIG.get(
        h.operator, ("combinación interdisciplinaria", 0.5))

    prompt = ENRICHMENT_TEMPLATE.format(
        role=role,
        name=h.suggested_name,
        description=h.description,
        disc_a=h.discipline_a_name,
        disc_b=h.discipline_b_name,
        operator=h.operator,
        plausibility=h.plausibility_score,
        co_occurrence=h.co_occurrence_total,
    )

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=700,
        )

        raw = resp.choices[0].message.content.strip()
        # Limpiar posibles backticks si el modelo los incluye igual
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)

    except json.JSONDecodeError as e:
        logger.error(f"Groq devolvió JSON inválido: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error en enriquecimiento Groq: {e}")
        return {}


def enriquecer_lote(hypotheses: list, max_enrichments: int = 6) -> list:
    """
    Enriquece un lote de hipótesis (máx. max_enrichments para controlar costos).
    Prioriza las de mayor plausibilidad.
    
    Returns:
        Lista de hipótesis con .groq_data asignado.
    """
    # Ordenar por plausibilidad y tomar las mejores
    ordenadas = sorted(hypotheses, key=lambda h: h.plausibility_score, reverse=True)
    
    for i, h in enumerate(ordenadas):
        if i >= max_enrichments:
            h.groq_data = {}
            continue
        h.groq_data = enriquecer_hipotesis(h)
    
    return ordenadas
