import {useEffect,useState,useRef} from 'react'
import {useQuery,useMutation} from '@tanstack/react-query'
import {api,post} from './api'
import type {Answer,Doc,Evidence} from './api'
import {Button} from '@/components/ui/button'
import {reasonText} from './error-text'

type Reply=Answer&{session_id:string;resolved_question?:string;conversation_reset?:boolean}
type Turn={question:string;answer:Reply}

export default function FinancialChat({selected,open}:{selected:Evidence|null;open:(e:Evidence)=>void}){
 const docs=useQuery({queryKey:['documents'],queryFn:()=>api<{documents:Doc[]}>('/documents'),refetchInterval:3000})
 const [docId,setDocId]=useState(()=>sessionStorage.getItem('active-document')||sessionStorage.getItem('analysis-document')||'')
 const [resetError,setResetError]=useState('');const [question,setQuestion]=useState(''),[turns,setTurns]=useState<Turn[]>([]),[session,setSession]=useState<string|undefined>()
 const [advanced,setAdvanced]=useState(false),[metric,setMetric]=useState(''),[operation,setOperation]=useState(''),[scope,setScope]=useState(''),[year,setYear]=useState('')
 const chosen=docId||docs.data?.documents.find(d=>d.status==='READY')?.id||''
 const scopeRef=useRef(chosen);scopeRef.current=chosen
 useEffect(()=>{if(selected?.document_id&&selected.document_id!==docId)setDocId(selected.document_id)},[selected?.document_id])
 useEffect(()=>{
  try{const saved=JSON.parse(sessionStorage.getItem('financial-chat-'+chosen)||'null');setTurns(saved?.turns||[]);setSession(saved?.session)}catch{setTurns([]);setSession(undefined)}
  if(chosen){sessionStorage.setItem('active-document',chosen);sessionStorage.setItem('analysis-document',chosen)}
 },[chosen])
 const run=useMutation({mutationFn:async()=>{
  const constraints:Record<string,string>={}
  if(advanced){if(metric)constraints.metric=metric;if(operation)constraints.operation=operation;if(scope)constraints.statement_scope=scope;if(year)constraints.current_period=year}
  const answer=await post<Reply>('/chat',{question,document_ids:[chosen],session_id:session,constraints})
  return {answer,asked:question,documentId:chosen}
 },onSuccess:({answer,asked,documentId})=>{if(scopeRef.current!==documentId)return;setSession(answer.session_id);setTurns(t=>{const next=[...(answer.conversation_reset?[]:t),{question:asked,answer}].slice(-20);sessionStorage.setItem('financial-chat-'+documentId,JSON.stringify({turns:next,session:answer.session_id}));return next});setQuestion('')}})
 const doc=docs.data?.documents.find(d=>d.id===chosen)
 return <section className="card financial-chat"><h2>Trợ lý tài chính</h2>
  <p className="muted">Chọn tài liệu, hỏi tự nhiên và mở từng nguồn để đối chiếu. Số liệu chỉ được tính khi ô nguồn đủ điều kiện.</p>
  <label>Tài liệu đang sử dụng<select aria-label="Tài liệu trợ lý" value={chosen} onChange={e=>setDocId(e.target.value)}>
   <option value="">Chọn một tài liệu READY</option>{docs.data?.documents.filter(d=>d.status==='READY').map(d=><option key={d.id} value={d.id}>{d.filename} · {d.issuer||'Chưa rõ doanh nghiệp'} · {d.report_period||'Chưa rõ kỳ'}</option>)}
  </select></label>
  <p className="notice" role="status">{doc?`${doc.filename} · ${doc.status} · ${doc.pages} trang`: 'Tải tài liệu tại Kho tài liệu để bắt đầu.'}</p>
  <div role="log" aria-label="Hội thoại tài chính" aria-live="polite">
   {turns.map((turn,i)=><article className="chat-turn" key={i}>
    <p className="chat-question"><strong>Bạn:</strong> {turn.question}</p>
    <div className={turn.answer.status==='SUPPORTED'?'answer':'notice'}>
     <strong>{turn.answer.status==='SUPPORTED'?'Đã xác minh ô nguồn':turn.answer.status==='SOURCE_EXCERPTS'?'Trích đoạn có nguồn · chưa xác minh số liệu':'Cần làm rõ hoặc bổ sung bằng chứng'}</strong>
     <p style={{whiteSpace:'pre-wrap'}}>{turn.answer.answer}</p>
     {turn.answer.status==='SUPPORTED'&&<p className="muted">Kỳ nguồn: {[...new Set(turn.answer.citations?.map(c=>c.period||c.report_period).filter(Boolean))].join(' · ')}</p>}
     {turn.answer.reason&&<p>{reasonText(turn.answer.reason)}</p>}
     {turn.answer.formula&&<details><summary>Công thức và phép tính</summary><p>{turn.answer.formula}</p><p>{turn.answer.values?.join('; ')} {turn.answer.unit==='MILLION_USD'?'triệu USD':turn.answer.unit}</p><div className="scroll-table"><table><thead><tr><th>Ô nguồn</th><th>Kỳ</th><th>Giá trị gốc</th><th>Tiền tệ / hệ số</th></tr></thead><tbody>{turn.answer.operands?.map((o,i)=><tr key={i}><td>{o.row_label||'Toán hạng'}</td><td>{o.fiscal_year?`FY${o.fiscal_year} · `:''}{o.period_end||o.period}</td><td>{o.value_raw||o.value_decimal||o.value}</td><td>{o.currency||o.unit} × {o.scale||'1'}</td></tr>)}</tbody></table></div></details>}
     <div className="sources">{turn.answer.citations?.map((c,j)=><button key={j} className="source-button" onClick={()=>open(c)}>{c.row_label||c.issuer||'Nguồn'} · trang {c.page||'SEC'}</button>)}</div>
     <details><summary>Phạm vi và thông tin kỹ thuật</summary><p>{turn.answer.verification_status} · {turn.answer.search_profile}</p><p>Câu hỏi có ngữ cảnh: {turn.answer.resolved_question}</p></details>
    </div></article>)}
  </div>
  <form onSubmit={e=>{e.preventDefault();run.mutate()}}>
   <label>Câu hỏi tài chính<textarea aria-label="Câu hỏi trợ lý" value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ví dụ: What was net income in fiscal year 2025?" maxLength={2000} required/></label>
   <details><summary>Tùy chọn nâng cao · chỉ gửi khi chủ động chọn</summary>
    <label><input type="checkbox" checked={advanced} onChange={e=>setAdvanced(e.target.checked)}/> Áp dụng ràng buộc thủ công</label>
    {advanced&&<div className="filters"><label>Chỉ tiêu<select aria-label="Chỉ tiêu trợ lý" value={metric} onChange={e=>setMetric(e.target.value)}><option value="">Tự động</option><option value="net_income">Net income</option><option value="net_revenue">Total net sales</option><option value="assets">Total assets</option></select></label>
     <label>Phép tính<select value={operation} onChange={e=>setOperation(e.target.value)}><option value="">Tự động</option><option value="EXTRACT">Đọc giá trị</option><option value="PERCENT_CHANGE">Tăng trưởng %</option><option value="ABS_CHANGE">Chênh lệch</option></select></label>
     <label>Phạm vi<select value={scope} onChange={e=>setScope(e.target.value)}><option value="">Tự động</option><option value="CONSOLIDATED">Hợp nhất</option><option value="SEPARATE">Riêng</option></select></label><label>Kỳ hiện tại<input value={year} onChange={e=>setYear(e.target.value)} placeholder="FY: 2025 hoặc ngày nguồn"/></label></div>}
   </details>
   <div className="row"><Button disabled={!chosen||run.isPending||question.length<2} type="submit">{run.isPending?'Đang tìm nguồn và xác minh…':'Gửi câu hỏi'}</Button><Button type="button" variant="outline" onClick={async()=>{try{if(session)await api(`/chat/${session}`,{method:'DELETE'});setTurns([]);setSession(undefined);sessionStorage.removeItem('financial-chat-'+chosen);setResetError('')}catch(e){setResetError(e instanceof Error?e.message:'Không thể xóa hội thoại')}}}>Hội thoại mới</Button></div>
   {run.error&&<p role="alert">{run.error.message}</p>}{resetError&&<p role="alert">{resetError}</p>}
  </form>
 </section>
}
