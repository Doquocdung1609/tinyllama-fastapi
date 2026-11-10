"""Replay five natural conversations against the live local Studio API."""
import json
import sys
import time
from pathlib import Path
import requests

QUESTIONS = (
    (
        'Apple năm 2025 kiếm tiền chủ yếu từ bán sản phẩm hay dịch vụ?',
        'Vậy cứ 100 đô doanh thu của Apple thì có khoảng bao nhiêu đô từ dịch vụ?',
        'Thế năm trước thì sao?',
        'Như vậy mảng dịch vụ đang quan trọng hơn đúng không?',
        'Giải thích đơn giản hơn được không, tôi không rành tài chính.',
        'Tôi muốn xem chính xác hai con số bạn dùng để tính ở câu trước.',
    ),
    (
        'Trong năm 2025, Apple có khu vực kinh doanh nào bị sụt doanh thu không?',
        'Sụt nhiều không? Tính thử cả số tiền lẫn phần trăm cho tôi.',
        'Tôi nhớ hình như giảm đến 5%, có đúng không?',
        'Vì sao khu vực này lại giảm?',
        'Vậy doanh thu toàn Apple cũng giảm theo à?',
        'Tóm tắt lại giúp tôi trong ba câu để đưa vào bài thuyết trình.',
    ),
    (
        'Biên lợi nhuận gộp mảng dịch vụ của Apple có cao hơn mảng sản phẩm nhiều không?',
        'Vậy cao hơn chính xác bao nhiêu?',
        'Có nghĩa dịch vụ cao hơn sản phẩm 38,6% đúng không?',
        'Nếu tính cao hơn theo tỷ lệ tương đối thì ra bao nhiêu?',
        'Hai kết quả khác nhau như vậy thì nên dùng kết quả nào khi thuyết trình?',
        'Ghi rõ cả hai công thức và số liệu gốc để tôi kiểm tra.',
    ),
    (
        'Tôi thấy Greater China năm 2025 đạt 69.377 triệu USD. Vậy tôi ghi vào slide như thế có đúng không?',
        'Apple có lợi nhuận ròng bằng 416.161 triệu USD năm 2025 à?',
        'Doanh thu tại Mỹ với Americas là cùng một chỉ tiêu đúng không?',
        'Vậy hai con số đó chênh nhau khoảng bao nhiêu?',
        'Đọc trong báo cáo này thì doanh thu cả năm 2026 của Apple là bao nhiêu?',
        'Đổi doanh thu Services 2025 sang tiền Việt cho tôi, dùng tỷ giá hôm nay nhé.',
    ),
    (
        'Nếu chỉ có một phút đọc báo cáo Apple năm 2025, bạn thấy ba điểm đáng chú ý nhất là gì?',
        'Trong những điểm đó, điều nào liên quan đến tăng trưởng doanh thu?',
        'Có phải Apple đang phụ thuộc ngày càng nhiều vào dịch vụ không?',
        'Tôi chưa hiểu vì sao dịch vụ có tỷ suất lợi nhuận cao hơn sản phẩm. Báo cáo có giải thích cụ thể không?',
        'Hãy giúp tôi giải thích điều đó cho người không học tài chính, không dùng thuật ngữ khó.',
        'Giờ viết cho tôi đoạn kết luận 4 câu, có nguồn để tôi kiểm tra.',
    ),
)
ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = '3eb270b22acb7d8d8e9c32a43dc221de'

def main():
    output = Path(sys.argv[1])
    client = requests.Session()
    token = (ROOT / 'tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip()
    client.headers['Authorization'] = 'Bearer ' + token
    records = []
    for scenario, questions in enumerate(QUESTIONS, 1):
        session = None
        for turn, question in enumerate(questions, 1):
            start = time.monotonic()
            reply = client.post('http://127.0.0.1:18110/studio/chat', json={
                'question': question, 'document_ids': [DOCUMENT], 'session_id': session
            }, timeout=180)
            body = reply.json()
            session = body.get('session_id', session)
            records.append({'scenario': scenario, 'turn': turn, 'question': question,
                            'http': reply.status_code, 'seconds': round(time.monotonic()-start, 2),
                            'response': body})
            output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
            print(scenario, turn, reply.status_code, body.get('status'), flush=True)

if __name__ == '__main__':
    main()
