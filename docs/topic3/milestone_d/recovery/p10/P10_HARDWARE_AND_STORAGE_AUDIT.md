# P10 hardware and storage audit

Observed on Windows 11 build 26300, Python 3.13.2, Ollama 0.30.10 and qdrant-client 1.20.0. Commands: `Get-CimInstance Win32_OperatingSystem`, `Get-PSDrive C`, `nvidia-smi --query-gpu=name,memory.total,memory.free,memory.used --format=csv,noheader`, `ollama --version`, `ollama list`, and Python `psutil.virtual_memory()`.

At the active build checkpoint, installed RAM was 8,419,053,568 bytes; available RAM was 1,351,553,024 bytes. C: free space was 6,750,945,280 bytes. GPU: NVIDIA GeForce GTX 1650 Ti, 4,096 MiB total, 3,543 MiB free, 393 MiB used. Readings vary during the live build; these are observations, not minimum requirements. The earlier P9 Ollama-unreachable and 0.75 GiB/3.82 GiB readings no longer describe the current session. The owner expressly authorized a small sequential run below prior precautionary thresholds.

The isolated research source clone is `t3-p7-isolated-review-20261026-v1`. P10 vectors are written only under sibling `t3-p10-isolated-vectors-20261027-v1`; no accepted owner collection is opened for writing. The raw float32 lower bound for 1,781 × 768 vectors is about 5.22 MiB; Qdrant metadata/index and loaded-model memory add overhead. The builder limits each embedding request to four parents and stops if actual available RAM drops below 128 MiB. It never deletes models or source files. No model download occurred.

Resource gate remains conditional on successful completion and a measured post-build storage/latency check; low free RAM alone is not counted as a failure.
