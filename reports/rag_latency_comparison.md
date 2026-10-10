# RAG latency comparison

Các số dưới đây là wall-clock end-to-end từ các lần gọi FastAPI thật; R01 là lượt cold, R02–R05 là warm.

| Case | Baseline ms | Final ms | Delta ms |
|---|---:|---:|---:|
| R01 | 38121.3 | 39312.9 | +1191.6 |
| R02 | 21092.5 | 21005.4 | -87.1 |
| R03 | 15830.7 | 17564.6 | +1733.9 |
| R04 | 17352.4 | 18143.2 | +790.8 |
| R05 | 13637.7 | 17236.0 | +3598.3 |

Baseline trung bình: **21206.9 ms**. Bản cuối trung bình: **22652.4 ms**. Chất lượng regression tăng lên 5/5; độ trễ chưa được tối ưu và phụ thuộc mạnh vào lượt cold của Ollama.
