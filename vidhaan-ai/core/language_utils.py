"""Language detection helpers for VidhaanAI."""

from __future__ import annotations

from langdetect import detect, LangDetectException

SUPPORTED_LANGUAGES = ["English", "Hindi", "Marathi"]


def detect_language(text: str) -> str:
    """Detect the language of a given text.

    Args:
        text: Input text.

    Returns:
        Language name if supported, otherwise "Unknown".
    """
    if not text:
        return "Unknown"

    try:
        code = detect(text)
    except LangDetectException:
        return "Unknown"

    if code == "en":
        return "English"
    if code == "hi":
        return "Hindi"
    if code == "mr":
        return "Marathi"

    return "Unknown"


def get_language_instruction(lang: str) -> str:
    """Get a prompt instruction for the target language.

    Args:
        lang: Language name.

    Returns:
        Instruction string for the LLM.
    """
    if lang == "Hindi":
        return "Respond entirely in simple Hindi."
    if lang == "Marathi":
        return "Respond entirely in simple Marathi (Devanagari script)."

    return "Respond entirely in simple English."
