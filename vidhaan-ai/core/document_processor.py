"""Document processing utilities for VidhaanAI."""

from __future__ import annotations

import re
from io import BytesIO
from typing import Dict, List

import pdfplumber
import pytesseract
from PIL import Image


IPC_PATTERN = re.compile(
    r"(Section|Sec|S\.)?\s*(IPC)?\s*(\d{1,3}[A-Z]?)(\s*(IPC|of\s+IPC))?",
    re.IGNORECASE,
)
BNS_PATTERN = re.compile(
    r"(Section|Sec|S\.)?\s*(BNS)?\s*(\d{1,3}[A-Z]?)(\s*(BNS|of\s+BNS))?",
    re.IGNORECASE,
)


def _ocr_image(image: Image.Image) -> str:
    """Run OCR on a PIL image and return extracted text."""
    try:
        return pytesseract.image_to_string(image)
    except Exception:
        return ""


def extract_text(file) -> str:
    """Extract raw text from an uploaded PDF, TXT, or image file.

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
            extracted = "\n".join(pages).strip()

            if extracted:
                return extracted

            ocr_pages = []
            for page in pdf.pages:
                page_image = page.to_image(resolution=300).original
                ocr_pages.append(_ocr_image(page_image))
            return "\n".join(ocr_pages).strip()

    if file_name.endswith((".png", ".jpg", ".jpeg")):
        image = Image.open(BytesIO(file.getvalue()))
        return _ocr_image(image).strip()

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
