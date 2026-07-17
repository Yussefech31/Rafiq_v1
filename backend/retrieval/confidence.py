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
    - HIGH (>= high_threshold): near-identical precedent found → reuse
    - MEDIUM (>= low_threshold): relevant docs → generate grounded answer
    - LOW (< low_threshold): nothing relevant → ABSTAIN
    """
    settings = get_settings()

    # Composite confidence
    confidence = fused.top_score * 0.6 + fused.agreement_score * 0.4

    # Regime assignment
    if fused.qa_match and confidence >= settings.confidence_high_threshold:
        regime = ConfidenceRegime.HIGH
    elif confidence >= settings.confidence_low_threshold:
        regime = ConfidenceRegime.MEDIUM
    else:
        regime = ConfidenceRegime.LOW

    # Update fused result
    fused.confidence = confidence
    fused.regime = regime
    return fused
