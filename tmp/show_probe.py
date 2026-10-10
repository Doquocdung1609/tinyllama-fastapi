import json
rows=json.load(open('reports/rag_master_retrieval_probe.json',encoding='utf-8'))
for cid in ['D01','D02','D05','D10','D11','D12','D13','H01','H02','H03','H07','H09','H10','H12','H16','H17','H18','H20']:
 r=next(x for x in rows if x['id']==cid)
 print('\n###',cid,r['question'])
 for x in r['top'][:5]: print(x['page'],x['chunk_id'],x['text'].replace('\n',' ')[:420])
