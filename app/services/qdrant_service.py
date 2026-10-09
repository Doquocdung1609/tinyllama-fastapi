"""Lazy Qdrant client with local persistent mode by default."""
from functools import lru_cache
from uuid import uuid5, NAMESPACE_URL
from app.config import get_settings


@lru_cache(maxsize=1)
def get_client():
    try:
        from qdrant_client import QdrantClient
    except ImportError as exc:
        raise RuntimeError("qdrant-client is missing. Install requirements.txt.") from exc
    settings = get_settings()
    if settings.qdrant_url:
        return QdrantClient(url=settings.qdrant_url)
    settings.qdrant_path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(settings.qdrant_path))


def ensure_collection(dimension: int) -> None:
    from qdrant_client.http.models import Distance, VectorParams
    client, name = get_client(), get_settings().qdrant_collection
    if client.collection_exists(name):
        info = client.get_collection(name)
        existing = info.config.params.vectors.size
        if existing != dimension:
            raise RuntimeError(f"Qdrant collection dimension is {existing}; embedding model returned {dimension}. Clear/recreate the collection after changing models.")
    else:
        client.create_collection(collection_name=name, vectors_config=VectorParams(size=dimension, distance=Distance.COSINE))


def upsert_chunks(chunks: list[dict], vectors: list[list[float]]) -> None:
    from qdrant_client.http.models import FieldCondition, Filter, MatchValue, PointIdsList, PointStruct
    if not chunks:
        return
    ensure_collection(len(vectors[0]))
    points = []
    for chunk, vector in zip(chunks, vectors):
        point_id = str(uuid5(NAMESPACE_URL, chunk["chunk_id"]))
        chunk["vector_id"] = point_id
        chunk["embedding_status"] = "ready"
        points.append(PointStruct(id=point_id, vector=vector, payload={k: chunk.get(k) for k in
            ("document_id", "filename", "page", "chunk_id", "chunk_index", "text", "original_text", "cleaned_text",
             "start", "end", "overlap", "token_estimate", "metadata")}))
    client = get_client()
    collection = get_settings().qdrant_collection
    client.upsert(collection_name=collection, points=points)

    # Re-indexing can produce fewer chunks than a previous index. Upsert replaces
    # matching IDs but cannot remove trailing IDs, so prune any points for this
    # document that are no longer part of the active chunk set.
    document_ids = {chunk.get("document_id") for chunk in chunks}
    if len(document_ids) == 1:
        document_id = next(iter(document_ids))
        active_ids = {point.id for point in points}
        stale_ids = []
        offset = None
        document_filter = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
        while True:
            records, offset = client.scroll(
                collection_name=collection,
                scroll_filter=document_filter,
                limit=256,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            stale_ids.extend(record.id for record in records if record.id not in active_ids)
            if offset is None:
                break
        if stale_ids:
            client.delete(collection_name=collection, points_selector=PointIdsList(points=stale_ids))


def search(vector: list[float], limit: int, document_id: str | None = None):
    from qdrant_client.http.models import FieldCondition, Filter, MatchValue
    client, collection = get_client(), get_settings().qdrant_collection
    if not client.collection_exists(collection):
        return []
    query_filter = None
    if document_id:
        query_filter = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
    return client.query_points(collection_name=collection, query=vector, query_filter=query_filter,
                               limit=limit, with_payload=True).points


def delete_document(document_id: str) -> None:
    from qdrant_client.http.models import FieldCondition, Filter, MatchValue
    client, collection = get_client(), get_settings().qdrant_collection
    if client.collection_exists(collection):
        client.delete(collection_name=collection, points_selector=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]))


def clear_collection() -> None:
    client, collection = get_client(), get_settings().qdrant_collection
    if client.collection_exists(collection):
        client.delete_collection(collection)


def collection_status() -> dict:
    settings = get_settings()
    try:
        client = get_client()
        if not client.collection_exists(settings.qdrant_collection):
            return {"online": True, "collection": settings.qdrant_collection, "vectors": 0, "dimension": None, "distance": "Cosine"}
        info = client.get_collection(settings.qdrant_collection)
        return {"online": True, "collection": settings.qdrant_collection, "vectors": info.points_count or 0,
                "dimension": info.config.params.vectors.size, "distance": "Cosine"}
    except Exception as exc:
        return {"online": False, "collection": settings.qdrant_collection, "vectors": 0, "error": str(exc)}
