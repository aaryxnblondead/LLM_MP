# VidhaanAI

VidhaanAI is a multilingual Indian legal document simplifier with IPC-to-BNS cross-referencing using RAG. It helps everyday users understand legal documents in plain language and highlights the mapped provisions between the Indian Penal Code (IPC) and the Bharatiya Nyaya Sanhita (BNS).

## Features
- Streamlit-based UI for document analysis, section lookup, and baseline comparison
- RAG pipeline using LangChain + ChromaDB with Gemini embeddings
- IPC-to-BNS cross-referencing with curated section metadata
- Multilingual output in all 22 official Indian languages, plus English

## Supported Languages
Assamese, Bengali, Bodo, Dogri, Gujarati, Hindi, Kannada, Kashmiri, Konkani, Maithili, Malayalam, Manipuri, Marathi, Nepali, Odia, Punjabi, Sanskrit, Santali, Sindhi, Tamil, Telugu, Urdu, and English.

## Setup
1. Install dependencies:
   - `pip install -r requirements.txt`
2. Create a `.env` file and add your API key:
   - `GEMINI_API_KEY=your_gemini_api_key_here`
   - Optional: `GEMINI_EMBEDDING_MODEL=models/embedding-001`
3. Build the vector store (one-time step):
   - `python scripts/build_vector_store.py`
4. Run the Streamlit app:
   - `streamlit run app.py`

## Architecture
- `core/document_processor.py` handles PDF/text extraction and section detection.
- `core/rag_engine.py` manages ChromaDB collections and retrieval.
- `core/llm_handler.py` orchestrates Gemini prompts and IPC/BNS cross-references.
- `scripts/build_vector_store.py` builds the vector index from curated section data.
- `app.py` provides the Streamlit UI and wires all components together.

## IPC to BNS Transition
The IPC was replaced by the Bharatiya Nyaya Sanhita (BNS) on July 1, 2024. This project provides quick references between commonly cited IPC sections and their BNS equivalents.

## Disclaimer
This application provides simplified legal explanations for informational purposes only. It is not legal advice. Always consult a qualified lawyer for legal matters.
