# Genuine image-to-video feasibility

## Kết luận

**BLOCKED — HARDWARE** và **BLOCKED — MODEL_NOT_AVAILABLE** cho Stable Video Diffusion XT trên máy hiện tại.

FFmpeg motion demo vẫn **PASS**, nhưng là hiệu ứng pan/zoom trên ảnh gốc và không được tính là generative video.

## Audit máy hiện tại

| Hạng mục | Quan sát |
|---|---|
| GPU | NVIDIA GTX 1650 Ti, 4,096 MiB VRAM |
| VRAM khi audit | khoảng 2,513 MiB used, 1,423 MiB free (Ollama đang resident) |
| RAM | 8 GB |
| Disk C free | khoảng 10.0 GiB ở lần đo cuối |
| Python | 3.13 |
| PyTorch / CUDA | 2.6.0+cu124 / CUDA 12.4 |
| Diffusers / Accelerate | 0.41 / 1.15 |
| Video checkpoint local | không có |

Checkpoint không được tải vì máy không đạt ngưỡng an toàn và dung lượng trống thấp. Không có lần chạy SVD thật, không có MP4 diffusion được tuyên bố là thành công.

## Option A: SVD-XT hiện có

SVD-XT là pipeline image-conditioned, tạo 25 frame ở 1024×576. Backend không nhận text prompt. Các điều khiển thật gồm seed, frame count, fps conditioning, `motion_bucket_id`, `noise_aug_strength` và `decode_chunk_size`.

Diffusers có CPU offload, forward chunking và decode chunking. Tài liệu chính thức nêu cấu hình kết hợp các kỹ thuật này có thể giảm nhu cầu VRAM xuống dưới 8 GB; mốc này vẫn cao hơn 4 GB. CPU offload còn chuyển áp lực sang RAM 8 GB, trong khi Ollama/Tiny-SD và hệ điều hành cũng dùng RAM. Vì vậy thử tải SVD trên máy này có rủi ro OOM/thrashing cao và không phải phép thử an toàn.

Nguồn chính thức:

- https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/blob/main/README.md
- https://huggingface.co/docs/diffusers/main/using-diffusers/svd

## Option B: text-guided image-to-video local

CogVideoX I2V hỗ trợ ảnh và text nhưng không phù hợp máy hiện tại. Tài liệu Diffusers nêu các cấu hình 2B vẫn cần khoảng 7.8–12.5 GB VRAM tùy tối ưu; 5B quantized khoảng 16 GB. Sequential CPU offload có thể hạ peak VRAM rất thấp nhưng cực chậm và vẫn cần tải/giữ model lớn bằng RAM hoặc disk. Với RAM 8 GB và disk trống khoảng 10 GB, đây không phải lựa chọn local thực tế.

Nguồn chính thức:

- https://huggingface.co/docs/diffusers/api/pipelines/cogvideox
- https://huggingface.co/docs/diffusers/main/using-diffusers/cogvideox
- https://huggingface.co/docs/diffusers/optimization/memory

Không tìm thấy backend text-guided thực dụng nào đáp ứng đồng thời 4 GB VRAM, 8 GB RAM, Python 3.13, disk hiện tại và thời gian demo hợp lý. Mô tả “lightweight” không được dùng làm bằng chứng đủ bộ nhớ.

## Option C: remote GPU tùy chọn

Giữ Streamlit/FastAPI local và thêm adapter remote là hướng khả thi nếu có GPU tối thiểu khoảng 12–16 GB VRAM và RAM hệ thống phù hợp. Adapter cần timeout, job status, backend/model metadata, secret qua environment và giới hạn concurrency. Không tích hợp dịch vụ trả phí hay credential vì chưa có chấp thuận.

## Safeguard đã triển khai

- `GET /video/capabilities` trả backend, conditioning, controls và blocker thật.
- UI chỉ bật diffusion khi `ready=true`.
- Không hiển thị text prompt cho SVD.
- Pipeline local-only, không tự tải checkpoint.
- Khi sẵn sàng trên máy khác: model CPU offload, forward chunking, decode chunk, semaphore dùng chung, giải phóng Ollama/Tiny-SD trước inference, dọn input tạm trong `finally`, bắt CUDA OOM và ghi peak VRAM.
- FFmpeg có endpoint/mode/nhãn riêng `ken_burns_motion_demo_not_diffusion`.

## Điều kiện để đổi trạng thái sang PASS

Chỉ đánh dấu GENUINE VIDEO PASS sau khi pipeline thực tạo frame mới, MP4 mở được, model/conditioning/settings/source image/runtime/peak resource được ghi lại và các tab khác vẫn ổn định. Trạng thái hiện tại chưa đáp ứng điều kiện này.
