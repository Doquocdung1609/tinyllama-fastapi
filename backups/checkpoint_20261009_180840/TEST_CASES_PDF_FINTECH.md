# Bộ test case cho GenAI Learning Studio

## 1. Phạm vi và dữ liệu kiểm thử

- Tài liệu: `Bài giảng Đổi mới sáng tạo Tài chính 2023 (18.12) (1).pdf`
- Quy mô kiểm tra: 249 trang, khoảng 5,3 MB.
- Chức năng cần kiểm tra: Dashboard, Chat với Llama 3, Talk to Documents/RAG, Chunk Explorer, English Script → Audio, Text → Image, Image → Video, System/GPU và các API kiểm tra dữ liệu đầu vào.
- Cấu hình RAG khởi đầu: `chunk_size=800`, `chunk_overlap=120`, `top_k=3`.

### Điều kiện trước khi chạy

1. Chạy FastAPI: `uvicorn main:app --reload`.
2. Chạy Streamlit: `streamlit run streamlit_app.py`.
3. Mở `http://localhost:8501/` và kiểm tra FastAPI URL là `http://127.0.0.1:8000`.
4. Ollama có hai model `llama3:latest` và `nomic-embed-text`.
5. Tải PDF lên trong **Talk to Documents / RAG** và đợi trạng thái `READY` trước khi hỏi.

> Với PDF này, một lần lập chỉ mục bình thường phải nhận đủ 249 trang. Số chunk mặc định dự kiến khoảng 1.053; con số có thể thay đổi nếu chỉnh thuật toán làm sạch hoặc chunking.

## 2. Quy ước đánh giá

Mỗi test case ghi một trong bốn kết quả: `PASS`, `FAIL`, `BLOCKED` hoặc `NOT RUN`.

- **PASS**: hành vi và nội dung đạt toàn bộ tiêu chí.
- **FAIL**: sai hành vi, thiếu dữ kiện bắt buộc, trích sai trang, bịa nội dung hoặc giao diện bị trắng/treo.
- **BLOCKED**: phụ thuộc chưa được cài, chẳng hạn Stable Diffusion, CUDA hoặc model video. Trường hợp này chỉ đạt yêu cầu khi ứng dụng báo lý do rõ ràng và các tab khác vẫn hoạt động.
- **NOT RUN**: chưa thực hiện.

Đối với câu trả lời RAG, chấm theo 10 điểm:

| Thành phần | Điểm tối đa | Cách chấm |
|---|---:|---|
| Đúng ý chính | 4 | Có đủ các ý bắt buộc trong đáp án kiểm chứng |
| Bám sát tài liệu | 2 | Không thêm số liệu, tác giả, ví dụ hoặc kết luận không có trong context |
| Nguồn đúng | 2 | Hiển thị đúng tên PDF và trang chứa ý trả lời; chấp nhận lệch 1 trang khi ý kéo dài qua hai trang |
| Rõ ràng | 1 | Tiếng Việt dễ hiểu, có cấu trúc phù hợp với câu hỏi |
| Biết từ chối | 1 | Với câu ngoài tài liệu, nói không đủ thông tin thay vì suy đoán |

Mức đánh giá một câu RAG:

- 9–10: tốt, có thể dùng.
- 7–8: đạt, nên chỉnh nhẹ.
- 5–6: chưa ổn định; xem chunk, threshold và prompt.
- Dưới 5: không đạt.

## 3. Test case khởi động, Dashboard và tải lại trang

| ID | Thao tác | Kết quả mong đợi |
|---|---|---|
| APP-01 | Mở `http://localhost:8501/`. | Dashboard hiện đầy đủ, không có trang trắng và sidebar có 8 mục chức năng. |
| APP-02 | Nhấn reload trình duyệt 5 lần, chờ mỗi lần tải xong. | Mỗi lần đều render lại Dashboard; không cần khởi động lại Streamlit. |
| APP-03 | Mở cùng URL ở tab trình duyệt thứ hai. | Phiên mới vẫn hiển thị bình thường. |
| APP-04 | Tắt rồi bật **Chế độ học tập**. | Phần giải thích pipeline lần lượt ẩn và hiện; các chức năng chính không thay đổi. |
| DASH-01 | Xem Dashboard khi Ollama và FastAPI đang chạy. | Ollama và Qdrant báo Online; model là `llama3:latest`; embedding dimension là 768 khi `nomic-embed-text` sẵn sàng. |
| DASH-02 | So sánh số Documents/Chunks với thư viện tài liệu. | Sau khi PDF sẵn sàng, số documents tăng 1, chunks khớp với tài liệu và Qdrant vectors tăng tương ứng. |
| DASH-03 | Tắt Ollama rồi reload Dashboard, sau đó bật lại. | UI báo Ollama Offline và hướng dẫn chạy Ollama; trang không trắng và vẫn điều hướng được. |

