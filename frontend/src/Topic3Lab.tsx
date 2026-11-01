import {useState} from 'react'
import {useMutation,useQuery} from '@tanstack/react-query'
import {api,post} from './api'

type Hit={rank:number;chunk_id:string;score:number;snippet:string;statement_title?:string}
type Arm={name:string;family:string;target_rank_top10:number|null;query_ms:number;hits:Hit[]}
type Question={id:string;query:string;ticker:string;source_url:string|null;source_locator:string|null;answerable:boolean;review_status:string;arms:Arm[]}
type Lab={status:string;base_commit:string;corpus:string;qrels_sha256:string;human_gold:boolean;limits:string[];live_modes:string[];unavailable_live_modes:string[];questions:Question[]}
type ReplayCase={case:string;question:string;accession:string;source_url:string;report_date:string;a1_top1:{chunk_id:string;label:string};a4_top1:{chunk_id:string;label:string;excerpt:string|null;verification_status:string}}
type Replay={status:string;review_status?:string;dataset?:string;aggregate?:Record<string,{known_positive_hit:Record<string,number>;top1_labels:Record<string,number>}>;cases?:ReplayCase[];limits?:string[]}
type LiveStatus={status:string;index_a:string;index_b:string;mode:string}
type LiveHit={rank:number;chunk_id:string;fiscal_period:string;source_url:string;accession_number:string;snippet:string;verification_status:string}
type LiveResult={status:string;experiment_id:string;arm:string;index:string;run_utc:string;elapsed_ms:number;hits:LiveHit[];limits:string[]}
type LiveSummary={status:string;case_count:number;human_gold:boolean;numeric_cells_verified:number;arms:Record<string,{known_positive_hit:Record<string,number>;top1_labels:Record<string,number>;p50_ms:number}>}

const names:Record<string,string>={R0_BM25:'BM25 tác giả',R1_DENSE:'Dense BGE-small',R2_SPLADE:'SPLADE',R3_BM25_DENSE_RRF:'BM25 + Dense RRF',R4_SPLADE_DENSE_RRF:'SPLADE + Dense RRF',R5_THREE_WAY_RRF:'RRF ba nhánh',R6_AUTHOR_DETERMINISTIC_STAGE2:'Stage-2 quy tắc',I1_STRUCTURE_BM25:'BM25 theo cấu trúc bảng'}

