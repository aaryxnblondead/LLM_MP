"""Language detection helpers for VidhaanAI."""

from __future__ import annotations

import re

from langdetect import detect, LangDetectException


OFFICIAL_INDIAN_LANGUAGES = [
    "Assamese",
    "Bengali",
    "Bodo",
    "Dogri",
    "Gujarati",
    "Hindi",
    "Kannada",
    "Kashmiri",
    "Konkani",
    "Maithili",
    "Malayalam",
    "Manipuri",
    "Marathi",
    "Nepali",
    "Odia",
    "Punjabi",
    "Sanskrit",
    "Santali",
    "Sindhi",
    "Tamil",
    "Telugu",
    "Urdu",
]

SUPPORTED_LANGUAGES = ["English", *OFFICIAL_INDIAN_LANGUAGES]

_LANGUAGE_CODE_TO_NAME = {
    "en": "English",
    "bn": "Bengali",
    "gu": "Gujarati",
    "hi": "Hindi",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Marathi",
    "ne": "Nepali",
    "pa": "Punjabi",
    "ta": "Tamil",
    "te": "Telugu",
    "ur": "Urdu",
}

_LANGUAGE_INSTRUCTIONS = {
    "English": "Respond entirely in simple English.",
    "Assamese": "Respond entirely in simple Assamese. Use Assamese/Bengali script.",
    "Bengali": "Respond entirely in simple Bengali. Use Bengali script.",
    "Bodo": "Respond entirely in simple Bodo. Use Devanagari script.",
    "Dogri": "Respond entirely in simple Dogri. Use Devanagari script.",
    "Gujarati": "Respond entirely in simple Gujarati. Use Gujarati script.",
    "Hindi": "Respond entirely in simple Hindi. Use Devanagari script.",
    "Kannada": "Respond entirely in simple Kannada. Use Kannada script.",
    "Kashmiri": "Respond entirely in simple Kashmiri. Use Perso-Arabic script.",
    "Konkani": "Respond entirely in simple Konkani. Use Devanagari script.",
    "Maithili": "Respond entirely in simple Maithili. Use Devanagari script.",
    "Malayalam": "Respond entirely in simple Malayalam. Use Malayalam script.",
    "Manipuri": "Respond entirely in simple Manipuri. Use Meitei Mayek script when possible.",
    "Marathi": "Respond entirely in simple Marathi. Use Devanagari script.",
    "Nepali": "Respond entirely in simple Nepali. Use Devanagari script.",
    "Odia": "Respond entirely in simple Odia. Use Odia script.",
    "Punjabi": "Respond entirely in simple Punjabi. Use Gurmukhi script.",
    "Sanskrit": "Respond entirely in simple Sanskrit. Use Devanagari script.",
    "Santali": "Respond entirely in simple Santali. Use Ol Chiki script when possible.",
    "Sindhi": "Respond entirely in simple Sindhi. Use Arabic script.",
    "Tamil": "Respond entirely in simple Tamil. Use Tamil script.",
    "Telugu": "Respond entirely in simple Telugu. Use Telugu script.",
    "Urdu": "Respond entirely in simple Urdu. Use Perso-Arabic script.",
}

_SCRIPT_PATTERNS = {
    "Gujarati": re.compile(r"[\u0A80-\u0AFF]"),
    "Punjabi": re.compile(r"[\u0A00-\u0A7F]"),
    "Odia": re.compile(r"[\u0B00-\u0B7F]"),
    "Tamil": re.compile(r"[\u0B80-\u0BFF]"),
    "Telugu": re.compile(r"[\u0C00-\u0C7F]"),
    "Kannada": re.compile(r"[\u0C80-\u0CFF]"),
    "Malayalam": re.compile(r"[\u0D00-\u0D7F]"),
    "Manipuri": re.compile(r"[\uAAE0-\uAAFF\uABC0-\uABFF]"),
    "Santali": re.compile(r"[\u1C50-\u1C7F]"),
}

_DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")
_BENGALI_ASSAMESE_PATTERN = re.compile(r"[\u0980-\u09FF]")
_ARABIC_SCRIPT_PATTERN = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")

_ASSAMESE_MARKERS = re.compile(r"[\u09F0\u09F1]")
_SINDHI_MARKERS = re.compile(r"[\u067B\u067D\u0684\u068A\u068D\u06B1\u06B3\u06BB]")
_KASHMIRI_MARKERS = re.compile(r"[\u0672\u0673\u067F\u06C2\u0620]")


def _infer_language_from_script(text: str) -> str | None:
    """Infer language from script ranges when langdetect has no direct mapping."""
    for language, pattern in _SCRIPT_PATTERNS.items():
        if pattern.search(text):
            return language

    if _BENGALI_ASSAMESE_PATTERN.search(text):
        if _ASSAMESE_MARKERS.search(text):
            return "Assamese"
        return "Bengali"

    if _ARABIC_SCRIPT_PATTERN.search(text):
        if _SINDHI_MARKERS.search(text):
            return "Sindhi"
        if _KASHMIRI_MARKERS.search(text):
            return "Kashmiri"
        return "Urdu"

    if _DEVANAGARI_PATTERN.search(text):
        # Devanagari is shared by several scheduled languages; default to Hindi.
        return "Hindi"

    return None


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
        code = ""

    language = _LANGUAGE_CODE_TO_NAME.get(code)
    if language:
        return language

    inferred = _infer_language_from_script(text)
    if inferred:
        return inferred

    return "Unknown"


def get_language_instruction(lang: str) -> str:
    """Get a prompt instruction for the target language.

    Args:
        lang: Language name.

    Returns:
        Instruction string for the LLM.
    """
    normalized = (lang or "").strip()
    if not normalized:
        return _LANGUAGE_INSTRUCTIONS["English"]

    instruction = _LANGUAGE_INSTRUCTIONS.get(normalized)
    if instruction:
        return instruction

    lowered = normalized.casefold()
    for language_name, language_instruction in _LANGUAGE_INSTRUCTIONS.items():
        if language_name.casefold() == lowered:
            return language_instruction

    return f"Respond entirely in simple {normalized}."
