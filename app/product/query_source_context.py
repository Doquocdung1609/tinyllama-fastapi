"""Conservative company slots; display corrections never authenticate an issuer."""
import re
from app.product.pdf_extract import folded


def company_mentions(question):
    stop=set('what was were is are the show tell me calculate compare for of in total net sales income revenue assets company document report year this selected please s which geographic segment generated highest largest maximum lowest minimum source sum annual consolidated quarterly fiscal how much many year-over-year yoy'.split())
    mentions=[]
    for match in re.finditer(r"\b((?:[\w&.-]+\s+){0,3}[\w&.-]+)['’]s\b",question):
        parts=match[1].split()
        while parts and parts[0].casefold() in stop:parts.pop(0)
        if parts:mentions.append(' '.join(parts))
    for match in re.finditer(r'\b(?:net income|net sales|revenue|total assets)\s+(?:of|for)\s+([A-Z][\w&.-]+(?:\s+(?:Inc\.?|Corp\.?|Ltd\.?))?)',question,re.I):
        if match[1].casefold() in stop|{'fiscal','fy','year'}:continue
        mentions.append(match[1])
    for match in re.finditer(r'\b((?:[A-Z][\w&.-]+\s+){0,2}[A-Z][\w&.-]+)\s+(?:net income|net sales|revenue|total assets)\b',question,re.I):
        parts=match[1].split()
        if parts[-1].casefold() in stop:continue
        while parts and parts[0].casefold() in stop:parts.pop(0)
        if parts:mentions.append(' '.join(parts))
    q=folded(question)
    for match in re.finditer(r'(?:nghien cuu|tong quan)\s+(?:(?:doanh nghiep|cong ty)\s+)?(.{2,70}?)(?=\s+(?:nam|dua tren|theo tai lieu)|[?.]|$)',q):
        value=match[1].strip()
        if not value.startswith(('dua tren','tai lieu','doanh nghiep','cong ty')):mentions.append(value)
    for match in re.finditer(r'(?:doanh thu(?: thuan)?|loi nhuan(?: sau thue)?|tong tai san)\s+(?:cua\s+)?(.{2,80}?)\s+(?:nam|fy|fiscal year)\s+20\d{2}',q):
        value=re.sub(r'^(?:cong ty|tap doan)\s+','',match[1]).strip()
        value=re.sub(r'^(?:hop nhat|rieng|cong ty me)\s+','',value)
        if value not in {'trong','tai','cuoi','cua','hop nhat','rieng','la bao nhieu'} and not value.startswith(('trong ','cho ','so voi ')):
            mentions.append(value)
    return sorted(set(mentions))


def source_company_conflict(workspace,document_ids,question):
    names=company_mentions(question)
    if not names:return None
    issuers=[]
    for doc_id in document_ids:
        doc=workspace.document(doc_id)
        if doc is None:continue
        if hasattr(workspace,'source_file'):
            from app.product.document_metadata import extract_metadata
            field=extract_metadata(workspace.source_file(doc_id))['fields']['issuer']
            if field['status']=='AUTO_CONFIRMED' and field['value']:issuers.append(folded(field['value']))
        else:issuers.append(folded(doc.get('issuer','')))
    conflicting=[name for name in names if not any(re.search(r'(?<!\w)'+re.escape(folded(name))+r'(?!\w)',issuer) for issuer in issuers)]
    return {'status':'QUERY_CONTEXT_CONFLICT','reason':'QUESTION_COMPANY_SCOPE_CONFLICT',
            'conflicting_fields':['issuer'],'issuer_mentions':conflicting,
            'answer':'Doanh nghiệp trong câu hỏi chưa khớp danh tính được xác nhận từ nội dung tài liệu.',
            'values':[],'citations':[],'verification_status':'QUERY_CONTEXT_CONFLICT'} if conflicting else None