export default function Topic3Lab(){
 const result=useQuery({queryKey:['topic3-historical-lab'],queryFn:()=>api<Lab>('/research-lab/topic3'),staleTime:300000})
 const replay=useQuery({queryKey:['faith-r-recorded-lab'],queryFn:()=>api<Replay>('/research-lab/faith-r'),staleTime:300000})
 const liveStatus=useQuery({queryKey:['faith-r-live-status'],queryFn:()=>api<LiveStatus>('/research-lab/faith-r/live/status'),staleTime:30000})
 const liveSummary=useQuery({queryKey:['faith-r-live-summary'],queryFn:()=>api<LiveSummary>('/research-lab/faith-r/live/summary'),staleTime:300000})
 const [liveQuestion,setLiveQuestion]=useState('What was Amazon total revenue in fiscal 2024?')
 const [liveArm,setLiveArm]=useState('A4R')
 const live=useMutation({mutationFn:()=>post<LiveResult>('/research-lab/faith-r/live',{query:liveQuestion,arm:liveArm})})
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
  {replay.data?.status==='RECORDED_EXPERIMENT'&&<details><summary>FAITH-R · thử nghiệm trên 15 câu hỏi đã lưu</summary>
   <p className="notice">RECORDED_EXPERIMENT · UNREVIEWED. Cùng Top-10 đã lưu; chỉ đổi thứ tự. Không phải tìm kiếm trực tiếp hoặc đánh giá độc lập.</p>
   <p>Đoạn được gắn nhãn đúng ở hạng 1: ban đầu {replay.data.aggregate?.A1_recorded.known_positive_hit['1']}/15; FAITH-R {replay.data.aggregate?.A4_reranked.known_positive_hit['1']}/15. Đây là nhãn đoạn, chưa xác minh ô số liệu.</p>
   <div className="scroll-table"><table><thead><tr><th>Câu hỏi</th><th>Ban đầu · Top 1</th><th>FAITH-R · Top 1</th><th>Bằng chứng ứng viên</th></tr></thead><tbody>{replay.data.cases?.map(item=><tr key={item.case}><td>{item.question}<br/><a href={item.source_url} target="_blank" rel="noreferrer">SEC {item.accession}</a> · {item.report_date}</td><td><code>{item.a1_top1.chunk_id}</code><br/>{item.a1_top1.label}</td><td><code>{item.a4_top1.chunk_id}</code><br/>{item.a4_top1.label} · {item.a4_top1.verification_status}</td><td><small>{item.a4_top1.excerpt||'Chưa định vị dòng nguồn'}</small></td></tr>)}</tbody></table></div>
   <ul>{replay.data.limits?.map(limit=><li key={limit}>{limit}</li>)}</ul>
  </details>}
  <div className="card"><h3>FAITH-R · chạy trên chỉ mục SEC phục hồi</h3>
   <p className="muted">{liveStatus.data?.status==='AVAILABLE'?'LIVE_ON_DEMAND · 8.670 đoạn SEC; Index A phục hồi P3D, Index B đã sửa kỳ tài chính.':'NOT_AVAILABLE · cần bật chỉ mục nghiên cứu riêng trên máy này.'} Kết quả là đoạn nguồn, chưa phải số liệu được xác minh.</p>
   {liveSummary.data&&<details><summary>Kết quả các phương án đã chạy · {liveSummary.data.case_count} câu công khai</summary><p className="notice">{liveSummary.data.status}. Nhãn đã lộ trong lúc phát triển; chưa có đối chiếu độc lập. Ô số liệu xác minh: {liveSummary.data.numeric_cells_verified}.</p><div className="scroll-table"><table><thead><tr><th>Phương án</th><th>Đoạn đúng Top 1/3/10</th><th>Top 1 chưa chấm</th><th>Trung vị ms</th></tr></thead><tbody>{Object.entries(liveSummary.data.arms).map(([arm,data])=><tr key={arm}><td>{arm}</td><td>{[1,3,10].map(k=>`${data.known_positive_hit[String(k)]}/${liveSummary.data.case_count}`).join(' · ')}</td><td>{data.top1_labels.UNJUDGED||0}</td><td>{data.p50_ms.toFixed(1)}</td></tr>)}</tbody></table></div></details>}
   {liveStatus.data?.status==='AVAILABLE'&&<><label>Câu hỏi nghiên cứu<input aria-label="Câu hỏi FAITH-R trực tiếp" value={liveQuestion} onChange={e=>setLiveQuestion(e.target.value)}/></label>
    <label>Phương án<select aria-label="Phương án FAITH-R trực tiếp" value={liveArm} onChange={e=>setLiveArm(e.target.value)}>{(['A0','A1','A2','A3','A4','A4R','A5'] as const).map(arm=><option key={arm} value={arm}>{arm}{arm==='A4R'?' · sửa lỗi dòng nguồn':''}</option>)}</select></label>
    <button disabled={live.isPending||liveQuestion.trim().length<3} onClick={()=>live.mutate()}>{live.isPending?'Đang truy vấn…':'Chạy truy vấn trên Qdrant nghiên cứu'}</button>
    {live.isError&&<p role="alert">Không chạy được truy vấn nghiên cứu: {String(live.error)}</p>}
    {live.data&&<><p className="notice">{live.data.status} · {live.data.experiment_id} · Index {live.data.index} · {live.data.arm} · {live.data.elapsed_ms.toLocaleString('vi-VN')} ms · {live.data.run_utc}</p>
     <div className="scroll-table"><table><thead><tr><th>Hạng</th><th>Đoạn và kỳ</th><th>Nguồn SEC</th><th>Trích đoạn</th></tr></thead><tbody>{live.data.hits.map(hit=><tr key={hit.chunk_id}><td>{hit.rank}</td><td><code>{hit.chunk_id}</code><br/>{hit.fiscal_period} · {hit.verification_status}</td><td><a href={hit.source_url} target="_blank" rel="noreferrer">{hit.accession_number}</a></td><td><small>{hit.snippet}</small></td></tr>)}</tbody></table></div>
     {live.data.hits.length===0&&<p>Không có đoạn nguồn phù hợp trong phạm vi này; không trả lời số liệu.</p>}
     <ul>{live.data.limits.map(limit=><li key={limit}>{limit}</li>)}</ul></>}
   </>}
  </div>
 </section>
}