## 4. Test case Chat với Llama 3

| ID | Dữ liệu/Thao tác | Kết quả mong đợi |
|---|---|---|
| CHAT-01 | Hỏi: `Giải thích RAG bằng tiếng Việt trong 5 câu.` | Có câu trả lời tiếng Việt, tối đa gần 5 câu, không rỗng. |
| CHAT-02 | Hỏi: `Tôi tên là Minh.` rồi hỏi tiếp `Tên tôi là gì?` | Câu thứ hai trả lời `Minh`, chứng minh lịch sử hội thoại được gửi lại. |
| CHAT-03 | Chọn Temperature `0.0`, hỏi hai lần cùng một câu. | Hai câu trả lời có nội dung ổn định hơn so với temperature cao. |
| CHAT-04 | Chọn Max tokens `64`, yêu cầu viết bài dài. | Câu trả lời bị giới hạn hợp lý, UI không treo. |
| CHAT-05 | Nhấn **Xóa hội thoại**. | Toàn bộ nội dung chat biến mất trong phiên hiện tại. |
| CHAT-06 | Gọi API `/chat` với `message=""`. | HTTP 422; không làm FastAPI dừng. |

## 5. Câu hỏi mẫu để đánh giá RAG bằng PDF tài chính

Nên chạy lần đầu với `top_k=5`, `threshold=0.45` để khảo sát score. Sau đó tăng threshold lên mức thấp hơn score của các chunk đúng khoảng 0,03–0,05. Không dùng cố định `0.7` nếu các câu đúng không lấy được context.

