"""Streamlit UI: Vietnamese GenAI Learning Studio."""
from pathlib import Path
import time
import requests
import streamlit as st

st.set_page_config(page_title="GenAI Learning Studio", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
API_URL = st.sidebar.text_input("FastAPI URL", "http://127.0.0.1:8000")
st.markdown("""
<style>
.stApp{background:#f6f8fb;color:#15243a}.block-container{padding-top:1.6rem;max-width:1450px}
[data-testid="stSidebar"]{background:#101d32}.stSidebar *{color:#eef4ff!important}
.hero{padding:1.4rem 1.7rem;border:1px solid #dce4ef;border-radius:16px;background:white;margin-bottom:1rem}
.hero h1{margin:0;color:#13233b}.hero p{margin:.35rem 0 0;color:#62738b}
.card{border:1px solid #dce4ef;border-radius:14px;padding:1rem 1.1rem;background:white;min-height:105px}
.small{font-size:.85rem;color:#60738b}.pipeline{font-weight:600;color:#234f81;line-height:2.2}
div[data-testid="stMetric"]{background:white;border:1px solid #dce4ef;padding:12px 14px;border-radius:12px}
</style>""", unsafe_allow_html=True)

PAGES = ["Dashboard", "Chat với Llama 3", "Talk to Documents / RAG", "Chunk Explorer", "English Script → Audio", "Text → Image", "Image → Video", "System / GPU"]
st.sidebar.markdown("## ◈ GenAI Studio")
st.sidebar.caption("FastAPI · Ollama · Qdrant")
page = st.sidebar.radio("Điều hướng", PAGES, label_visibility="collapsed")
learning = st.sidebar.toggle("Chế độ học tập", value=True)
if learning:
    st.sidebar.info("RAG: Extraction → Cleaning → Chunking → Embedding → Retrieval → LLM")


def api(method, path, **kwargs):
    try:
        response = requests.request(method, f"{API_URL.rstrip('/')}{path}", timeout=kwargs.pop("timeout", 60), **kwargs)
        if response.ok:
            return response.json()
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        st.error(f"API: {detail}")
    except requests.RequestException as exc:
        st.error(f"Không thể kết nối FastAPI tại {API_URL}. Hãy chạy `uvicorn main:app --reload`. ({exc})")
    return None


def page_header(title, desc):
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{desc}</p></div>', unsafe_allow_html=True)


def explain(text):
    if learning:
        st.caption("🎓 " + text)


def status_dot(label, ok, detail=""):
    st.markdown(f"**{'🟢' if ok else '🔴'} {label}: {'Online' if ok else 'Offline'}**  {detail}")


if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "selected_doc" not in st.session_state:
    st.session_state.selected_doc = None

if page == "Dashboard":
    page_header("GenAI Learning Studio", "Một dịch vụ GenAI đa năng · RAG là lõi học tập, Llama 3 chạy cục bộ qua Ollama.")
    status = api("GET", "/system/status", timeout=10) or {}
    stats = api("GET", "/stats", timeout=10) or {}
    ollama = status.get("ollama", {}); qdrant = status.get("qdrant", {})
    a,b,c,d = st.columns(4)
    a.metric("Ollama", "Online" if ollama.get("online") else "Offline")
    b.metric("Model LLM", status.get("model", "llama3:latest"))
    c.metric("Tài liệu / Chunks", f"{stats.get('documents',0)} / {stats.get('chunks',0)}")
    d.metric("Qdrant vectors", qdrant.get("vectors", 0))
    a,b,c,d = st.columns(4)
    a.metric("Embedding dim", status.get("embedding",{}).get("dimension") or "Chưa sẵn sàng")
    vram=ollama.get("gpu_vram_bytes",0)
    b.metric("VRAM Ollama đang dùng", f"{vram/1024**3:.1f} GB" if vram else "Chưa có báo cáo")
    c.metric("Audio", stats.get("audio_files", 0)); d.metric("Ảnh / Video", f"{stats.get('images',0)} / {stats.get('videos',0)}")
    st.subheader("Pipeline Talk to Documents")
    st.markdown('<div class="card pipeline">PDF　→　Extract　→　Clean　→　Chunk　→　Embedding　→　Qdrant　→　Retrieve　→　Llama 3　→　Answer</div>', unsafe_allow_html=True)
    st.write("")
    status_dot("Ollama", ollama.get("online",False), status.get("model","llama3:latest"))
    status_dot("Qdrant", qdrant.get("online",False), f"{qdrant.get('collection','knowledgebase')} · {qdrant.get('distance','Cosine')}")
    if status.get("embedding",{}).get("error"):
        st.warning(f"Embedding chưa sẵn sàng: {status['embedding']['error']}")
        st.code("ollama pull nomic-embed-text")
    if not ollama.get("online") or not ollama.get("model_available"):
        st.info("Khởi động Ollama và kiểm tra: `ollama list`, `ollama run llama3:latest`.")

elif page == "Chat với Llama 3":
    page_header("Chat với Llama 3", "Hỏi đáp thông thường bằng mô hình Ollama trên máy của bạn.")
    status = api("GET", "/system/status", timeout=8) or {}
    status_dot("Ollama", status.get("ollama",{}).get("online",False), status.get("model","llama3:latest"))
    temperature = st.sidebar.slider("Temperature", 0.0, 1.5, .7, .1)
    max_tokens = st.sidebar.slider("Max tokens", 64, 2048, 512, 64)
    for item in st.session_state.chat_history:
        with st.chat_message(item["role"]): st.markdown(item["content"])
    prompt = st.chat_input("Nhập câu hỏi của bạn…")
    if prompt:
        st.session_state.chat_history.append({"role":"user","content":prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Llama 3 đang trả lời…"):
                result = api("POST", "/chat", json={"message":prompt,"temperature":temperature,"max_tokens":max_tokens,"history":st.session_state.chat_history[:-1]}, timeout=300)
            if result:
                st.markdown(result["answer"]); st.session_state.chat_history.append({"role":"assistant","content":result["answer"]})
    if st.button("Xóa hội thoại"): st.session_state.chat_history=[]; st.rerun()

elif page == "Talk to Documents / RAG":
    page_header("Talk to Documents", "Tải PDF, quan sát trạng thái xử lý và đặt câu hỏi có căn cứ theo tài liệu.")
    explain("Extraction lấy text theo trang; các bước tiếp theo được xử lý nền và lưu vector cùng metadata.")
    uploaded = st.file_uploader("Chọn một hoặc nhiều PDF", type=["pdf"], accept_multiple_files=True, key="rag_pdf")
    if uploaded and st.button("Tải lên và lập chỉ mục", type="primary"):
        for pdf_file in uploaded:
            with st.spinner(f"Đang gửi {pdf_file.name}…"):
                result = api("POST", "/documents/upload", files={"file":(pdf_file.name,pdf_file.getvalue(),"application/pdf")}, timeout=180)
            if result:
                st.session_state.selected_doc=result["document_id"]
                st.success(f"Đã nhận {pdf_file.name}; xử lý nền bắt đầu.")
                with st.status(f"Đang xử lý {pdf_file.name}…", expanded=True) as processing:
                    progress_bar=st.progress(0.08,text="UPLOADED")
                    current=result
                    for _ in range(180):
                        current=api("GET",f"/documents/{result['document_id']}",timeout=30) or current
                        stage=current.get("status","UPLOADED")
                        progress={"UPLOADED":.08,"PROCESSING":.12,"EXTRACTING":.25,"CLEANING":.35,"CHUNKING":.48,"EMBEDDING":.68,"INDEXING":.86,"READY":1.0,"ERROR":0.0}.get(stage,.05)
                        progress_bar.progress(progress,text=f"{stage} · {current.get('pages',0)} trang · {current.get('chunks',0)} chunks")
                        if stage in {"READY","ERROR"}: break
                        time.sleep(1)
                    processing.update(label=f"{current.get('status','UNKNOWN')}: {pdf_file.name}",state="complete" if current.get("status")=="READY" else "error")
                    if current.get("error"): st.error(current["error"])
    docs = api("GET", "/documents", timeout=10) or []
    if docs:
        doc_options = {f"{d['filename']} · {d['status']} · {d.get('chunks',0)} chunks":d["document_id"] for d in docs}
        selected = st.selectbox("Thư viện tài liệu", list(doc_options), index=next((i for i,v in enumerate(doc_options.values()) if v==st.session_state.selected_doc),0))
        doc_id=doc_options[selected]; st.session_state.selected_doc=doc_id
        doc=api("GET",f"/documents/{doc_id}",timeout=10) or {}
        progress={"UPLOADED":.08,"PROCESSING":.12,"EXTRACTING":.25,"CLEANING":.35,"CHUNKING":.48,"EMBEDDING":.68,"INDEXING":.86,"READY":1.0,"ERROR":0.0}.get(doc.get("status"),0.05)
        st.progress(progress,
                    text=f"Pipeline: {doc.get('status','UNKNOWN')} · {doc.get('pages',0)} trang · {doc.get('chunks',0)} chunks")
        if doc.get("error"): st.error(doc["error"])
        if st.button("Re-index tài liệu", disabled=(doc.get("status") in {"UPLOADED","EXTRACTING","CLEANING","CHUNKING","EMBEDDING","INDEXING"}), key=f"reindex_{doc_id}"):
            if api("POST",f"/documents/{doc_id}/process",timeout=15): st.info("Đã đưa tài liệu vào hàng xử lý lại.")
        top_k=st.slider("Top-k",1,10,3); threshold=st.slider("Similarity threshold",0.0,1.0,0.7,.05)
        question=st.text_input("Câu hỏi theo tài liệu",placeholder="Ví dụ: Chính sách nghỉ phép quy định thế nào?")
        debug=st.checkbox("RAG Debug Mode",value=True)
        if st.button("Tìm kiếm và trả lời",type="primary",disabled=(doc.get("status")!="READY" or not question)):
            with st.spinner("Embedding câu hỏi → Qdrant retrieval → Llama 3…"):
                result=api("POST","/rag/query",json={"question":question,"top_k":top_k,"score_threshold":threshold},timeout=300)
            if result:
                st.subheader("Câu trả lời"); st.markdown(result["answer"])
                st.subheader("Nguồn")
                for index,source in enumerate(result["sources"],1): st.write(f"#{index} · {source['filename']} · trang {source['page']} · {source['score']:.3f} · `{source['chunk_id']}`")
                for index,chunk in enumerate(result["retrieved_chunks"],1):
                    with st.expander(f"Chunk #{index} · {chunk.get('filename')} · trang {chunk.get('page')} · score {chunk['score']:.3f}"): st.write(chunk.get("text"))
                if debug:
                    with st.expander("Retrieved Context"): st.code(result["context"] or "Không có context")
                    with st.expander("Final Prompt"): st.code(result["final_prompt"])
    else: st.info("Thư viện đang trống. Tải PDF lên để bắt đầu.")

elif page == "Chunk Explorer":
    page_header("Chunk Explorer", "Xem từng bước từ PDF đến các chunk, chỉnh kích thước và overlap trực tiếp.")
    explain("Chunking chia văn bản để retrieval; chunk giữ trang nguồn, vị trí ký tự và metadata.")
    docs=api("GET","/documents",timeout=10) or []
    if not docs: st.info("Hãy tải PDF trong tab Talk to Documents trước.")
    else:
        labels={f"{d['filename']} · {d['status']}":d["document_id"] for d in docs}
        label=st.selectbox("Tài liệu",list(labels)); size=st.slider("chunk_size",100,2000,800,50); overlap=st.slider("chunk_overlap",0,size-1,min(120,size-1),10)
        did=labels[label]
        data=api("GET",f"/documents/{did}/preview",params={"chunk_size":size,"chunk_overlap":overlap},timeout=60)
        if data:
            chunks=data["chunks"]; raw="\n\n".join(p["text"] for p in data["pages"]); cleaned="\n\n".join(p["cleaned_text"] for p in data["pages"])
            lens=[len(x["text"]) for x in chunks]
            a,b,c,d=st.columns(4); a.metric("Ký tự sạch",len(cleaned)); b.metric("Tổng chunks",len(chunks)); c.metric("TB ký tự",round(sum(lens)/max(1,len(lens)))); d.metric("Token ước tính",sum(x["token_estimate"] for x in chunks))
            st.markdown("**RAW TEXT　↓　CLEAN TEXT　↓　"+"　↓　".join(f"CHUNK {i+1}" for i in range(min(len(chunks),4)))+("　↓　…" if len(chunks)>4 else "")+"**")
            with st.expander("Hiển thị raw extracted text"): st.text_area("Raw text",raw,height=200)
            with st.expander("Hiển thị cleaned text"): st.text_area("Cleaned text",cleaned,height=200)
            table=[{"Chunk ID":x["chunk_id"],"Page":x["page"],"Length":len(x["text"]),"Preview":x["text"][:100],"Vector":x.get("vector_id") or "Chưa index"} for x in chunks]
            st.dataframe(table,use_container_width=True,hide_index=True)
            for x in chunks:
                with st.expander(f"Chunk {x['chunk_index']+1:02d} · Page {x['page']} · {len(x['text'])} ký tự"):
                    st.write(x["text"]); st.caption(f"ID {x['chunk_id']} · chars {x['start']}–{x['end']} · overlap {x['overlap']} · ~{x['token_estimate']} tokens · embedding {x['embedding_status']}")
                    st.json(x["metadata"])

elif page == "English Script → Audio":
    page_header("English Script → Audio", "Llama 3 chuẩn hóa lời thoại; local TTS tạo file âm thanh có thể tải về.")
    explain("Llama 3 chuẩn bị câu chữ; Windows SAPI/pyttsx3 tổng hợp giọng nói cục bộ, không yêu cầu API trả phí.")
    script=st.text_area("English script",height=220,placeholder="Hello everyone. Today I am going to introduce our project…")
    voice_data=api("GET","/tts/voices",timeout=10) or {"voices":[]}
    voice_options=["Windows SAPI default"]+voice_data.get("voices",[])
    a,b,c,d=st.columns(4); rate=a.slider("Speech rate",80,300,175); volume=b.slider("Volume",0.0,1.0,1.0,.05); normalize=c.toggle("Chuẩn hóa bằng Llama 3",True); voice=d.selectbox("Voice",voice_options)
    if st.button("Tạo audio",type="primary",disabled=not script.strip()):
        with st.spinner("Đang chuẩn bị script và tạo giọng nói…"):
            data=api("POST","/tts/generate",json={"script":script,"normalize":normalize,"rate":rate,"volume":volume,"voice":None if voice=="Windows SAPI default" else voice},timeout=300)
        if data:
            st.success(f"Đã tạo audio · {data['voice']} · {data['duration_seconds'] or '—'} giây · {data['size_bytes']:,} bytes")
            a,b=st.columns(2); a.text_area("Original script",data["original_script"],height=150); b.text_area("Normalized script",data["processed_script"],height=150)
            audio=requests.get(f"{API_URL.rstrip('/')}{data['audio_file']}",timeout=30).content
            st.audio(audio); st.download_button("Tải audio",audio,file_name=Path(data["audio_file"]).name,mime="audio/wav" if data["audio_file"].endswith("wav") else "audio/mpeg")

elif page == "Text → Image":
    page_header("Text → Image", "Tạo ảnh bằng Stable Diffusion cục bộ nếu model và GPU khả dụng.")
    prompt=st.text_area("Prompt",placeholder="A cosy living room with trees in it")
    neg=st.text_input("Negative prompt"); a,b,c=st.columns(3); steps=a.slider("Steps",1,60,25); scale=b.slider("Guidance scale",1.0,15.0,7.5,.5); seed=c.number_input("Seed (0 = random)",min_value=0,value=0)
    w,h=st.columns(2); width=w.select_slider("Width",[256,384,512,640,768],512); height=h.select_slider("Height",[256,384,512,640,768],512)
    if st.button("Tạo ảnh",type="primary",disabled=not prompt):
        with st.spinner("Đang tạo ảnh…"):
            result=api("POST","/image/generate",json={"prompt":prompt,"negative_prompt":neg,"steps":steps,"guidance_scale":scale,"width":width,"height":height,"seed":int(seed) or None},timeout=900)
        if result: st.image(f"{API_URL.rstrip('/')}{result['image_url']}",caption=f"Seed: {result['seed']} · {steps} steps · {width}×{height} · {result['generation_seconds']} giây")
    st.caption("Tab vẫn hoạt động khi dependency/model ảnh chưa cài; API trả lời rõ lý do. Ảnh không bị giả lập.")

elif page == "Image → Video":
    page_header("Image → Video", "Tab thử nghiệm Stable Video Diffusion: ảnh đầu vào → frame → MP4.")
    source=st.file_uploader("Ảnh đầu vào",type=["png","jpg","jpeg"]); a,b=st.columns(2); frames=a.slider("Số frames",2,25,14); fps=b.slider("FPS",1,30,7)
    if source and st.button("Tạo video",type="primary"):
        st.image(source,width=350)
        with st.spinner("Đang tạo frames và mã hóa video…"):
            result=api("POST","/video/generate",files={"file":(source.name,source.getvalue(),source.type)},data={"num_frames":frames,"fps":fps},timeout=1800)
        if result:
            video=requests.get(f"{API_URL.rstrip('/')}{result['video_url']}",timeout=60).content
            st.video(video); st.caption(f"{result['frames']} frames · {result['fps']} FPS · {result['generation_seconds']} giây · {result['size_bytes']:,} bytes")
    st.info("Video diffusion thường cần GPU có VRAM lớn; thiếu mô hình/GPU sẽ trả lỗi thân thiện và các tab khác vẫn dùng được.")

else:
    page_header("System / Models / GPU", "Thông tin runtime thực tế của FastAPI, Ollama, embedding, Qdrant và phần cứng.")
    data=api("GET","/system/status",timeout=15)
    if data:
        st.json(data)
        st.info(f"Model LLM chính: {data['model']}. `ollama ps` được đọc qua API: `size_vram` báo VRAM thực tế Ollama đang dùng. CUDA cho Diffusers chỉ báo khả dụng khi PyTorch xác nhận.")
        with st.expander("Document library"):
            docs=api("GET","/documents",timeout=10) or []
            if docs:
                st.dataframe([{k:d.get(k) for k in ("filename","status","pages","chunks","indexed_at","error")} for d in docs],use_container_width=True,hide_index=True)
                choice=st.selectbox("Chọn tài liệu để xóa",[d["document_id"] for d in docs],format_func=lambda v:next(d["filename"] for d in docs if d["document_id"]==v))
                if st.button("Xóa tài liệu và vectors",type="secondary") and api("DELETE",f"/documents/{choice}"): st.success("Đã xóa."); st.rerun()
            else: st.caption("Chưa có tài liệu.")
        with st.expander("Qdrant collection"):
            qdrant=api("GET","/qdrant/status",timeout=10) or {}
            st.write(f"Collection `{qdrant.get('collection','knowledgebase')}` · vectors {qdrant.get('vectors',0)} · dimension {qdrant.get('dimension') or '—'} · cosine")
