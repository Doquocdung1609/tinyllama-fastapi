"""Retrieve bounded source windows from saved PDF lines across page boundaries."""
import re

from app.product.document_page_map import source_ref
from app.product.pdf_extract import folded


_PAGE = re.compile(r'\b(?:trang(?: pdf)?|pdf page|page)\s+(\d{1,3})\b')
_EXCERPT = re.compile(r'^(?:hay\s+)?(?:trich dan|trich nguyen van|quote|show (?:me )?the source)\b')
_STOP = set('hay trich dan nguyen van dong muc doan o tai cua trong va the line quote show me source on at from'.split())


def _pairs(text):
    words = [word for word in re.findall(r'[a-z]+', folded(text)) if word not in _STOP]
    return set(zip(words, words[1:]))


def answer(workspace, question, document_ids):
    """Answer explicit multi-page excerpt requests using one citation per page."""
    if len(document_ids) != 1:
        return None
    query = folded(question).strip()
    if not _EXCERPT.match(query) or re.search(r'\b(tinh|bao nhieu|calculate|how much|difference)\b', query):
        return None
    mentions = list(_PAGE.finditer(query))
    if not 2 <= len(mentions) <= 6:
        return None
    numbers = [int(match[1]) for match in mentions]
    if len(set(numbers)) != len(numbers):
        return None
    doc = workspace.document(document_ids[0])
    if not doc or doc['status'] != 'READY':
        return None

    citations = []
    paragraphs = []
    for index, (number, mention) in enumerate(zip(numbers, mentions)):
        start = mentions[index - 1].end() if index else 0
        target = _pairs(query[start:mention.start()])
        try:
            page = workspace.page_evidence(doc['id'], number) if 1 <= number <= doc['pages'] else None
        except ValueError:
            page = None
        lines = page.get('lines', []) if page and page.get('status') != 'FAILED' else []
        if not lines or not target:
            paragraphs.append(f'**Trang PDF {number}** · Chưa đủ văn bản hoặc tên dòng để xác định đoạn nguồn.')
            continue

        scores = [len(target & _pairs(line['text'])) for line in lines]
        best = max(scores)
        if not best or scores.count(best) != 1:
            paragraphs.append(f'**Trang PDF {number}** · Chưa tìm được một dòng khớp rõ với yêu cầu.')
            continue
        anchor = scores.index(best)
        line = lines[anchor]
        # Read across stored chunk cuts but keep every citation within its own page.
        window = lines[max(0, anchor - 1):anchor + 2]
        citations.append(source_ref(doc, number, '\n'.join(part['text'] for part in window),
                                    box=line['box'], identity=f'page-context-{anchor}',
                                    extraction_method=page.get('method')))
        paragraphs.append(f"**Trang PDF {number}** · {line['text']} [{len(citations)}]")

    return {
        'status': 'SOURCE_EXCERPTS' if citations else 'INSUFFICIENT_EVIDENCE',
        'answer': '\n\n'.join(paragraphs), 'citations': citations, 'values': [],
        'verification_status': 'SOURCE_TEXT_UNREVIEWED',
        'warnings': ['Các dòng được trích từ tài liệu. Số liệu trong đoạn trích cần được đối chiếu với ô nguồn.'],
    }