| ID | Câu hỏi mẫu | Ý bắt buộc trong câu trả lời | Trang kiểm chứng |
|---|---|---|---:|
| RAG-Q01 | `Ba loại đổi mới tài chính căn cứ theo loại hình là gì?` | Đổi mới sản phẩm; đổi mới chuyển đổi rủi ro; đổi mới quy trình. | 155 |
| RAG-Q02 | `Phân biệt đổi mới công cụ và đổi mới hậu hợp đồng. Cho ví dụ.` | Công cụ mới có tập đặc tính cụ thể; hậu hợp đồng dùng kỹ thuật thay đổi đặc điểm tài sản/nợ; ví dụ hoán đổi nợ xấu để chuyển rủi ro tín dụng. | 156 |
| RAG-Q03 | `Theo cách tiếp cận chức năng, đổi mới tài chính được chia thành tám loại nào?` | Chuyển giao rủi ro; định giá rủi ro; tăng thanh khoản; tăng tạo tín dụng; tạo vốn chủ sở hữu; bảo hiểm; quản lý tài sản và nợ; tài trợ tổ chức tài chính. | 156–158 |
| RAG-Q04 | `Hai yếu tố thúc đẩy đổi mới tài chính theo tài liệu là gì?` | Biến động lãi suất/tỷ giá và bất định thị trường; biện pháp ứng phó pháp lý để giảm hoặc tránh ràng buộc. | 158 |
| RAG-Q05 | `Đổi mới tài chính giúp phân bổ vốn và quản lý rủi ro như thế nào?` | Tách, định giá rủi ro thành phần; phân bổ vốn theo rủi ro/lợi nhuận; chuyển rủi ro cho bên có khả năng hoặc sẵn sàng chịu; tăng thanh khoản cho khoản vay. | 160 |
| RAG-Q06 | `Cho vay theo nhóm trong tài chính vi mô hoạt động dựa trên cơ chế nào và phù hợp trong môi trường nào?` | Gắn kết và áp lực xã hội, các thành viên biết và hỗ trợ/bảo lãnh nhau; phù hợp nơi gắn kết xã hội mạnh và khả năng di chuyển hạn chế. | 163 |
| RAG-Q07 | `Việc thay thế chi nhánh bằng ATM ảnh hưởng đến chi phí vận hành ra sao?` | Giảm chi phí vận hành đơn vị; mức giảm khác nhau giữa các quốc gia do mức độ ATM thay thế chi nhánh khác nhau. | 169–170 |
| RAG-Q08 | `Chương 8 mô tả các dòng sản phẩm fintech phổ biến nào?` | Thanh toán, huy động vốn đám đông, đầu tư và bảo hiểm; có thể nêu các luồng thanh toán C2B, C2C, B2B và quốc tế nếu context chứa trang kế tiếp. | 181, 190–191 |
| RAG-Q09 | `Ngân hàng mở và API liên hệ với nhau như thế nào?` | Open banking cho phép dữ liệu khách hàng được chia sẻ/di chuyển khi có sự đồng ý; API là giao diện kỹ thuật giúp bên thứ ba truy cập dịch vụ/dữ liệu theo chuẩn và kiểm soát. | 213–216 |
| RAG-Q10 | `Điện toán đám mây thay đổi mô hình dịch vụ ngân hàng như thế nào?` | Giảm rào cản/hạ tầng CNTT; cung cấp tài nguyên theo nhu cầu, tự phục vụ và tự động; hỗ trợ mô hình nền tảng/BaaS và API. | 224–227 |
| RAG-Q11 | `Quy trình huấn luyện một mô hình học máy gồm những bước chính nào?` | Thu thập dữ liệu; tiền xử lý; chọn/huấn luyện và tinh chỉnh mô hình; chia training/validation/testing; đánh giá/triển khai theo phần nội dung được truy xuất. | 233–234 |
| RAG-Q12 | `Trong ví dụ Bayes của tài liệu, nếu 20% dân số mắc bệnh và xét nghiệm chính xác 90%, xác suất thực sự mắc bệnh khi dương tính là bao nhiêu? Giải thích phép tính.` | 18 dương tính thật, 8 dương tính giả trên 100 người; `18/(18+8) ≈ 69%`. | 237 |
| RAG-Q13 | `Những rủi ro thực tiễn nào cần cân nhắc khi áp dụng AI trong tài chính?` | Đánh giá độc lập với thuật toán rủi ro cao; thiếu kỹ năng kiểm toán; concept drift và giám sát liên tục; thiên lệch dữ liệu/thuật toán; đa dạng nhóm; độc quyền dữ liệu; câu hỏi đạo đức. | 246–247 |
| RAG-Q14 | `Hãy tổng hợp mối liên hệ giữa open banking, cloud và AI trong đổi mới dịch vụ ngân hàng, đồng thời trích nguồn theo từng ý.` | Tổng hợp đúng ba phần: chia sẻ dữ liệu/API; hạ tầng và dịch vụ linh hoạt trên cloud; dùng dữ liệu/ML để tự động hóa hoặc dự đoán. Mỗi phần phải có nguồn tương ứng. | 213–247 |
| RAG-Q15 | `Tài liệu dự báo giá Bitcoin vào ngày 31/12/2026 là bao nhiêu?` | Phải nói tài liệu không cung cấp đủ thông tin; `sources` nên rỗng nếu threshold loại hết context hoặc không được dùng chunk không liên quan để suy đoán. | Không có |
| RAG-Q16 | `Theo tài liệu, ai là Tổng thống Việt Nam năm 2026?` | Phải từ chối vì ngoài phạm vi tài liệu, không dùng kiến thức ngoài để trả lời. | Không có |

### Phiếu ghi kết quả cho từng câu RAG

| ID câu hỏi | Top-k | Threshold | Top score | Trang nguồn trả về | Điểm /10 | PASS/FAIL | Ghi chú sai/thiếu |
|---|---:|---:|---:|---|---:|---|---|
| RAG-Q__ |  |  |  |  |  |  |  |

## 6. Test case pipeline tài liệu và retrieval

