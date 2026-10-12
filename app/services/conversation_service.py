"""Persistent, document-scoped conversational RAG backed by local SQLite."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import re
import sqlite3
from time import perf_counter
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.services import rag_service


class ConversationNotFoundError(LookupError):
    pass


class DocumentScopeError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    path = get_settings().conversation_db
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def init_database() -> None:
    with _connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            title TEXT NOT NULL,
            active_document_ids TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            settings TEXT NOT NULL DEFAULT '{}',
            last_message_id TEXT,
            summary TEXT NOT NULL DEFAULT '',
            active_context TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            question_type TEXT,
            original_question TEXT,
            resolved_question TEXT,
            resolution_context TEXT NOT NULL DEFAULT '{}',
            resolution_uncertainty TEXT,
            source_evidence_ids TEXT NOT NULL DEFAULT '[]',
            citations TEXT NOT NULL DEFAULT '[]',
            referenced_calculations TEXT NOT NULL DEFAULT '[]',
            model TEXT,
            retrieval_metadata TEXT NOT NULL DEFAULT '{}',
            processing_status TEXT NOT NULL,
            latency TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_messages_conversation_time
          ON messages(conversation_id, timestamp);
        """)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _loads(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except (ValueError, TypeError):
        return default


def _conversation(row: sqlite3.Row) -> dict:
    item = dict(row)
    item["active_document_ids"] = _loads(item["active_document_ids"], [])
    item["settings"] = _loads(item["settings"], {})
    item["active_context"] = _loads(item["active_context"], {})
    return item


def _message(row: sqlite3.Row) -> dict:
    item = dict(row)
    for field, default in (("resolution_context", {}), ("source_evidence_ids", []),
                           ("citations", []), ("referenced_calculations", []),
                           ("retrieval_metadata", {}), ("latency", {})):
        item[field] = _loads(item[field], default)
    return item


def _validate_scope(document_ids: list[str], require_ready: bool = True) -> list[dict]:
    if not document_ids or len(document_ids) > 20 or len(set(document_ids)) != len(document_ids):
        raise DocumentScopeError("Phạm vi tài liệu phải gồm 1–20 document ID duy nhất.")
    documents = []
    for document_id in document_ids:
        if not re.fullmatch(r"[a-f0-9]{32}", document_id):
            raise DocumentScopeError("Document ID không hợp lệ.")
        document = rag_service.get_document(document_id)
        if not document:
            raise DocumentScopeError(f"Tài liệu {document_id} không còn tồn tại.")
        if require_ready and document.get("status") not in {"READY", "PARTIAL"}:
            raise DocumentScopeError(f"Tài liệu {document.get('filename')} chưa sẵn sàng.")
        documents.append(document)
    return documents


def create_conversation(active_document_ids: list[str], title: str | None = None,
                        settings: dict | None = None) -> dict:
    documents = _validate_scope(active_document_ids)
    conversation_id, timestamp = uuid4().hex, _now()
    resolved_title = (title or f"Chat: {documents[0]['filename']}")[:160]
    with _connect() as db:
        db.execute("""INSERT INTO conversations
          (conversation_id,created_at,updated_at,title,active_document_ids,status,settings)
          VALUES (?,?,?,?,?,'ACTIVE',?)""",
          (conversation_id, timestamp, timestamp, resolved_title,
           _json(active_document_ids), _json(settings or {})))
    return get_conversation(conversation_id)


def list_conversations() -> list[dict]:
    init_database()
    with _connect() as db:
        rows = db.execute("SELECT * FROM conversations ORDER BY updated_at DESC").fetchall()
    return [_conversation(row) for row in rows]


def get_conversation(conversation_id: str, include_messages: bool = False) -> dict:
    if not re.fullmatch(r"[a-f0-9]{32}", conversation_id):
        raise ConversationNotFoundError("Conversation ID không hợp lệ.")
    init_database()
    with _connect() as db:
        row = db.execute("SELECT * FROM conversations WHERE conversation_id=?", (conversation_id,)).fetchone()
    if not row:
        raise ConversationNotFoundError("Không tìm thấy cuộc hội thoại.")
    result = _conversation(row)
    if include_messages:
        result["messages"] = list_messages(conversation_id)
    return result


def update_conversation(conversation_id: str, *, title: str | None = None,
                        active_document_ids: list[str] | None = None,
                        status: str | None = None, settings: dict | None = None) -> dict:
    current = get_conversation(conversation_id)
    scope = active_document_ids if active_document_ids is not None else current["active_document_ids"]
    _validate_scope(scope)
    with _connect() as db:
        db.execute("""UPDATE conversations SET title=?,active_document_ids=?,status=?,settings=?,updated_at=?
                      WHERE conversation_id=?""",
                   ((title or current["title"])[:160], _json(scope), status or current["status"],
                    _json(settings if settings is not None else current["settings"]), _now(), conversation_id))
    return get_conversation(conversation_id)


def delete_conversation(conversation_id: str) -> None:
    get_conversation(conversation_id)
    with _connect() as db:
        db.execute("DELETE FROM conversations WHERE conversation_id=?", (conversation_id,))


def list_messages(conversation_id: str, limit: int = 100) -> list[dict]:
    get_conversation(conversation_id)
    with _connect() as db:
        rows = db.execute("""SELECT * FROM messages WHERE conversation_id=?
                             ORDER BY timestamp ASC LIMIT ?""", (conversation_id, min(limit, 500))).fetchall()
    return [_message(row) for row in rows]


_METRICS = ("tỷ lệ thanh toán hiện hành", "biên lợi nhuận", "tổng tài sản", "doanh thu",
            "lợi nhuận", "dòng tiền", "tỷ lệ thanh toán", "chi phí", "roa", "roe", "nợ", "chỉ tiêu")
_FOLLOWUP_MARKERS = ("đó", "này", "vừa nói", "năm trước", "thế còn", "vậy", "lại như vậy",
                     "trang tiếp theo", "bảng trên", "bảng thứ", "chuỗi thứ", "còn lại")


def _question_type(question: str) -> str:
    lowered = question.casefold()
    if any(term in lowered for term in ("tăng bao nhiêu", "tăng trưởng", "tỷ lệ", "tính ")):
        return "CALCULATION"
    if any(term in lowered for term in ("so sánh", "đối chiếu", "khác nhau")):
        return "COMPARISON"
    if any(term in lowered for term in ("biểu đồ", "đồ thị", "chart", "chuỗi")):
        return "CHART"
    if any(term in lowered for term in ("bảng", "table")):
        return "TABLE"
    return "DOCUMENT_QA"


def _latest_context(conversation: dict, history: list[dict]) -> dict:
    context = dict(conversation.get("active_context") or {})
    for item in reversed(history):
        resolved = item.get("resolved_question") or ""
        years = re.findall(r"\b(?:19|20)\d{2}\b", resolved)
        if years and not context.get("years"):
            context["years"] = years[-2:]
        for metric in _METRICS:
            if metric in resolved.casefold() and metric != "chỉ tiêu":
                context.setdefault("metric", metric)
                break
        citations = item.get("citations") or []
        if citations and not context.get("pages"):
            context["pages"] = sorted({int(c["page"]) for c in citations if c.get("page")})
    return context


def resolve_question(original: str, conversation: dict, history: list[dict]) -> dict:
    question = re.sub(r"\s+", " ", original).strip()
    lowered = question.casefold()
    context = _latest_context(conversation, history[-8:])
    explicit_years = re.findall(r"\b(?:19|20)\d{2}\b", question)
    metric = next((item for item in _METRICS if item in lowered and item != "chỉ tiêu"), None)
    followup = len(question.split()) <= 12 or any(marker in lowered for marker in _FOLLOWUP_MARKERS)
    additions: list[str] = []
    uncertainty = None
    clarification = None

    if followup and not metric and context.get("metric") and any(term in lowered for term in
            ("chỉ tiêu", "đó", "tỷ lệ", "năm trước", "thế còn", "bao nhiêu phần trăm")):
        additions.append(f"Chỉ tiêu đang nói đến: {context['metric']}.")
        additions.append("Truy xuất bảng tài chính gốc cho chỉ tiêu này.")
    if "năm trước" in lowered:
        reference_years = explicit_years or context.get("years", [])
        if reference_years:
            current = max(int(year) for year in reference_years)
            additions.append(f"Kỳ đang nói đến: {current}; năm trước: {current - 1}.")
        else:
            clarification = "Bạn muốn so sánh với năm nào?"
            uncertainty = "MISSING_REPORTING_PERIOD"
    elif followup and not explicit_years and context.get("years"):
        additions.append("Kỳ báo cáo đang nói đến: " + ", ".join(context["years"]) + ".")
    explicit_page = re.search(r"trang\s+(\d+)", lowered)
    if "trang tiếp theo" in lowered:
        if context.get("pages"):
            additions.append(f"Trang được tham chiếu: {max(context['pages']) + 1}.")
        else:
            clarification = "Bạn đang muốn nói đến trang nào?"
            uncertainty = "MISSING_PAGE_REFERENCE"
    elif followup and not explicit_page and context.get("pages") and any(term in lowered for term in ("bảng", "biểu đồ", "trang")):
        additions.append("Trang đã trích dẫn gần nhất: " + ", ".join(map(str, context["pages"])) + ".")
    ordinal_tables = {"bảng thứ nhất": 1, "bảng đầu tiên": 1, "bảng thứ hai": 2,
                      "bảng thứ ba": 3, "bảng thứ tư": 4}
    requested_table = next((number for phrase, number in ordinal_tables.items() if phrase in lowered), None)
    if requested_table:
        page = int(explicit_page.group(1)) if explicit_page else (max(context.get("pages", [])) if context.get("pages") else None)
        if page:
            additions.append(f"Bảng cần tìm có source ID table:p{page}:t{requested_table}.")
        else:
            clarification = "Bạn muốn mở bảng đó ở trang nào?"
            uncertainty = "MISSING_PAGE_REFERENCE"
    if "ngân hàng còn lại" in lowered or "ngân hàng khác" in lowered:
        if len(conversation["active_document_ids"]) < 2:
            clarification = "Cuộc hội thoại chỉ có một tài liệu; bạn muốn thêm tài liệu ngân hàng nào?"
            uncertainty = "MISSING_COMPARISON_DOCUMENT"
        elif not context.get("entity"):
            clarification = "Bạn muốn so sánh ngân hàng nào trong các tài liệu đang chọn?"
            uncertainty = "AMBIGUOUS_ENTITY"
    if any(term in lowered for term in ("sửa câu trả lời", "đính chính", "trả lời lại")) and history:
        previous = next((item.get("original_question") for item in reversed(history)
                         if item.get("role") == "user" and item.get("original_question")), None)
        if previous:
            # User-proposed numbers are hypotheses. Remove non-year numeric
            # assertions so the retrieval guard can find the documentary value.
            sanitized = re.sub(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])",
                               lambda match: match.group(0) if re.fullmatch(r"(?:19|20)\d{2}", match.group(0)) else "[giá trị cần kiểm tra]",
                               previous)
            sanitized = re.sub(r"\[giá trị cần kiểm tra\]\s*(?:triệu|tỷ)?\s*đồng\s*đúng không\??",
                               "bao nhiêu?", sanitized, flags=re.IGNORECASE)
            additions.append(f"Hãy kiểm tra lại câu hỏi trước từ tài liệu gốc: {sanitized}")
    resolved = question + (("\n" + " ".join(additions)) if additions else "")
    return {"original_question": question, "resolved_question": resolved,
            "question_type": _question_type(question), "resolution_context": context,
            "resolution_additions": additions, "uncertainty": uncertainty,
            "clarification": clarification, "history_turns_used": min(len(history), 8)}


