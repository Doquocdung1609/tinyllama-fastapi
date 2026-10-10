import json,re,unicodedata
from pathlib import Path
p=Path('processed/aedb60bc088e4242970a43da1e897bde.json')
d=json.loads(p.read_text(encoding='utf-8'))
chunks=d.get('chunks',[])
queries=['năng lực hấp thụ','thương mại hóa đổi mới','đổi mới tuần tự đổi mới đột phá','hiệu quả chuyển giao công nghệ','chia sẻ công nghệ','đổi mới dựa trên tri thức','chế biến khối','chứng khoán hóa thanh khoản','mức độ bất ổn môi trường cơ hội','ý tưởng chấp nhận tổ chức','khóa chặt khách hàng','thu lợi nhuận từ đổi mới','tri thức ngầm','nhà cung cấp đổi mới','đổi mới kiến trúc thành phần','thiết kế chủ đạo','nhà đổi mới phụ','thời điểm đưa công nghệ ra thị trường','quản lý rủi ro công cụ tài chính mới','ngân hàng số chi nhánh','dữ liệu giao dịch khách hàng','cơ quan quản lý đổi mới tài chính']
def toks(s):
 s=unicodedata.normalize('NFKC',s).casefold();return set(re.findall(r'[^\W_]+',s))
for q in queries:
 qt=toks(q); scored=[]
 for c in chunks:
  ct=toks(c.get('text','')); score=len(qt&ct)/max(1,len(qt))
  if score: scored.append((score,c.get('page'),c.get('chunk_id'),c.get('text','')[:160].replace('\n',' ')))
 scored.sort(reverse=True)
 print('\n###',q)
 for x in scored[:5]: print(x)
