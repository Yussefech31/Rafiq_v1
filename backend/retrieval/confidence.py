"""
backend.retrieval.confidence
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Calcul du score de confiance composite et routage par régime.
"""

from backend.config import get_settings, FusedResult, ConfidenceRegime


def compute_confidence(fused: FusedResult) -> FusedResult:
    """
    Compute composite confidence score and assign regime.
    Formula: confidence = top_score * 0.6 + agreement_score * 0.4

    Regimes:
    - HIGH: near-identical validated precedent found (qa_match set)
    - MEDIUM: composite confidence >= low_threshold → generate grounded answer
    - LOW: otherwise → ABSTAIN
    """
    settings = get_settings()

    confidence = fused.top_score * 0.6 + fused.agreement_score * 0.4

    if fused.qa_match:
        regime = ConfidenceRegime.HIGH
    elif confidence >= settings.confidence_low_threshold:
        regime = ConfidenceRegime.MEDIUM
    else:
        regime = ConfidenceRegime.LOW

    fused.confidence = confidence
    fused.regime = regime
    return fused
