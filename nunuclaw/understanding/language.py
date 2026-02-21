"""Language detection — identifies the language of user input.

Phase 1: Simple heuristic-based detection.
Phase 2+: fasttext lid.176.bin for accurate multilingual detection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Common Hindi characters (Devanagari Unicode range)
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

# Common Tamil characters
_TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]")

# Common Telugu characters
_TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]")

# Common Bengali characters
_BENGALI_RE = re.compile(r"[\u0980-\u09FF]")

# Common Kannada characters
_KANNADA_RE = re.compile(r"[\u0C80-\u0CFF]")

# Common Malayalam characters
_MALAYALAM_RE = re.compile(r"[\u0D00-\u0D7F]")

# Common Gujarati characters
_GUJARATI_RE = re.compile(r"[\u0A80-\u0AFF]")

# Common Odia characters
_ODIA_RE = re.compile(r"[\u0B00-\u0B7F]")

_SCRIPT_MAP: list[tuple[re.Pattern, str]] = [
    (_DEVANAGARI_RE, "hi"),
    (_TAMIL_RE, "ta"),
    (_TELUGU_RE, "te"),
    (_BENGALI_RE, "bn"),
    (_KANNADA_RE, "kn"),
    (_MALAYALAM_RE, "ml"),
    (_GUJARATI_RE, "gu"),
    (_ODIA_RE, "or"),
]


@dataclass
class LanguageResult:
    """Result of language detection."""

    code: str           # ISO 639-1 language code (e.g., "hi", "en", "ta")
    name: str           # Human-readable name
    confidence: float   # 0.0 to 1.0
    is_mixed: bool      # Code-mixed text (e.g., Hinglish)


_LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "kn": "Kannada",
    "ml": "Malayalam",
    "gu": "Gujarati",
    "or": "Odia",
    "mr": "Marathi",
    "pa": "Punjabi",
}


def detect_language(text: str) -> LanguageResult:
    """Detect the language of the given text.

    Phase 1 implementation uses Unicode script detection.
    Works well for identifying Hindi, Tamil, Telugu, etc. from Devanagari/Tamil scripts.
    Falls back to English for Latin-script text.

    Args:
        text: The input text to analyze.

    Returns:
        LanguageResult with detected language code, name, confidence, and mixed flag.
    """
    if not text or not text.strip():
        return LanguageResult(code="en", name="English", confidence=0.5, is_mixed=False)

    total_chars = len(text.replace(" ", ""))
    if total_chars == 0:
        return LanguageResult(code="en", name="English", confidence=0.5, is_mixed=False)

    # Count script characters
    script_counts: dict[str, int] = {}
    for pattern, lang_code in _SCRIPT_MAP:
        count = len(pattern.findall(text))
        if count > 0:
            script_counts[lang_code] = count

    # No non-Latin scripts found → English
    if not script_counts:
        return LanguageResult(code="en", name="English", confidence=0.8, is_mixed=False)

    # Find dominant script
    dominant_lang = max(script_counts, key=script_counts.get)  # type: ignore[arg-type]
    dominant_count = script_counts[dominant_lang]
    script_ratio = dominant_count / total_chars

    # Check for code-mixing (e.g., Hinglish = Hindi script + Latin letters)
    is_mixed = 0.1 < script_ratio < 0.7

    confidence = min(0.95, script_ratio + 0.3) if not is_mixed else 0.6

    return LanguageResult(
        code=dominant_lang,
        name=_LANGUAGE_NAMES.get(dominant_lang, dominant_lang),
        confidence=confidence,
        is_mixed=is_mixed,
    )
