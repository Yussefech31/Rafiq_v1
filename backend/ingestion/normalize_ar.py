"""Arabic text normalization utilities for RAFIQ."""
import re
import unicodedata


# Arabic diacritics (tashkeel) range
_TASHKEEL_RE = re.compile(r'[\u064B-\u065F\u0670]')

# Alef variants → plain alef
_ALEF_VARIANTS = {
    '\u0623': '\u0627',  # أ → ا
    '\u0625': '\u0627',  # إ → ا
    '\u0622': '\u0627',  # آ → ا
}

# Tatweel (kashida)
_TATWEEL = '\u0640'

# Teh marbuta → heh
_TEH_MARBUTA = '\u0629'
_HEH = '\u0647'

# Multiple whitespace
_MULTI_SPACE_RE = re.compile(r'\s+')


def normalize_arabic(text: str, normalize_teh_marbuta: bool = False) -> str:
    """
    Apply light Arabic text normalization.

    - Remove tashkeel (diacritics)
    - Normalize alef variants (أ إ آ → ا)
    - Remove tatweel/kashida (ـ)
    - Optionally normalize teh marbuta (ة → ه)
    - Collapse multiple whitespace
    - Strip leading/trailing whitespace
    - Preserves non-Arabic characters (French, numbers, etc.)

    Args:
        text: Input text (may be mixed Arabic/French).
        normalize_teh_marbuta: If True, replace ة with ه.

    Returns:
        Normalized text string.
    """
    if not text:
        return ""

    # Remove tashkeel
    text = _TASHKEEL_RE.sub('', text)

    # Normalize alef variants
    for variant, replacement in _ALEF_VARIANTS.items():
        text = text.replace(variant, replacement)

    # Remove tatweel
    text = text.replace(_TATWEEL, '')

    # Optionally normalize teh marbuta
    if normalize_teh_marbuta:
        text = text.replace(_TEH_MARBUTA, _HEH)

    # Collapse whitespace
    text = _MULTI_SPACE_RE.sub(' ', text)

    # Strip
    text = text.strip()

    return text


def detect_text_direction(text: str) -> str:
    """
    Detect if text is primarily RTL (Arabic) or LTR (French/Latin).

    Returns:
        'rtl' if majority Arabic characters, 'ltr' otherwise.
    """
    if not text:
        return 'ltr'

    arabic_count = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    latin_count = sum(1 for c in text if c.isascii() and c.isalpha())

    return 'rtl' if arabic_count > latin_count else 'ltr'