| ID | Thao tác | Kết quả mong đợi |
|---|---|---|
| DOC-01 | Tải PDF mẫu lên. | API nhận file, hiển thị tên đúng, không lỗi với dấu tiếng Việt. |
| DOC-02 | Theo dõi pipeline. | Trạng thái đi qua `UPLOADED → EXTRACTING → CLEANING → CHUNKING → EMBEDDING → INDEXING → READY`; có 249 trang và khoảng 1.053 chunks. |
| DOC-03 | Khi tài liệu chưa `READY`, thử đặt câu hỏi. | Nút hỏi bị vô hiệu hóa; không gửi truy vấn vào index chưa hoàn tất. |
| DOC-04 | Chạy RAG-Q01 với `top_k=5`, threshold `0.45`, bật Debug Mode. | Context có đoạn trang 155; Final Prompt chỉ yêu cầu dùng context; câu trả lời nêu đủ ba loại. |
| DOC-05 | Chạy RAG-Q12. | Trả về khoảng 69% và phép tính 18/(18+8), nguồn trang 237. |
| DOC-06 | Chạy RAG-Q15 và Q16 với threshold phù hợp. | Không bịa; trả lời rằng tài liệu không đủ thông tin. |
| DOC-07 | Với cùng Q01, đổi top-k lần lượt 1, 3, 5, 10. | Số nguồn không vượt top-k; nguồn liên quan vẫn đứng đầu; câu trả lời không giảm độ chính xác khi thêm context. |
| DOC-08 | Với Q01, tăng threshold từ 0 đến 0.95 theo bước 0.05. | Số chunk giảm dần hoặc giữ nguyên; khi không còn chunk, context hiển thị `Không có context` và model từ chối trả lời. |
| DOC-09 | Nhấn **Re-index tài liệu**, chờ READY rồi hỏi lại Q01. | Không tạo tài liệu trùng trong thư viện; số vector của tài liệu không tăng gấp đôi; đáp án vẫn đúng. |
| DOC-10 | Khởi động lại FastAPI sau khi tài liệu READY. | Tài liệu và chunks được khôi phục từ `processed/*.json`; RAG tiếp tục dùng được. |
| DOC-11 | Tải file `.txt` đổi tên không hợp lệ hoặc gửi MIME không phải PDF qua API. | HTTP 415 với thông báo tệp phải là PDF. |
| DOC-12 | Tải PDF lớn hơn `MAX_UPLOAD_MB`. | HTTP 413, file dở dang bị xóa và server vẫn hoạt động. |
| DOC-13 | Trong System/GPU, xóa tài liệu đã chọn. | Tài liệu, file upload, metadata và vectors tương ứng biến mất; document khác không bị xóa. |

## 7. Test case Chunk Explorer

| ID | Thao tác | Kết quả mong đợi |
|---|---|---|
| CHUNK-01 | Mở PDF với `chunk_size=800`, `overlap=120`. | Có raw text, cleaned text, bảng chunk, page, start/end, token estimate và metadata. |
| CHUNK-02 | Tìm chunk chứa `Đổi mới sản phẩm` ở trang 155. | Text đọc được và metadata giữ đúng filename, document ID và page 155. |
| CHUNK-03 | Đổi `chunk_size` từ 800 xuống 400, giữ overlap 80. | Tổng chunk tăng; mỗi chunk không vượt quá kích thước cấu hình, trừ sai khác do trim khoảng trắng chỉ làm ngắn hơn. |
| CHUNK-04 | Đổi `chunk_size=1200`, `overlap=0`. | Tổng chunk giảm; chunk đầu mỗi trang báo overlap 0. |
| CHUNK-05 | So sánh cuối chunk N và đầu chunk N+1 khi overlap 120. | Có phần nội dung lặp gần mức 120 ký tự; không bỏ mất đoạn giữa hai chunk. |
| CHUNK-06 | Kiểm tra các trang có dấu tiếng Việt. | Dấu vẫn giữ được; việc trích xuất có thể chèn khoảng trắng giữa chữ ở một số PDF nhưng không được làm mất cả đoạn hoặc đổi số liệu. |

## 8. Test case English Script → Audio

Dùng script mẫu:

```text
Hello everyone. Today I will explain how open banking APIs, cloud computing, and artificial intelligence are changing financial services. First, APIs allow approved applications to exchange data securely with a customer's consent. Second, cloud platforms provide flexible computing resources. Finally, AI can support prediction and automation, but its outputs still require careful review.
```

