"""Vietnamese-first Financial Intelligence Studio product UI.

All document counts, results, statuses and answers are read from local APIs.
Concept images under docs/topic3/ui_references are layout references only.
"""
from __future__ import annotations

import html
import json
import os
import re
from decimal import Decimal, InvalidOperation
from time import perf_counter
from urllib.parse import urlparse

import requests
import streamlit as st


st.set_page_config(page_title="Financial Intelligence Studio", page_icon="📈", layout="wide",
                   initial_sidebar_state="auto")

PAGES = ["Tổng quan", "Tìm kiếm tài chính", "Phân tích tài chính AI", "Kho tài liệu",
         "So sánh truy xuất", "Hệ thống & cài đặt"]
API = os.getenv("STUDIO_API_URL", "http://127.0.0.1:8000").rstrip("/")
RESEARCH_API = os.getenv("TOPIC3_RESEARCH_API_URL", "http://127.0.0.1:8767").rstrip("/")
for endpoint in (API, RESEARCH_API):
    parsed = urlparse(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.username:
        st.error("Chỉ hỗ trợ API cục bộ được cấu hình rõ ràng.")
        st.stop()

st.markdown("""
<style>
  :root {--navy:#081a35;--blue:#176cff;--cyan:#0aa6d6;--ink:#142b54;--muted:#72839d;--line:#e2eaf4;}
  .stApp {background:#f3f7fc;color:#142646;}
  .block-container {max-width:1530px;padding:1.2rem 1.6rem 3rem;}
  [data-testid="stSidebar"] {background:linear-gradient(165deg,#081a35,#0b2850);min-width:245px;}
  [data-testid="stSidebar"] * {color:#eaf2ff;}
  [data-testid="stSidebar"] [role="radiogroup"] label {padding:.46rem .65rem;border-radius:9px;}
  [data-testid="stSidebar"] [role="radiogroup"] label:hover {background:#176cff55;}
  h1,h2,h3 {color:#142b54;letter-spacing:-.025em;}
  h1 {font-size:2rem!important;font-weight:760!important;}
  h2 {font-size:1.32rem!important;}
  .eyebrow {color:#6b83a5;font-size:.74rem;font-weight:750;letter-spacing:.1em;text-transform:uppercase;}
  .subtle {color:#72839d;font-size:.9rem;}
  .fis-card {background:#fff;border:1px solid #e2eaf4;border-radius:13px;padding:1.05rem 1.2rem;margin:.35rem 0 .85rem;box-shadow:0 2px 9px #17395d09;}
  .fis-card h3 {margin:.1rem 0 .55rem;font-size:1.08rem;}
  .fis-hero {background:linear-gradient(115deg,#176cff,#079fc5);border-radius:15px;color:white;padding:1.45rem;margin:.5rem 0 1rem;}
  .fis-hero.purple {background:linear-gradient(115deg,#4e4dd4,#775ded);}
  .fis-hero h2,.fis-hero p {color:white;margin:0 0 .35rem;}
  .fis-evidence {background:#f7faff;border:1px solid #d9e6f8;border-radius:10px;padding:.85rem;line-height:1.55;white-space:pre-wrap;}
  .fis-evidence mark {background:#ffeb9a;color:#142646;border-radius:3px;padding:0 2px;}
  .fis-rank {color:#176cff;font-weight:750;}
  .fis-badge {display:inline-block;background:#def8ee;color:#00845f;border-radius:5px;padding:.12rem .45rem;font-size:.75rem;font-weight:750;}
  .fis-warning {background:#fff6e6;color:#855512;border:1px solid #f5d89c;border-radius:9px;padding:.75rem;}
  div[data-testid="stMetric"] {background:white;border:1px solid #e2eaf4;padding:12px 14px;border-radius:13px;}
  .stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"] {background:#176cff;border-color:#176cff;}
  @media(max-width:1000px){.block-container{padding:.8rem}.fis-hero{padding:1rem}}
</style>
""", unsafe_allow_html=True)


def request_json(method, path, *, research=False, quiet=False, **kwargs):
    base = RESEARCH_API if research else API
    token = (os.getenv("TOPIC3_RESEARCH_API_TOKEN", "") or st.session_state.get("research_token", "")) if research else (
        os.getenv("STUDIO_API_TOKEN", "") or st.session_state.get("studio_token", ""))
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        response = requests.request(method, base + path, headers=headers,
                                    timeout=kwargs.pop("timeout", 60), **kwargs)
        if response.ok:
            return response.json()
        detail = response.json().get("detail", {}) if response.headers.get("content-type", "").startswith("application/json") else {}
        code = detail.get("code") if isinstance(detail, dict) else str(detail)
        if not quiet:
            st.error(f"Yêu cầu không hoàn thành ({response.status_code}): {code or 'SERVICE_ERROR'}")
    except (requests.RequestException, ValueError) as exc:
        if not quiet:
            st.error("Không kết nối được dịch vụ cục bộ. Kiểm tra FastAPI/Ollama và thử lại.")
    return None


def heading(kicker, title, description):
    st.markdown(f'<div class="eyebrow">{html.escape(kicker)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.caption(description)


def safe_highlight(text, query):
    escaped = html.escape(text)
    terms = [t for t in re.findall(r"\w+", query, re.UNICODE) if len(t) >= 3][:12]
    for term in sorted(set(terms), key=len, reverse=True):
        escaped = re.sub(re.escape(html.escape(term)), lambda match: "<mark>" + match.group(0) + "</mark>",
                         escaped, flags=re.IGNORECASE)
    return escaped


def display_decimal(value):
    try:
        return format(Decimal(str(value)), ",f")
    except (InvalidOperation, ValueError):
        return str(value)


def open_page(page):
    st.session_state.nav_next = page
    st.rerun()


def get_catalog():
    return request_json("GET", "/studio/sec/catalog", quiet=True) or {"status": "UNAVAILABLE", "filings": []}


def get_pdfs():
    return (request_json("GET", "/studio/documents", quiet=True) or {}).get("documents", [])


def evidence_viewer(item, query=""):
    st.markdown("### Trình xem tài liệu & chứng cứ")
    left, right = st.columns([1.7, 1], gap="medium")
    with left:
        if item.get("document_id"):
            st.markdown(f"**{item.get('filename','PDF')} · trang {item['page']}**")
            token = os.getenv("STUDIO_API_TOKEN", "") or st.session_state.get("studio_token", "")
            try:
                response = requests.get(API + f"/studio/documents/{item['document_id']}/pages/{item['page']}/highlight",
                    params={"chunk_id": item["chunk_id"], "phrase": query[:120]},
                    headers={"Authorization": "Bearer " + token}, timeout=30)
                response.raise_for_status()
                st.image(response.content, caption=f"Trang PDF {item['page']} · {response.headers.get('X-Highlight-Status','')}",
                         width="stretch")
            except requests.RequestException:
                st.warning("Không thể dựng trang PDF đã xác minh; không hiển thị vị trí highlight chưa kiểm tra.")
        else:
            st.info("Nguồn là SEC HTML. Đoạn dưới được đối chiếu với filing gốc; SEC không cung cấp anchor ổn định tới đúng ô.")
            st.markdown('<div class="fis-evidence">' + safe_highlight(item.get("text", ""), query) + "</div>",
                        unsafe_allow_html=True)
            source_url = item.get("source_url", "")
            if source_url.startswith("https://www.sec.gov/Archives/"):
                st.link_button("Mở filing SEC chính thức ↗", source_url)
    with right:
        st.markdown('<div class="fis-card"><h3>Đoạn chứng cứ liên quan</h3><span class="fis-badge">Nguồn đã đối chiếu</span></div>',
                    unsafe_allow_html=True)
        st.write("**Tổ chức:**", item.get("issuer") or item.get("ticker") or "Tài liệu của bạn")
        st.write("**Tài liệu:**", item.get("filename") or item.get("form") or "—")
        st.write("**Kỳ filing / người dùng nhập:**", item.get("report_period") or "Chưa xác định")
        st.write("**Vị trí:**", f"Trang {item['page']}" if item.get("page") else item.get("source_location", {}))
        st.write("**Nguồn SHA256:**", item.get("source_sha256", "—"))
        st.write("**Chunk / parent:**", item.get("chunk_id", "—"))
        st.caption(item.get("provenance_status", "Chưa có xác minh"))
        if item.get("extraction_status") == "PARTIAL_EXTRACTION":
            st.warning("Trích xuất SEC chưa đầy đủ; chứng cứ khác có thể còn thiếu.")
        if item.get("document_id"):
            st.markdown('<div class="fis-evidence">' + safe_highlight(item.get("text", ""), query) + "</div>",
                        unsafe_allow_html=True)
            st.caption("Vùng tô sáng lấy từ tọa độ dòng văn bản PDF đã trích xuất và đối chiếu hash trang.")
        else:
            st.caption("Liên kết mở đúng filing; vị trí bảng/hàng/ô trong trình duyệt chưa được bảo đảm.")


st.sidebar.markdown("## 📈 Financial Intelligence Studio")
st.sidebar.caption("Hybrid Search · Financial AI")
if st.session_state.get("nav_next"):
    st.session_state.nav = st.session_state.pop("nav_next")
page = st.sidebar.radio("Điều hướng", PAGES, key="nav")
with st.sidebar.expander("Kết nối cục bộ", expanded=False):
    st.caption("API chính: " + API)
    if not os.getenv("STUDIO_API_TOKEN"):
        st.text_input("Studio token", type="password", key="studio_token")
    if not os.getenv("TOPIC3_RESEARCH_API_TOKEN"):
        st.text_input("Financial AI token", type="password", key="research_token")
    st.caption("Token chỉ dùng trong phiên giao diện cục bộ.")
health = request_json("GET", "/health", quiet=True) or {}
st.sidebar.caption("● FastAPI online" if health.get("status") == "ok" else "○ FastAPI chưa kết nối")


if page == "Tổng quan":
    heading("Financial Intelligence Platform", "Financial Intelligence Studio",
            "Tìm chứng cứ tài chính và phân tích số liệu có nguồn xác thực.")
    a, b = st.columns(2)
    with a:
        st.markdown('<div class="fis-hero"><h2>Tìm kiếm tài chính</h2><p>BM25 · Dense · Hybrid RRF trên tài liệu thực.</p></div>', unsafe_allow_html=True)
        if st.button("Bắt đầu tìm kiếm →", type="primary", width="stretch"):
            open_page("Tìm kiếm tài chính")
    with b:
        st.markdown('<div class="fis-hero purple"><h2>Phân tích tài chính AI</h2><p>Câu trả lời số chỉ từ ô nguồn đã xác minh.</p></div>', unsafe_allow_html=True)
        if st.button("Phân tích tài chính →", width="stretch"):
            open_page("Phân tích tài chính AI")
    catalog = get_catalog()
    pdf_health = request_json("GET", "/studio/health", quiet=True) or {}
    research = request_json("GET", "/research/v1/health", research=True, quiet=True) or {}
    cols = st.columns(4)
    cols[0].metric("Filing SEC khả dụng", len(catalog.get("filings", [])) if catalog.get("status") == "READY" else "—")
    cols[1].metric("Parent SEC", catalog.get("parents", "—"))
    cols[2].metric("PDF sẵn sàng", pdf_health.get("ready_documents", "—"))
    cols[3].metric("Financial AI", "Sẵn sàng" if research.get("status") == "ready" else "Chưa cấu hình")
    left, right = st.columns([1.5, 1])
    with left:
        st.subheader("Tài liệu đang có")
        rows = [{"Tên": r["issuer"], "Loại": r["form"], "Kỳ filing": r["report_period"],
                 "Trạng thái": r["extraction_status"]} for r in catalog.get("filings", [])]
        rows += [{"Tên": d["filename"], "Loại": d["document_type"], "Kỳ filing": d["report_period"],
                  "Trạng thái": d["status"]} for d in get_pdfs()]
        if rows:
            st.dataframe(rows[:8], width="stretch", hide_index=True)
        else:
            st.info("Chưa có tài liệu được cấu hình. Tải PDF lên hoặc kết nối corpus SEC.")
    with right:
        st.subheader("Trạng thái truy xuất")
        st.write("**BM25 SEC:**", "READY" if catalog.get("status") == "READY" else "Chưa sẵn sàng")
        st.write("**Dense SEC:**", "READY" if catalog.get("dense_vectors") == catalog.get("parents") and catalog.get("status") == "READY" else "Chưa sẵn sàng")
        st.write("**PDF của bạn:**", f"{pdf_health.get('ready_documents',0)} tài liệu READY")
        st.write("**Nguồn AI:**", research.get("source_type", "Chưa kết nối"))
    st.subheader("Quy trình từ tài liệu đến câu trả lời")
    st.markdown('<div class="fis-card">PDF / SEC → Trích xuất → Chia đoạn → BM25 + Dense → Hybrid RRF → Chứng cứ → Kiểm chứng số → Câu trả lời có nguồn</div>', unsafe_allow_html=True)

elif page == "Tìm kiếm tài chính":
    heading("Core 01 / Hybrid Search", "Tìm kiếm bằng chứng tài chính",
            "Tìm trên filing SEC đã xác minh hoặc PDF riêng của bạn; mở đúng nguồn của từng kết quả.")
    catalog = get_catalog()
    pdfs = [d for d in get_pdfs() if d["status"] == "READY"]
    source = st.selectbox("Nguồn tài liệu", ["Hồ sơ SEC", "PDF của bạn"], key="search_source")
    if st.session_state.get("_last_search_source") != source:
        st.session_state.pop("search_response", None)
        st.session_state.pop("selected_evidence", None)
        st.session_state._last_search_source = source
    with st.form("search_form"):
        query = st.text_input("Câu hỏi hoặc từ khóa", value=st.session_state.get("search_query", ""),
                              placeholder="Ví dụ: total sales and revenues trong báo cáo quý")
        c1, c2 = st.columns([2, .7])
        mode = c1.radio("Phương pháp", ["BM25", "Dense", "Hybrid RRF"], horizontal=True)
        top_k = c2.selectbox("Số kết quả", [5, 10, 20])
        issuer = period = ""
        ids = []
        if source == "Hồ sơ SEC":
            filings = catalog.get("filings", [])
            ticker = st.selectbox("Doanh nghiệp", ["Tất cả"] + sorted({r["ticker"] for r in filings}))
            issuer = "" if ticker == "Tất cả" else ticker
            periods = sorted({r["report_period"] for r in filings if not issuer or r["ticker"] == issuer})
            chosen = st.selectbox("Kỳ báo cáo của filing", ["Tất cả"] + periods)
            period = "" if chosen == "Tất cả" else chosen
            st.caption("Bộ lọc kỳ filing không xác minh từng cột số liệu so sánh trong bảng.")
        else:
            choices = {f"{d['filename']} · {d['status']}": d["id"] for d in pdfs}
            selected = st.multiselect("Tài liệu", list(choices))
            ids = [choices[x] for x in selected]
        run = st.form_submit_button("Tìm kiếm", type="primary", width="stretch")
    if run:
        st.session_state.search_query = query
        path = "/studio/sec/search" if source == "Hồ sơ SEC" else "/studio/search"
        payload = {"query": query, "mode": {"BM25": "bm25", "Dense": "dense", "Hybrid RRF": "hybrid"}[mode],
                   "top_k": top_k}
        payload.update({"ticker": issuer, "report_period": period} if source == "Hồ sơ SEC" else {"document_ids": ids})
        with st.spinner("Đang truy xuất và đối chiếu nguồn..."):
            response = request_json("POST", path, json=payload, timeout=120)
        if response is not None:
            st.session_state.search_response = response
            st.session_state.search_origin = source
            st.session_state.selected_evidence = None
    response = st.session_state.get("search_response")
    if response:
        results = response.get("results", [])
        st.caption(f"{len(results)} kết quả · {response.get('mode','—')} · {response.get('latency_ms','—')} ms · generation {str(response.get('generation','PDF riêng'))[:12]}")
        if not results:
            st.info("Không có chứng cứ phù hợp trong phạm vi đã chọn; không suy diễn kết quả.")
        filters, center, preview = st.columns([.8, 1.8, 1], gap="medium")
        with filters:
            st.markdown("### Bộ lọc & nguồn")
            st.write("**Nguồn:**", st.session_state.get("search_origin"))
            st.write("**Trạng thái:**", response.get("status", "—"))
            if response.get("scope_note"):
                st.caption(response["scope_note"])
            if response.get("fusion"):
                st.caption("RRF k=" + str(response["fusion"]["k"]))
        with center:
            st.markdown("### Kết quả đã đối chiếu")
            for item in results:
                with st.container(border=True):
                    st.markdown(f"**{item['rank']}. {item.get('issuer') or item.get('filename') or item.get('ticker','Tài liệu')}**")
                    st.caption(f"{item.get('form') or item.get('document_type','PDF')} · {item.get('report_period') or 'Kỳ chưa xác định'} · B #{item.get('bm25_rank') or '—'} · D #{item.get('dense_rank') or '—'}")
                    st.markdown('<div class="fis-evidence">' + safe_highlight(item.get("text", "")[:380], st.session_state.get("search_query", "")) + "</div>", unsafe_allow_html=True)
                    if st.button("Xem đoạn nguồn →", key="view_" + item["chunk_id"]):
                        st.session_state.selected_evidence = item
                        st.session_state.selected_query = st.session_state.get("search_query", "")
                        st.rerun()
        with preview:
            st.markdown("### Xem nhanh chứng cứ")
            selected_item = st.session_state.get("selected_evidence") or (results[0] if results else None)
            if selected_item:
                st.write(selected_item.get("issuer") or selected_item.get("filename"))
                st.caption(selected_item.get("provenance_status"))
                st.markdown('<div class="fis-evidence">' + safe_highlight(selected_item.get("text", "")[:500], st.session_state.get("search_query", "")) + "</div>", unsafe_allow_html=True)
                st.write("**Nguồn SHA256:**", selected_item.get("source_sha256", "—")[:16] + "…")
        selected_item = st.session_state.get("selected_evidence")
        if selected_item:
            evidence_viewer(selected_item, st.session_state.get("selected_query", ""))
            if st.button("Dùng issuer này trong Financial AI", key="send_ai"):
                st.session_state.ai_context = selected_item
                open_page("Phân tích tài chính AI")
    else:
        st.info("Nhập truy vấn để xem kết quả thực, rank từng phương pháp và chứng cứ nguồn.")

elif page == "Phân tích tài chính AI":
    heading("Core 02 / Grounded Financial QA", "Phân tích tài chính với AI",
            "Chỉ hiển thị số liệu khi nguồn SEC, kỳ và phép tính được kiểm chứng; thiếu chứng cứ sẽ từ chối rõ ràng.")
    context = st.session_state.get("ai_context")
    if context:
        st.info("Ngữ cảnh từ Search: " + str(context.get("issuer") or context.get("filename")) +
                " · " + str(context.get("accession") or context.get("filename")) +
                " · " + str(context.get("chunk_id")))
        if context.get("document_id"):
            st.warning("Chưa có bộ kiểm chứng số dành cho PDF tải lên. Financial AI hiện chỉ xác minh ô số từ filing SEC được hỗ trợ.")
    with st.form("ai_form"):
        question = st.text_area("Câu hỏi tài chính", value=st.session_state.get("ai_question", ""),
                                placeholder="Ví dụ: What were P&G's net sales for the three months ended September 30, 2026?", max_chars=2000)
        operation = st.selectbox("Phép toán", ["EXTRACT", "COMPARE", "ABS_CHANGE", "PERCENT_CHANGE"],
                                 format_func=lambda x: {"EXTRACT":"Giá trị chính xác", "COMPARE":"So sánh hai kỳ", "ABS_CHANGE":"Chênh lệch tuyệt đối", "PERCENT_CHANGE":"Thay đổi phần trăm"}[x])
        cik = st.text_input("CIK giới hạn (nếu cần)", value=context.get("cik", "") if context else "")
        pin_filing = st.checkbox("Giới hạn ở filing SEC đã chọn", value=True,
                                disabled=not bool(context and context.get("filing_id")))
        submit = st.form_submit_button("Phân tích có chứng cứ", type="primary")
    if submit:
        filters = {"cik": cik} if cik else {}
        if pin_filing and context and context.get("filing_id"):
            filters["filing_ids"] = [context["filing_id"]]
        with st.spinner("Đang giải quyết phạm vi, truy xuất ô nguồn và kiểm chứng phép tính..."):
            data = request_json("POST", "/research/v1/query", research=True,
                json={"question": question, "filters": filters, "arm": "B",
                      "operation": operation, "workflow": "automatic_real", "use_llm": False}, timeout=120)
        if data is not None:
            st.session_state.ai_result = data
            st.session_state.ai_question = question
    data = st.session_state.get("ai_result")
    if data:
        answer = data.get("answer", {})
        left, right = st.columns([1.8, 1], gap="medium")
        with left:
            if answer.get("status") == "SUPPORTED":
                st.success("Câu trả lời có ô nguồn SEC đã xác minh")
                values = answer.get("result_values", [])
                st.markdown("## " + "; ".join(display_decimal(v) for v in values) + " " + str(answer.get("result_unit") or ""))
                st.write("**Phép tính Decimal:**", answer.get("formula") or "Giá trị nguồn trực tiếp")
                for n, cell in enumerate(answer.get("source_cells", []), 1):
                    st.caption(f"Ô nguồn {n}: {cell.get('row_label')} · {cell.get('raw_value')} "
                               f"(×{cell.get('multiplier')}) · {cell.get('period_start') or 'as of'} "
                               f"{cell.get('period_end')} · {cell.get('fact_name')}")
            else:
                st.warning("Chưa đủ chứng cứ để đưa ra câu trả lời số.")
                st.write("**Trạng thái:**", answer.get("status", "—"))
                st.write("**Lý do:**", ", ".join(answer.get("reasons", [])) or data.get("failure_code") or "Không xác định")
            st.caption("Financial AI không dùng LLM để tự chọn hoặc suy đoán số tài chính.")
            st.write("**Câu hỏi:**", st.session_state.get("ai_question", ""))
            st.write("**Nguồn phân tích:**", data.get("source_type", "—"))
        with right:
            st.markdown("### Nguồn & phép tính")
            st.write("**Phạm vi:**", data.get("retrieval_status", "—"))
            st.write("**Generation:**", data.get("generation", "—"))
            for n, item in enumerate(data.get("evidence", []), 1):
                with st.container(border=True):
                    st.write(f"**[{n}] {item.get('issuer','Nguồn SEC')} · {item.get('form','')}**")
                    st.caption(str(item.get("financial_period") or item.get("report_date") or ""))
                    st.write(item.get("row_label") or item.get("content", "")[:160])
                    st.write("**Ô gốc:**", item.get("raw_value", "—"), " · **Header:**", " › ".join(item.get("header_path", [])))
                    st.caption("Accession: " + str(item.get("accession", "—")) + " · " + str(item.get("locator", {})))
                    for warning in item.get("warnings", []):
                        st.warning(warning)
                    st.caption(item.get("verification_status", ""))
                    if st.button("Xem nguồn", key=f"ai_evidence_{n}"):
                        cell = next((c for c in answer.get("source_cells", [])
                                     if c.get("parent_id") == item.get("parent_id")), {})
                        st.session_state.ai_selected_evidence = {
                            **item, "chunk_id": item.get("parent_id"),
                            "text": item.get("content", ""), "report_period": str(item.get("financial_period", "")),
                            "source_location": item.get("locator", {}),
                            "source_sha256": cell.get("raw_sha256", ""),
                            "provenance_status": item.get("verification_status", ""),
                            "extraction_status": item.get("extraction_status", ""),
                        }
            if answer.get("status") == "SUPPORTED":
                st.download_button("Sao chép/xuất tóm tắt có nguồn", data=json.dumps(data, ensure_ascii=False, indent=2),
                                   file_name="financial_answer_evidence.json", mime="application/json")
        selected = st.session_state.get("ai_selected_evidence")
        if selected:
            evidence_viewer(selected, st.session_state.get("ai_question", ""))

elif page == "Kho tài liệu":
    heading("Document Library / Upload", "Kho tài liệu tài chính",
            "Tải PDF vào workspace riêng; chỉ tài liệu có BM25 và Dense hoàn tất mới trở thành READY.")
    tab_library, tab_upload = st.tabs(["Danh sách tài liệu", "Tải PDF lên"])
    with tab_upload:
        with st.form("upload_form"):
            file = st.file_uploader("Kéo thả hoặc chọn PDF", type=["pdf"], help="Giới hạn 20 MiB; không tải model mới tự động")
            c1, c2, c3 = st.columns(3)
            issuer = c1.text_input("Tên công ty / issuer (bạn cung cấp)")
            kind = c2.selectbox("Loại tài liệu", ["PDF", "Báo cáo tài chính", "Báo cáo thường niên", "10-K", "10-Q"])
            period = c3.text_input("Kỳ tài liệu (bạn cung cấp)")
            upload = st.form_submit_button("Tải lên & lập chỉ mục", type="primary")
        if upload:
            if file is None:
                st.warning("Hãy chọn một tệp PDF trước.")
            else:
                with st.spinner("Đang tải PDF vào workspace riêng..."):
                    result = request_json("POST", "/studio/documents", files={"file": (file.name, file.getvalue(), "application/pdf")},
                        data={"issuer": issuer, "document_type": kind, "report_period": period}, timeout=60)
                if result:
                    st.success("Đã nhận PDF. Theo dõi trạng thái ở danh sách tài liệu.")
                    st.session_state.uploaded_id = result["id"]
        if st.session_state.get("uploaded_id"):
            job = request_json("GET", "/studio/documents/" + st.session_state.uploaded_id, quiet=True)
            if job:
                st.write("**Giai đoạn:**", job["stage"], " · **Trạng thái:**", job["status"])
                stages = [("EXTRACTING", "Trích xuất văn bản và tọa độ PDF"),
                          ("CHUNKING", "Chia đoạn và gắn trang nguồn"),
                          ("INDEXING_BM25", "Lập chỉ mục BM25"),
                          ("EMBEDDING", "Tạo Nomic embedding"),
                          ("INDEXING_DENSE", "Xác minh vector Qdrant")]
                current = str(job["stage"]).split(" ", 1)[0]
                position = next((i for i, (key, _) in enumerate(stages) if key == current), -1)
                for i, (_, label) in enumerate(stages):
                    mark = "✓" if job["status"] == "READY" or (position >= 0 and i < position) else ("●" if i == position else "○")
                    st.caption(f"{mark} {label}")
                if current == "EMBEDDING" and " " in str(job["stage"]):
                    try:
                        done, total = map(int, str(job["stage"]).split(" ", 1)[1].split("/"))
                        if total > 0:
                            st.progress(min(done / total, 1.0), text=f"Embedding {done}/{total} chunks")
                    except ValueError:
                        pass
                if job.get("error_code"):
                    st.error(job["error_code"])
            if st.button("Làm mới tiến độ"):
                st.rerun()
    with tab_library:
        pdfs = get_pdfs()
        sec = get_catalog().get("filings", [])
        a, b, c = st.columns(3)
        a.metric("PDF của bạn", len(pdfs))
        b.metric("PDF READY", sum(d["status"] == "READY" for d in pdfs))
        c.metric("Filing SEC", len(sec))
        rows = [{"Tài liệu": d["filename"], "Nguồn": "PDF của bạn", "Issuer": d["issuer"],
                 "Loại": d["document_type"], "Kỳ": d["report_period"], "Chunks": d["chunks"],
                 "Trạng thái": d["status"], "id": d["id"]} for d in pdfs]
        rows += [{"Tài liệu": f"{d['ticker']} · {d['form']}", "Nguồn": "SEC chính thức",
                  "Issuer": d["issuer"], "Loại": d["form"], "Kỳ": d["report_period"],
                  "Chunks": d["chunks"], "Trạng thái": d["extraction_status"], "id": d["filing_id"]} for d in sec]
        search_text = st.text_input("Lọc tên, issuer hoặc kỳ")
        if search_text:
            rows = [r for r in rows if search_text.casefold() in " ".join(map(str, r.values())).casefold()]
        st.dataframe(rows, hide_index=True, width="stretch")
        if pdfs:
            selected_id = st.selectbox("Chi tiết PDF của bạn", [d["id"] for d in pdfs],
                                       format_func=lambda x: next(d["filename"] for d in pdfs if d["id"] == x))
            doc = next(d for d in pdfs if d["id"] == selected_id)
            st.write("SHA256:", doc["sha256"], " · Trang:", doc["pages"], " · Chunks:", doc["chunks"])
            st.write("**Giai đoạn:**", doc["stage"])
            if doc["status"] in {"FAILED", "INTERRUPTED"} and st.button("Thử lại xử lý"):
                request_json("POST", f"/studio/documents/{selected_id}/retry")
                st.rerun()
            if doc["status"] == "READY":
                if st.button("Mở trang đầu"):
                    evidence = request_json("GET", f"/studio/documents/{selected_id}/first-chunk")
                    if evidence:
                        st.session_state.selected_evidence = evidence
                        evidence_viewer(evidence)
            with st.expander("Xóa PDF của bạn"):
                st.warning("Xóa chỉ ảnh hưởng tài liệu trong workspace riêng này.")
                confirm = st.checkbox("Tôi xác nhận xóa tài liệu này", key="delete_confirm")
                if st.button("Xóa tài liệu", disabled=not confirm):
                    request_json("DELETE", f"/studio/documents/{selected_id}", params={"confirm": selected_id})
                    st.rerun()
        with st.expander("Chẩn đoán chunk nâng cao"):
            st.caption("Mỗi kết quả Search hiển thị chunk ID, SHA256 nguồn, trang và tọa độ dòng PDF đã trích xuất.")

elif page == "So sánh truy xuất":
    heading("Retrieval Comparison", "So sánh BM25 · Dense · Hybrid RRF",
            "Một câu hỏi, cùng nguồn và bộ lọc. Chỉ hiển thị độ trễ đo thực và thứ hạng chứng cứ.")
    catalog = get_catalog()
    source = st.selectbox("Nguồn so sánh", ["Hồ sơ SEC", "PDF của bạn"], key="compare_source")
    if st.session_state.get("_last_compare_source") != source:
        st.session_state.pop("compare_runs", None)
        st.session_state._last_compare_source = source
    with st.form("compare_form"):
        question = st.text_input("Câu hỏi dùng chung", value=st.session_state.get("compare_question", ""))
        c1, c2 = st.columns(2)
        ticker = c1.selectbox("Issuer", ["Tất cả"] + sorted({r["ticker"] for r in catalog.get("filings", [])})) if source == "Hồ sơ SEC" else "Tất cả"
        top_k = c2.selectbox("Top-k", [5, 10])
        run = st.form_submit_button("So sánh 3 phương pháp", type="primary")
    if run:
        runs = {}
        for mode in ("bm25", "dense", "hybrid"):
            with st.spinner("Đang chạy " + mode.upper() + " trên cùng corpus..."):
                path = "/studio/sec/search" if source == "Hồ sơ SEC" else "/studio/search"
                payload = {"query": question, "mode": mode, "top_k": top_k}
                payload.update({"ticker": "" if ticker == "Tất cả" else ticker} if source == "Hồ sơ SEC" else {})
                started = perf_counter()
                response = request_json("POST", path, json=payload, timeout=120, quiet=True)
                runs[mode] = {"response": response, "http_ms": round((perf_counter()-started)*1000, 2)}
        st.session_state.compare_runs = runs
        st.session_state.compare_question = question
    runs = st.session_state.get("compare_runs")
    if runs:
        generations = {r["response"].get("generation") for r in runs.values() if r.get("response")}
        if len(generations) > 1:
            st.error("Các kênh không dùng cùng generation; kết quả không thể so sánh.")
        else:
            st.caption("Cùng generation: " + str(next(iter(generations), "PDF riêng")))
        cols = st.columns(3)
        for col, mode in zip(cols, ("bm25", "dense", "hybrid")):
            with col:
                result = runs[mode]["response"]
                st.markdown(f"### {mode.upper() if mode != 'hybrid' else 'Hybrid RRF'}")
                if result is None:
                    st.warning("Kênh không khả dụng; không gán điểm chất lượng bằng 0.")
                    continue
                st.metric("HTTP đo thực", str(runs[mode]["http_ms"]) + " ms")
                st.caption("Backend: " + str(result.get("latency_ms", "—")) + " ms")
                for item in result.get("results", []):
                    with st.container(border=True):
                        st.write(f"**#{item['rank']} {item.get('issuer') or item.get('filename')}**")
                        st.caption(f"B #{item.get('bm25_rank') or '—'} · D #{item.get('dense_rank') or '—'} · {item.get('provenance_status','')}")
                        st.write(item.get("text", "")[:160])
                        if st.button("Xem chứng cứ", key=f"compare_{mode}_{item['chunk_id']}"):
                            st.session_state.compare_selected = item
        sets = {m: {x["chunk_id"] for x in (runs[m]["response"] or {}).get("results", [])}
                for m in ("bm25", "dense", "hybrid")}
        a, b, c = st.columns(3)
        a.metric("Chung B ∩ D", len(sets["bm25"] & sets["dense"]))
        b.metric("Chỉ Dense", len(sets["dense"] - sets["bm25"]))
        c.metric("Hybrid top-k", len(sets["hybrid"]))
        if st.session_state.get("compare_selected"):
            evidence_viewer(st.session_state.compare_selected, st.session_state.get("compare_question", ""))
        with st.expander("Đánh giá chất lượng có nhãn"):
            st.info("Không có bộ qrel đã được người duyệt cho corpus đang chọn; chỉ hiển thị so sánh chức năng. Nhãn P11 development là đề xuất tự động, chưa phải chuẩn độc lập.")

elif page == "Hệ thống & cài đặt":
    heading("System & Settings", "Trạng thái hệ thống",
            "Tình trạng dịch vụ và tài nguyên thực. Chẩn đoán kỹ thuật nằm trong phần mở rộng.")
    status = request_json("GET", "/system/status", quiet=True) or {}
    pdf_health = request_json("GET", "/studio/health", quiet=True) or {}
    sec = get_catalog()
    research = request_json("GET", "/research/v1/health", research=True, quiet=True) or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("FastAPI", "Online" if health.get("status") == "ok" else "Offline")
    c2.metric("Ollama", "Online" if status.get("ollama", {}).get("online") else "Offline")
    c3.metric("BM25 SEC", "READY" if sec.get("status") == "READY" else "Chưa sẵn sàng")
    c4.metric("PDF READY", pdf_health.get("ready_documents", "—"))
    st.markdown("### Chỉ mục & mô hình")
    st.write("**Embedding model:**", pdf_health.get("model", "—"), " · **Chiều:**", pdf_health.get("dimension", "—"))
    st.write("**SEC generation:**", sec.get("generation", "—"))
    st.write("**SEC vectors:**", sec.get("dense_vectors", "—"))
    st.write("**Financial AI:**", research.get("status", "Chưa cấu hình"))
    ram = status.get("ram", {})
    disk = status.get("disk", {})
    gpu = status.get("gpu", {})
    r1, r2, r3 = st.columns(3)
    r1.metric("RAM khả dụng", str(ram.get("available_gb", "—")) + " GB")
    r2.metric("Ổ đĩa trống", str(disk.get("free_gb", "—")) + " GB")
    r3.metric("GPU", gpu.get("name") or "Không phát hiện")
    if st.button("Kết nối lại / cập nhật trạng thái"):
        st.rerun()
    with st.expander("Chẩn đoán nâng cao"):
        st.write("Studio workspace:", pdf_health.get("workspace", "—"))
        st.write("SEC manifest:", sec.get("manifest_hash", "—"))
        st.write("SEC model digest:", sec.get("model_digest", "—"))
        st.write("Nguồn AI:", research.get("source_type", "—"))
        st.caption("Không có thao tác dọn dẹp hoặc ghi vào generation SEC được chấp nhận.")
