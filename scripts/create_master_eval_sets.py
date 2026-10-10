import json
from pathlib import Path
D = [
('D01','Năng lực hấp thụ của doanh nghiệp là gì và nó ảnh hưởng thế nào đến khả năng khai thác đổi mới?',['năng lực tiếp nhận','tri thức','khai thác'],[72,73,74,75],'partial'),
('D02','Vì sao một doanh nghiệp có công nghệ tốt vẫn có thể thất bại trong quá trình thương mại hóa đổi mới?',['tài sản bổ sung','năng lực công nghệ'],[15,32,33],'full'),
('D03','Đổi mới tuần tự khác đổi mới đột phá ở những điểm nào?',['tri thức hiện tại','tri thức hoàn toàn khác|triệt tiêu','năng lực'],[16,17,31],'full'),
('D04','Những nhân tố nào ảnh hưởng đến hiệu quả chuyển giao công nghệ giữa các tổ chức?',['năng lực tiếp nhận','năng lực chuyển giao','khác biệt văn hóa','bản chất của đổi mới','thời điểm'],[72,73,74,75],'full'),
('D05','Tại sao các doanh nghiệp đôi khi chủ động chia sẻ công nghệ cho đối thủ hoặc đối tác?',['hợp tác','quy mô lợi nhuận|tiêu chuẩn','năng lực bổ sung|tài sản bổ sung'],[135,136,137,138,149,150,151],'partial'),
('D06','Phân biệt đổi mới dựa trên tri thức và đổi mới chế biến khối.',['tri thức hàm ẩn','chế biến khối','tài sản bổ sung'],[26,27,32,105,106],'full'),
('D07','Chứng khoán hóa có thể cải thiện khả năng thanh khoản của ngân hàng bằng cơ chế nào?',['khoản vay','chứng khoán','thanh khoản','bán'],[156,159,160],'full'),
('D08','CDS và chứng khoán hóa giống và khác nhau thế nào về chuyển giao rủi ro?',['CDS','chứng khoán hóa','rủi ro tín dụng','thanh khoản'],[156,157,159,160,161],'partial'),
('D09','Đổi mới tài chính có thể mang lại lợi ích gì cho khách hàng và tổ chức trung gian tài chính?',['chi phí','rủi ro','sản phẩm','phân bổ vốn'],[159,160,161,162],'full'),
('D10','Vì sao mức độ bất ổn của môi trường có thể ảnh hưởng đến khả năng nhận ra cơ hội đổi mới?',['thu thập','xử lý thông tin','bất ổn','nhận ra tiềm năng'],[84,93,94,105],'full'),
('D11','Điều gì khiến một ý tưởng mới khó được một tổ chức chấp nhận dù ý tưởng đó có giá trị?',['văn hóa','NIH|not invented here','chống đối'],[76,93,94,102],'full'),
('D12','Hiệu ứng khóa chặt khách hàng ảnh hưởng thế nào đến việc thay đổi công nghệ?',['khóa','sức ì','khách hàng'],[21,22,23,188],'partial'),
('D13','Những chiến lược chủ yếu để doanh nghiệp thu lợi nhuận từ đổi mới được giáo trình đề cập là gì?',['ngăn chặn','tăng tốc','hợp tác'],[142,143,144,147,149,151],'full'),
('D14','Đổi mới tài chính tác động đến rủi ro như thế nào? Phân biệt các cơ chế nếu tài liệu đề cập.',['chuyển giao rủi ro','phân tán rủi ro','quản lý rủi ro','định giá rủi ro'],[155,156,157,159,160,161],'full'),
('D15','Theo giáo trình, cổ phiếu của ngân hàng ACB sẽ đạt giá bao nhiêu vào ngày 31/12/2030?',[],[],'unsupported')]
H = [
('H01','Vì sao tri thức ngầm thường khó chuyển giao hơn tri thức được thể hiện rõ bằng văn bản?',['tri thức ẩn|tri thức ngầm','khó xác định','khó chuyển'],[28,54,73,74,75],'partial'),
('H02','Các mối quan hệ với nhà cung cấp có thể hỗ trợ hoặc cản trở đổi mới ra sao?',['nhà cung cấp','năng lực','mối quan hệ'],[23,24,78,142,143],'partial'),
('H03','Đổi mới kiến trúc khác đổi mới thành phần như thế nào?',['kiến trúc','thành phần','liên kết'],[20,21,31],'full'),
('H04','Tại sao một thiết kế chủ đạo có thể làm thay đổi chiến lược cạnh tranh của doanh nghiệp?',['thiết kế chủ đạo','tiêu chuẩn','hợp tác|cạnh tranh'],[34,111,114,149,151],'partial'),
('H05','Vì sao công ty lớn không phải lúc nào cũng khai thác đổi mới đột phá tốt hơn doanh nghiệp mới?',['tri thức','năng lực hiện tại','tài sản bổ sung','doanh nghiệp mới|start-up'],[15,17,18,31,32,139,140],'full'),
('H06','Năng lực tiếp nhận và năng lực chuyển giao công nghệ có vai trò gì trong hợp tác đổi mới?',['năng lực tiếp nhận','năng lực chuyển giao','tri thức'],[72,73,74,75],'full'),
('H07','Những yếu tố nào giúp một doanh nghiệp nhận ra tiềm năng của một đổi mới trước đối thủ?',['thu thập','xử lý thông tin','chiến lược','cơ cấu','con người'],[84,93,94,95,96,97,98,99,100,101,102,103,104,105],'full'),
('H08','Đổi mới công nghệ ảnh hưởng như thế nào đến cấu trúc ngành và khả năng cạnh tranh?',['cấu trúc ngành','cạnh tranh','gia nhập','sản phẩm thay thế'],[17,30,31,108,109,110,111],'full'),
('H09','Vì sao nhà đổi mới phụ có thể đóng vai trò quan trọng đối với thành công của sản phẩm mới?',['nhà đổi mới phụ','năng lực','chuỗi giá trị'],[21,23,24,62,63,74,78],'partial'),
('H10','Thời điểm đưa công nghệ ra thị trường ảnh hưởng thế nào đến khả năng thu lợi nhuận từ đổi mới?',['thời điểm','lợi thế','tài sản bổ sung|năng lực'],[32,33,111,120],'partial'),
('H11','Vai trò của quản lý rủi ro trong sự phát triển của các công cụ tài chính mới là gì?',['quản lý rủi ro','chuyển giao','phân tán','công cụ tài chính'],[155,156,159,160,161],'full'),
('H12','Giải thích vì sao các tổ chức tài chính có động cơ phát triển sản phẩm ngay cả khi sản phẩm hiện tại vẫn hoạt động tốt.',['cạnh tranh','nhu cầu khách hàng','công nghệ mới','chủ động'],[158,162,220],'partial'),
('H13','Chuyển giao rủi ro tín dụng có thể tác động như thế nào đến khả năng cho vay của ngân hàng?',['hạn chế vốn','cho vay','chuyển rủi ro tín dụng'],[160,161],'full'),
('H14','Vì sao sự phát triển của ngân hàng số có thể làm giảm lợi thế của mạng lưới chi nhánh truyền thống?',['không cần đến chi nhánh','chuyển đổi nhà cung cấp','bất tiện'],[213],'full'),
('H15','Dữ liệu giao dịch khách hàng tạo ra lợi thế cạnh tranh gì cho ngân hàng truyền thống?',['dữ liệu giao dịch','phát triển sản phẩm','bán kèm','quản lý rủi ro tín dụng'],[213],'full'),
('H16','Đổi mới sản phẩm và đổi mới quy trình có thể tác động khác nhau đến chi phí và chất lượng dịch vụ như thế nào?',['đổi mới sản phẩm','đổi mới quy trình','cắt giảm chi phí','chất lượng|khác biệt'],[15,34,66,161,162],'partial'),
('H17','Cơ quan quản lý có thể ảnh hưởng đến đổi mới tài chính theo những hướng nào?',['thụ động','chủ động','tiêu chuẩn','quy định'],[158,205,206,207,208],'full'),
('H18','Hãy phân biệt vai trò của công nghệ, nhu cầu khách hàng và cạnh tranh trong việc thúc đẩy đổi mới.',['công nghệ mới','nhu cầu khách hàng','cạnh tranh'],[158,162,185,247],'full'),
('H19','Giá Bitcoin chính xác vào ngày 31/12/2030 là bao nhiêu theo tài liệu?',[],[],'unsupported'),
('H20','Giáo trình chứng minh thuật toán Qdrant HNSW của dự án có độ chính xác tìm kiếm tuyệt đối 100% như thế nào?',[],[],'unsupported')]
def build(rows):
 out=[]
 for cid,q,e,p,s in rows:
  out.append({'id':cid,'question':q,'expected_elements':e,'pages':p,'refusal':s=='unsupported','support_status':s,'category':'master-prompt-'+s})
 return out
Path('reports/rag_development_cases.json').write_text(json.dumps(build(D),ensure_ascii=False,indent=2),encoding='utf-8')
Path('reports/rag_holdout_cases.json').write_text(json.dumps(build(H),ensure_ascii=False,indent=2),encoding='utf-8')
print('wrote',len(D),len(H))
