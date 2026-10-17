# Phase 1 resource profile

- Tested commit: `fe0462bbd777740138dd50488572dde2950d090a`
- API PID: 20436
- System RAM total: 7.84 GB
- System RAM available after benchmark: 0.50 GB
- Minimum available RAM sampled: 0.20 GB
- API RSS peak sampled: 214.6 MB
- Disk free: 12.02 GB
- GPU snapshot: `NVIDIA GeForce GTX 1650 Ti, 4096, 2513, 1423, 0`

## Process and storage boundaries

- PDF extraction and OCR operate one page at a time; rendered PIL images are local variables released after each page.
- Document embedding is batched by the configured provider; duplicate jobs are suppressed by a process lock.
- Tiny-SD and video models are not loaded by ordinary RAG requests.
- Uploads are hash keyed, size bounded, disk guarded, and temporary upload files are removed on errors.

## Actual API state

```json
{
  "qdrant": {
    "online": true,
    "collection": "knowledgebase",
    "vectors": 255,
    "dimension": 768,
    "distance": "Cosine"
  },
  "ollama": {
    "online": true,
    "model": "qwen2.5:3b",
    "model_available": true,
    "models": [
      "qwen2.5:3b",
      "nomic-embed-text:latest",
      "llama3:latest"
    ],
    "running_models": [
      {
        "name": "qwen2.5:3b",
        "model": "qwen2.5:3b",
        "size": 2159374499,
        "digest": "357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b",
        "details": {
          "parent_model": "",
          "format": "gguf",
          "family": "qwen2",
          "families": [
            "qwen2"
          ],
          "parameter_size": "3.1B",
          "quantization_level": "Q4_K_M"
        },
        "expires_at": "2026-10-13T01:00:34.2674749+07:00",
        "size_vram": 2159374499,
        "context_length": 4096
      },
      {
        "name": "nomic-embed-text:latest",
        "model": "nomic-embed-text:latest",
        "size": 323150151,
        "digest": "0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f",
        "details": {
          "parent_model": "",
          "format": "gguf",
          "family": "nomic-bert",
          "families": [
            "nomic-bert"
          ],
          "parameter_size": "137M",
          "quantization_level": "F16"
        },
        "expires_at": "2026-10-13T01:00:25.7898576+07:00",
        "size_vram": 323150151,
        "context_length": 2048
      }
    ],
    "gpu_vram_bytes": 2482524650
  },
  "documents": 36
}
```

## Reproduce

`PYTHONPATH=. python scripts/phase1_performance.py`
