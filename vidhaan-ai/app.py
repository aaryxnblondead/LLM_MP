"""Streamlit application for VidhaanAI."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, cast

import streamlit as st
from dotenv import load_dotenv

from core.document_processor import extract_text, detect_sections, classify_document_type
from core.language_utils import SUPPORTED_LANGUAGES
from core.llm_handler import simplify_document, cross_reference_sections
from core.rag_engine import RAGEngine
from scripts.build_vector_store import main as build_vector_store

DATA_DIR = Path(__file__).resolve().parent / "data"
BNS_CSV_PATH = Path(__file__).resolve().parent.parent / "bns_sections.csv"


def load_json(file_name: str) -> Any:
    """Load a JSON file from the data directory."""
    file_path = DATA_DIR / file_name
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_bns_csv() -> list[dict]:
    """Load BNS sections from the CSV dataset if available."""
    if not BNS_CSV_PATH.exists():
        return []

    sections: list[dict] = []
    with BNS_CSV_PATH.open("r", encoding="utf-8") as handle:
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
                }
            )
    return sections


@st.cache_resource
def get_rag_engine() -> RAGEngine:
    """Create a cached RAGEngine instance."""
    return RAGEngine()


@st.cache_data
def get_section_data() -> tuple[list[dict], list[dict], dict]:
    """Load IPC, BNS, and mapping data."""
    ipc_sections = cast(list[dict], load_json("ipc_sections.json"))
    bns_sections = load_bns_csv()
    if not bns_sections:
        bns_sections = cast(list[dict], load_json("bns_sections.json"))
    mapping = cast(dict, load_json("ipc_bns_mapping.json"))
    return ipc_sections, bns_sections, mapping


def render_tags(items: list[str], color: str) -> None:
    """Render tags for detected sections."""
    if not items:
        st.write("None detected")
        return

    tags = "".join(
        f"<span style='background:{color};color:white;padding:4px 8px;border-radius:12px;"
        f"margin-right:6px;font-size:12px;display:inline-block;'>{item}</span>"
        for item in items
    )
    st.markdown(tags, unsafe_allow_html=True)


def render_doc_type(doc_type: str) -> None:
    """Render a badge for the document type."""
    st.markdown(
        f"<span style='background:#333;color:white;padding:6px 12px;border-radius:12px;'>"
        f"{doc_type}</span>",
        unsafe_allow_html=True,
    )


def get_retrieved_context(rag: RAGEngine, query_text: str) -> str:
    """Retrieve relevant context for a query."""
    results = rag.query(query_text, law_type="both", k=5)
    return "\n\n".join(
        f"[{item['law_type']}] {item['content']}" for item in results
    )


def find_section_details(
    section_number: str, ipc_sections: list[dict], bns_sections: list[dict]
) -> dict | None:
    """Find section details by number across IPC and BNS."""
    for entry in ipc_sections:
        if entry["section_number"] == section_number:
            return {**entry, "law_type": "IPC"}
    for entry in bns_sections:
        if entry["section_number"] == section_number:
            return {**entry, "law_type": "BNS"}
    return None


def main() -> None:
    """Run the Streamlit app."""
    load_dotenv()
    st.set_page_config(page_title="VidhaanAI", layout="wide")

    st.markdown(
        """
        <style>
        .section-label { font-weight: 600; margin-top: 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.title("VidhaanAI")
    st.sidebar.caption("Indian Legal Documents, Simplified.")

    selected_language = st.sidebar.selectbox(
        "Language",
        SUPPORTED_LANGUAGES,
        index=0,
        help="Supports all 22 official Indian languages plus English.",
    )
    mode = st.sidebar.radio(
        "Compare Modes",
        ["Standard (RAG)", "Baseline (No RAG)"],
        index=0,
    )

    st.sidebar.info(
        "The IPC was replaced by the Bharatiya Nyaya Sanhita (BNS) on July 1, 2024. "
        "VidhaanAI cross-references IPC sections to their BNS equivalents."
    )

    rag = get_rag_engine()
    if not rag.is_index_built():
        st.warning("Vector index not found. Please build the index before analysis.")
        if st.button("Build Index"):
            with st.spinner("Building vector store..."):
                try:
                    build_vector_store()
                    st.success("Vector store built successfully.")
                except Exception as exc:
                    st.error(f"Failed to build vector store: {exc}")

    ipc_sections, bns_sections, mapping = get_section_data()

    tab1, tab2, tab3 = st.tabs([
        "📄 Document Analysis",
        "🔍 Section Lookup",
        "📊 Baseline Comparison",
    ])

    with tab1:
        st.subheader("Analyze a document")
        file = st.file_uploader(
            "Upload a PDF, TXT, or image",
            type=["pdf", "txt", "png", "jpg", "jpeg"],
            key="analysis_file",
        )
        raw_text = st.text_area("Or paste raw text", height=200, key="analysis_text")
        analyze_clicked = st.button("Analyze Document")

        if analyze_clicked:
            if not file and not raw_text.strip():
                st.warning("Please upload a file or paste text to analyze.")
            else:
                try:
                    text = extract_text(file) if file else raw_text.strip()
                except RuntimeError as exc:
                    st.error(
                        "OCR failed. Install Tesseract OCR and set TESSERACT_CMD if needed. "
                        f"Details: {exc}"
                    )
                    text = ""
                if not text:
                    st.warning(
                        "We could not extract any text from the uploaded file. "
                        "If this is a scanned PDF, OCR may be required."
                    )
                else:
                    doc_type = classify_document_type(text)
                    detected = detect_sections(text)
                    context = ""
                    if mode == "Standard (RAG)" and rag.is_index_built():
                        context = get_retrieved_context(rag, text[:2000])

                    with st.spinner("Generating explanation..."):
                        result = simplify_document(
                            text,
                            doc_type,
                            detected,
                            context,
                            selected_language,
                            baseline_mode=(mode == "Baseline (No RAG)"),
                        )
                    st.session_state["analysis_result"] = {
                        "doc_type": doc_type,
                        "detected": detected,
                        "cross_refs": result["cross_references"],
                        "explanation": result["explanation"],
                    }

        if "analysis_result" in st.session_state:
            result = st.session_state["analysis_result"]
            st.markdown("**Detected Document Type**")
            render_doc_type(result["doc_type"])

            st.markdown("**Detected IPC Sections**")
            render_tags(result["detected"]["ipc"], "#F39C12")

            st.markdown("**Detected BNS Sections**")
            render_tags(result["detected"]["bns"], "#3498DB")

            st.markdown("**IPC ↔ BNS Cross-Reference**")
            if result["cross_refs"]:
                st.table(result["cross_refs"])
            else:
                st.info("No cross-references available for the detected sections.")

            st.markdown("**Plain-Language Explanation**")
            st.write(result["explanation"])

            st.markdown(
                "<span style='color:red;font-weight:600;'>"
                "⚠️ This is a simplified explanation for informational purposes only. "
                "Please consult a qualified lawyer for legal advice."
                "</span>",
                unsafe_allow_html=True,
            )

    with tab2:
        st.subheader("Section lookup")
        lookup = st.text_input("Enter any IPC or BNS section number", key="lookup_input")
        lookup_clicked = st.button("Find Section")

        if lookup_clicked:
            normalized = lookup.replace("IPC", "").replace("BNS", "").strip().upper()
            details = find_section_details(normalized, ipc_sections, bns_sections)

            if not details:
                st.warning("Section not found in the current dataset.")
            else:
                st.markdown(f"**{details['law_type']} Section {details['section_number']}**")
                st.write(details["title"])
                st.write(details["description"])
                st.write(f"Punishment: {details['punishment']}")
                st.write(f"Category: {details['category']}")

                cross_refs = cross_reference_sections(
                    [details["section_number"]] if details["law_type"] == "IPC" else [],
                    [details["section_number"]] if details["law_type"] == "BNS" else [],
                )

                if cross_refs:
                    st.markdown("**Cross-Reference**")
                    st.table(cross_refs)
                else:
                    st.info("No cross-reference found for this section.")

    with tab3:
        st.subheader("Baseline vs RAG comparison")
        file_cmp = st.file_uploader(
            "Upload a PDF, TXT, or image",
            type=["pdf", "txt", "png", "jpg", "jpeg"],
            key="cmp_file",
        )
        raw_cmp_text = st.text_area("Or paste raw text", height=200, key="cmp_text")
        compare_clicked = st.button("Run Comparison")

        if compare_clicked:
            if not file_cmp and not raw_cmp_text.strip():
                st.warning("Please upload a file or paste text for comparison.")
            else:
                try:
                    text = extract_text(file_cmp) if file_cmp else raw_cmp_text.strip()
                except RuntimeError as exc:
                    st.error(
                        "OCR failed. Install Tesseract OCR and set TESSERACT_CMD if needed. "
                        f"Details: {exc}"
                    )
                    text = ""
                if not text:
                    st.warning(
                        "We could not extract any text from the uploaded file. "
                        "If this is a scanned PDF, OCR may be required."
                    )
                else:
                    doc_type = classify_document_type(text)
                    detected = detect_sections(text)
                    context = ""
                    if rag.is_index_built():
                        context = get_retrieved_context(rag, text[:2000])

                    with st.spinner("Generating comparison outputs..."):
                        standard = simplify_document(
                            text,
                            doc_type,
                            detected,
                            context,
                            selected_language,
                            baseline_mode=False,
                        )
                        baseline = simplify_document(
                            text,
                            doc_type,
                            detected,
                            "",
                            selected_language,
                            baseline_mode=True,
                        )

                    st.session_state["comparison_result"] = {
                        "standard": standard,
                        "baseline": baseline,
                        "detected": detected,
                    }

        if "comparison_result" in st.session_state:
            result = st.session_state["comparison_result"]
            st.caption("This comparison demonstrates the improvement RAG context provides.")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Standard (RAG)**")
                st.write(result["standard"]["explanation"])
            with col2:
                st.markdown("**Baseline (No RAG)**")
                st.write(result["baseline"]["explanation"])

            expected_bns = None
            ipc_list = result["detected"].get("ipc", [])
            if ipc_list:
                mapping_entry = mapping.get(f"IPC_{ipc_list[0]}")
                if mapping_entry:
                    expected_bns = mapping_entry["bns_section"]

            if expected_bns:
                baseline_text = result["baseline"]["explanation"].lower()
                indicator = "Yes" if expected_bns.lower() in baseline_text else "No"
                st.info(f"Baseline correctly identified BNS {expected_bns}: {indicator}")


if __name__ == "__main__":
    main()
