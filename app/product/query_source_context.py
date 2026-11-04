"""Conservative company slots; display corrections never authenticate an issuer."""
import re
from app.product.pdf_extract import folded


def company_mentions(question):
    stop=set('and or both versus with what was were is are the show tell me calculate compare for of in total net sales income revenue assets company document report year this selected please s which geographic segment generated highest largest maximum lowest minimum source sum annual consolidated quarterly fiscal how much many year-over-year yoy greater china americas u.s. us europe japan pacific asia effective tax rate parent-company parent separate services products percentage percent margin gross fy2025 fy2024 fy2023'.split())
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
    from app.product.financial_understanding import issuers
    known=issuers(question)
    if known:return known
    # A bounded, case-sensitive name slot follows a Vietnamese metric.
    # Lowercase accounting prose (chưa phân phối...) cannot become an issuer.
    for m in re.finditer(r'(?i:doanh thu(?: thuần)?|lợi nhuận(?: sau thuế)?|tổng tài sản)\s+(?i:(?:của|công ty|tập đoàn)\s+)?([A-ZĐ][\w&.-]*(?:\s+(?:Inc\.?|Corp\.?|Ltd\.?))?)',question):
        mentions.append(m[1])
    q=folded(question)
    for match in re.finditer(r'(?:nghien cuu|tong quan)\s+(?:(?:doanh nghiep|cong ty)\s+)?(.{2,70}?)(?=\s+(?:nam|dua tren|theo tai lieu)|[?.]|$)',q):
        value=match[1].strip()
        if not value.startswith(('dua tren','tai lieu','doanh nghiep','cong ty')):mentions.append(value)
    return sorted({m for m in mentions if not re.fullmatch(r'(?:FY\s*)?20\d{2}|Services|Products',m,re.I)})


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
    from app.product.financial_understanding import issuers as resolve_issuers
    identities=set()
    for doc_id in document_ids:
        doc=workspace.document(doc_id)
        if not doc:continue
        from app.product.financial_understanding import document_profile
        identities.update(document_profile(workspace,{**doc,'id':doc_id})['identities'])
    # A verified legal-entity name can prove mismatch even outside the alias
    # catalog. Statement titles and empty fields cannot establish that proof.
    trusted_names=[v for v in issuers if (not hasattr(workspace,'source_file') or re.search(r'\binc\.?|\bcorp\.?|\bltd\.?|\bcong ty\b|\bngan hang tmcp\b',v)) and v and not re.match(r'bao cao|bang can doi|statements?|balance sheet',v)]
    for issuer in trusted_names:identities.update(resolve_issuers(issuer))
    # Unknown metadata is not positive evidence of a contradiction.
    conflicting=[name for name in names if (identities and resolve_issuers(name) and not identities.intersection(resolve_issuers(name))) or
        (resolve_issuers(name) and not identities and trusted_names) or
        (not resolve_issuers(name) and trusted_names and not any(re.search(r'(?<!\w)'+re.escape(folded(name))+r'(?!\w)',issuer) for issuer in trusted_names))]
    return {'status':'QUERY_CONTEXT_CONFLICT','reason':'QUESTION_COMPANY_SCOPE_CONFLICT',
            'conflicting_fields':['issuer'],'issuer_mentions':conflicting,
            'answer':'Doanh nghiệp trong câu hỏi chưa khớp danh tính được xác nhận từ nội dung tài liệu.',
            'values':[],'citations':[],'verification_status':'QUERY_CONTEXT_CONFLICT'} if conflicting else None
