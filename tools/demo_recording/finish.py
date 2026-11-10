"""Encode real browser recordings, measure the result, and create handoff files."""
from pathlib import Path
import hashlib
import json
import subprocess
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'deliverables/FAITH_R_FIS_DEMO_20261110'

for result_file in ('E2E_CASE_RESULTS.json', 'RECORDED_CASE_RESULTS.json'):
    result_path = OUT / result_file
    report = json.loads(result_path.read_text(encoding='utf-8'))
    cases = report['cases']
    for parent_id, source_id, expected_page in (
        ('APPLE-01', 'APPLE-01-SOURCE', 32),
        ('APPLE-02', 'APPLE-02-SOURCE', 25),
        ('HPG-OCR', 'HPG-OCR-SOURCE', 4),
    ):
        parent = next((case for case in cases if case['id'] == parent_id), None)
        source = next((case for case in cases if case['id'] == source_id), None)
        if parent and source:
            citations = parent.get('citations', [])
            actual = citations[0].get('page') if citations else None
            source['expected_page'] = expected_page
            source['returned_page'] = actual
            if actual != expected_page and source['status'] == 'PASS':
                source.update(status='PARTIAL', reason='Viewer opened the returned citation, but its page does not match the requested target.')
    result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)
    ], text=True))


def stamp(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    return f'{minutes:02}:{seconds:02}'


subprocess.run(['node', str(ROOT / 'tools/demo_recording/metadata_clip.cjs')], cwd=ROOT, check=True)
scenes = json.loads((OUT / 'SCENES.json').read_text(encoding='utf-8'))
timeline = []
elapsed = 0
files = []
for scene in scenes:
    source = OUT / 'scenes' / scene['file']
    target = source.with_suffix('.mp4')
    if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
        subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source),
        '-an', '-vf', 'fps=30,scale=1920:1080', '-c:v', 'libx264', '-threads', '2',
        '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', str(target)
        ], check=True)
    duration = float(probe(target)['format']['duration'])
    timeline.append({**scene, 'start_seconds': elapsed, 'duration_seconds': duration})
    elapsed += duration
    files.append(f"file 'scenes/{target.name}'")
    print(scene['key'], stamp(duration), flush=True)

listing = OUT / 'concat.txt'
listing.write_text('\n'.join(files), encoding='utf-8')
movie = OUT / 'FAITH_R_FIS_FULL_DEMO.mp4'
subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                '-f', 'concat', '-safe', '0', '-i', str(listing), '-c', 'copy',
                '-movflags', '+faststart', str(movie)], check=True)
technical = probe(movie)
(OUT / 'FFPROBE.json').write_text(json.dumps(technical, indent=2), encoding='utf-8')
digest = hashlib.file_digest(movie.open('rb'), 'sha256').hexdigest()
git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
manifest = {
    'captured_at': datetime.now(timezone(timedelta(hours=7))).isoformat(),
    'git_head': git('rev-parse', 'HEAD'), 'branch': git('branch', '--show-current'),
    'workspace_id': 'react-product-20261028', 'runtime_port': 18110,
    'frontend_index_sha256': hashlib.sha256((ROOT / 'frontend/dist/index.html').read_bytes()).hexdigest(),
    'capture': 'Playwright Chromium real browser video, headless Windows',
    'source_format': 'WebM', 'output_codec': 'H.264', 'fps': 30, 'width': 1920, 'height': 1080,
    'duration_seconds': float(technical['format']['duration']), 'bytes': movie.stat().st_size,
    'sha256': digest, 'scene_count': len(timeline), 'scenes': timeline,
    'real_application': True, 'response_mocking': False,
    'product_code_modified_for_demo': False,
    'evaluation': 'Disclosed development examples, not independent benchmark',
    'acceptance_status': 'PARTIAL',
    'known_product_limits': [
        'APPLE-02 returned company total net sales instead of geographic segment; excluded from main recording.',
        'HPG-OCR refused numeric publication and cited page 5 instead of requested liability page 4; recorded as a limitation.',
    ],
    'recording_substitution': 'APPLE-GROWTH-EN replaces APPLE-02; both were preflight tested.',
    'formula_supplement': 'Restored an authentic server-saved Apple calculation conversation and expanded its calculation details in React.',
}
(OUT / 'CAPTURE_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT / 'VIDEO_TIMELINE.md').write_text(
    '# Mốc thời gian video\n\n' + '\n'.join(
        f"- {stamp(scene['start_seconds'])} — {scene['title']}" for scene in timeline
    ), encoding='utf-8')
