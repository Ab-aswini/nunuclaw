"""Text-to-speech stub — placeholder for Phase 2+ voice output."""

from __future__ import annotations


async def text_to_speech(text: str, language: str = "en") -> str | None:
    """Convert text to speech audio file.

    Phase 1: Returns None (not implemented).
    Phase 2+: Will use Edge-TTS or Piper for voice output.

    Args:
        text: Text to speak.
        language: Language code for voice.

    Returns:
        Path to audio file, or None if not available.
    """
    # Not implemented in Phase 1
    return None
