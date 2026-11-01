import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {api} from './api'

type Hit={rank:number;chunk_id:string;score:number;snippet:string;statement_title?:string}
type Arm={name:string;family:string;target_rank_top10:number|null;query_ms:number;hits:Hit[]}
type Question={id:string;query:string;ticker:string;source_url:string|null;source_locator:string|null;answerable:boolean;review_status:string;arms:Arm[]}
type Lab={status:string;base_commit:string;corpus:string;qrels_sha256:string;human_gold:boolean;limits:string[];live_modes:string[];unavailable_live_modes:string[];questions:Question[]}

const names:Record<string,string>={R0_BM25:'BM25 tác giả',R1_DENSE:'Dense BGE-small',R2_SPLADE:'SPLADE',R3_BM25_DENSE_RRF:'BM25 + Dense RRF',R4_SPLADE_DENSE_RRF:'SPLADE + Dense RRF',R5_THREE_WAY_RRF:'RRF ba nhánh',R6_AUTHOR_DETERMINISTIC_STAGE2:'Stage-2 quy tắc',I1_STRUCTURE_BM25:'BM25 theo cấu trúc bảng'}

export default function Topic3Lab(){
 const result=useQuery({queryKey:['topic3-historical-lab'],queryFn:()=>api<Lab>('/research-lab/topic3'),staleTime:300000})
 const [selected,setSelected]=useState('')
 const lab=result.data
 const q=lab?.questions.find(item=>item.id===selected)||lab?.questions[0]
 return <section className="card" aria-label="Topic 3 Research Lab">
  <h2>Topic 3 · phòng thí nghiệm nghiên cứu</h2>
  <p className="notice"><strong>Kết quả đã đo trước đây — không phải truy vấn vừa chạy.</strong> Ba cột BM25/Dense/Hybrid phía trên là so sánh trực tiếp trên tài liệu đang chọn. Bảng dưới dùng hai hồ sơ SEC năm 2026 và cấu hình mô hình khác.</p>
  {result.isLoading&&<p>Đang đọc bằng chứng đã lưu…</p>}
  {result.isError&&<p role="alert">Chưa đọc được gói thực nghiệm Topic 3; kết quả live phía trên vẫn dùng được.</p>}
  {lab&&q&&<>
   <p className="muted">Corpus: {lab.corpus}. Commit nền: <code>{lab.base_commit.slice(0,12)}</code>. Nhãn: {lab.human_gold?'đã rà soát':'máy chuẩn bị, chưa rà soát độc lập'}.</p>
   <label>Câu hỏi đã đo<select aria-label="Câu hỏi thực nghiệm Topic 3" value={q.id} onChange={e=>setSelected(e.target.value)}>{lab.questions.map(item=><option key={item.id} value={item.id}>{item.ticker} · {item.query}</option>)}</select></label>
   <p className="muted">{q.answerable?'Đã xác định một vị trí dòng nguồn ứng viên':'Không có nguồn trong corpus khóa'} · {q.review_status}. {q.source_locator&&<span>Vị trí: {q.source_locator}.</span>} {q.source_url&&<a href={q.source_url} target="_blank" rel="noreferrer">Mở SEC gốc</a>}</p>
   <div className="scroll-table"><table><thead><tr><th>Phương pháp đã đo</th><th>Nhóm</th><th>Hạng dòng nguồn*</th><th>Qdrant ms*</th><th>Top-1 và trích đoạn</th></tr></thead><tbody>{q.arms.map(arm=><tr key={arm.name}><td><strong>{names[arm.name]||arm.name}</strong></td><td><small>{arm.family}</small></td><td>{q.answerable?(arm.target_rank_top10??'ngoài Top-10'):'không áp dụng'}</td><td>{arm.query_ms.toFixed(2)}</td><td><code>{arm.hits[0]?.chunk_id||'—'}</code><br/><small>{arm.hits[0]?.snippet||arm.hits[0]?.statement_title||'Đoạn nguồn lưu trong JSON thực nghiệm'}</small></td></tr>)}</tbody></table></div>
   <p className="muted">* Hạng của một dòng nguồn máy chuẩn bị; chưa phải Recall độc lập. Thời gian chỉ tính truy vấn Qdrant, không gồm embedding, API hay trình duyệt. Điểm BM25, Dense, SPLADE và RRF không cùng thang.</p>
   <details><summary>Giới hạn và trạng thái live</summary><p>Live trong ứng dụng: {lab.live_modes.join(', ')}. Chỉ có bản đo lưu, chưa có index online phù hợp: {lab.unavailable_live_modes.join(', ')}.</p><ul>{lab.limits.map(limit=><li key={limit}>{limit}</li>)}</ul><p>Qrels SHA-256: <code>{lab.qrels_sha256}</code></p></details>
  </>}
 </section>
}
