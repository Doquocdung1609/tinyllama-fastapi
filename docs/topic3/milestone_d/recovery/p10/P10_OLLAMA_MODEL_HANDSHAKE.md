# P10 live Ollama handshake

`GET http://127.0.0.1:11434/api/tags` and real `POST /api/embed` succeeded. The live `nomic-embed-text:latest` digest exactly matched accepted Milestone C: `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`. `scripts/p10_ollama_handshake.py` supplied `search_query: ` and `search_document: ` to separate requests and saved `p10_embedding_identity.json`.

Both outputs had 768 finite values. Query vector Euclidean norm was 0.9999996958; document norm was 1.0000000308. Repeated identical query input produced max absolute delta 0.0 in this session. Measured first query 5,411.76 ms, repeated query 70.66 ms, first document 75.10 ms. This is a bounded compatibility check, not a repeatability guarantee across service versions/hardware. Full vectors and raw model bytes are not committed. No new weights were pulled.