records = json.loads((OUT / 'E2E_CASE_RESULTS.json').read_text(encoding='utf-8'))
counts = {state: sum(c['status'] == state for c in records['cases'])
          for state in ('PASS', 'PARTIAL', 'FAIL', 'SKIPPED')}
summary = (
    '# Đọc trước khi trình chiếu\n\n'
    f"Video chính — FAITH_R_FIS_FULL_DEMO.mp4. Thời lượng {stamp(elapsed)}, 1920 × 1080, H.264, 30 FPS.\n\n"
    'Video không lời, ghi thật Chromium đang truy cập React và FastAPI cục bộ trên Windows. '
    'Các cảnh quay dùng dữ liệu trong workspace react-product-20261028. '
    'Xem VIDEO_TIMELINE.md để tìm từng chức năng.\n\n'
    f"Preflight {counts}. Đọc E2E_CASE_RESULTS.json và RECORDED_CASE_RESULTS.json để xem câu trả lời thật và lỗi.\n\n"
    'READY là trạng thái xử lý tài liệu. Ô OCR chưa được người duyệt xác nhận vẫn cần đối chiếu ảnh gốc. '
    'Nguồn SEC trong video là bản cục bộ đã lưu. Không tuyên bố đã truy cập thành công SEC.gov. '
    'Các ca là ví dụ phát triển đã công bố đáp án, không phải đánh giá độc lập.\n\n'
    'Trạng thái nghiệm thu toàn bộ yêu cầu — PARTIAL do hai hạn chế sản phẩm. '
    'APPLE-02 hỏi khu vực nhưng trả tổng doanh thu công ty, đã loại khỏi video chính và thay bằng '
    'APPLE-GROWTH-EN (tăng trưởng doanh thu 6,43%). HPG-OCR chưa trả số nợ và dẫn trang 5 thay vì trang 4, '
    'được quay như giới hạn thực tế, không tính là câu trả lời số đúng.\n\n'
    'PREFLIGHT_INITIAL.json giữ lần thử đầu, gồm lỗi tự động hóa chờ PDF tải chậm. '
    'Các lỗi chờ này đã được sửa trong công cụ quay và chạy lại trước khi ghi hình. '
    'Mã sản phẩm không được sửa nhằm làm bài demo đạt.\n\n'
    'Đoạn bổ sung mở công thức Apple khôi phục một hội thoại thật đã lưu trên máy chủ. '
    'Một lần thử gửi lại câu hỏi bị quá thời gian chờ 30 giây của công cụ; '
    'đoạn bổ sung cuối dùng chức năng khôi phục hội thoại và mở phần tính toán trên React.\n\n'
    'Video dùng để nộp — FAITH_R_FIS_FULL_DEMO.mp4. Có thể gửi kèm VIDEO_TIMELINE.md. '
    'Các file WebM trong scenes là bản quay gốc. Không đưa video dung lượng lớn lên Git.\n\n'
    f"SHA256 video — {digest}\n"
)
summary += '\n| Ca preflight | Kết quả |\n| --- | --- |\n' + '\n'.join(
    f"| {case['id']} | {case['status']} |" for case in records['cases'])
(OUT / 'README_FIRST.md').write_text(summary, encoding='utf-8')
(OUT / 'QC_DIAGNOSTICS.json').write_text(json.dumps({'technical': technical, 'counts': counts}), encoding='utf-8')
print(json.dumps({'duration': elapsed, 'sha256': digest, 'bytes': movie.stat().st_size, 'counts': counts}), flush=True)
