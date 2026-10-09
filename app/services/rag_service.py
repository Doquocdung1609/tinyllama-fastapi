"""Document indexing, retrieval and grounded prompt construction."""
from datetime import datetime, timezone
import json
import logging
import math
import re
from time import perf_counter
import unicodedata
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
INDEX_VERSION = 2

_STOP_WORDS = {
    "ai", "bao", "bằng", "bị", "các", "căn", "cho", "có", "của", "đã", "đang", "đâu",
    "đến", "để", "được", "gì", "hay", "hơn", "khi", "không", "là", "làm", "mà", "một",
    "những", "như", "nào", "ra", "rằng", "sẽ", "theo", "thế", "thì", "trong", "trên", "từ",
    "và", "vào", "về", "với", "the", "a", "an", "and", "are", "how", "is", "of", "to", "what",
}


def _terms(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return [token for token in re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
            if token not in _STOP_WORDS and (len(token) > 1 or token.isdigit())]


def _lexical_candidates(question: str, chunks: list[dict], limit: int) -> list[dict]:
    """Small BM25-style ranker used to rescue exact Vietnamese terminology."""
    query_terms = set(_terms(question))
    if not query_terms or not chunks:
        return []
    token_sets = []
    document_frequency = {term: 0 for term in query_terms}
    for chunk in chunks:
        tokens = set(_terms(chunk.get("text", "")))
        token_sets.append(tokens)
        for term in query_terms & tokens:
            document_frequency[term] += 1
    total = len(chunks)
    weights = {term: math.log(1 + (total - count + .5) / (count + .5))
               for term, count in document_frequency.items()}
    denominator = sum(weights.values()) or 1.0
    ranked = []
    for chunk, tokens in zip(chunks, token_sets):
        matched = query_terms & tokens
        coverage = sum(weights[term] for term in matched) / denominator
        if coverage:
            ranked.append({**chunk, "lexical_score": min(1.0, coverage)})
    ranked.sort(key=lambda item: item["lexical_score"], reverse=True)
    return ranked[:limit]


def _numeric_anchor_supported(question: str, chunks: list[dict]) -> bool:
    """Require explicit numeric evidence for questions containing dates or values."""
    required = set(re.findall(r"\d+(?:[.,]\d+)?", unicodedata.normalize("NFKC", question)))
    if not required:
        return True
    for chunk in chunks:
        available = set(re.findall(r"\d+(?:[.,]\d+)?", unicodedata.normalize("NFKC", chunk.get("text", ""))))
        if required.issubset(available):
            return True
    return False


def _context_with_neighbors(results: list[dict], eligible_chunks: list[dict]) -> list[dict]:
    """Add transparent adjacent chunks so lists split at page/chunk boundaries stay complete."""
    by_index = {int(chunk.get("chunk_index", -1)): chunk for chunk in eligible_chunks}
    expanded = []
    seen = set()
    for rank, item in enumerate(results):
        chunk_id = item.get("chunk_id")
        if chunk_id not in seen:
            expanded.append({**item, "context_role": "retrieved"})
            seen.add(chunk_id)
        if rank >= 2:
            continue
        index = int(item.get("chunk_index", -10))
        for neighbor_index in (index - 1, index + 1):
            neighbor = by_index.get(neighbor_index)
            if not neighbor or neighbor.get("document_id") != item.get("document_id"):
                continue
            neighbor_id = neighbor.get("chunk_id")
            if neighbor_id in seen:
                continue
            expanded.append({**neighbor, "context_role": "adjacent"})
            seen.add(neighbor_id)
    return expanded


def load_saved_documents() -> None:
    """Restore the ready document library from processed metadata after restart."""
    directory = get_settings().processed_dir
    directory.mkdir(parents=True, exist_ok=True)
    for metadata_path in directory.glob("*.json"):
        try:
            saved = json.loads(metadata_path.read_text(encoding="utf-8"))
            doc = saved.get("document")
            if doc and Path(doc.get("path", "")).exists():
                doc.setdefault("index_version", int(saved.get("index_version", 1)))
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
    processing_started = perf_counter()
    timings: dict[str, float] = {}
    try:
        doc["status"] = "EXTRACTING"
        stage_started = perf_counter()
        pages = extract_pdf(doc["path"], document_id, doc["filename"])
        timings["extraction_seconds"] = round(perf_counter() - stage_started, 3)
        doc["status"] = "CLEANING"
        stage_started = perf_counter()
        text = "\n\n".join(page["text"] for page in pages)
        (settings.processed_dir / f"{document_id}.txt").write_text(text, encoding="utf-8")
        timings["cleaning_seconds"] = round(perf_counter() - stage_started, 3)
        doc["status"] = "CHUNKING"
        stage_started = perf_counter()
        made = chunk_pages(pages, document_id, doc["filename"], settings.chunk_size, settings.chunk_overlap)
        timings["chunking_seconds"] = round(perf_counter() - stage_started, 3)
        _chunks[document_id] = made
        doc.update({"pages": len(pages), "chunks": len(made), "status": "EMBEDDING",
                    "embedding_progress": {"completed": 0, "total": len(made)},
                    "processing_timings": timings})
        from app.services.inference_manager import heavy_inference, mark_stage, release_ollama_gpu
        provider = get_embedding_provider()
        def progress(completed: int, total: int) -> None:
            doc["embedding_progress"] = {"completed": completed, "total": total}
        stage_started = perf_counter()
        with heavy_inference("document_embedding"):
            release_ollama_gpu()
            mark_stage("RUNNING")
            vectors = provider.embed([chunk["text"] for chunk in made], progress_callback=progress)
        timings["embedding_seconds"] = round(perf_counter() - stage_started, 3)
        doc["status"] = "INDEXING"
        stage_started = perf_counter()
        qdrant_service.upsert_chunks(made, vectors)
        timings["indexing_seconds"] = round(perf_counter() - stage_started, 3)
        timings["total_seconds"] = round(perf_counter() - processing_started, 3)
        doc.update({"status": "READY", "indexed_at": datetime.now(timezone.utc).isoformat(),
                    "error": None, "index_version": INDEX_VERSION, "extraction_mode": "layout",
                    "embedding_progress": {"completed": len(made), "total": len(made)},
                    "processing_timings": timings})
        (settings.processed_dir / f"{document_id}.json").write_text(json.dumps(
            {"index_version": INDEX_VERSION, "document": doc, "pages": pages, "chunks": made},
            ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("indexed document id=%s chunks=%d", document_id, len(made))
    except Exception as exc:
        timings["total_seconds"] = round(perf_counter() - processing_started, 3)
        doc.update({"status": "ERROR", "error": str(exc), "processing_timings": timings})
        logger.exception("document processing failed id=%s", document_id)


def register_document(document_id: str, filename: str, path: str) -> dict:
    doc = {"document_id": document_id, "filename": filename, "path": path,
           "status": "UPLOADED", "pages": 0, "chunks": 0, "indexed_at": None, "error": None,
           "embedding_progress": {"completed": 0, "total": 0}}
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
    saved_path = get_settings().processed_dir / f"{document_id}.json"
    pages = []
    if saved_path.exists():
        try:
            pages = json.loads(saved_path.read_text(encoding="utf-8")).get("pages", [])
        except (OSError, ValueError):
            pages = []
    if not pages:
        pages = extract_pdf(path, document_id, filename)
    for page in pages:
        page["cleaned_text"] = clean_text(page["text"])
    return pages, chunk_pages(pages, document_id, filename, chunk_size, chunk_overlap)


def query(question: str, top_k: int = 3, score_threshold: float = 0.0,
          document_id: str | None = None, generate_answer: bool = True) -> dict:
    total_started = perf_counter()
    provider = get_embedding_provider()
    stage_started = perf_counter()
    query_vector = provider.embed([question])[0]
    embedding_ms = round((perf_counter() - stage_started) * 1000, 1)

    candidate_limit = min(120, max(40, top_k * 8))
    stage_started = perf_counter()
    points = qdrant_service.search(query_vector, candidate_limit, document_id)
    semantic_ms = round((perf_counter() - stage_started) * 1000, 1)
    candidates: dict[str, dict] = {}
    for point in points:
        payload = dict(point.payload or {})
        chunk_id = payload.get("chunk_id")
        if chunk_id:
            candidates[chunk_id] = {**payload, "semantic_score": float(point.score), "lexical_score": 0.0}

    stage_started = perf_counter()
    eligible_chunks = chunks_for(document_id)
    lexical_ranked = _lexical_candidates(question, eligible_chunks, candidate_limit)
    max_lexical = max((float(item.get("lexical_score", 0.0)) for item in lexical_ranked), default=0.0)
    for item in lexical_ranked:
        chunk_id = item.get("chunk_id")
        if not chunk_id:
            continue
        if chunk_id in candidates:
            candidates[chunk_id]["lexical_score"] = item["lexical_score"]
        else:
            candidates[chunk_id] = {**item, "semantic_score": .45,
                                    "lexical_score": item["lexical_score"]}
    lexical_ms = round((perf_counter() - stage_started) * 1000, 1)

    results = []
    for item in candidates.values():
        semantic = float(item.get("semantic_score", 0.0))
        lexical = float(item.get("lexical_score", 0.0))
        if lexical >= .35:
            # Strong rare-term coverage is highly reliable for named concepts,
            # page headings and numeric examples in Vietnamese course PDFs.
            hybrid = max(.45 * semantic + .55 * lexical, .55 + .45 * lexical)
        elif lexical >= .15:
            hybrid = .65 * semantic + .35 * lexical
        else:
            # A query with almost no rare-term overlap is probably outside the
            # selected document. Down-weight dense similarity instead of
            # attaching unrelated high-cosine sources.
            hybrid = semantic * .50 if max_lexical < .15 else semantic
        item["score"] = round(min(1.0, hybrid), 6)
        if item["score"] >= score_threshold:
            results.append(item)
    results.sort(key=lambda item: (item["score"], item.get("lexical_score", 0.0)), reverse=True)
    results = results[:top_k]
    if not _numeric_anchor_supported(question, eligible_chunks):
        # Dense embeddings often assign high similarity to an unrelated future
        # date or amount. Grounded RAG must refuse when the requested numeric
        # anchor never occurs in one source chunk.
        results = []
    logger.info("rag retrieval complete top_k=%d matches=%d threshold=%.3f", top_k, len(results), score_threshold)
    context_items = _context_with_neighbors(results, eligible_chunks)
    context = "\n\n".join(
        f"[{'Nguồn liền kề' if item.get('context_role') == 'adjacent' else 'Nguồn truy xuất'}: "
        f"{item.get('filename')}, trang {item.get('page')}, chunk {item.get('chunk_id')}]\n{item.get('text','')}"
        for item in context_items)
    # Bound prompt size on low-memory local LLMs while retaining complete chunks.
    context = context[:4800]
    final_prompt = (
        "Bạn là trợ lý hỏi đáp tài liệu. Chỉ dùng nội dung trong phần NGỮ CẢNH. "
        "Trả lời cùng ngôn ngữ với câu hỏi, ngắn gọn nhưng đủ ý. "
        "Nếu ngữ cảnh không chứa câu trả lời, hãy nói rõ tài liệu không cung cấp đủ thông tin. "
        "Không dùng kiến thức bên ngoài, không suy đoán và không bịa nguồn. "
        "Khi có căn cứ, hãy ghi tên tệp và số trang.\n\n"
        f"NGỮ CẢNH:\n{context or '[Không tìm thấy ngữ cảnh phù hợp]'}\n\n"
        f"CÂU HỎI: {question}\nTRẢ LỜI:")
    generation_started = perf_counter()
    if results and generate_answer:
        answer = generate(final_prompt, temperature=0.1, max_tokens=256)
    elif generate_answer:
        answer = "Tài liệu không cung cấp đủ thông tin để trả lời câu hỏi này."
    else:
        answer = ""
    generation_ms = round((perf_counter() - generation_started) * 1000, 1)
    timings = {"embedding_ms": embedding_ms, "semantic_search_ms": semantic_ms,
               "lexical_search_ms": lexical_ms, "generation_ms": generation_ms,
               "total_ms": round((perf_counter() - total_started) * 1000, 1)}
    return {"answer": answer, "sources": [{"filename": r.get("filename"), "page": r.get("page"),
             "chunk_id": r.get("chunk_id"), "score": r["score"],
             "semantic_score": r.get("semantic_score", 0.0), "lexical_score": r.get("lexical_score", 0.0)}
            for r in results], "retrieved_chunks": results, "context_chunks": context_items, "context": context,
            "final_prompt": final_prompt, "question_vector_dimension": len(query_vector),
            "retrieval_method": "hybrid_bm25_semantic", "timings": timings}
