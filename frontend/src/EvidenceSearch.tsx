import {useEffect,useRef,useState} from 'react'
import {useMutation,useQuery} from '@tanstack/react-query'
import {Search,SlidersHorizontal,ArrowUpRight,MessageSquare,FileText} from 'lucide-react'
import {api,post,evidenceId} from './api'
import type {Doc,Evidence,SearchParams,SearchResult} from './api'
import EvidencePanel,{sourceLabel} from './EvidencePanel'
import {reasonText} from './error-text'
type Props={params:SearchParams;setParams:(p:SearchParams)=>void;result:SearchResult|null;setResult:(r:SearchResult|null)=>void;open:(e:Evidence)=>void;selected:Evidence|null;select:(e:Evidence|null)=>void;askSource?:(e:Evidence)=>void}
type SecFiling={filing_id:string;ticker:string;report_period:string;form:string;accession:string;ownership?:string;dense_ready?:boolean}
const methods=[['bm25','BM25'],['dense','Dense'],['hybrid','Hybrid RRF'],['faith','FAITH-R']] as const
const methodName=(p:SearchParams)=>p.search_profile==='baseline'?p.mode:'faith'
function RetrievalDetails({item}:{item:Evidence}){
 const [expanded,setExpanded]=useState(false)
 const direct=item.retrieval_origin==='PDF_CELL'||item.retrieval_origin==='PDF_SECTION'
 const chunk=direct?undefined:item.chunk_id
 const lookup=!!(chunk&&item.document_id&&item.page&&item.source_kind!=='SEC')
 const stored=useQuery({
  queryKey:['search-chunk',item.document_id,item.page,chunk],
  enabled:expanded&&lookup,
  queryFn:()=>api<{chunks:{chunk_id:string;text:string}[]}>(`/documents/${encodeURIComponent(item.document_id!)}/chunks?page=${item.page}&chunk_id=${encodeURIComponent(chunk!)}`),
 })
 const content=lookup?stored.data?.chunks.find(entry=>entry.chunk_id===chunk)?.text:item.text
 return <details className="hit-trace" onToggle={event=>setExpanded(event.currentTarget.open)}><summary>Chi tiết truy xuất</summary>
  {chunk?<p>Chunk <code>{chunk}</code></p>:direct?
   <p>{item.retrieval_origin==='PDF_CELL'?'Ô bảng':'Đề mục'} đọc trực tiếp từ PDF · trang {item.page}</p>:
   <p>Kết quả này chưa có mã chunk riêng.</p>}
  {item.parent_id&&item.parent_id!==chunk&&<p>Đoạn cha <code>{item.parent_id}</code></p>}
  {item.row_id&&<p>Dòng bảng <code>{item.row_id}</code></p>}
  {item.column_id&&<p>Ô nguồn <code>{item.column_id}</code></p>}
  {item.bm25_rank&&<p>BM25 #{item.bm25_rank}</p>}
  {item.dense_rank&&<p>Dense #{item.dense_rank}</p>}
  {expanded&&<>
   {lookup&&stored.isPending&&<p role="status">Đang tải nội dung chunk…</p>}
   {lookup&&stored.isError&&<p>Chưa tải được nội dung chunk. <button type="button" onClick={()=>stored.refetch()}>Thử lại</button></p>}
   {lookup&&stored.isSuccess&&content===undefined&&<p>Không tìm thấy chunk này trong trang nguồn.</p>}
   {content!==undefined&&<><p><strong>{lookup?'Nguyên văn chunk đã lập chỉ mục':direct?'Nội dung bằng chứng đọc trực tiếp':'Nội dung kết quả truy xuất'}</strong></p>
    <pre className="chunk-content">{content}</pre></>}
  </>}
 </details>
}
function Match({text,query}:{text:string;query:string}){const words=query.split(/\s+/).filter(s=>s.length>3).slice(0,10),escaped=words.map(s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'));return <>{escaped.length?text.split(new RegExp('('+escaped.join('|')+')','giu')).map((s,i)=>words.some(w=>w.toLowerCase()===s.toLowerCase())?<mark key={i}>{s}</mark>:s):text}</>}
export default function EvidenceSearch({params,setParams,result,setResult,open,selected,select,askSource}:Props){
 const docs=useQuery({queryKey:['documents'],queryFn:()=>api<{documents:Doc[]}>('/documents')});const sec=useQuery({queryKey:['search-sec'],queryFn:()=>api<{status:string;filings:SecFiling[]}>('/sec/catalog')})
 const [filters,setFilters]=useState(false),[drawer,setDrawer]=useState<Evidence|null>(null),[submitted,setSubmitted]=useState(()=>sessionStorage.getItem('last-search-question')||''),[viewScope,setViewScope]=useState(()=>sessionStorage.getItem('last-search-scope')||'')
 useEffect(()=>{if(!['baseline','faith_r_product_v1','auto'].includes(params.search_profile||'auto'))setParams({...params,mode:'hybrid',search_profile:'faith_r_product_v1'});if(result&&result.requested_top_k==null)setResult(null)},[]) // Migrate legacy view cache; durable chats and sources are untouched.
 const showSec=params.source==='US_SEC'||params.source==='ALL'
 const filings=sec.data?.filings??[]
 const demoAvailable=filings.some(f=>f.ownership!=='USER_PRODUCT')
 const filing=showSec?filings.find(f=>f.filing_id===params.filing_ids?.[0]):undefined
 const lexicalOnly=filing?.dense_ready===false
 const effectiveParams=lexicalOnly?{...params,mode:'bm25' as const}:params
 const missingFiling=showSec&&!!params.filing_ids?.length&&!filing
 const secUnavailable=missingFiling||params.source==='US_SEC'&&!filing&&!demoAvailable
 const current=JSON.stringify(params),scope=useRef(current);scope.current=current
 const run=useMutation({networkMode:'always',mutationFn:async()=>{const sent={...effectiveParams},key=JSON.stringify(params);return {key,sent,data:await post<SearchResult>('/query',sent)}},onSuccess:({key,sent,data})=>{if(scope.current!==key)return;setResult(data);setSubmitted(sent.query);sessionStorage.setItem('last-search-question',sent.query);setViewScope(key);sessionStorage.setItem('last-search-scope',key);select(data.results[0]||null)}})
 useEffect(()=>{const y=sessionStorage.getItem('search-return-scroll');if(y){requestAnimationFrame(()=>window.scrollTo(0,Number(y)));sessionStorage.removeItem('search-return-scroll')}},[])
 const stale=!!result&&!!viewScope&&viewScope!==current
 const choose=(id:string)=>{if(id)sessionStorage.setItem('active-document',id);setParams({...params,document_ids:id?[id]:[],issuer:'',period:''})}
 const changeSource=(source:SearchParams['source'])=>setParams({...params,source,document_ids:source==='US_SEC'?[]:params.document_ids,
  filing_ids:source==='USER_UPLOADS'?[]:params.filing_ids,issuer:'',period:'',statement_scope:null})
 const chooseFiling=(id:string)=>setParams({...params,filing_ids:id?[id]:[],issuer:'',period:'',
  mode:filings.find(f=>f.filing_id===id)?.dense_ready===false?'bm25':params.mode})
 const ask=(e:Evidence)=>{
  if(e.document_id){askSource?.(e);return}
  if(e.source_kind==='SEC'&&e.filing_id){
   const id='SEC:'+e.filing_id
   sessionStorage.removeItem('active-financial-chat')
   sessionStorage.removeItem('chat-citation-focus')
   sessionStorage.setItem('draft-chat-sources',JSON.stringify([id]))
   sessionStorage.setItem('active-document',id)
   location.hash='/analysis'
  }
 }
 const answer=result?.financial_evidence
 return <div className="evidence-search"><form className="search-command" onSubmit={e=>{e.preventDefault();if(!run.isPending&&!secUnavailable)run.mutate()}}><div className="search-entry"><Search size={20}/><label className="sr-only" htmlFor="financial-search">Câu hỏi tìm kiếm</label><input id="financial-search" aria-label="Câu hỏi tìm kiếm" value={params.query} onChange={e=>setParams({...params,query:e.target.value})} placeholder="Tìm chỉ tiêu, bảng số liệu hoặc nội dung trong tài liệu…" minLength={2} required/><button className="primary-action" disabled={run.isPending||secUnavailable||params.query.trim().length<2}>{run.isPending?'Đang tìm…':'Tìm kiếm'}</button></div><div className="search-source-row">
  <label>Nguồn
   <select aria-label="Nguồn dữ liệu" value={params.source} onChange={e=>changeSource(e.target.value as SearchParams['source'])}>
    <option value="USER_UPLOADS">PDF tải lên</option>
    <option value="US_SEC">Hồ sơ SEC (EDGAR)</option>
    <option value="ALL">PDF và SEC</option>
   </select>
  </label>
  <div className="stack">
   {params.source!=='US_SEC'&&<label>Tài liệu PDF
    <select aria-label="Tài liệu tìm kiếm" value={params.document_ids[0]||''} onChange={e=>choose(e.target.value)}>
     <option value="">Tất cả PDF sẵn sàng</option>
     {docs.data?.documents.filter(d=>d.status==='READY').map(d=><option key={d.id} value={d.id}>{d.issuer||'PDF'} · {d.report_period||'Chưa rõ kỳ'} · {d.filename.length>45?d.filename.slice(0,42)+'…':d.filename}</option>)}
    </select>
   </label>}
   {showSec&&<label>Hồ sơ SEC
    <select aria-label="Tài liệu SEC tìm kiếm" value={params.filing_ids?.[0]||''} onChange={e=>chooseFiling(e.target.value)} disabled={!filings.length}>
     <option value="">{sec.isPending?'Đang tải hồ sơ SEC…':demoAvailable?'Tất cả hồ sơ demo':filings.length?'Chọn hồ sơ SEC':'Chưa có hồ sơ SEC sẵn sàng'}</option>
     {params.filing_ids?.[0]&&!filing&&<option value={params.filing_ids[0]} disabled>Hồ sơ đã chọn chưa khả dụng</option>}
     {[['SHARED_DEMO','Kho SEC demo'],['USER_PRODUCT','Kho SEC cá nhân']].map(([ownership,label])=>{
      const group=filings.filter(f=>ownership==='SHARED_DEMO'?f.ownership!=='USER_PRODUCT':f.ownership===ownership)
      return group.length>0&&<optgroup key={ownership} label={label}>
       {group.map(f=><option key={f.filing_id} value={f.filing_id}>{f.ticker} · {f.form} · {f.report_period} · {f.accession}{f.dense_ready===false?' · BM25':''}</option>)}
      </optgroup>
     })}
    </select>
   </label>}
  </div>
 </div>
 {showSec&&!sec.isPending&&!filings.length&&<p className="notice" role="status">Chưa tải được hồ sơ SEC sẵn sàng. Kiểm tra tab Hồ sơ SEC trong Kho tài liệu hoặc <button type="button" onClick={()=>sec.refetch()}>tải lại danh sách</button>.</p>}
 {missingFiling&&!sec.isPending&&filings.length>0&&<p className="notice" role="status">Chọn lại hồ sơ SEC đang khả dụng để tìm kiếm.</p>}
 {lexicalOnly&&<p className="method-hint">Hồ sơ SEC đã chọn tìm được bằng BM25. Dense và Hybrid đang chờ chỉ mục vector.</p>}
 <div className="search-method-row"><div className="method-segment" role="group" aria-label="Phương pháp">{methods.map(([key,name])=><button type="button" key={key} aria-pressed={methodName(effectiveParams)===key} disabled={lexicalOnly&&(key==='dense'||key==='hybrid')} onClick={()=>setParams({...params,mode:key==='faith'?(lexicalOnly?'bm25':'hybrid'):key,search_profile:key==='faith'?'faith_r_product_v1':'baseline'})}>{name}</button>)}</div><label className="topk-select">Số kết quả tối đa<select aria-label="Số kết quả tối đa" value={params.top_k} onChange={e=>setParams({...params,top_k:Number(e.target.value)})}>{[5,10,20].map(k=><option key={k} value={k}>Top-{k}</option>)}</select></label><button type="button" className="filter-toggle" aria-expanded={filters} onClick={()=>setFilters(!filters)}><SlidersHorizontal size={15}/> Bộ lọc</button></div>{methodName(params)==='faith'&&<p className="method-hint">{lexicalOnly?'FAITH-R dùng BM25 để lấy ứng viên cho hồ sơ này, sau đó xếp hạng theo bằng chứng tài chính.':'FAITH-R truy xuất ứng viên bằng Hybrid RRF, sau đó xếp hạng theo chỉ tiêu và bằng chứng tài chính.'}</p>}{filters&&<div className="search-filters"><label>Doanh nghiệp<input aria-label="Doanh nghiệp" value={params.issuer} onChange={e=>setParams({...params,issuer:e.target.value})}/></label><label>Kỳ tài liệu<input aria-label="Kỳ báo cáo tìm kiếm" value={params.period} onChange={e=>setParams({...params,period:e.target.value})} placeholder="Ví dụ: 2024"/></label>{params.source!=='US_SEC'&&<label>Phạm vi báo cáo<select aria-label="Phạm vi báo cáo tìm kiếm" value={params.statement_scope||''} onChange={e=>setParams({...params,statement_scope:e.target.value as SearchParams['statement_scope']||null})}><option value="">Tất cả phạm vi</option><option value="SEPARATE">Riêng / công ty mẹ</option><option value="CONSOLIDATED">Hợp nhất</option></select></label>}</div>}</form>
 {run.isError&&<div className="error" role="alert">{reasonText(run.error.message)}<button onClick={()=>run.mutate()}>Thử lại</button></div>}
 {stale&&<p className="notice" role="status">Bộ chọn đã thay đổi. Nhấn Tìm kiếm để xem kết quả mới. Kết quả bên dưới thuộc câu hỏi trước.</p>}
 {result&&<><div className="search-results-heading"><div><h2>Kết quả truy xuất <span>{result.returned_count??result.results.length} / tối đa {result.requested_top_k??params.top_k}</span></h2><p>“{submitted||params.query}”</p></div><small>{result.mode_executed==null?'Chưa có nguồn để thực thi':result.search_profile_executed==='faith_r_product_v1'?(result.mode_executed==='bm25'?'FAITH-R · BM25':'FAITH-R'):result.mode_executed==='bm25'?'BM25':result.mode_executed==='dense'?'Dense':'Hybrid RRF'} · {(result.latency_ms/1000).toFixed(2)} giây</small></div><div className="search-metrics"><span>Ứng viên truy xuất <b>{result.candidate_count??'Chưa đo'}</b></span><span>Bằng chứng phù hợp <b>{result.matching_evidence_count??'Chưa phân loại'}</b></span><span>Ô nguồn đã xác minh <b>{result.verified_value_count??0}</b></span></div>{result.results.length<(result.requested_top_k??params.top_k)&&result.results.length>0&&<p className="result-note">Hiển thị {result.results.length} kết quả phù hợp / giới hạn {result.requested_top_k??params.top_k}. {result.filter_reason==='METRIC_SCOPE_AND_TABLE_DIVERSITY'?'Đã lọc theo chỉ tiêu, phạm vi và dòng nguồn trùng lặp.':'Nguồn chỉ có bấy nhiêu kết quả trong phạm vi truy xuất.'} Không thêm đoạn không liên quan để đủ số lượng.</p>}
 {answer?.answer&&!!result.results.length&&<section className="search-answer"><div><span>{answer.answer_status==='VERIFIED_ANSWER'?'Kết luận đã đối chiếu':'Thông tin theo nguồn'}</span><p>{answer.primary_answer||answer.answer}</p></div><div className="inline-sources">{answer.citations?.map((c,i)=><button key={i} onClick={()=>setDrawer(c)}>[{i+1}] Trang {c.page}</button>)}</div></section>}
 {(result.retrieval_status==='CLARIFY_SCOPE'||answer?.status==='QUERY_CONTEXT_CONFLICT')&&<div className="notice" role="alert">Câu hỏi và danh tính tài liệu đang chọn chưa khớp. Đổi tài liệu hoặc doanh nghiệp trong câu hỏi để tiếp tục.</div>}{result.retrieval_status==='NO_RESULTS'&&<div className="empty" role="status"><FileText/><h3>Không tìm thấy nguồn trong phạm vi này</h3><p>Thử đổi tài liệu, kỳ hoặc từ khóa. Không có giá trị tài chính nào được suy đoán.</p></div>}{result.source_errors?.map(e=><p className="notice" key={e.source}>Nguồn {e.source==='US_SEC'?'SEC':e.source} chưa sẵn sàng. Kết quả chỉ gồm nguồn đang truy cập được.</p>)}
 <div className="evidence-results-grid"><section aria-label="Danh sách kết quả">{result.results.map(item=><article key={evidenceId(item)} className={'evidence-hit '+(selected&&evidenceId(selected)===evidenceId(item)?'active':'')}><button className="hit-select" onClick={()=>{select(item);if(window.innerWidth<1000)setDrawer(item)}}><span className="hit-rank">#{item.rank}</span><div><p className="hit-meta">{item.issuer||'PDF'} · {item.source_kind==='SEC'?`SEC · ${item.accession||'Filing'}`:`trang ${item.page||'—'}`} · {sourceLabel(item.statement_scope)} · {item.period||item.report_period||'Chưa rõ kỳ'}</p><h3><Match text={item.row_label||item.text.slice(0,90)} query={submitted}/></h3><p className="hit-excerpt">{item.text}</p></div></button>{!!item.source_cells?.length&&<details><summary>Dòng bảng gốc · cần đối chiếu cột</summary><p className="raw-source-row">{item.source_cells.map(c=>c.text).filter(Boolean).join(' | ')}</p></details>}<footer><button onClick={()=>open(item)}>Mở trang nguồn <ArrowUpRight size={14}/></button><button onClick={()=>ask(item)}>Hỏi về bằng chứng <MessageSquare size={14}/></button></footer><RetrievalDetails item={item}/></article>)}</section><aside className="evidence-preview"><h2>Xem nhanh nguồn</h2>{selected?<><p className="hit-meta">{selected.source_kind==='SEC'?`SEC · ${selected.accession||'Filing'}`:`Trang ${selected.page||'—'}`} · {sourceLabel(selected.statement_scope)}</p><h3>{selected.row_label||'Trích đoạn liên quan'}</h3><blockquote>{selected.text}</blockquote><p>{selected.period||selected.report_period||'Kỳ chưa xác định'} · {sourceLabel(selected.unit)}</p><button className="primary-action" onClick={()=>open(selected)}>Mở trang nguồn</button><button className="secondary-action" onClick={()=>ask(selected)}>Hỏi về bằng chứng</button><details><summary>Nguồn gốc kỹ thuật</summary><p>{selected.filename}</p><p>SHA256 {selected.source_sha256}</p></details></>:<p>Chọn kết quả để đối chiếu ngữ cảnh.</p>}</aside></div><details className="execution-trace"><summary>Phương pháp đã thực thi & chẩn đoán</summary><pre>{JSON.stringify({mode_requested:result.mode_requested,mode_executed:result.mode_executed,profile_requested:result.search_profile_requested,profile_executed:result.search_profile_executed,candidate_count:result.candidate_count,returned_count:result.returned_count,dedup_count:result.dedup_count,filter_reason:result.filter_reason,truncation_reason:result.truncation_reason},null,2)}</pre></details></>}
 {!result&&!run.isPending&&<div className="search-welcome"><FileText size={32}/><h2>Từ câu hỏi đến đúng dòng nguồn</h2><p>Chọn tài liệu, phương pháp và số kết quả tối đa để bắt đầu.</p></div>}{run.isPending&&<p role="status" className="search-progress">Đang truy xuất và đối chiếu nguồn thật…</p>}
 <EvidencePanel evidence={drawer} close={()=>setDrawer(null)} open={open}/></div>
}
