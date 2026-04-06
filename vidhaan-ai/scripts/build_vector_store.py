"""Build the ChromaDB vector store for VidhaanAI."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.rag_engine import RAGEngine

DATA_DIR = PROJECT_ROOT / "data"
BNS_CSV_PATH = PROJECT_ROOT.parent / "bns_sections.csv"


def load_sections(file_path: Path, law_type: str) -> list[dict]:
    """Load section data from JSON and attach law_type."""
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    return [{**entry, "law_type": law_type} for entry in raw]


def load_bns_sections_from_csv(file_path: Path) -> list[dict]:
    """Load BNS sections from the provided CSV dataset."""
    if not file_path.exists():
        raise FileNotFoundError(
            f"BNS CSV dataset not found at {file_path}. Please place bns_sections.csv in the repo root."
        )

    sections: list[dict] = []
    with file_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            section_number = (row.get("Section") or "").strip()
            section_name = (row.get("Section _name") or row.get("Section_name") or "").strip()
            description = (row.get("Description") or "").strip()
            category = (row.get("Chapter_name") or "").strip().lower() or "general"

            if not section_number or not description:
                continue

            sections.append(
                {
                    "section_number": section_number,
                    "title": section_name or f"Section {section_number}",
                    "description": description,
                    "punishment": "Not specified in dataset",
                    "category": category,
                    "law_type": "BNS",
                }
            )
    return sections


def build_documents(sections: list[dict]) -> list[dict]:
    """Convert section data into RAG-ready documents."""
    documents = []
    for entry in sections:
        content = (
            f"Section {entry['section_number']}: {entry['title']}\n"
            f"Description: {entry['description']}\n"
            f"Punishment: {entry['punishment']}\n"
            f"Category: {entry['category']}"
        )
        metadata = {
            "source": entry.get("source", "legal_corpus"),
            "section_number": entry["section_number"],
            "law_type": entry["law_type"],
        }
        documents.append(
            {
                "content": content,
                "metadata": metadata,
                "law_type": entry["law_type"],
            }
        )
    return documents


def main() -> None:
    """Build the vector store if not already present."""
    load_dotenv()
    rag = RAGEngine()

    if rag.is_index_built():
        print("Vector store already exists. Skipping rebuild.")
        return

    ipc_file = DATA_DIR / "ipc_sections.json"
    bns_file = DATA_DIR / "bns_sections.json"

    ipc_sections = load_sections(ipc_file, "IPC")
    if BNS_CSV_PATH.exists():
        bns_sections = load_bns_sections_from_csv(BNS_CSV_PATH)
    else:
        bns_sections = load_sections(bns_file, "BNS")

    documents = build_documents(ipc_sections + bns_sections)
    rag.build_index(documents)

    print(f"Stored {len(documents)} documents in the vector store.")


if __name__ == "__main__":
    main()
