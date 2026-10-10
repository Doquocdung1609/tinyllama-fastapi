# Image-to-video hoạt động như thế nào?

## Stable Video Diffusion trong ứng dụng

```text
Ảnh đầu vào
  → resize/preprocess 1024×576
  → image encoder tạo đặc trưng điều kiện
  → latent video ban đầu chứa nhiễu
  → UNet không gian-thời gian khử nhiễu nhiều bước dưới điều kiện của ảnh
  → VAE giải mã latent thành chuỗi frame
  → FFmpeg/imageio mã hóa frame thành MP4
```

Ảnh cung cấp bố cục, màu sắc và đối tượng ban đầu. Mô hình đã học các quy luật chuyển động từ video huấn luyện, rồi dự đoán một diễn tiến chuyển động có khả năng phù hợp với ảnh. Vì sampling có nhiễu, seed giúp tái lập gần như cùng kết quả khi các điều kiện khác giống nhau.

## Điều khiển SVD thật

- `seed`: khởi tạo random generator.
- `num_frames`: số frame, giới hạn UI 2–25; SVD-XT được huấn luyện cho 25 frame.
- `fps`: điều kiện chuyển động và tốc độ mã hóa MP4 trong implementation hiện tại.
- `motion_bucket_id`: mức chuyển động học được; số cao thường tăng motion nhưng không phải lệnh ngôn ngữ.
- `noise_aug_strength`: thêm nhiễu vào ảnh điều kiện; có thể tăng motion nhưng làm giảm độ giống ảnh.
- `decode_chunk_size`: số frame giải mã mỗi đợt; nhỏ hơn tiết kiệm VRAM nhưng chậm hơn và có thể giảm nhất quán frame.

SVD không có text encoder trong conditioning path này. Một ô “người đi về phía trước” sẽ bị bỏ qua nếu chỉ truyền ảnh vào `StableVideoDiffusionPipeline`. Vì vậy UI không hiển thị motion prompt ở mode SVD.

## Ba cơ chế cần phân biệt

| Cơ chế | Input | Frame mới do mô hình sinh? | Text motion có tác dụng? |
|---|---|---:|---:|
| SVD image-conditioned diffusion | ảnh + numeric controls | Có | Không |
| Text-guided image-to-video như CogVideoX I2V | ảnh + prompt + controls | Có | Có |
| FFmpeg Ken Burns | ảnh + pan/zoom parameters | Không; biến đổi ảnh có sẵn | Không |

FFmpeg vẫn hữu ích để chứng minh upload, preview, encoding, playback và download trên máy yếu. Output phải luôn ghi “motion demo — không phải diffusion”.

## Trình bày ngắn với giảng viên

“Hệ thống hiện có hai đường xử lý. Stable Video Diffusion dùng chính ảnh làm điều kiện thị giác và sinh các frame mới bằng khử nhiễu trong latent video; model này không hiểu câu lệnh chuyển động bằng chữ. FFmpeg chỉ phóng và lia một ảnh, nên tạo MP4 nhưng không tạo nội dung hình ảnh mới. Máy demo có 4 GB VRAM và 8 GB RAM, thấp hơn mức an toàn cho SVD, nên giao diện báo BLOCKED thay vì tạo một video giả rồi gọi đó là AI.”
