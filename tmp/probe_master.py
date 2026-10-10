import json, requests, sys, time
sys.stdout.reconfigure(encoding='utf-8')
dev = {
'D01':'Năng lực hấp thụ của doanh nghiệp là gì và nó ảnh hưởng thế nào đến khả năng khai thác đổi mới?',
'D02':'Vì sao một doanh nghiệp có công nghệ tốt vẫn có thể thất bại trong quá trình thương mại hóa đổi mới?',
'D03':'Đổi mới tuần tự khác đổi mới đột phá ở những điểm nào?',
'D04':'Những nhân tố nào ảnh hưởng đến hiệu quả chuyển giao công nghệ giữa các tổ chức?',
'D05':'Tại sao các doanh nghiệp đôi khi chủ động chia sẻ công nghệ cho đối thủ hoặc đối tác?',
'D06':'Phân biệt đổi mới dựa trên tri thức và đổi mới chế biến khối.',
'D07':'Chứng khoán hóa có thể cải thiện khả năng thanh khoản của ngân hàng bằng cơ chế nào?',
'D08':'CDS và chứng khoán hóa giống và khác nhau thế nào về chuyển giao rủi ro?',
'D09':'Đổi mới tài chính có thể mang lại lợi ích gì cho khách hàng và tổ chức trung gian tài chính?',
'D10':'Vì sao mức độ bất ổn của môi trường có thể ảnh hưởng đến khả năng nhận ra cơ hội đổi mới?',
'D11':'Điều gì khiến một ý tưởng mới khó được một tổ chức chấp nhận dù ý tưởng đó có giá trị?',
'D12':'Hiệu ứng khóa chặt khách hàng ảnh hưởng thế nào đến việc thay đổi công nghệ?',
'D13':'Những chiến lược chủ yếu để doanh nghiệp thu lợi nhuận từ đổi mới được giáo trình đề cập là gì?',
'D14':'Đổi mới tài chính tác động đến rủi ro như thế nào? Phân biệt các cơ chế nếu tài liệu đề cập.',
'D15':'Theo giáo trình, cổ phiếu của ngân hàng ACB sẽ đạt giá bao nhiêu vào ngày 31/12/2030?'}
hold = {
'H01':'Vì sao tri thức ngầm thường khó chuyển giao hơn tri thức được thể hiện rõ bằng văn bản?',
'H02':'Các mối quan hệ với nhà cung cấp có thể hỗ trợ hoặc cản trở đổi mới ra sao?',
'H03':'Đổi mới kiến trúc khác đổi mới thành phần như thế nào?',
'H04':'Tại sao một thiết kế chủ đạo có thể làm thay đổi chiến lược cạnh tranh của doanh nghiệp?',
'H05':'Vì sao công ty lớn không phải lúc nào cũng khai thác đổi mới đột phá tốt hơn doanh nghiệp mới?',
'H06':'Năng lực tiếp nhận và năng lực chuyển giao công nghệ có vai trò gì trong hợp tác đổi mới?',
'H07':'Những yếu tố nào giúp một doanh nghiệp nhận ra tiềm năng của một đổi mới trước đối thủ?',
'H08':'Đổi mới công nghệ ảnh hưởng như thế nào đến cấu trúc ngành và khả năng cạnh tranh?',
'H09':'Vì sao nhà đổi mới phụ có thể đóng vai trò quan trọng đối với thành công của sản phẩm mới?',
'H10':'Thời điểm đưa công nghệ ra thị trường ảnh hưởng thế nào đến khả năng thu lợi nhuận từ đổi mới?',
'H11':'Vai trò của quản lý rủi ro trong sự phát triển của các công cụ tài chính mới là gì?',
'H12':'Giải thích vì sao các tổ chức tài chính có động cơ phát triển sản phẩm ngay cả khi sản phẩm hiện tại vẫn hoạt động tốt.',
'H13':'Chuyển giao rủi ro tín dụng có thể tác động như thế nào đến khả năng cho vay của ngân hàng?',
'H14':'Vì sao sự phát triển của ngân hàng số có thể làm giảm lợi thế của mạng lưới chi nhánh truyền thống?',
'H15':'Dữ liệu giao dịch khách hàng tạo ra lợi thế cạnh tranh gì cho ngân hàng truyền thống?',
'H16':'Đổi mới sản phẩm và đổi mới quy trình có thể tác động khác nhau đến chi phí và chất lượng dịch vụ như thế nào?',
'H17':'Cơ quan quản lý có thể ảnh hưởng đến đổi mới tài chính theo những hướng nào?',
'H18':'Hãy phân biệt vai trò của công nghệ, nhu cầu khách hàng và cạnh tranh trong việc thúc đẩy đổi mới.',
'H19':'Giá Bitcoin chính xác vào ngày 31/12/2030 là bao nhiêu theo tài liệu?',
'H20':'Giáo trình chứng minh thuật toán Qdrant HNSW của dự án có độ chính xác tìm kiếm tuyệt đối 100% như thế nào?'}
out=[]
for group,cases in [('development',dev),('holdout',hold)]:
 for cid,q in cases.items():
  t=time.perf_counter(); d=requests.post('http://127.0.0.1:8001/rag/query',json={'question':q,'top_k':5,'score_threshold':.55,'document_id':'aedb60bc088e4242970a43da1e897bde','generate_answer':False},timeout=180).json()
  row={'group':group,'id':cid,'question':q,'latency':round(time.perf_counter()-t,3),'retrieved_pages':[x.get('page') for x in d.get('retrieved_chunks',[])],'prompt_pages':[x.get('page') for x in d.get('included_prompt_context',[])],'top':[{'page':x.get('page'),'chunk_id':x.get('chunk_id'),'score':x.get('score'),'text':x.get('text','')[:500]} for x in d.get('reranked_candidates',[])[:10]],'timings':d.get('timings',{})}
  out.append(row); open('reports/rag_master_retrieval_probe.json','w',encoding='utf-8').write(json.dumps(out,ensure_ascii=False,indent=2)); print(cid,row['retrieved_pages'],row['prompt_pages'],row['latency'],flush=True)
