"""
backend.generation.generate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Module de génération. Appelle l'API Claude avec routage selon le régime de confiance.
"""

import anthropic

from backend.config import (
    get_settings,
    GenerationResult,
    ConfidenceRegime,
    FusedResult,
)
from backend.generation.prompts import (
    SYSTEM_PROMPT,
    build_generate_prompt,
    build_reuse_prompt,
    build_abstain_response,
)


def generate_answer(question: str, fused: FusedResult) -> GenerationResult:
    """
    Generate an answer based on the confidence regime.
    - HIGH: reuse/reformulate validated precedent
    - MEDIUM: generate grounded answer with citations
    - LOW: abstain, return best snippets for human expert
    """
    settings = get_settings()

    # LOW confidence → ABSTAIN (never generate)
    if fused.regime == ConfidenceRegime.LOW:
        return GenerationResult(
            answer=build_abstain_response(fused.results),
            sources=[
                {
                    "chunk_id": r.chunk_id,
                    "text": r.text[:200],
                    "collection": r.collection,
                }
                for r in fused.results[:3]
            ],
            confidence=fused.confidence,
            regime=fused.regime.value,
            abstained=True,
        )

    # HIGH confidence with QA match → REUSE
    if fused.regime == ConfidenceRegime.HIGH and fused.qa_match:
        prompt = build_reuse_prompt(question, fused.qa_match, fused.results)
    else:
        # MEDIUM confidence → GENERATE grounded answer
        prompt = build_generate_prompt(question, fused.results)

    # Call Claude
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.llm_model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    answer_text = response.content[0].text

    return GenerationResult(
        answer=answer_text,
        sources=[
            {
                "chunk_id": r.chunk_id,
                "text": r.text[:200],
                "collection": r.collection,
            }
            for r in fused.results
        ],
        confidence=fused.confidence,
        regime=fused.regime.value,
        abstained=False,
        qa_match_id=fused.qa_match.chunk_id if fused.qa_match else None,
    )
