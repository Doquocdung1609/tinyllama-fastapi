import {useEffect,useState,useRef,useCallback} from 'react'
import {useQuery,useMutation,useQueryClient} from '@tanstack/react-query'
import {Plus,MessageSquare,Send,Copy,BookOpen,Pencil,Trash2,Search,Sparkles} from 'lucide-react'
import {api,post,evidenceId} from './api'
import type {Answer,Doc,Evidence} from './api'
import {Button} from '@/components/ui/button'
import EvidencePanel from './EvidencePanel'
import {reasonText} from './error-text'

type Reply=Answer&{session_id:string;resolved_question?:string;conversation_reset?:boolean;retrieval_trace?:Record<string,unknown>}
type Turn={question:string;response:Reply;created_at?:string}
type Session={id:string;title:string;updated_at:string;document_ids:string[];turns?:Turn[];message_count:number}
const suggestions=['Tìm dòng "Lợi nhuận sau thuế chưa phân phối" trong tài liệu đang chọn. Cho biết các đoạn nguồn liên quan và trang PDF.','Tóm tắt tài liệu đang chọn và dẫn nguồn.','Những số liệu nào được điều chỉnh trong tài liệu?']

const financialLabels:Record<string,string>={TRIEU_VND:'triệu đồng',TY_VND:'tỷ đồng',MILLION_USD:'triệu USD',VND:'đồng',USD:'USD',PERCENTAGE_POINTS:'điểm phần trăm',CONSOLIDATED:'Hợp nhất',SEPARATE:'Riêng / công ty mẹ',ORIGINAL:'Đã công bố',ADJUSTMENT:'Điều chỉnh',RESTATED:'Trình bày lại',AS_REPORTED:'Theo báo cáo',NATIVE:'Lớp chữ PDF gốc',OCR:'OCR cần đối chiếu',INDEPENDENT_SOURCE_CELL_VERIFIED:'Đã đối chiếu lại ô PDF gốc'}
const formulaLabels:Record<string,string>={'current tax rate − previous tax rate':'Thuế suất kỳ hiện tại − thuế suất kỳ trước','source cell':'Ô nguồn gốc','current − previous':'Kỳ hiện tại − kỳ trước','consolidated adjustment − separate adjustment':'Điều chỉnh hợp nhất − điều chỉnh riêng','(current − previous) / previous × 100':'(Kỳ hiện tại − kỳ trước) / kỳ trước × 100','numerator / total net sales × 100':'Chỉ tiêu / tổng doanh thu thuần × 100','adjustment / original × 100':'Điều chỉnh / số đã công bố × 100','Services margin % − Products margin %':'Biên gộp Services − biên gộp Products','original + adjustment − restated':'Đã công bố + điều chỉnh − trình bày lại','Products + Services − total net sales':'Products + Services − tổng doanh thu thuần'}
const label=(value:string|undefined)=>value?(financialLabels[value]||value):'Chưa xác định'
const decimalDisplay=(value:string)=>{const [whole,fraction]=value.split('.');return whole.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(fraction===undefined?'':','+fraction)}