| ID | Thao tác | Kết quả mong đợi |
|---|---|---|
| TTS-01 | Bật chuẩn hóa, rate 175, volume 1.0, voice mặc định rồi tạo audio. | Có original và processed script; processed script giữ nguyên ý; tạo file WAV có kích thước lớn hơn 0, nghe và tải được. |
| TTS-02 | Tắt chuẩn hóa và tạo lại. | Processed script bằng nội dung đầu vào sau khi trim; không cần gọi Llama để sửa câu. |
| TTS-03 | Tạo hai file liên tiếp. | Tên file có timestamp và không ghi đè file trước. |
| TTS-04 | So sánh rate 100 và 250 bằng cùng script. | Bản rate 250 đọc nhanh hơn rõ ràng; cả hai vẫn phát được. |
| TTS-05 | Chọn một voice có trong danh sách. | Phản hồi ghi đúng voice đã chọn và âm thanh được tạo. |
| TTS-06 | Gọi API với voice không tồn tại. | HTTP 503 có nguyên nhân `Voice ... is not installed`; không để lại file audio rỗng. |
| TTS-07 | Gửi script rỗng qua API. | HTTP 422. |

## 9. Test case Text → Image và Image → Video

Prompt ảnh mẫu:

```text
A modern fintech classroom, students studying open banking, cloud computing and AI, clean educational infographic style, blue and white color palette, high detail
```

Negative prompt: `blurry, unreadable text, watermark, distorted hands`

| ID | Thao tác | Kết quả mong đợi |
|---|---|---|
| IMG-01 | Tạo ảnh 512×512, 25 steps, guidance 7.5, seed 1234. | Nếu dependency/model/CUDA sẵn sàng: ảnh PNG hiện được, caption đúng seed/kích thước/thời gian. Nếu chưa sẵn sàng: báo lỗi rõ ràng và app không sập. |
| IMG-02 | Chạy lại cùng prompt và seed 1234. | Với cùng model và cấu hình, ảnh phải giống hoặc gần như giống lần trước. |
| IMG-03 | Gửi width 257 qua API. | HTTP 422 vì kích thước phải là bội số của 8. |
| IMG-04 | Để prompt rỗng. | Nút tạo ảnh bị vô hiệu hóa hoặc API trả HTTP 422. |
| VID-01 | Dùng một PNG/JPEG dưới 20 MB, frames 14, FPS 7. | Nếu model video/CUDA sẵn sàng: tạo MP4 phát được, trả đúng 14 frames và 7 FPS. Nếu chưa: báo đúng phụ thuộc bị thiếu, các tab khác vẫn hoạt động. |
| VID-02 | Tải file `.txt` vào API video. | HTTP 415. |
| VID-03 | Gửi frames 1 hoặc FPS 31 qua API. | HTTP 422; server vẫn hoạt động. |
| VID-04 | Tải ảnh lớn hơn 20 MB. | HTTP 413 và file tạm bị xóa. |

## 10. Test case System/GPU và API

| ID | Thao tác | Kết quả mong đợi |
|---|---|---|
| SYS-01 | Mở **System / GPU**. | JSON có Python, FastAPI, Streamlit, Ollama, model, Qdrant, embedding, GPU, CPU và RAM. |
| SYS-02 | So sánh `/health`, `/stats`, `/qdrant/status` với Dashboard. | `/health` trả `{"status":"ok"}`; các số documents/chunks/vectors thống nhất. |
| SYS-03 | Kiểm tra `ollama ps` khi model đang chạy. | `gpu_vram_bytes` phản ánh VRAM Ollama báo cáo; trường CUDA của PyTorch có thể khác vì hai runtime độc lập. |
| SYS-04 | Chỉ trên môi trường test trống: gọi `DELETE /qdrant/collection`. | Collection bị xóa/đưa về rỗng, API vẫn sống. Sau đó phải re-index trước khi test RAG tiếp. |
| API-01 | Gọi `/rag/query` với `top_k=0`, `top_k=21`, threshold âm hoặc lớn hơn 1. | HTTP 422 cho mọi giá trị ngoài giới hạn. |
| API-02 | Gọi ID tài liệu không tồn tại ở GET/POST/DELETE. | HTTP 404 với thông báo không tìm thấy tài liệu. |
| API-03 | Mở `http://127.0.0.1:8000/docs`. | Swagger hiển thị toàn bộ endpoint và có thể thử request. |

## 11. Bảng tổng hợp nghiệm thu

