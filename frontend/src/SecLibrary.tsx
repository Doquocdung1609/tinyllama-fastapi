import {useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {api,post} from './api'

type Filing={filing_id:string;company_name?:string;issuer?:string;ticker:string;form_type?:string;form?:string;report_date?:string;report_period?:string;filing_date?:string;accession_number?:string;accession?:string;source_url:string;discovery_id?:string;dense_ready?:boolean}
type Recovery={ticker:string;cik:string;form:string;report_date:string;accession:string;source_url:string;local_status:string;recovery:string;product_status?:string;product_reason?:string;reason?:string;search_ready:boolean;dense_ready?:boolean}
type Job={id:string;status:string;reason?:string;metadata:Filing;progress?:{
 last_progress_at:number;source_bytes?:number;tables?:number;extracted_chunks?:number;published_chunks?:number;completed_embeddings?:number;target_embeddings?:number
}}
const stageLabels:Record<string,string>={
 DOWNLOADING:'Đang tải từ EDGAR',SOURCE_VERIFIED:'Đã xác thực nguồn',EXTRACTING:'Đang đọc filing',
 EXTRACTED:'Đã trích xuất',INDEXING:'Đang lập chỉ mục',BUILDING_LEXICAL:'Đang lập chỉ mục BM25',
 LEXICAL_READY:'BM25 đã xuất bản',READY:'BM25 và Dense đã xuất bản',RETRYABLE:'Có thể thử lại',FAILED:'Cần kiểm tra lỗi'
}
const reasonLabels:Record<string,string>={
 BUILDING_DENSE:'Đang xây dựng Dense. Vẫn có thể tìm kiếm BM25 và hỏi đáp có nguồn.',
 DENSE_PENDING:'Đã có thể tìm theo từ khóa. Dense và Hybrid đang chờ lập chỉ mục.',
 WORKER_PROGRESS_TIMEOUT_RETRY:'Tác vụ quá hạn tiến độ. Hãy thử lại từ checkpoint đã xác thực.',
 PROCESS_RESTARTED_RETRY_IMPORT:'Tác vụ đã dừng khi khởi động lại. Hãy thử lại từ checkpoint đã xác thực.',
 LIVE_MODEL_DIGEST_MISMATCH:'Mô hình embedding đang chạy không khớp phiên bản của chỉ mục.'
}
export default function SecLibrary(){
 const qc=useQueryClient(),[query,setQuery]=useState(''),[form,setForm]=useState('10-Q'),[contact,setContact]=useState('')
 const [reportEnd,setReportEnd]=useState(''),[filedFrom,setFiledFrom]=useState(''),[filedTo,setFiledTo]=useState('')
 const catalog=useQuery({queryKey:['sec-library-catalog'],queryFn:()=>api<{filings:Filing[]}>('/sec/catalog'),refetchInterval:5000})
 const jobs=useQuery({queryKey:['sec-library-jobs'],queryFn:()=>api<{contact_configured:boolean;dense_build_enabled?:boolean;filings:Job[]}>('/sec/library'),refetchInterval:2500})
 const recovery=useQuery({queryKey:['sec47-recovery'],queryFn:()=>api<{filings:Recovery[]}>('/sec/library/sec47'),staleTime:30000})
 const [recoveryFilter,setRecoveryFilter]=useState('')
 const recoveryRows=recovery.data?.filings||[]
 const search=useMutation({networkMode:'always',mutationFn:()=>api<{status:string;companies?:{ticker:string;title:string}[];filings:Filing[]}>(`/sec/library/discover?query=${encodeURIComponent(query)}&form=${encodeURIComponent(form)}&report_end=${reportEnd}&filed_from=${filedFrom}&filed_to=${filedTo}`)})
 const add=useMutation({networkMode:'always',mutationFn:(id:string)=>post('/sec/library/import',{discovery_id:id}),onSuccess:()=>qc.invalidateQueries({queryKey:['sec-library-jobs']})})
 const save=useMutation({networkMode:'always',mutationFn:()=>post('/sec/library/contact',{user_agent:contact}),onSuccess:()=>{setContact('');qc.invalidateQueries({queryKey:['sec-library-jobs']})}})
 const remove=useMutation({networkMode:'always',mutationFn:(id:string)=>api(`/sec/library/${id}`,{method:'DELETE'}),onSuccess:()=>{qc.invalidateQueries({queryKey:['sec-library-jobs']});qc.invalidateQueries({queryKey:['sec-library-catalog']})}})
 const ask=(f:Filing)=>{
  const selected='SEC:'+f.filing_id
  sessionStorage.removeItem('active-financial-chat')
  sessionStorage.removeItem('chat-citation-focus')
  sessionStorage.setItem('draft-chat-sources',JSON.stringify([selected]))
  sessionStorage.setItem('active-document',selected)
  location.hash='/analysis'
 }
 return <div className="stack"><h2>Kho SEC · {catalog.data?.filings.length||0} filing sẵn sàng</h2><p>Tìm báo cáo chính thức theo ticker, tên công ty hoặc CIK; kiểm tra kỳ báo cáo trước khi thêm. Kho cá nhân tách riêng khỏi dữ liệu nghiên cứu.</p>
 {!jobs.data?.contact_configured&&<form onSubmit={e=>{e.preventDefault();save.mutate()}}><label>Liên hệ ứng dụng cho SEC<input aria-label="Liên hệ SEC" value={contact} onChange={e=>setContact(e.target.value)} placeholder="Tên ứng dụng email@congty.vn" required/></label><button disabled={save.isPending}>Lưu riêng trên máy</button></form>}
 <form className="row" onSubmit={e=>{e.preventDefault();search.mutate()}}><label>Ticker / tên / CIK<input aria-label="Tìm công ty SEC" value={query} onChange={e=>setQuery(e.target.value)} required maxLength={120}/></label><label>Loại filing<select aria-label="Loại filing SEC" value={form} onChange={e=>setForm(e.target.value)}>{['10-Q','10-K','20-F','6-K','10-Q/A','10-K/A'].map(f=><option key={f}>{f}</option>)}</select></label><label>Kỳ báo cáo kết thúc<input aria-label="Kỳ báo cáo SEC" type="date" value={reportEnd} onChange={e=>setReportEnd(e.target.value)}/></label><label>Nộp từ ngày<input aria-label="Ngày nộp SEC từ" type="date" value={filedFrom} onChange={e=>setFiledFrom(e.target.value)}/></label><label>Nộp đến ngày<input aria-label="Ngày nộp SEC đến" type="date" value={filedTo} onChange={e=>setFiledTo(e.target.value)}/></label><button className="primary-action" disabled={search.isPending}>{search.isPending?'Đang tìm SEC…':'Tìm trên EDGAR'}</button></form>
 {[search.error,add.error,save.error,remove.error,jobs.error].filter(Boolean).map((e,i)=><p className="error" role="alert" key={i}>{String(e)}. Kiểm tra kết nối hoặc liên hệ SEC rồi thử lại.</p>)}
 {search.data?.status==='OK'&&!search.data.filings.length&&<p role="status">Không có filing khớp trong danh mục gần đây từ SEC. Hãy kiểm tra loại filing, kỳ và ngày nộp.</p>}
 {search.data?.companies?.map(c=><button key={c.ticker} onClick={()=>setQuery(c.ticker)}>{c.ticker} · {c.title}</button>)}
 {search.data?.filings.map(f=><article className="hit" key={f.filing_id}><h3>{f.ticker} · {f.form_type} · kỳ {f.report_date||'chưa rõ'}</h3><p>Ngày nộp {f.filing_date} · accession {f.accession_number}</p><a href={f.source_url} target="_blank" rel="noreferrer">Xem nguồn SEC</a><button disabled={add.isPending} onClick={()=>add.mutate(f.discovery_id!)}>Thêm vào kho SEC</button></article>)}
 {!!recoveryRows.length&&<details><summary>Khôi phục SEC47 · {recoveryRows.filter(f=>f.search_ready).length}/{recoveryRows.length} nguồn đã lập chỉ mục</summary>
  <label>Lọc danh mục kiểm toán<input value={recoveryFilter} onChange={e=>setRecoveryFilter(e.target.value)} placeholder="Ticker, CIK, loại hoặc năm"/></label>
  <div className="scroll-table"><table><thead><tr><th>Filing</th><th>Kỳ</th><th>Nguồn và trạng thái</th></tr></thead><tbody>
   {recoveryRows.filter(f=>`${f.ticker} ${f.cik} ${f.form} ${f.report_date}`.toLowerCase().includes(recoveryFilter.trim().toLowerCase())).map(f=><tr key={f.accession}>
    <td><a href={f.source_url} target="_blank" rel="noreferrer">{f.ticker} · {f.form} · {f.accession}</a></td>
    <td>{f.report_date}</td><td>{f.search_ready?(f.dense_ready?'BM25 + Dense':'BM25 · chờ Dense'):f.product_status||'Danh mục'} · {f.recovery==='NOT_ATTEMPTED'?f.local_status:f.recovery}{(f.product_reason||f.reason)&&<small> · {f.product_reason||f.reason}</small>}</td>
   </tr>)}
  </tbody></table></div>
 </details>}
 <h3>Nguồn READY</h3>{catalog.data?.filings.map(f=><article className="hit" key={f.filing_id}><strong>{f.ticker} · {f.form||f.form_type} · {f.report_period||f.report_date}{f.dense_ready===false?' · BM25':''}</strong><p>{f.accession||f.accession_number}</p><a href={f.source_url} target="_blank" rel="noreferrer">Nguồn SEC</a> <button onClick={()=>ask(f)}>Hỏi báo cáo này</button></article>)}
 <details open><summary>Tiến trình kho cá nhân</summary>{jobs.data?.filings.filter(j=>j.status!=='DISCOVERED').map(j=><article className="hit" key={j.id}>
  <strong>{j.metadata.ticker} · {j.metadata.form_type} · kỳ {j.metadata.report_date} · {stageLabels[j.status]||j.status}</strong>
  <p>Accession {j.metadata.accession_number}</p>
  {j.reason&&<p>{reasonLabels[j.reason]||(j.status==='LEXICAL_READY'?'BM25 vẫn dùng được. Dense cần được thử lại.':'Tác vụ cần kiểm tra trước khi thử lại.')}</p>}
  {j.progress?.source_bytes!=null&&<p>{j.progress.source_bytes.toLocaleString('vi-VN')} byte đã xác thực · {j.progress.tables} bảng đã đọc.</p>}
  {j.progress?.published_chunks!=null&&<p>Đã xuất bản {j.progress.published_chunks} mục BM25.</p>}
  {j.progress?.target_embeddings!=null&&<p>Vector đã lưu {j.progress.completed_embeddings??0}/{j.progress.target_embeddings}.</p>}
  {j.progress?.last_progress_at&&<p>Cập nhật gần nhất {new Date(j.progress.last_progress_at*1000).toLocaleString('vi-VN')}</p>}
  {j.reason&&!reasonLabels[j.reason]&&<details><summary>Thông tin kỹ thuật</summary>{j.reason}</details>}
  {j.status==='LEXICAL_READY'&&jobs.data?.dense_build_enabled===false&&<p>Workspace này chỉ xây chỉ mục BM25 theo cấu hình hiện tại.</p>}
  {j.reason!=='BUILDING_DENSE'&&(['RETRYABLE','FAILED'].includes(j.status)||j.status==='LEXICAL_READY'&&jobs.data?.dense_build_enabled!==false)&&
    <button disabled={add.isPending} onClick={()=>add.mutate(j.id)}>{j.status==='LEXICAL_READY'?'Thử xây Dense':'Thử nhập lại'}</button>}
  {j.reason!=='BUILDING_DENSE'&&['READY','LEXICAL_READY','FAILED','RETRYABLE'].includes(j.status)&&
    <button onClick={()=>{if(confirm('Gỡ filing khỏi kho cá nhân? Nguồn gốc được giữ để kiểm toán.'))remove.mutate(j.id)}}>Gỡ khỏi kho cá nhân</button>}
 </article>)}</details>
 </div>
}