def _insert_message(db: sqlite3.Connection, **item: Any) -> dict:
    fields = ("message_id", "conversation_id", "role", "content", "timestamp", "question_type",
              "original_question", "resolved_question", "resolution_context", "resolution_uncertainty",
              "source_evidence_ids", "citations", "referenced_calculations", "model",
              "retrieval_metadata", "processing_status", "latency")
    encoded = dict(item)
    for name in ("resolution_context", "source_evidence_ids", "citations", "referenced_calculations",
                 "retrieval_metadata", "latency"):
        encoded[name] = _json(encoded.get(name, {} if name.endswith("metadata") or name in {"resolution_context", "latency"} else []))
    db.execute(f"INSERT INTO messages ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",
               tuple(encoded.get(field) for field in fields))
    row = db.execute("SELECT * FROM messages WHERE message_id=?", (item["message_id"],)).fetchone()
    return _message(row)


def post_message(conversation_id: str, content: str, *, top_k: int = 5,
                 score_threshold: float = .55, model: str | None = None,
                 generate_answer: bool = True) -> dict:
    total_started = perf_counter()
    conversation = get_conversation(conversation_id)
    documents = _validate_scope(conversation["active_document_ids"])
    history = list_messages(conversation_id, limit=24)
    resolution = resolve_question(content, conversation, history)
    timestamp = _now()
    with _connect() as db:
        user = _insert_message(db, message_id=uuid4().hex, conversation_id=conversation_id,
            role="user", content=content, timestamp=timestamp, question_type=resolution["question_type"],
            original_question=content, resolved_question=resolution["resolved_question"],
            resolution_context={**resolution["resolution_context"], "additions": resolution["resolution_additions"]},
            resolution_uncertainty=resolution["uncertainty"], source_evidence_ids=[], citations=[],
            referenced_calculations=[], model=model, retrieval_metadata={"history_turns_used": resolution["history_turns_used"]},
            processing_status="COMPLETED", latency={"resolution_ms": round((perf_counter()-total_started)*1000, 1)})

    if resolution["clarification"]:
        result = {"answer": resolution["clarification"], "model": None, "supporting_sources": [],
                  "calculation_validation": None, "timings": {}, "selected_evidence": [],
                  "citation_validation": {"citation_valid": True, "citation_missing": True}}
        status = "NEEDS_CLARIFICATION"
    else:
        result = rag_service.query(resolution["resolved_question"], top_k, score_threshold,
                                   conversation["active_document_ids"], generate_answer, model)
        status = "COMPLETED"

    citations = result.get("supporting_sources") or []
    evidence_ids = [item.get("chunk_id") for item in citations if item.get("chunk_id")]
    calculation = result.get("calculation_validation")
    retrieval_metadata = {
        "active_document_ids": conversation["active_document_ids"],
        "selected_evidence": [{key: item.get(key) for key in ("chunk_id", "document_id", "page", "source_id", "modality")}
                              for item in result.get("selected_evidence", [])],
        "evidence_selection": result.get("evidence_selection", {}),
        "citation_validation": result.get("citation_validation", {}),
        "timings": result.get("timings", {}),
    }
    assistant_timestamp = _now()
    with _connect() as db:
        assistant = _insert_message(db, message_id=uuid4().hex, conversation_id=conversation_id,
            role="assistant", content=result["answer"], timestamp=assistant_timestamp,
            question_type=resolution["question_type"], original_question=content,
            resolved_question=resolution["resolved_question"], resolution_context=resolution["resolution_context"],
            resolution_uncertainty=resolution["uncertainty"], source_evidence_ids=evidence_ids,
            citations=citations, referenced_calculations=[calculation] if calculation else [],
            model=result.get("model"), retrieval_metadata=retrieval_metadata,
            processing_status=status,
            latency={**result.get("timings", {}), "conversation_total_ms": round((perf_counter()-total_started)*1000, 1)})
        active_context = dict(resolution["resolution_context"])
        years = re.findall(r"\b(?:19|20)\d{2}\b", resolution["resolved_question"])
        if years:
            active_context["years"] = years[-2:]
        # An explicit page in the user's request remains valid conversational
        # context even when the answer is a refusal and therefore has no
        # citation. This lets a later "bảng thứ hai trên trang đó" resolve to
        # the page the user actually named.
        explicit_pages = [int(value) for value in re.findall(
            r"trang\s+(\d+)", resolution["original_question"], flags=re.IGNORECASE)]
        if explicit_pages:
            active_context["pages"] = explicit_pages[-4:]
        metric = next((item for item in _METRICS if item in resolution["resolved_question"].casefold() and item != "chỉ tiêu"), None)
        if metric:
            active_context["metric"] = metric
        if citations:
            active_context["pages"] = sorted({int(item["page"]) for item in citations if item.get("page")})
            active_context["source_evidence_ids"] = evidence_ids[-8:]
        title = conversation["title"]
        if title.startswith("Chat:") and len(history) == 0:
            title = content[:80]
        db.execute("""UPDATE conversations SET updated_at=?,last_message_id=?,active_context=?,title=?
                      WHERE conversation_id=?""",
                   (assistant_timestamp, assistant["message_id"], _json(active_context), title, conversation_id))
    return {"conversation": get_conversation(conversation_id), "user_message": user,
            "assistant_message": assistant, "resolution": resolution, "rag": result}
