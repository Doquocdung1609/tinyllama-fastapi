"""Conversational views over verified annual PDF facts.

Session state records the subject and periods, never answer numbers. Every view,
including a rephrasing, obtains its figures from the selected source again.
"""
from decimal import Decimal, ROUND_HALF_UP
import re

from app.product.answer_composer_v2 import (
    LABELS, _select, _source_explanation, display,
)
from app.product.independent_verifier_v2 import recompute, verify_operand
from app.product.pdf_extract import folded
from app.product.source_cells_v2 import native_catalog

REGIONS = {
    'americas': 'Americas', 'europe': 'Europe', 'greater_china': 'Greater China',
    'japan': 'Japan', 'rest_of_asia_pacific': 'Rest of Asia Pacific',
}
MONEY = 'triệu USD'


def respond(workspace, question, documents, history):
    """Return None when the ordinary financial planner should handle the turn."""
    if len(documents) != 1:
        return None
    q = folded(question)
    if not re.search(r'[à-ỹđ]', question.casefold()):
        return None
    if re.search(r'diem phan tram|percentage points', q) and re.search(r'tuong doi|relative', q):
        return None
    if re.search(r'\b(?:quy\s*[1-4]|q[1-4]|ytd|luy ke|bao cao rieng|cong ty me|truoc dieu chinh|sau dieu chinh)\b', q):
        return None
    previous = history[-1].get('response', {}) if history else {}
    state = previous.get('dialogue_state', {})
    if not state and previous.get('answer_status') == 'VERIFIED_ANSWER':
        slots = previous.get('conversation_slots', {})
        prior_years = slots.get('years') or []
        operation = slots.get('operation')
        metric = slots.get('metric')
        inferred = {
            'FIND_DECLINES': 'decline',
            'GEOGRAPHY_DIFFERENCE': 'geography',
            'PERCENTAGE_POINT_DIFFERENCE': 'margin',
            'RELATIVE_DIFFERENCE': 'margin',
        }.get(operation)
        if metric == 'services_net_sales' and operation in {'PER_100', 'SHARE_PERCENT'}:
            inferred = 'share'
        if metric == 'geography_definition':
            inferred = 'geography'
        if inferred and prior_years:
            state = {'topic': inferred, 'year': prior_years[-1], 'anchor': prior_years[-1]}
    prior = state.get('topic')
    years = list(dict.fromkeys(re.findall(r'(?<!\d)20\d{2}(?!\d)', q)))
    if len(years) > 1:
        return None
    service = re.search(r'dich vu|services', q)
    product = re.search(r'san pham|products', q)
    plain = re.search(r'don gian|de hieu|khong ranh|khong hoc tai chinh|thuat ngu kho', q)
    sources = re.search(r'so (?:lieu )?goc|con so.*(?:dung|tinh)|toan hang|cong thuc', q)
    summary = re.search(r'tom tat lai|doan ket luan|viet.*cau.*(?:kiem tra|thuyet trinh)', q)
    previous_year = re.search(r'^(?:the|con|vay)?\s*nam truoc\b', q)
    explicit_cause = re.search(r'vi sao|tai sao|nguyen nhan', q)
    if re.search(r'ty gia|sang tien viet|doi.*(?:vnd|tien viet)', q):
        topic = 'fx'
    elif years and re.search(r'doanh thu ca nam|doanh thu nam tai chinh', q):
        topic = 'annual_revenue'
    elif re.search(r'ba diem|diem dang chu y|mot phut doc', q):
        topic = 'highlights'
    elif re.search(r'to[aà]n.*(?:cung giam|giam theo)|tong doanh thu.*(?:cung giam|giam theo)', q):
        topic = 'total_growth'
    elif re.search(r'(?:bien|ty suat) loi nhuan gop|gross margin|ty suat loi nhuan', q) and service and product:
        topic = 'margin'
    elif re.search(r'(?:tai my|hoa ky|united states|u\.s\.)', q) and 'americas' in q:
        if 'tai my' not in q:
            return None  # The existing typed geography plan includes a scope-definition citation.
        topic = 'geography'
    elif re.search(r'loi nhuan rong', q) and re.search(r'bang|la|dat', q):
        topic = 'income_check'
    elif re.search(r'greater china.*(?:dat|la|bang)', q) and re.search(r'dung|xac nhan', q):
        from app.product.answer_planner_v2 import plan_question
        if 'loi nhuan' in q or plan_question(question).proposed_amount is not None:
            return None
        topic = 'region_check'
    elif re.search(r'khu vuc|phan khuc', q) and re.search(r'sut|giam', q) and not explicit_cause:
        topic = 'decline'
    elif service and (re.search(r'100\s*(?:do|usd|dong)|ty trong|phu thuoc|quan trong hon', q)):
        if years and 'usd' in q and '100' in q:
            return None
        topic = 'share_change' if re.search(r'phu thuoc|quan trong hon', q) else 'share'
    elif service and product and re.search(r'chu yeu|kiem tien|phan lon|mang nao.*nhieu hon', q):
        topic = 'mix'
    elif not years and prior and (plain or sources or summary or previous_year or
            re.search(r'^(?:vay|the|nhu vay|sut|toi nho|co nghia|neu tinh|hai ket qua|trong nhung diem)|vi sao.*(?:nay|do)', q)):
        topic = prior
    elif plain or sources:
        if previous.get('independent_verification', {}).get('status') == 'VERIFIED':
            view = _explain_verified_operands(workspace, documents, previous, show_sources=bool(sources))
            if view:
                return view
        return {'status': 'SOURCE_EXCERPTS', 'answer_status': 'REQUIRES_SOURCE_REVIEW',
                'answer': 'Bạn muốn tôi giải thích ý nào hoặc mở số gốc của phép tính nào? Hãy nhắc lại chỉ tiêu hoặc kỳ báo cáo để tôi đối chiếu đúng phần.',
                'values': [], 'citations': []}
    else:
        return None

    try:
        catalog = native_catalog(workspace, documents)
    except ValueError:
        return None
    if not catalog:
        return None
    report_year = str(workspace.document(documents[0]).get('report_period', ''))[:4]
    anchor = (state.get('anchor') if prior else None) or report_year
    year = years[-1] if years else state.get('year', report_year)
    if years:
        anchor = year
    if not year.isdigit():
        return None
    if previous_year:
        year = str(int(year)-1)
        if topic in {'share_change', 'mix'}:
            topic = 'share'
    if topic in {'highlights', 'total_growth'} and not years:
        year = anchor
    old = str(int(year)-1)
    citations, values, facts = [], [], {}

    def fact(metric, period=year):
        key = (metric, period)
        if key not in facts:
            cell = _select(catalog, metric, period)
            if cell is None:
                raise ValueError('SOURCE_CELL_NOT_AVAILABLE')
            facts[key] = verify_operand(workspace, cell)
            if facts[key]['period_type'] != 'FY' or facts[key]['unit'] not in {'MILLION_USD', '%'}:
                raise ValueError('UNSUPPORTED_ANNUAL_FACT')
        return facts[key]

    def cite(*cells):
        refs = []
        for cell in cells:
            if cell not in citations:
                citations.append(cell)
            refs.append(f'[{citations.index(cell)+1}]')
        return ''.join(refs)

    def number(value):
        return display(value, 'vi')

    def amount(cell):
        return f"{number(cell['value'])} {MONEY} {cite(cell)}"

    def calc(operation, *cells):
        value = Decimal(recompute(operation, list(cells)))
        values.append(str(value))
        return value

    def ratio(period):
        inputs = (fact('services_net_sales', period), fact('net_revenue', period))
        # Use the same verified operands for both the displayed share and its explanation.
        rounded = calc('SHARE_PERCENT', *inputs)
        return rounded, inputs

    def growth(metric):
        current, earlier = fact(metric), fact(metric, old)
        return calc('ABS_CHANGE', current, earlier), calc('PERCENT_CHANGE', current, earlier), (current, earlier)

    def share_change():
        nonlocal year
        year = anchor
        earlier = str(int(anchor)-1)
        now, now_inputs = ratio(anchor)
        before, before_inputs = ratio(earlier)
        comparable = {(c['statement_scope'], c['basis'], c['currency']) for c in (*now_inputs, *before_inputs)}
        if len(comparable) != 1:
            raise ValueError('INCOMPARABLE_REVENUE_SHARES')
        precise_now = Decimal(recompute('SHARE_PERCENT', list(now_inputs), places=12))
        precise_before = Decimal(recompute('SHARE_PERCENT', list(before_inputs), places=12))
        delta = (precise_now - precise_before).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        values.append(str(delta))
        if plain:
            return (f'Nói dễ hiểu, cứ thu 100 đô thì năm trước có khoảng {number(before)} đô từ dịch vụ, '
                    f'còn năm sau là {number(now)} đô. {cite(*before_inputs, *now_inputs)}')
        if sources:
            return ('Đây là hai số dùng để tính tỷ trọng mới nhất: doanh thu dịch vụ '
                    f'{amount(now_inputs[0])} và tổng doanh thu {amount(now_inputs[1])}. '
                    f'Chia số thứ nhất cho số thứ hai rồi nhân 100. Để so với FY{earlier}, '
                    f'tôi dùng {amount(before_inputs[0])} chia {amount(before_inputs[1])}.')
        direction = 'tăng' if delta > 0 else 'giảm' if delta < 0 else 'không đổi'
        return (f'Tỷ trọng dịch vụ {direction}: từ {number(before)}% năm tài chính {earlier} '
                f'đến {number(now)}% năm tài chính {anchor}, chênh {number(abs(delta))} điểm phần trăm '
                f'sau khi làm tròn. {cite(*before_inputs, *now_inputs)} '
                'Điều này cho biết dịch vụ đóng góp nhiều hay ít hơn vào doanh thu, chưa đủ để kết luận doanh nghiệp phụ thuộc vào dịch vụ.')

    def margin():
        a = fact('services_gross_margin_percentage')
        b = fact('products_gross_margin_percentage')
        refs = cite(a, b)
        left, right = number(a['value']), number(b['value'])
        if explicit_cause:
            paragraph = margin_reason(a['metric'])
            trend = (' Báo cáo giải thích biên dịch vụ tăng so với năm trước chủ yếu vì cơ cấu dịch vụ thay đổi, '
                     'và chi phí cao hơn bù bớt phần tăng đó. '+cite(paragraph)) if paragraph else ''
            return (f'Bảng cho thấy dịch vụ đạt {left}% và sản phẩm đạt {right}%. {refs} '
                    'Phần tôi đối chiếu chưa giải thích riêng vì sao có toàn bộ khoảng cách giữa hai mảng.'+trend)
        if plain:
            explanation = (f'Cứ bán được 100 đô dịch vụ thì còn khoảng {left} đô sau chi phí trực tiếp. '
                           f'Nếu bán 100 đô sản phẩm thì còn khoảng {right} đô. {refs} '
                           'Hai con số này chưa trừ các chi phí khác của công ty.')
            if state.get('margin_cause'):
                paragraph = margin_reason(a['metric'])
                if paragraph:
                    explanation += (' Báo cáo nói việc bán các loại dịch vụ khác nhau giúp công ty giữ lại nhiều tiền hơn '
                                    'so với năm trước, dù chi phí cao hơn làm giảm bớt mức tăng. ' + cite(paragraph))
            return explanation
        pp = calc('PERCENTAGE_POINT_DIFFERENCE', a, b)
        relative = calc('RELATIVE_DIFFERENCE', a, b)
        if sources:
            return (f'Số gốc là {left}% cho dịch vụ và {right}% cho sản phẩm. {refs}\n\n'
                    f'Chênh lệch trực tiếp: {left} − {right} = {number(pp)} điểm phần trăm.\n\n'
                    f'Chênh lệch tương đối: ({left} − {right}) ÷ {right} × 100 ≈ {number(relative)}%. {refs}')
        if re.search(r'nen dung|thuyet trinh', q):
            return (f'Khi trình bày hai mức biên cạnh nhau, dùng {number(pp)} điểm phần trăm vì người nghe '
                    f'có thể lấy {left}% trừ {right}% ngay. Dùng {number(relative)}% nếu muốn diễn đạt mức chênh '
                    f'so với mức biên của sản phẩm làm gốc. {refs}')
        if re.search(r'tuong doi', q):
            return f'Lấy mức biên của sản phẩm làm gốc, dịch vụ cao hơn khoảng {number(relative)}%. {refs}'
        proposal = re.search(r'(\d+(?:[.,]\d+)?)\s*%', q)
        if proposal and re.search(r'dung khong|co nghia', q):
            claimed = Decimal(proposal[1].replace(',', '.'))
            verdict = 'Đúng, nếu bạn đang nói theo tỷ lệ tương đối.' if claimed == relative else 'Không.'
            return (f'{verdict} {number(pp)} điểm phần trăm là kết quả của phép trừ trực tiếp {left}% − {right}%. '
                    f'Nếu muốn nói cao hơn bao nhiêu phần trăm so với sản phẩm, chia chênh lệch cho {right}% '
                    f'rồi nhân 100. Kết quả là {number(relative)}%. {refs}')
        if prior == 'margin' and re.search(r'bao nhieu|chinh xac', q):
            return f'Chênh {number(pp)} điểm phần trăm: {left}% − {right}%. {refs}'
        return (f'Biên lợi nhuận gộp dịch vụ là {left}%, còn sản phẩm là {right}%. '
                f'Khoảng cách là {number(pp)} điểm phần trăm. {refs}')

    def margin_reason(metric):
        for paragraph in _source_explanation(workspace, documents, metric, [old, year]):
            if re.search(r'different mix of services, partially offset by higher costs', paragraph['text'], re.I):
                return paragraph
        return None

    def decline(include_cause=False):
        changes = []
        for key, label in REGIONS.items():
            metric = key+'_net_sales'
            current, earlier = fact(metric), fact(metric, old)
            delta = Decimal(recompute('ABS_CHANGE', [current, earlier]))
            if delta < 0:
                changes.append((metric, label, current, earlier))
        sentences = []
        for metric, label, current, earlier in changes:
            proposal = re.search(r'(\d+(?:[.,]\d+)?)\s*%', q)
            if not include_cause:
                delta = calc('ABS_CHANGE', current, earlier)
                percent = calc('PERCENT_CHANGE', current, earlier)
                references = cite(current, earlier)
                if proposal and 'dung' in q:
                    claimed = Decimal(proposal[1].replace(',', '.'))
                    verdict = 'Đúng' if claimed == abs(percent) else 'Không đúng'
                    sentences.append(f'{verdict}. Tính từ báo cáo, mức giảm là {number(abs(percent))}%. {references}')
                elif re.search(r'tinh thu|ca so tien|ca.*phan tram', q):
                    sentences.append(f'{label} giảm từ {amount(earlier)} xuống {amount(current)}. '
                                     f'Lấy số năm trước trừ số năm sau, mức giảm là {number(abs(delta))} {MONEY}. '
                                     f'Chia mức giảm đó cho doanh thu năm trước, kết quả khoảng {number(abs(percent))}%. {references}')
                else:
                    sentences.append(f'{label} giảm {number(abs(delta))} {MONEY}, tương đương {number(abs(percent))}% so với FY{old}. {references}')
            if include_cause:
                paragraphs = _source_explanation(workspace, documents, metric, [old, year])
                if paragraphs:
                    passage = paragraphs[0]
                    match = re.search(r'lower net sales of ([\w -]+), partially offset by higher net sales of ([\w -]+)', passage['text'], re.I)
                    if match:
                        sentences.append(f'Tại {label}, báo cáo cho biết doanh thu {match[1]} giảm, được bù một phần nhờ doanh thu {match[2]} tăng. {cite(passage)}')
                    else:
                        sentences.append(f'Báo cáo giải thích biến động tại {label} trong đoạn nguồn đính kèm. {cite(passage)}')
                else:
                    sentences.append(f'Tôi đối chiếu được doanh thu tại {label} giảm, nhưng chưa tìm thấy đoạn giải thích nguyên nhân trong báo cáo. {cite(current, earlier)}')
        return ' '.join(sentences) or 'Tôi chưa tìm thấy khu vực giảm trong các kỳ đối chiếu.'

    def total():
        delta, percent, inputs = growth('net_revenue')
        direction = 'tăng' if delta > 0 else 'giảm' if delta < 0 else 'không đổi'
        return f'Doanh thu toàn công ty {direction} {number(abs(percent))}% so với FY{old}. {cite(*inputs)}'

    try:
        if topic == 'fx':
            if not service:
                return None
            cell = fact('services_net_sales')
            return {'status': 'SOURCE_EXCERPTS', 'answer_status': 'REQUIRES_SOURCE_REVIEW',
                    'answer': (f'Doanh thu dịch vụ FY{year} là {amount(cell)}. '
                               'Để đổi sang VND theo tỷ giá hôm nay, tôi cần một nguồn USD/VND có ngày áp dụng. '
                               'Báo cáo này chỉ cung cấp số doanh thu bằng USD.'),
                    'values': [], 'citations': citations}
        if topic == 'annual_revenue':
            if int(year) <= int(report_year):
                return None
            cell = fact('net_revenue', report_year)
            return {'status': 'SOURCE_EXCERPTS', 'answer_status': 'REQUIRES_SOURCE_REVIEW',
                    'answer': (f'Tài liệu đang chọn là báo cáo FY{report_year}. {cite(cell)} '
                               f'Tôi chưa có doanh thu cả năm FY{year} từ tài liệu này. '
                               f'Bạn có thể chọn báo cáo FY{year} để tôi kiểm tra đúng kỳ.'),
                    'values': [], 'citations': citations}
        if topic == 'mix':
            a, b = fact('products_net_sales'), fact('services_net_sales')
            recompute('SUM', [a, b])  # Check scope, period and units before ranking.
            aa, bb = Decimal(a['value']), Decimal(b['value'])
            lead = 'Sản phẩm mang về nhiều doanh thu hơn.' if aa > bb else 'Dịch vụ mang về nhiều doanh thu hơn.' if aa < bb else 'Hai mảng mang về doanh thu bằng nhau.'
            answer = f'{lead} FY{year}, sản phẩm mang về {amount(a)}, còn dịch vụ mang về {amount(b)}.'
        elif topic == 'share':
            share, (part, whole) = ratio(year)
            answer = f'Trong mỗi 100 USD doanh thu năm tài chính {year}, khoảng {number(share)} USD đến từ dịch vụ. {cite(part, whole)}'
            if not plain:
                answer += f' Tôi lấy doanh thu dịch vụ {amount(part)} chia tổng doanh thu {amount(whole)}, rồi nhân 100.'
        elif topic == 'share_change':
            answer = share_change()
        elif topic == 'margin':
            if summary:
                a = fact('services_gross_margin_percentage')
                b = fact('products_gross_margin_percentage')
                gap = calc('PERCENTAGE_POINT_DIFFERENCE', a, b)
                share, inputs = ratio(year)
                answer = (f'Biên gộp dịch vụ đạt {number(a["value"])}%, sản phẩm đạt {number(b["value"])}%, '
                          f'chênh {number(gap)} điểm phần trăm. {cite(a, b)} '
                          f'Dịch vụ đóng góp {number(share)}% doanh thu FY{year}. {cite(*inputs)} {total()}')
                paragraph = margin_reason(a['metric'])
                if paragraph:
                    answer += (' Báo cáo giải thích mức tăng so với năm trước bằng sự thay đổi cơ cấu dịch vụ '
                               'và tác động bù trừ của chi phí cao hơn, còn nguyên nhân của toàn bộ khoảng cách '
                               'với sản phẩm chưa được xác định trong đoạn này. ' + cite(paragraph))
                else:
                    answer += ' Các số liệu trên cho thấy mức chênh lệch giữa hai mảng, còn nguyên nhân cần bằng chứng riêng.'
            else:
                answer = margin()
        elif topic == 'geography':
            a, b = fact('americas_net_sales'), fact('us_net_sales')
            diff = calc('GEOGRAPHY_DIFFERENCE', a, b)
            lead = f'Chênh lệch là {number(diff)} {MONEY}. {cite(a, b)} ' if not ('americas' in q) else ''
            answer = lead + (f'Hai phạm vi khác nhau. Mỹ là một quốc gia và Americas là một khu vực báo cáo. '
                      f'FY{year}, Mỹ ghi nhận {amount(b)}, Americas ghi nhận {amount(a)}. '
                      + ('' if lead else f'Chênh lệch là {number(diff)} {MONEY}. {cite(a, b)}'))
        elif topic in {'income_check', 'region_check'}:
            metric = 'net_income' if topic == 'income_check' else 'greater_china_net_sales'
            cell = fact(metric)
            proposal = re.search(r'(\d[\d.,]*)\s*(?:trieu|million)', q)
            if not proposal or not re.search(r'\busd\b|\$', q):
                return None
            raw = proposal[1]
            asserted = Decimal(raw.replace('.', '').replace(',', '') if re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+', raw) else raw.replace(',', '.'))
            delta = Decimal(recompute('PROPOSAL_DIFFERENCE', [cell], proposed_amount=str(asserted)))
            verdict = 'Đúng.' if delta == 0 else 'Không đúng.'
            answer = f'{verdict} FY{year}, {LABELS[metric][0]} là {amount(cell)}.'
            if delta:
                answer += f' Số bạn nêu chênh {number(abs(delta))} {MONEY}.'
            if topic == 'income_check' and asserted == Decimal(fact('net_revenue')['value']):
                answer += f" Con số bạn nêu là doanh thu thuần {cite(fact('net_revenue'))}."
        elif topic == 'decline':
            answer = decline(include_cause=bool(explicit_cause))
        elif topic == 'total_growth':
            answer = total()
            if summary:
                answer = f'{total()} {decline()} {decline(include_cause=True)}'
        elif topic == 'highlights':
            answer = total() if re.search(r'tang truong doanh thu|lien quan.*doanh thu', q) else '\n\n'.join([total(), share_change(), decline()])
        else:
            return None
    except (ValueError, ArithmeticError):
        # Delegate to the standard planner so it can diagnose the requested metric or period.
        return None

    return {'status': 'SUPPORTED', 'answer_status': 'SOURCE_SUPPORTED_NON_NUMERIC' if not values else 'VERIFIED_ANSWER',
            'answer': answer, 'values': values, 'citations': citations,
            'verification_status': 'VERIFIED_SOURCE_EVIDENCE',
            'dialogue_state': {'topic': topic, 'year': year, 'anchor': anchor,
                               'margin_cause': topic == 'margin' and bool(explicit_cause or state.get('margin_cause'))},
            'operands': list(facts.values())}


def _explain_verified_operands(workspace, documents, previous, *, show_sources):
    """Give older supported answers a source-bound explanation path too."""
    operands = previous.get('operands') or []
    if not 0 < len(operands) <= 6:
        return None
    citations = []
    try:
        for operand in operands:
            if operand.get('document_id') not in documents:
                return None
            citations.append(verify_operand(workspace, operand))
    except (ValueError, ArithmeticError):
        return None
    from app.product.answer_composer_v2 import UNITS
    lines = []
    for index, cell in enumerate(citations, 1):
        label = LABELS.get(cell['metric'], (cell.get('row_label', cell['metric']),))[0]
        unit = UNITS.get(cell['unit'], (cell['unit'],))[0]
        lines.append(f"{label.capitalize()} năm {cell['period']}: {display(cell['value'], 'vi')} {unit} [{index}].")
    intro = 'Đây là các số gốc từ báo cáo mà tôi dùng.' if show_sources else 'Tách ý trước thành từng số trong báo cáo sẽ dễ theo dõi hơn.'
    return {'status': 'SUPPORTED', 'answer_status': 'SOURCE_SUPPORTED_NON_NUMERIC',
            'answer': intro + '\n\n' + '\n\n'.join(lines), 'citations': citations,
            'values': [], 'operands': citations, 'verification_status': 'VERIFIED_SOURCE_EVIDENCE'}
