"""
backend.generation.prompts
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Templates de prompts pour la génération fondée sur les documents.
CRITIQUE : chaque affirmation doit citer un chunk_id source.
"""

from typing import Any


SYSTEM_PROMPT = """Tu es RAFIQ, un assistant administratif du Ministère de la Transition Numérique du Maroc.
Tu réponds aux questions administratives en te basant UNIQUEMENT sur les documents fournis.

Règles strictes :
1. Chaque affirmation doit citer sa source avec [source: chunk_id].
2. Ne génère JAMAIS d'information qui n'est pas dans les documents fournis.
3. Si les documents ne contiennent pas assez d'information, dis-le explicitement.
4. Réponds en français ou en arabe selon la langue de la question.
5. Utilise un ton formel et administratif."""

GENERATE_PROMPT = """Question posée : {question}

Documents pertinents trouvés :
{context}

Rédige une réponse administrative formelle et complète.
Chaque affirmation DOIT citer sa source avec [source: chunk_id].
Si l'information est insuffisante, indique clairement les lacunes."""

REUSE_PROMPT = """Question posée : {question}

Une réponse validée similaire a été trouvée dans les précédents :

Question précédente : {precedent_question}
Réponse validée : {precedent_answer}
[source: {precedent_id}]

Documents complémentaires :
{context}

Reformule cette réponse validée pour répondre à la nouvelle question.
Cite le précédent avec [source: {precedent_id}] et tout document complémentaire utilisé."""

ABSTAIN_MESSAGE = """Le système n'a pas trouvé de documents suffisamment pertinents pour répondre à cette question de manière fiable.

Cette question a été escaladée à un expert humain pour validation.

Meilleurs extraits trouvés (pour référence de l'expert) :
{best_snippets}"""


def format_context(results: list[Any]) -> str:
    """Format search results into context string for the prompt."""
    parts: list[str] = []
    for r in results:
        collection = getattr(r, "collection", "unknown")
        parts.append(
            f"[{r.chunk_id}] (score: {r.score:.3f}, collection: {collection})\n{r.text}"
        )
    return "\n\n---\n\n".join(parts)


def build_generate_prompt(question: str, results: list[Any]) -> str:
    """Build the generation prompt with question and formatted context."""
    return GENERATE_PROMPT.format(
        question=question,
        context=format_context(results),
    )


def build_reuse_prompt(question: str, qa_match: Any, results: list[Any]) -> str:
    """Build the reuse prompt with precedent info and complementary context."""
    return REUSE_PROMPT.format(
        question=question,
        precedent_question=qa_match.metadata.get("question", ""),
        precedent_answer=qa_match.text,
        precedent_id=qa_match.chunk_id,
        context=format_context(
            [r for r in results if r.chunk_id != qa_match.chunk_id]
        ),
    )


def build_abstain_response(results: list[Any]) -> str:
    """Build the abstain response with best available snippets."""
    snippets = (
        format_context(results[:3]) if results else "Aucun document trouvé."
    )
    return ABSTAIN_MESSAGE.format(best_snippets=snippets)
