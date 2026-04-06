"""Document processing utilities for VidhaanAI."""

from __future__ import annotations

import re
from io import BytesIO
from typing import Dict, List

import pdfplumber


IPC_PATTERN = re.compile(
    r"(Section|Sec|S\.)?\s*(IPC)?\s*(\d{1,3}[A-Z]?)(\s*(IPC|of\s+IPC))?",
    re.IGNORECASE,
)
BNS_PATTERN = re.compile(
    r"(Section|Sec|S\.)?\s*(BNS)?\s*(\d{1,3}[A-Z]?)(\s*(BNS|of\s+BNS))?",
    re.IGNORECASE,
)


def extract_text(file) -> str:
    """Extract raw text from an uploaded PDF or TXT file.

    Args:
        file: Streamlit uploaded file object.

    Returns:
        Extracted text as a single string.
    """
    if file is None:
        return ""

    file_name = (file.name or "").lower()
    if file_name.endswith(".pdf"):
        with pdfplumber.open(BytesIO(file.getvalue())) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages).strip()

    raw_bytes = file.getvalue()
    try:
        return raw_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1").strip()


def detect_sections(text: str) -> Dict[str, List[str]]:
    """Detect IPC and BNS section references in the given text.

    Args:
        text: Raw document text.

    Returns:
        Dictionary with IPC and BNS section lists.
    """
    ipc_matches = [match[2].upper() for match in IPC_PATTERN.findall(text or "")]
    bns_matches = [match[2].upper() for match in BNS_PATTERN.findall(text or "")]

    ipc_sections = sorted({s for s in ipc_matches if s})
    bns_sections = sorted({s for s in bns_matches if s})

    return {"ipc": ipc_sections, "bns": bns_sections}


def classify_document_type(text: str) -> str:
    """Classify document type using keyword heuristics.

    Args:
        text: Raw document text.

    Returns:
        Document type label.
    """
    if not text:
        return "Unknown"

    lowered = text.lower()
    if "first information report" in lowered or "fir" in lowered:
        return "FIR"
    if "rent" in lowered and "agreement" in lowered:
        return "Rental Agreement"
    if "right to information" in lowered or "rti" in lowered:
        return "RTI Application"
    if "legal notice" in lowered:
        return "Legal Notice"
    if "order" in lowered and "court" in lowered:
        return "Court Order"

    return "Unknown"