// Source content is escaped by React; HTML from PDFs is never injected.
function readableAnswer(reply:Reply){
 const text=reply.answer||'Không có nội dung trả lời.'
 if(reply.verification_status!=='HUMAN_SOURCE_VERIFIED'||!/\{['"]INSTANT['"]\s*:/.test(text))return text
 return (reply.citations||[]).map((c,i)=>{
  const value=reply.values?.[i]
  const period=c.column_label||c.period
  return value&&period?`${c.row_label||'Ô nguồn'} · ${period} là ${decimalDisplay(value)} ${label(c.unit)}. Người dùng đã đối chiếu ảnh gốc, trang ${c.page}. [${i+1}]`:''
 }).filter(Boolean).join(' ')||'Giá trị đã được đối chiếu. Mở trích dẫn để đọc ô nguồn.'
}

function AnswerText({text,citations,open}:{text:string;citations:Evidence[];open:(e:Evidence)=>void}){
 const inline=(text:string)=>text.split(/(\[\d+\]|\*\*[^*]+\*\*)/).map((s,j)=>{const n=/^\[(\d+)\]$/.exec(s);const c=n?citations[Number(n[1])-1]:null;return c?<button className="inline-citation" key={j} onClick={()=>open(c)} aria-label={c.source_kind==='SEC'?`Mở nguồn ${n![1]} filing ${c.accession}`:`Mở nguồn ${n![1]} trang ${c.page}`}>{s}</button>:s.startsWith('**')?<strong key={j}>{s.slice(2,-2)}</strong>:s})
 const cells=(line:string)=>line.trim().replace(/^\||\|$/g,'').split('|').map(s=>s.trim())
 return <div className="answer-prose">{text.split(/\n\n/).map((p,i)=>{
  const lines=p.split('\n')
  if(lines.length>2&&lines[0].includes('|')&&/^\|?[\s:|-]+$/.test(lines[1]))return <div className="scroll-table" key={i}><table><thead><tr>{cells(lines[0]).map((s,j)=><th key={j}>{inline(s)}</th>)}</tr></thead><tbody>{lines.slice(2).map((l,j)=><tr key={j}>{cells(l).map((s,k)=><td key={k}>{inline(s)}</td>)}</tr>)}</tbody></table></div>
  if(lines.every(l=>/^[-*] /.test(l)))return <ul key={i}>{lines.map((l,j)=><li key={j}>{inline(l.slice(2))}</li>)}</ul>
  if(/^#{1,3} /.test(p))return <h3 key={i}>{inline(p.replace(/^#{1,3} /,''))}</h3>
  return <p key={i}>{inline(p)}</p>
 })}</div>
}

export default function FinancialChat({focus,clearFocus,open}:{focus?:Evidence|null;clearFocus?:()=>void;open:(e:Evidence)=>void}){
 const qc=useQueryClient()
 const docs=useQuery({queryKey:['documents'],queryFn:()=>api<{documents:Doc[]}>('/documents'),refetchInterval:10000})
 const sec=useQuery({queryKey:['sec-chat-catalog'],queryFn:()=>api<{status:string;filings:{ticker:string;issuer:string;report_period:string;filing_id:string;form:string;accession:string}[]}>('/sec/catalog')})
 const [filter,setFilter]=useState(''),[offset,setOffset]=useState(0)
 const sessions=useQuery({queryKey:['chat-sessions',filter,offset],queryFn:()=>api<{sessions:Session[];has_more:boolean}>(`/chat/sessions?q=${encodeURIComponent(filter)}&offset=${offset}`)})
 const [docId,setDocId]=useState(()=>sessionStorage.getItem('active-document')||'')
 const [additionalSources,setAdditionalSources]=useState<string[]>(()=>{
  try{const saved=JSON.parse(sessionStorage.getItem('draft-chat-sources')||'null');return saved?.[0]===sessionStorage.getItem('active-document')?saved.slice(1):[]}catch{return []}
 })
 const [pickerOpen,setPickerOpen]=useState(false)
 const [session,setSession]=useState<string|undefined>(()=>sessionStorage.getItem('active-financial-chat')||undefined)
 const [turns,setTurns]=useState<Turn[]>([]),[question,setQuestion]=useState(''),[error,setError]=useState(''),[toast,setToast]=useState('')
 const [inspected,setInspected]=useState<Evidence|null>(null),[rename,setRename]=useState(false),[title,setTitle]=useState('')
 const [advanced,setAdvanced]=useState(false),[scope,setScope]=useState(''),[showEvidence,setShowEvidence]=useState(false),[historyOpen,setHistoryOpen]=useState(false)
 useEffect(()=>{if(!historyOpen)return;const close=(e:KeyboardEvent)=>{if(e.key==='Escape')setHistoryOpen(false)};window.addEventListener('keydown',close);return()=>window.removeEventListener('keydown',close)},[historyOpen])
 const [explicit,setExplicit]=useState<Evidence|null>(focus||null)
 const inspect=(e:Evidence)=>{setInspected(e);setShowEvidence(true);if(session)sessionStorage.setItem('chat-citation-focus',JSON.stringify([session,evidenceId(e)]))}
 function askEvidence(e:Evidence){if(!e.document_id)return;setExplicit(e);setShowEvidence(false);setQuestion('Giải thích đoạn nguồn này.');composer.current?.focus()}
 const closeEvidence=useCallback(()=>setShowEvidence(false),[])
 const composer=useRef<HTMLTextAreaElement>(null),following=useRef(true)
 const [showLatest,setShowLatest]=useState(false)
 useEffect(()=>{const el=composer.current;if(el){el.style.height='auto';el.style.height=Math.min(140,Math.max(38,el.scrollHeight))+'px'}},[question])
 const bottom=useRef<HTMLDivElement>(null),abort=useRef<AbortController|null>(null),epoch=useRef(0)
 const chosen=docId||docs.data?.documents.find(d=>d.status==='READY')?.id||''
 const isSec=chosen.startsWith('SEC:')
 const sourceIds=[...new Set([chosen,...additionalSources].filter(id=>id&&id.startsWith('SEC:')===isSec))]
 const sourceKey=sourceIds.slice().sort().join('|')
 const scopeRef=useRef(sourceKey)
 useEffect(()=>{scopeRef.current=sourceKey},[sourceKey])
 useEffect(()=>{if(chosen){sessionStorage.setItem('active-document',chosen);sessionStorage.setItem('draft-chat-sources',JSON.stringify([chosen,...additionalSources]))}},[chosen,additionalSources])
 const sourceOptions=[
  ...(docs.data?.documents.filter(d=>d.status==='READY').map(d=>({id:d.id,label:`${d.issuer||'PDF'} · ${d.report_period||'Kỳ chưa xác định'} · ${d.filename}`}))||[]),
  ...(sec.data?.filings?.map(f=>({id:'SEC:'+f.filing_id,label:`SEC · ${f.ticker} · ${f.form} · ${f.report_period} · ${f.accession}`}))||[]),
 ]
 const sourceName=(id:string)=>sourceOptions.find(item=>item.id===id)?.label||id
 useEffect(()=>{const saved=sessionStorage.getItem('chat-return-scroll');if(saved&&turns.length){requestAnimationFrame(()=>{const node=document.querySelector('.chat-messages');if(node)node.scrollTop=Number(saved)});sessionStorage.removeItem('chat-return-scroll')}else{const box=document.querySelector('.chat-messages'),last=box?.querySelector<HTMLElement>('.chat-exchange:last-of-type .message-assistant');if(box&&last&&following.current)box.scrollTop+=last.getBoundingClientRect().top-box.getBoundingClientRect().top-16}},[turns.length])
 useEffect(()=>{if(focus?.document_id){setDocId(focus.document_id);setExplicit(focus);setQuestion('Giải thích đoạn nguồn này.')}},[focus])
 useEffect(()=>{if(!session)return;let active=true;api<Session>(`/chat/${session}`).then(s=>{if(active&&s.turns){setTurns(s.turns);if(s.document_ids?.length){setDocId(s.document_ids[0]);setAdditionalSources(s.document_ids.slice(1))}setTitle(s.title);const citations=s.turns.flatMap(t=>t.response.citations||[]);let saved:string[]=[]
 try{saved=JSON.parse(sessionStorage.getItem('chat-citation-focus')||'[]')}catch{}
 setInspected((saved[0]===s.id?citations.find(c=>evidenceId(c)===saved[1]):undefined)||s.turns.at(-1)?.response.citations?.[0]||null)}}).catch(e=>{if(active)setError(reasonText(e.message))});return()=>{active=false}},[session])
 function resetFocus(){setExplicit(null);clearFocus?.();setInspected(null);setShowEvidence(false)}
 function newChat(){resetFocus();epoch.current++;abort.current?.abort();setSession(undefined);sessionStorage.removeItem('active-financial-chat');setTurns([]);setInspected(null);setError('');setQuestion('');setTitle('Hội thoại mới')}
 function selectSession(s:Session){resetFocus();setTurns([]);setQuestion('');setDocId(s.document_ids[0]||'');setAdditionalSources(s.document_ids.slice(1));epoch.current++;abort.current?.abort();setSession(s.id);sessionStorage.setItem('active-financial-chat',s.id);setError('')}
 function toggleSource(id:string){
  if(sourceIds.includes(id)){
   const remaining=sourceIds.filter(item=>item!==id)
   if(!remaining.length)return
   newChat();setDocId(remaining[0]);setAdditionalSources(remaining.slice(1))
  }else if(sourceIds.length<20){
   newChat();setAdditionalSources([...additionalSources,id])
  }
 }
 const [progressId,setProgressId]=useState('')
 const run=useMutation({networkMode:'always',mutationFn:async(asked:string)=>{
  const id=crypto.randomUUID().replace(/-/g,'')
  setProgressId(id)
  const requestEpoch=epoch.current
  abort.current=new AbortController()
  const secIds=sourceIds.filter(id=>id.startsWith('SEC:sec:')).map(id=>id.slice(4))
  const source=isSec?{source:'US_SEC',...(secIds.length?{filing_ids:secIds}:{ticker:chosen.slice(4)})}:{}
  const answer=await post<Reply>('/chat',{question:asked,document_ids:isSec?[]:sourceIds,...source,session_id:session,
   ...(!isSec&&explicit?.document_id&&sourceIds.includes(explicit.document_id)?{evidence_context:{intent:'USER_SOURCE_FOCUS',document_id:explicit.document_id,page:explicit.page,row_id:explicit.row_id,column_id:explicit.column_id,chunk_id:explicit.chunk_id,citation_id:explicit.citation_id}}:{}),
   progress_id:id, constraints:advanced&&scope&&!isSec?{statement_scope:scope}:{}},{signal:abort.current.signal})
  return {answer,asked,requestScope:sourceKey,requestEpoch}
 },onSuccess:({answer,asked,requestScope,requestEpoch})=>{
  if(scopeRef.current!==requestScope||requestEpoch!==epoch.current)return
  setExplicit(null);clearFocus?.();sessionStorage.removeItem('chat-citation-focus');setSession(answer.session_id);sessionStorage.setItem('active-financial-chat',answer.session_id);setTurns(t=>[...(answer.conversation_reset?[]:t),{question:asked,response:answer,created_at:new Date().toISOString()}]);setQuestion('');setTitle(t=>!t||t==='Hội thoại mới'?asked.slice(0,100):t);setInspected(answer.citations?.[0]||null);setError('');qc.invalidateQueries({queryKey:['chat-sessions']})
 },onError:e=>setError(e.name==='AbortError'?'Đã dừng chờ. Máy chủ có thể vẫn hoàn tất và lưu câu trả lời.':reasonText(e.message))})
 async function copy(text:string){try{await navigator.clipboard.writeText(text);setToast('Đã sao chép')}catch{setToast('Không thể truy cập clipboard')}}
 async function remove(){if(!session||!window.confirm('Xóa vĩnh viễn hội thoại này?'))return;try{await api(`/chat/${session}`,{method:'DELETE'});newChat();qc.invalidateQueries({queryKey:['chat-sessions']})}catch(e){setError(String(e))}}
 const busy=run.isPending
 const progress=useQuery({queryKey:['chat-progress',progressId],enabled:busy&&!!progressId,refetchInterval:350,
  queryFn:()=>api<{stage?:string;pages_read?:number;pages_total?:number;tasks_done?:number;tasks_total?:number;needs_review?:number}>(`/chat/progress/${progressId}`),retry:false})
 const work=progress.data
 const progressLabel=work?.stage==='reading'?`Đã đọc ${work.pages_read}/${work.pages_total} trang`:work?.stage==='checking'?
  `Đã xử lý ${work.tasks_done}/${work.tasks_total} mục${work.needs_review?' · '+work.needs_review+' mục cần xác minh':''}`:work?.stage==='composing'?'Đang tổng hợp kết quả':work?.stage==='planning'?'Đang phân tích yêu cầu nhiều bước':''

 return <section className={'chat-workspace '+(historyOpen?'history-visible':'history-collapsed')} aria-label="Trợ lý tài chính">
  <aside className="chat-history"><div className="chat-history-heading"><MessageSquare size={20}/><strong>Hội thoại</strong><button aria-label="Đóng lịch sử hội thoại" onClick={()=>setHistoryOpen(false)}>×</button></div><Button onClick={()=>{setHistoryOpen(false);newChat()}} variant="outline"><Plus size={16}/> Hội thoại mới</Button><label className="chat-filter"><Search size={15}/><input aria-label="Tìm hội thoại" placeholder="Tìm trong lịch sử…" value={filter} onChange={e=>{setFilter(e.target.value);setOffset(0)}}/></label>
   <div className="session-list">{sessions.data?.sessions?.map(s=><button key={s.id} className={'session-item '+(s.id===session?'active':'')} onClick={()=>{setHistoryOpen(false);selectSession(s)}}><strong>{s.title}</strong><small>{new Date(s.updated_at).toLocaleString('vi-VN')} · {s.message_count} tin nhắn</small><small>{docs.data?.documents.find(d=>d.id===s.document_ids[0])?.filename||'Nguồn đã lưu'}</small></button>)}</div>{!sessions.data?.sessions?.length&&<p className="muted">Hội thoại được lưu tự động trên máy chủ.</p>}<div className="row"><button disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-20))}>Trước</button><button disabled={!sessions.data?.has_more} onClick={()=>setOffset(offset+20)}>Tiếp</button></div>{sessions.error&&<p role="alert">Không tải được lịch sử. {sessions.error.message}</p>}
  </aside>
  <div className="chat-center"><header className="chat-header"><button className="history-toggle" aria-label="Hội thoại đã lưu" aria-expanded={historyOpen} onClick={()=>setHistoryOpen(!historyOpen)}><MessageSquare size={18}/></button><div><small>FINANCIAL INTELLIGENCE STUDIO</small><h2 title={title||'Trợ lý tài chính'}>{title||'Trợ lý tài chính'}</h2></div><div className="row"><button aria-label="Bắt đầu hội thoại mới" onClick={newChat}><Plus size={18}/></button><button aria-label="Mở nguồn đã chọn" onClick={()=>{if(inspected)setShowEvidence(true)}} disabled={!inspected}><BookOpen size={18}/></button>{session&&<><button aria-label="Đổi tên hội thoại" onClick={()=>{setHistoryOpen(false);setRename(!rename)}}><Pencil size={16}/></button><button aria-label="Xóa hội thoại" onClick={remove}><Trash2 size={16}/></button></>}</div></header>
   {rename&&<form className="row" onSubmit={async e=>{e.preventDefault();try{await api(`/chat/${session}`,{method:'PATCH',body:JSON.stringify({title})});setRename(false);qc.invalidateQueries({queryKey:['chat-sessions']})}catch(e){setError(String(e))}}}><input aria-label="Tên hội thoại" value={title} onChange={e=>setTitle(e.target.value)} maxLength={120} required/><Button>Lưu tên</Button></form>}
   <div className="chat-source-bar">
    <label className="chat-source-select">Nguồn chính<select aria-label="Tài liệu trợ lý" value={chosen} onChange={e=>{newChat();setDocId(e.target.value);setAdditionalSources([])}}>
     <option value="">Chọn tài liệu READY</option>{sourceOptions.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}
    </select></label>
    {chosen&&<details className="chat-source-picker" onToggle={event=>setPickerOpen(event.currentTarget.open)}><summary>Nguồn ({sourceIds.length})</summary>
     {pickerOpen&&<div className="chat-source-options"><p>Chọn tối đa 20 {isSec?'filing SEC':'tệp PDF'}. Thay đổi bộ nguồn mở hội thoại mới.</p>
      {sourceOptions.filter(item=>item.id.startsWith('SEC:')===isSec).map(item=><label key={item.id}>
       <input type="checkbox" checked={sourceIds.includes(item.id)} disabled={sourceIds.length===1&&sourceIds.includes(item.id)||sourceIds.length===20&&!sourceIds.includes(item.id)} onChange={()=>toggleSource(item.id)}/>
       <span>{item.label}</span>
      </label>)}
     </div>}
    </details>}
   </div>
   {sourceIds.length>1&&<ul className="chat-selected-sources" aria-label="Nguồn đang sử dụng">{sourceIds.map(id=><li key={id} title={sourceName(id)}>{sourceName(id)}</li>)}</ul>}

   {explicit?.document_id&&sourceIds.includes(explicit.document_id)&&<div className="handoff-source">Nguồn bạn chọn cho câu hỏi tiếp theo · trang {explicit.page} <button onClick={()=>{setExplicit(null);clearFocus?.()}}>Bỏ giới hạn nguồn</button></div>}
   {inspected&&<div className="handoff-source"><button onClick={()=>setShowEvidence(true)}>Bằng chứng câu trả lời · {inspected.page?'trang '+inspected.page:'filing SEC'}</button></div>}
   {sec.data?.status==='UNAVAILABLE'&&<details className="sec-availability"><summary>SEC chưa khả dụng · PDF vẫn hoạt động</summary><p>Cần snapshot SEC và chỉ mục tương thích được cấu hình trên máy chủ. Không tải hay thay thế dữ liệu nghiên cứu tự động.</p></details>}
   <div className="chat-messages" onScroll={e=>{const el=e.currentTarget;following.current=el.scrollHeight-el.scrollTop-el.clientHeight<100;setShowLatest(!following.current)}} role="log" aria-label="Hội thoại tài chính" aria-live="polite">
    {!turns.length&&<div className="chat-welcome"><div className="welcome-icon"><Sparkles size={30}/></div><h2>Hiểu tài liệu. Đối chiếu từng nguồn.</h2><p>Hỏi về báo cáo tài chính của bạn. Mỗi trích dẫn đưa bạn đến trang nguồn để kiểm tra.</p><div className="chat-suggestions">{suggestions.map(s=><button key={s} onClick={()=>setQuestion(s)}>{s}<Send size={14}/></button>)}</div></div>}
    {turns.map((turn,i)=><article className="chat-exchange" key={i}><div className="message-user"><small>Bạn</small><p>{turn.question}</p></div><div className="message-assistant"><div className="assistant-label"><Sparkles size={17}/><strong>Trợ lý tài chính</strong><small>{turn.created_at?new Date(turn.created_at).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'}):''}</small></div><span className={'answer-status '+(turn.response.status==='SUPPORTED'?'verified':'')}>{turn.response.answer_status==='PARTIAL_VERIFIED'?'Đã xác minh một phần':turn.response.status==='SUPPORTED'?(turn.response.semantic_question_coverage?.status==='COMPLETE'?'Đã đối chiếu nguồn và câu hỏi':'Đã đối chiếu ô nguồn · xem phạm vi trả lời'):turn.response.answer_status==='OCR_CANDIDATE_ANSWER'?'Số OCR ứng viên · chưa xác minh':turn.response.citations?.length?'Có nguồn để đối chiếu':'Cần làm rõ phạm vi hoặc bằng chứng'}</span>
     <AnswerText text={readableAnswer(turn.response)} citations={turn.response.citations||[]} open={inspect}/>{turn.response.answer_explanation&&<p className="answer-explanation">{turn.response.answer_explanation}</p>}{!!turn.response.calculation_steps?.some(s=>s.operation!=='EXTRACT')&&turn.response.independent_verification?.status==='VERIFIED'&&<details className="calculation-details"><summary>Các bước tính · Đã kiểm chứng độc lập</summary>{turn.response.calculation_steps.filter(s=>s.operation!=='EXTRACT').map(step=><div key={step.calculation_id}><strong>{formulaLabels[step.title]||step.title}</strong><ul>{step.substitution.map((v,i)=><li key={i}>{decimalDisplay(v.value.replace(/,/g,'').replace(/%$/,''))} {label(v.unit)} · {v.period} · {label(v.scope)} · {label(v.basis)} <AnswerText text={v.citation} citations={turn.response.citations||[]} open={inspect}/></li>)}</ul><p>Kết quả: {decimalDisplay(step.result)} {label(step.unit)}</p><small>Tỷ lệ làm tròn đến hai chữ số; số tiền giữ độ chính xác của nguồn.</small></div>)}</details>}<div className="sources">{turn.response.citations?.map((c,j)=><button key={j} className="source-button" onClick={()=>inspect(c)}>[{j+1}] {c.statement_scope==='SEPARATE'?'Riêng':c.statement_scope==='CONSOLIDATED'?'Hợp nhất':c.row_label||'Nguồn'} · trang {c.page||'SEC'}</button>)}</div>
     <div className="message-actions"><button onClick={()=>copy(readableAnswer(turn.response)+'\n'+(turn.response.citations||[]).map((c,j)=>`[${j+1}] ${c.filename} · trang ${c.page} · SHA ${c.source_sha256}`).join('\n'))}><Copy size={13}/> Sao chép</button><button disabled={busy} onClick={()=>{setQuestion(turn.question);run.mutate(turn.question)}}>Hỏi lại</button><details><summary>Cách hiểu câu hỏi & kỹ thuật</summary><p>{turn.response.verification_status} · {turn.response.search_profile}</p>{turn.response.reason&&<p>{reasonText(turn.response.reason)}</p>}<p>{turn.response.resolved_question}</p>{!!turn.response.query_plan?.inherited_slots?.length&&<p>Ngữ cảnh được kế thừa: {turn.response.query_plan.inherited_slots.map(s=>({metric:'chỉ tiêu',years:'kỳ',scope:'phạm vi',operation:'phép tính'} as Record<string,string>)[s]||s).join(', ')}.</p>}{turn.response.semantic_question_coverage&&<p>Đã giải quyết {turn.response.semantic_question_coverage.answered_count}/{turn.response.semantic_question_coverage.requested_count} phần của câu hỏi.</p>}<pre>{JSON.stringify(turn.response.retrieval_trace,null,2)}</pre></details></div></div></article>)}
    {busy&&<div className="chat-loading" role="status"><span className="pulse-dot"/> Đang truy xuất nguồn và kiểm tra bằng chứng…<small>Trả lời khi xử lý xong; không phát trực tiếp từng token.</small></div>}<div ref={bottom}/>
   </div>
   {showLatest&&<button className="latest-message" onClick={()=>{following.current=true;bottom.current?.scrollIntoView({block:'end'});setShowLatest(false)}}>Về tin nhắn mới nhất ↓</button>}
   <form className="chat-composer" onSubmit={e=>{e.preventDefault();if(!busy&&question.trim().length>1)run.mutate(question)}}><textarea ref={composer} rows={1} aria-label="Câu hỏi trợ lý" value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();if(!busy&&chosen&&question.trim().length>1)run.mutate(question)}}} placeholder="Hỏi về tài liệu đang chọn…" maxLength={2000} required/><div className="composer-toolbar"><small>{busy&&progressLabel?<span role="status">{progressLabel}</span>:"Enter gửi · Shift + Enter xuống dòng"}</small><div className="row">{busy&&<Button type="button" variant="outline" onClick={()=>abort.current?.abort()}>Dừng chờ</Button>}<Button disabled={!chosen||busy||question.trim().length<2} type="submit"><Send size={15}/> Gửi câu hỏi</Button></div></div><details><summary>Tùy chọn nâng cao</summary><label><input type="checkbox" checked={advanced} onChange={e=>setAdvanced(e.target.checked)}/> Áp dụng phạm vi thủ công</label>{advanced&&<select aria-label="Phạm vi trợ lý" value={scope} onChange={e=>setScope(e.target.value)}><option value="">Tự động theo nguồn</option><option value="SEPARATE">Riêng / công ty mẹ</option><option value="CONSOLIDATED">Hợp nhất</option></select>}</details>{error&&<div className="error" role="alert">{error}<button type="button" disabled={busy} onClick={()=>run.mutate(question)}>Thử lại</button></div>}{toast&&<button type="button" className="copy-toast" role="status" onClick={()=>setToast('')}>{toast}</button>}</form>
  </div>
  <EvidencePanel evidence={showEvidence?inspected:null} close={closeEvidence} open={open} ask={askEvidence}/>
 </section>
}
