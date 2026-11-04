import {useEffect,useState,useRef} from 'react'
import {useQuery,useMutation,useQueryClient} from '@tanstack/react-query'
import {Plus,MessageSquare,Send,Copy,BookOpen,Pencil,Trash2,Search,FileText,Sparkles} from 'lucide-react'
import {api,post} from './api'
import type {Answer,Doc,Evidence} from './api'
import {Button} from '@/components/ui/button'
import {reasonText} from './error-text'

type Reply=Answer&{session_id:string;resolved_question?:string;conversation_reset?:boolean;retrieval_trace?:Record<string,unknown>}
type Turn={question:string;response:Reply;created_at?:string}
type Session={id:string;title:string;updated_at:string;document_ids:string[];turns?:Turn[];message_count:number}
const suggestions=['Tìm dòng "Lợi nhuận sau thuế chưa phân phối" trong tài liệu đang chọn. Cho biết các đoạn nguồn liên quan và trang PDF.','Tóm tắt tài liệu đang chọn và dẫn nguồn.','Những số liệu nào được điều chỉnh trong tài liệu?']

// Source content is escaped by React; HTML from PDFs is never injected.
function AnswerText({text,citations,open}:{text:string;citations:Evidence[];open:(e:Evidence)=>void}){
 const inline=(text:string)=>text.split(/(\[\d+\]|\*\*[^*]+\*\*)/).map((s,j)=>{const n=/^\[(\d+)\]$/.exec(s);const c=n?citations[Number(n[1])-1]:null;return c?<button className="inline-citation" key={j} onClick={()=>open(c)} aria-label={`Mở nguồn ${n![1]} trang ${c.page}`}>{s}</button>:s.startsWith('**')?<strong key={j}>{s.slice(2,-2)}</strong>:s})
 const cells=(line:string)=>line.trim().replace(/^\||\|$/g,'').split('|').map(s=>s.trim())
 return <div className="answer-prose">{text.split(/\n\n/).map((p,i)=>{
  const lines=p.split('\n')
  if(lines.length>2&&lines[0].includes('|')&&/^\|?[\s:|-]+$/.test(lines[1]))return <div className="scroll-table" key={i}><table><thead><tr>{cells(lines[0]).map((s,j)=><th key={j}>{inline(s)}</th>)}</tr></thead><tbody>{lines.slice(2).map((l,j)=><tr key={j}>{cells(l).map((s,k)=><td key={k}>{inline(s)}</td>)}</tr>)}</tbody></table></div>
  if(lines.every(l=>/^[-*] /.test(l)))return <ul key={i}>{lines.map((l,j)=><li key={j}>{inline(l.slice(2))}</li>)}</ul>
  if(/^#{1,3} /.test(p))return <h3 key={i}>{inline(p.replace(/^#{1,3} /,''))}</h3>
  return <p key={i}>{inline(p)}</p>
 })}</div>
}

export default function FinancialChat({selected,open}:{selected:Evidence|null;open:(e:Evidence)=>void}){
 const qc=useQueryClient()
 const docs=useQuery({queryKey:['documents'],queryFn:()=>api<{documents:Doc[]}>('/documents'),refetchInterval:10000})
 const sec=useQuery({queryKey:['sec-chat-catalog'],queryFn:()=>api<{status:string;filings:{ticker:string;issuer:string;report_period:string}[]}>('/sec/catalog')})
 const [filter,setFilter]=useState(''),[offset,setOffset]=useState(0)
 const sessions=useQuery({queryKey:['chat-sessions',filter,offset],queryFn:()=>api<{sessions:Session[];has_more:boolean}>(`/chat/sessions?q=${encodeURIComponent(filter)}&offset=${offset}`)})
 const [docId,setDocId]=useState(()=>sessionStorage.getItem('active-document')||'')
 const [session,setSession]=useState<string|undefined>(()=>sessionStorage.getItem('active-financial-chat')||undefined)
 const [turns,setTurns]=useState<Turn[]>([]),[question,setQuestion]=useState(''),[error,setError]=useState(''),[toast,setToast]=useState('')
 const [inspected,setInspected]=useState<Evidence|null>(selected),[rename,setRename]=useState(false),[title,setTitle]=useState('')
 const [advanced,setAdvanced]=useState(false),[scope,setScope]=useState(''),[showEvidence,setShowEvidence]=useState(false)
 const bottom=useRef<HTMLDivElement>(null),abort=useRef<AbortController|null>(null),epoch=useRef(0)
 const chosen=docId||docs.data?.documents.find(d=>d.status==='READY')?.id||''
 const scopeRef=useRef(chosen)
 useEffect(()=>{scopeRef.current=chosen},[chosen])
 const doc=docs.data?.documents.find(d=>d.id===chosen)
 useEffect(()=>{if(chosen)sessionStorage.setItem('active-document',chosen)},[chosen])
 useEffect(()=>{bottom.current?.scrollIntoView?.({behavior:'smooth',block:'nearest'})},[turns.length])
 useEffect(()=>{if(selected?.document_id){setDocId(selected.document_id);setInspected(selected)}},[selected])
 useEffect(()=>{if(!session)return;let active=true;api<Session>(`/chat/${session}`).then(s=>{if(active&&s.turns){setTurns(s.turns);if(s.document_ids?.length)setDocId(s.document_ids[0]);setTitle(s.title)}}).catch(e=>{if(active)setError(reasonText(e.message))});return()=>{active=false}},[session])
 function newChat(){epoch.current++;abort.current?.abort();setSession(undefined);sessionStorage.removeItem('active-financial-chat');setTurns([]);setInspected(null);setError('');setQuestion('');setTitle('Hội thoại mới')}
 function selectSession(s:Session){epoch.current++;abort.current?.abort();setSession(s.id);sessionStorage.setItem('active-financial-chat',s.id);setError('')}
 const run=useMutation({mutationFn:async(asked:string)=>{const requestEpoch=epoch.current;abort.current=new AbortController();const answer=await post<Reply>('/chat',{question:asked,document_ids:chosen.startsWith('SEC:')?[]:[chosen],...(chosen.startsWith('SEC:')?{source:'US_SEC',ticker:chosen.slice(4)}:{}),session_id:session,constraints:advanced&&scope&&!chosen.startsWith('SEC:')?{statement_scope:scope}:{}},{signal:abort.current.signal});return {answer,asked,documentId:chosen,requestEpoch}},onSuccess:({answer,asked,documentId,requestEpoch})=>{
  if(scopeRef.current!==documentId||requestEpoch!==epoch.current)return;setSession(answer.session_id);sessionStorage.setItem('active-financial-chat',answer.session_id);setTurns(t=>[...(answer.conversation_reset?[]:t),{question:asked,response:answer,created_at:new Date().toISOString()}]);setQuestion('');setInspected(answer.citations?.[0]||null);setError('');qc.invalidateQueries({queryKey:['chat-sessions']})
 },onError:e=>setError(e.name==='AbortError'?'Đã dừng chờ. Máy chủ có thể vẫn hoàn tất và lưu câu trả lời.':reasonText(e.message))})
 async function copy(text:string){try{await navigator.clipboard.writeText(text);setToast('Đã sao chép')}catch{setToast('Không thể truy cập clipboard')}}
 async function remove(){if(!session||!window.confirm('Xóa vĩnh viễn hội thoại này?'))return;try{await api(`/chat/${session}`,{method:'DELETE'});newChat();qc.invalidateQueries({queryKey:['chat-sessions']})}catch(e){setError(String(e))}}
 const busy=run.isPending
 return <section className="chat-workspace" aria-label="Trợ lý tài chính">
  <aside className="chat-history"><div className="chat-history-heading"><MessageSquare size={20}/><strong>Hội thoại</strong></div><Button onClick={newChat} variant="outline"><Plus size={16}/> Hội thoại mới</Button><label className="chat-filter"><Search size={15}/><input aria-label="Tìm hội thoại" placeholder="Tìm trong lịch sử…" value={filter} onChange={e=>{setFilter(e.target.value);setOffset(0)}}/></label>
   <div className="session-list">{sessions.data?.sessions?.map(s=><button key={s.id} className={'session-item '+(s.id===session?'active':'')} onClick={()=>selectSession(s)}><strong>{s.title}</strong><small>{new Date(s.updated_at).toLocaleString('vi-VN')} · {s.message_count} tin nhắn</small><small>{docs.data?.documents.find(d=>d.id===s.document_ids[0])?.filename||'Nguồn đã lưu'}</small></button>)}</div>{!sessions.data?.sessions?.length&&<p className="muted">Hội thoại được lưu tự động trên máy chủ.</p>}<div className="row"><button disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-20))}>Trước</button><button disabled={!sessions.data?.has_more} onClick={()=>setOffset(offset+20)}>Tiếp</button></div>{sessions.error&&<p role="alert">Không tải được lịch sử. {sessions.error.message}</p>}
  </aside>
  <div className="chat-center"><header className="chat-header"><div><small>FINANCIAL INTELLIGENCE STUDIO</small><h2>{title||'Trợ lý tài chính'}</h2></div><div className="row">{session&&<><button aria-label="Đổi tên hội thoại" onClick={()=>setRename(!rename)}><Pencil size={16}/></button><button aria-label="Xóa hội thoại" onClick={remove}><Trash2 size={16}/></button></>}</div></header>
   {rename&&<form className="row" onSubmit={async e=>{e.preventDefault();try{await api(`/chat/${session}`,{method:'PATCH',body:JSON.stringify({title})});setRename(false);qc.invalidateQueries({queryKey:['chat-sessions']})}catch(e){setError(String(e))}}}><input aria-label="Tên hội thoại" value={title} onChange={e=>setTitle(e.target.value)} maxLength={120} required/><Button>Lưu tên</Button></form>}
   <label className="chat-source-select">Nguồn đang sử dụng<select aria-label="Tài liệu trợ lý" value={chosen} onChange={e=>{newChat();setDocId(e.target.value)}}><option value="">Chọn một tài liệu READY</option>{docs.data?.documents.filter(d=>d.status==='READY').map(d=><option key={d.id} value={d.id}>{d.filename} · {d.issuer||'Chưa rõ doanh nghiệp'} · {d.report_period||'Chưa rõ kỳ'}</option>)}{[...new Set(sec.data?.filings?.map(f=>f.ticker)||[])].map(t=><option key={t} value={'SEC:'+t}>SEC · {t} · snapshot HTML/iXBRL</option>)}</select></label>
   <div className="source-chip"><FileText size={14}/><span title={doc?.filename}>{chosen.startsWith('SEC:')?'SEC '+chosen.slice(4)+' · HTML/iXBRL':doc?`${doc.issuer||'PDF'} · ${doc.report_period||'Kỳ chưa xác định'}`:'Chọn PDF trong kho tài liệu'}</span><small>{chosen.startsWith('SEC:')?'SEC':`${doc?.pages||0} trang · PDF ${doc?.status||''}`}</small></div>
   {selected?.document_id===chosen&&<details className="handoff-source"><summary>Đoạn đang xem · trang {selected.page}</summary><span>Nguồn đang xem: trang {selected.page} · {selected.text.slice(0,90)}</span><button onClick={()=>setQuestion(`Giải thích đoạn nguồn trên trang ${selected.page}: ${selected.text.slice(0,650)}`)}>Hỏi về đoạn này</button></details>}
   {sec.data?.status==='UNAVAILABLE'&&<details className="sec-availability"><summary>SEC chưa khả dụng · PDF vẫn hoạt động</summary><p>Cần snapshot SEC và chỉ mục tương thích được cấu hình trên máy chủ. Không tải hay thay thế dữ liệu nghiên cứu tự động.</p></details>}
   <div className="chat-messages" role="log" aria-label="Hội thoại tài chính" aria-live="polite">
    {!turns.length&&<div className="chat-welcome"><div className="welcome-icon"><Sparkles size={30}/></div><h2>Hiểu tài liệu. Đối chiếu từng nguồn.</h2><p>Hỏi về báo cáo tài chính của bạn. Mỗi trích dẫn đưa bạn đến trang nguồn để kiểm tra.</p><div className="chat-suggestions">{suggestions.map(s=><button key={s} onClick={()=>setQuestion(s)}>{s}<Send size={14}/></button>)}</div></div>}
    {turns.map((turn,i)=><article className="chat-exchange" key={i}><div className="message-user"><small>Bạn</small><p>{turn.question}</p></div><div className="message-assistant"><div className="assistant-label"><Sparkles size={17}/><strong>Financial Assistant</strong><small>{turn.created_at?new Date(turn.created_at).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'}):''}</small></div><span className={'answer-status '+(turn.response.status==='SUPPORTED'?'verified':'')}>{turn.response.status==='SUPPORTED'?'Đã xác minh ô nguồn':turn.response.citations?.length?'Có trích dẫn · kiểm tra nguồn':'Cần làm rõ phạm vi hoặc bằng chứng'}</span>
     <AnswerText text={turn.response.answer||'Không có nội dung trả lời.'} citations={turn.response.citations||[]} open={open}/><div className="sources">{turn.response.citations?.map((c,j)=><button key={j} className="source-button" onMouseEnter={()=>setInspected(c)} onFocus={()=>setInspected(c)} onClick={()=>open(c)}>[{j+1}] {c.statement_scope==='SEPARATE'?'Riêng':c.statement_scope==='CONSOLIDATED'?'Hợp nhất':c.row_label||'Nguồn'} · trang {c.page||'SEC'}</button>)}</div>
     <div className="message-actions"><button onClick={()=>copy((turn.response.answer||'')+'\n'+(turn.response.citations||[]).map((c,j)=>`[${j+1}] ${c.filename} · trang ${c.page} · SHA ${c.source_sha256}`).join('\n'))}><Copy size={13}/> Sao chép</button><button disabled={busy} onClick={()=>{setQuestion(turn.question);run.mutate(turn.question)}}>Hỏi lại</button><details><summary>Phạm vi & kỹ thuật</summary><p>{turn.response.verification_status} · {turn.response.search_profile}</p>{turn.response.reason&&<p>{reasonText(turn.response.reason)}</p>}<p>{turn.response.resolved_question}</p><pre>{JSON.stringify(turn.response.retrieval_trace,null,2)}</pre></details></div></div></article>)}
    {busy&&<div className="chat-loading" role="status"><span className="pulse-dot"/> Đang truy xuất nguồn và kiểm tra bằng chứng…<small>Trả lời khi xử lý xong; không phát trực tiếp từng token.</small></div>}<div ref={bottom}/>
   </div>
   <button className="evidence-mobile-toggle" onClick={()=>setShowEvidence(true)}>Nguồn & bằng chứng</button>
   <form className="chat-composer" onSubmit={e=>{e.preventDefault();if(!busy&&question.trim().length>1)run.mutate(question)}}><textarea aria-label="Câu hỏi trợ lý" value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();if(!busy&&chosen&&question.trim().length>1)run.mutate(question)}}} placeholder="Hỏi về tài liệu đang chọn…" maxLength={2000} required/><div className="composer-toolbar"><small>Enter gửi · Shift + Enter xuống dòng</small><div className="row">{busy&&<Button type="button" variant="outline" onClick={()=>abort.current?.abort()}>Dừng chờ</Button>}<Button disabled={!chosen||busy||question.trim().length<2} type="submit"><Send size={15}/> Gửi câu hỏi</Button></div></div><details><summary>Tùy chọn nâng cao</summary><label><input type="checkbox" checked={advanced} onChange={e=>setAdvanced(e.target.checked)}/> Áp dụng phạm vi thủ công</label>{advanced&&<select aria-label="Phạm vi trợ lý" value={scope} onChange={e=>setScope(e.target.value)}><option value="">Tự động theo nguồn</option><option value="SEPARATE">Riêng / công ty mẹ</option><option value="CONSOLIDATED">Hợp nhất</option></select>}</details>{error&&<div className="error" role="alert">{error}<button type="button" disabled={busy} onClick={()=>run.mutate(question)}>Thử lại</button></div>}{toast&&<button type="button" className="copy-toast" role="status" onClick={()=>setToast('')}>{toast}</button>}</form>
  </div>
  <aside className={'chat-evidence '+(showEvidence?'drawer-open':'')} aria-label="Nguồn và bằng chứng"><button className="evidence-mobile-toggle" onClick={()=>setShowEvidence(false)}>Đóng bằng chứng</button><div className="chat-history-heading"><BookOpen size={19}/><strong>Nguồn & bằng chứng</strong></div>{inspected?<><span className="answer-status">PDF · trang {inspected.page}</span><h3>{inspected.row_label||'Trích đoạn tài liệu'}</h3><blockquote>{inspected.text}</blockquote><dl><dt>Phạm vi</dt><dd>{inspected.statement_scope||'Chưa xác định'}</dd><dt>Kỳ / đơn vị</dt><dd>{inspected.report_period||'Chưa xác định'} · {inspected.unit||'Chưa xác minh'}</dd><dt>Trích xuất</dt><dd>{inspected.extraction_method||'Xem nguồn'}</dd><dt>Xác minh số</dt><dd>{inspected.verification||'Chưa chứng nhận ô số'}</dd></dl><Button onClick={()=>open(inspected)}><BookOpen size={15}/> Mở trang {inspected.page}</Button><small className="source-hash">SHA256 {inspected.source_sha256}</small></>:<div className="evidence-empty"><BookOpen size={32}/><p>Các nguồn xuất hiện ở đây sau câu trả lời.</p><small>Chọn citation để mở PDF và vùng chữ nguồn.</small></div>}</aside>
 </section>
}