| Nhóm | Trọng số | Điều kiện đạt |
|---|---:|---|
| Khởi động, reload, Dashboard | 15 | APP-01 đến APP-04 và DASH-01/02 đều PASS |
| RAG và quản lý tài liệu | 40 | Ít nhất 12/16 câu RAG đạt từ 7 điểm; Q01, Q12, Q15, Q16 bắt buộc PASS; không có lỗi bịa nghiêm trọng |
| Chunk Explorer | 10 | Metadata/trang đúng, thay đổi size/overlap có hiệu lực |
| Chat | 10 | Chat cơ bản, lịch sử, giới hạn và xóa hội thoại hoạt động |
| TTS | 10 | Tạo, nghe, tải được audio; normalize không đổi nghĩa |
| Image/Video | 5 | PASS nếu môi trường đủ; BLOCKED hợp lệ nếu báo lỗi phụ thuộc rõ và app vẫn ổn định |
| System/API/Validation | 10 | Status nhất quán, lỗi 4xx đúng và server không dừng |

Xếp loại toàn hệ thống:

- **Đạt tốt**: từ 85/100, không có lỗi bắt buộc.
- **Đạt**: 70–84/100, không có lỗi trang trắng, mất dữ liệu hoặc RAG bịa ở Q15/Q16.
- **Cần sửa**: dưới 70/100 hoặc có bất kỳ lỗi bắt buộc nào.

## 12. Mẫu biên bản kết quả

```text
Ngày kiểm thử:
Người kiểm thử:
Phiên bản code/commit:
Python / FastAPI / Streamlit:
Ollama model:
Embedding model:
Thiết bị CPU/GPU/RAM:

Số test PASS:
Số test FAIL:
Số test BLOCKED:
Điểm RAG trung bình:
Thời gian index PDF 249 trang:
Thời gian trả lời RAG trung bình:

Lỗi nghiêm trọng:
1.

Nhận xét và đề xuất:
1.
```

## 13. Kết quả baseline đã chạy ngày 09/10/2026

Trạng thái lập chỉ mục thực tế của PDF:

- `READY`
- 249 trang
- 1.053 chunks
- Embedding dimension: 768

| Câu | Cấu hình | Kết quả retrieval và câu trả lời | Điểm | Kết luận |
|---|---|---|---:|---|
| RAG-Q01 | top-k 5, threshold 0.45 | Trả các trang 87, 149, 242, 105, 144 thay vì trang 155; model nói không tìm thấy đáp án. | 3/10 | FAIL |
| RAG-Q09 | top-k 5, threshold 0.45 | Lấy đúng các chunk trang 214–215 với score cao nhất 0.757, nhưng câu kết luận chỉ nhấn mạnh ví dụ “thực đơn nhà hàng”, chưa nêu rõ chia sẻ dữ liệu khi khách hàng đồng ý; có thêm nguồn không liên quan trang 176–177. | 6/10 | FAIL |
| RAG-Q12 | top-k 10, threshold 0.0 | Lấy đúng nhiều chunk trang 237, score cao nhất 0.850; trả đúng `18/(18+8) = 69%`. | 9/10 | PASS |
| RAG-Q15 | top-k 5, threshold 0.95 | Không có source và trả lời rằng tài liệu không cung cấp đủ thông tin. | 10/10 | PASS |

Điểm trung bình mẫu: **7,0/10**. Kết quả cho thấy pipeline chạy được, metadata trang và cơ chế từ chối hoạt động, nhưng retrieval tiếng Việt chưa ổn định với câu khái niệm và câu tổng hợp. Thời gian trả lời quan sát được dao động khoảng 12–185 giây; cần ghi thêm cấu hình CPU/GPU và token đầu ra khi đo chính thức.

Ưu tiên cải thiện trước khi nghiệm thu:

1. Làm sạch lỗi khoảng trắng xen giữa chữ tiếng Việt trong text PDF trước khi embedding.
2. Đo score của toàn bộ 16 câu rồi chọn threshold theo dữ liệu; không mặc định coi 0.7 là phù hợp với mọi câu.
3. Yêu cầu prompt RAG trả lời cùng ngôn ngữ với câu hỏi, ngắn gọn và chỉ trích các trang trực tiếp hỗ trợ kết luận.
4. Kiểm tra lại cấu hình embedding cho truy vấn và tài liệu, sau đó re-index toàn bộ PDF nếu thay đổi cách tiền xử lý hoặc embedding.
