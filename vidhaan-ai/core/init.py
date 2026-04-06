"""Core package exports for VidhaanAI."""

from .document_processor import extract_text, detect_sections, classify_document_type
from .language_utils import detect_language, get_language_instruction, SUPPORTED_LANGUAGES
from .rag_engine import RAGEngine
from .llm_handler import simplify_document, cross_reference_sections

__all__ = [
    "extract_text",
    "detect_sections",
    "classify_document_type",
    "detect_language",
    "get_language_instruction",
    "SUPPORTED_LANGUAGES",
    "RAGEngine",
    "simplify_document",
    "cross_reference_sections",
]
