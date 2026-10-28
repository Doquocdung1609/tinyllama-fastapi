"""Financial Intelligence Studio FastAPI entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.documents import router as documents_router
from app.api.rag import router as rag_router
from app.api.financial import router as financial_router
from app.api.financial_index import router as financial_index_router
from app.api.financial_corpus import router as financial_corpus_router, initialize_financial_registry
from app.api.qdrant import router as qdrant_router
from app.api.conversations import router as conversations_router
from app.product.api import router as product_router
from app.services import rag_service
from app.services.system_service import status as runtime_status


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
settings = get_settings()
settings.prepare_dirs()


@asynccontextmanager
async def lifespan(_app):
    rag_service.load_saved_documents()
    initialize_financial_registry()
    from app.services.conversation_service import init_database
    init_database()
    try:
        yield
    finally:
        from app.api.financial_index import close_index
        from app.product.api import workspace, sec_index
        close_index()
        if workspace.cache_info().currsize:
            workspace().close()
        if sec_index.cache_info().currsize:
            sec_index().close()


app = FastAPI(
    title="Financial Intelligence Studio",
    description="Tìm kiếm tài chính có nguồn và phân tích số liệu SEC được kiểm chứng.",
    version="2.0.0", lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
)
for router in (documents_router, rag_router, financial_router, financial_index_router,
               financial_corpus_router, qdrant_router, conversations_router, product_router):
    app.include_router(router)


@app.get("/")
def home():
    return {"message": "Financial Intelligence Studio API is running", "docs": "/docs",
            "model": settings.ollama_model}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/system/status")
def system_status():
    return runtime_status()


@app.get("/stats")
def stats():
    docs = rag_service.documents()
    return {"documents": len(docs), "chunks": sum(d.get("chunks", 0) for d in docs)}
