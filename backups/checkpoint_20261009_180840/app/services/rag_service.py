"""Document indexing, retrieval and grounded prompt construction."""
from datetime import datetime, timezone
import json
import logging
import json
from pathlib import Path
from app.config import get_settings
from app.services.chunk_service import chunk_pages, clean_text
from app.services.embedding_service import get_embedding_provider
from app.services.ollama_service import generate
from app.services.pdf_service import extract_pdf
from app.services import qdrant_service

logger = logging.getLogger(__name__)
_documents: dict[str, dict] = {}
_chunks: dict[str, list[dict]] = {}


def load_saved_documents() -> None:
    """Restore the ready document library from processed metadata after restart."""
    directory = get_settings().processed_dir
    directory.mkdir(parents=True, exist_ok=True)
    for metadata_path in directory.glob("*.json"):
        try:
            saved = json.loads(metadata_path.read_text(encoding="utf-8"))
            doc = saved.get("document")
            if doc and Path(doc.get("path", "")).exists():
                _documents[doc["document_id"]] = doc
                _chunks[doc["document_id"]] = saved.get("chunks", [])
        except (OSError, ValueError, KeyError) as exc:
            logger.warning("could not restore processed document metadata path=%s error=%s", metadata_path.name, exc)


def documents() -> list[dict]:
    return list(_documents.values())


def get_document(document_id: str) -> dict | None:
    return _documents.get(document_id)


def chunks_for(document_id: str | None = None) -> list[dict]:
    if document_id:
        return list(_chunks.get(document_id, []))
    return [chunk for group in _chunks.values() for chunk in group]


def process_document(document_id: str) -> None:
    doc = _documents.get(document_id)
    if not doc:
        return
    settings = get_settings()
    try:
        doc["status"] = "EXTRACTING"
        pages = extract_pdf(doc["path"], document_id, doc["filename"])
        doc["status"] = "CLEANING"
        text = "\n\n".join(page["text"] for page in pages)
        (settings.processed_dir / f"{document_id}.txt").write_text(text, encoding="utf-8")
        doc["status"] = "CHUNKING"
        made = chunk_pages(pages, document_id, doc["filename"], settings.chunk_size, settings.chunk_overlap)
        _chunks[document_id] = made
        doc.update({"pages": len(pages), "chunks": len(made), "status": "EMBEDDING"})
        provider = get_embedding_provider()
        vectors = provider.embed([chunk["text"] for chunk in made])
        doc["status"] = "INDEXING"
        qdrant_service.upsert_chunks(made, vectors)
        doc.update({"status": "READY", "indexed_at": datetime.now(timezone.utc).isoformat(), "error": None})
        (settings.processed_dir / f"{document_id}.json").write_text(json.dumps({"document": doc, "pages": pages, "chunks": made}, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("indexed document id=%s chunks=%d", document_id, len(made))
    except Exception as exc:
        doc.update({"status": "ERROR", "error": str(exc)})
        logger.exception("document processing failed id=%s", document_id)


def register_document(document_id: str, filename: str, path: str) -> dict:
    doc = {"document_id": document_id, "filename": filename, "path": path,
           "status": "UPLOADED", "pages": 0, "chunks": 0, "indexed_at": None, "error": None}
    _documents[document_id] = doc
    return doc


def remove_document(document_id: str) -> bool:
    doc = _documents.pop(document_id, None)
    _chunks.pop(document_id, None)
    if not doc:
        return False
    qdrant_service.delete_document(document_id)
    for path in (Path(doc["path"]), get_settings().processed_dir / f"{document_id}.txt", get_settings().processed_dir / f"{document_id}.json"):
        path.unlink(missing_ok=True)
    return True


def preview_chunks(path: str, document_id: str, filename: str, chunk_size: int, chunk_overlap: int) -> tuple[list[dict], list[dict]]:
    pages = extract_pdf(path, document_id, filename)
    for page in pages:
        page["cleaned_text"] = clean_text(page["text"])
    return pages, chunk_pages(pages, document_id, filename, chunk_size, chunk_overlap)


def query(question: str, top_k: int = 3, score_threshold: float = 0.0) -> dict:
    provider = get_embedding_provider()
    query_vector = provider.embed([question])[0]
    points = qdrant_service.search(query_vector, top_k)
    results = [{"score": float(point.score), **(point.payload or {})} for point in points if float(point.score) >= score_threshold]
    logger.info("rag retrieval complete top_k=%d matches=%d threshold=%.3f", top_k, len(results), score_threshold)
    context = "\n\n".join(f"[Source: {item.get('filename')}, page {item.get('page')}, chunk {item.get('chunk_id')}]\n{item.get('text','')}" for item in results)
    final_prompt = ("Answer the user's question using only the retrieved document context. If the context does not contain the answer, say the documents do not provide enough information. Do not invent sources. Cite filename and page when relevant.\n\n"
        f"Retrieved context:\n{context or '[No matching context found]'}\n\nQuestion: {question}\nAnswer:")
    answer = generate(final_prompt, temperature=0.2, max_tokens=1024)
    return {"answer": answer, "sources": [{"filename": r.get("filename"), "page": r.get("page"), "chunk_id": r.get("chunk_id"), "score": r["score"]} for r in results],
            "retrieved_chunks": results, "context": context, "final_prompt": final_prompt, "question_vector_dimension": len(query_vector)}
