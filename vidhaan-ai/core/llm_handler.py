"""LLM handling and prompt orchestration for VidhaanAI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
import google.generativeai as genai

from .language_utils import get_language_instruction

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def simplify_document(
    text: str,
    doc_type: str,
    detected_sections: Dict[str, List[str]],
    retrieved_context: str,
    target_language: str,
    baseline_mode: bool = False,
) -> Dict:
    """Simplify a legal document using Gemini.

    Args:
        text: Raw document text.
        doc_type: Classified document type.
        detected_sections: IPC/BNS section references.
        retrieved_context: RAG context string.
        target_language: Language to respond in.
        baseline_mode: Whether to bypass RAG context.

    Returns:
        Dictionary containing explanation and metadata.
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    configure = getattr(genai, "configure", None)
    model_cls = getattr(genai, "GenerativeModel", None)
    if api_key and callable(configure):
        configure(api_key=api_key)
    language_instruction = get_language_instruction(target_language)

    if baseline_mode:
        system_prompt = (
            "You are VidhaanAI, an expert Indian legal assistant. "
    "You analyze legal documents in a neutral, professional manner. "
    "The text below is a legal record and may contain sensitive or criminal terms. "
    "Do not produce graphic or prohibited content. "
    "Only explain the legal meaning, obligations, risks, and section references."
            f"{language_instruction}"
        )
        user_prompt = (
            "Document type: {doc_type}\n\n"
    f"Detected sections: IPC={detected_sections.get('ipc', [])}, "
    f"BNS={detected_sections.get('bns', [])}\n\n"
    "Summarize the legal meaning of this document and explain it simply. "
    "Do not repeat graphic details from the text.\n\n"
    f"Document excerpt:\n{text[:4000]}"
        )
    else:
        system_prompt = (
            "You are VidhaanAI, an expert Indian legal assistant. You help ordinary citizens "
            "understand legal documents in simple, plain language.\n\n"
            "You have been provided with relevant sections from the Indian Penal Code (IPC) "
            "and the Bharatiya Nyaya Sanhita (BNS), which replaced the IPC on July 1, 2024.\n\n"
            "Your tasks:\n"
            "1. Explain the document in plain language that any layperson can understand\n"
            "2. Identify every legal section cited and explain what it means\n"
            "3. For every IPC section found, show its BNS equivalent (or state if no direct equivalent exists)\n"
            "4. For every BNS section found, show the original IPC section it replaced\n"
            "5. Highlight the key rights, obligations, or risks for the person reading this document\n"
            "6. Use the retrieved legal context provided to ensure accuracy. Do not hallucinate section numbers.\n"
            "7. Always end with: \"⚠️ This is a simplified explanation for informational purposes only. "
            "Please consult a qualified lawyer for legal advice.\"\n"
            f"8. {language_instruction}\n\n"
            "Retrieved Legal Context:\n"
            f"{retrieved_context}\n"
        )
        user_prompt = (
            f"Document type: {doc_type}\n\n"
            f"Detected sections: IPC={detected_sections.get('ipc', [])}, "
            f"BNS={detected_sections.get('bns', [])}\n\n"
            f"Document text:\n{text}"
        )

    try:
        if model_cls is None:
            raise RuntimeError("Gemini SDK is not available in this environment.")
        model = model_cls(
            model_name="gemini-2.5-flash",
            system_instruction=system_prompt,
        )
        response = model.generate_content(user_prompt)
        explanation = response.text or ""
    except Exception as exc:
        explanation = (
            "We ran into an issue while generating the explanation. "
            f"Please check your API key and try again. Details: {exc}"
        )

    cross_refs = cross_reference_sections(
        detected_sections.get("ipc", []), detected_sections.get("bns", [])
    )

    return {
        "explanation": explanation,
        "sections_found": detected_sections,
        "cross_references": cross_refs,
        "language": target_language,
    }


def cross_reference_sections(ipc_sections: List[str], bns_sections: List[str]) -> List[Dict]:
    """Generate IPC-BNS cross-reference cards for detected sections.

    Args:
        ipc_sections: List of IPC section numbers.
        bns_sections: List of BNS section numbers.

    Returns:
        List of cross-reference dictionaries.
    """
    mapping_path = DATA_DIR / "ipc_bns_mapping.json"
    if not mapping_path.exists():
        return []

    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    reverse_map = {value["bns_section"]: value for value in mapping.values()}

    cards: List[Dict] = []
    for ipc in ipc_sections:
        key = f"IPC_{ipc}"
        if key in mapping:
            entry = mapping[key]
            cards.append(
                {
                    "ipc_section": entry["ipc_section"],
                    "ipc_title": entry["ipc_title"],
                    "bns_section": entry["bns_section"],
                    "bns_title": entry["bns_title"],
                    "status": entry.get("status", "replaced"),
                }
            )

    for bns in bns_sections:
        entry = reverse_map.get(bns)
        if entry:
            cards.append(
                {
                    "ipc_section": entry["ipc_section"],
                    "ipc_title": entry["ipc_title"],
                    "bns_section": entry["bns_section"],
                    "bns_title": entry["bns_title"],
                    "status": entry.get("status", "replaced"),
                }
            )
        else:
            cards.append(
                {
                    "ipc_section": "Unknown",
                    "ipc_title": "No direct IPC reference found",
                    "bns_section": bns,
                    "bns_title": "Unknown",
                    "status": "unknown",
                }
            )

    return cards
