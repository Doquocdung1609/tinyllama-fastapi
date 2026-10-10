# Qwen2.5 3B và Llama 3: benchmark generation

## Phương pháp

`scripts/compare_llms.py` lấy selected context từ cùng FastAPI/Qdrant một lần cho mỗi câu, sau đó gửi **cùng prompt** trực tiếp tới từng model với temperature 0, `num_ctx=4096` và `num_predict=320`. Mẫu gồm 10 câu đại diện cho liệt kê, định nghĩa, số liệu, quan hệ, từ chối và so sánh. Q01 của mỗi model là cold run; chín câu sau là warm run.

Nguồn thô: `reports/llm_comparison.csv`.

| Chỉ số | qwen2.5:3b | llama3:latest |
|---|---:|---:|
| Answer correctness | 8/10 | 8/10 |
| Citation correctness | 10/10 | 7/10 |
| Correct + citation | 8/10 | 5/10 |
| Cold wall time | 27.20 s | 140.59 s |
| Warm wall time trung bình | 15.59 s | 72.71 s |
| Warm median | 15.80 s | 73.01 s |
| Generation throughput trung bình | 17.61 token/s | 2.74 token/s |
| Ollama VRAM lớn nhất quan sát | 2,059 MB | 2,265 MB |
| System RAM used lớn nhất quan sát | 7.43 GB | 7.49 GB |

Qwen và Llama có cùng answer score trên mẫu này. Qwen giữ citation tốt hơn, grounded pass cao hơn và nhanh hơn nhiều trên GTX 1650 Ti. Vì vậy `qwen2.5:3b` là default hợp lý cho demo 4 GB VRAM / 8 GB RAM. Cả hai vẫn có trong dropdown Chat và RAG; API nhận trường `model` theo request.

Các số RAM/CPU/GPU là snapshot ở cuối request, không phải profiler liên tục. So sánh này đủ để chọn model demo nhưng không đại diện cho mọi prompt hay phần cứng.

## Chạy lại

```powershell
.\.venv\Scripts\python.exe scripts\compare_llms.py `
  --document-id aedb60bc088e4242970a43da1e897bde `
  --models qwen2.5:3b llama3:latest `
  --output reports\llm_comparison.csv
```
