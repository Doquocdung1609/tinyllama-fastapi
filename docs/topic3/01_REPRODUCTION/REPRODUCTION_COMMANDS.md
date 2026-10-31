# Isolated Windows reproduction commands

From the repository root in PowerShell. The code below uses the pinned public author commit and the two tracked SEC source snapshots. It does not use the product workspace, owner models or local access token.

```powershell
git clone https://github.com/satyam671/financial-hybrid-search-qdrant.git tmp/topic3/original-author
git -C tmp/topic3/original-author checkout 16682dd42ca9cd4887ae74935cb3526dce580c49
py -3.12 -m venv tmp/topic3/original-venv
.\tmp\topic3\original-venv\Scripts\python.exe -m pip install -e tmp/topic3/original-author
.\tmp\topic3\original-venv\Scripts\python.exe -m pip install pytest pytest-asyncio fastapi psutil
.\tmp\topic3\original-venv\Scripts\python.exe -m pytest tmp/topic3/original-author/tests/unit -q
.\tmp\topic3\original-venv\Scripts\python.exe scripts/topic3_author_corpus.py
$env:FASTEMBED_CACHE_PATH = (Join-Path (Resolve-Path '.').Path 'tmp\topic3\model-cache')
.\tmp\topic3\original-venv\Scripts\python.exe scripts/topic3_embed_author.py bm25
.\tmp\topic3\original-venv\Scripts\python.exe scripts/topic3_embed_author.py dense
.\tmp\topic3\original-venv\Scripts\python.exe scripts/topic3_embed_author.py splade
.\tmp\topic3\original-venv\Scripts\python.exe scripts/topic3_index_author_vectors.py
.\tmp\topic3\original-venv\Scripts\python.exe scripts/topic3_query_author.py bm25
.\tmp\topic3\original-venv\Scripts\python.exe scripts/topic3_query_author.py dense
.\tmp\topic3\original-venv\Scripts\python.exe scripts/topic3_query_author.py splade
.\tmp\topic3\original-venv\Scripts\python.exe scripts/topic3_run_author_arms.py
```

Checkpoint scripts refuse existing output/index files to prevent silent overwrite. For a fresh replay, use a new isolated checkout/workspace and point scripts at that root after reviewing their source. Do not delete or reset the owner's existing `tmp/topic3` and V3R3 data merely to rerun. The SPLADE document embedding used a 5,516.5 MiB process peak and system RAM fell to 0.8 MiB available; schedule this step only with ample memory, smaller batches and no concurrent product/OCR/browser workload. Query-only SPLADE with one thread was much lighter. The outputs are provisional and do not establish the author's published 47-filing benchmark.
