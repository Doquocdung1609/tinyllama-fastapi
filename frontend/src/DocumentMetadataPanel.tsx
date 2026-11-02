import {useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from './api'
import {Button} from '@/components/ui/button'
type Metadata={fields:Record<string,{value:string|null;status:string;source_page:number|null;source_snippet:string}>;corrections:{changes:Record<string,string>;timestamp:string}[]}
export default function DocumentMetadataPanel({id}:{id:string}){
 const client=useQueryClient();const data=useQuery({queryKey:['metadata',id],queryFn:()=>api<Metadata>(`/documents/${id}/metadata`)})
 const [issuer,setIssuer]=useState(''),[period,setPeriod]=useState(''),[type,setType]=useState('')
 const save=useMutation({mutationFn:()=>api(`/documents/${id}/metadata`,{method:'PATCH',body:JSON.stringify({changes:{...(issuer?{issuer}:{}),...(period?{report_period:period}:{}),...(type?{document_type:type}:{})}})}),onSuccess:()=>{sessionStorage.removeItem('financial-chat-'+id);client.invalidateQueries({queryKey:['metadata',id]});client.invalidateQueries({queryKey:['documents']})}})
 return <details className="card"><summary>Metadata tự nhận diện · xem nguồn hoặc hiệu chỉnh</summary>
  <dl className="kv">{Object.entries(data.data?.fields||{}).map(([key,field])=><div key={key}><dt>{key}</dt><dd>{field.value||'Chưa xác định'} · {field.status}{field.source_page?` · trang ${field.source_page}`:''}<small style={{display:'block'}}>{field.source_snippet}</small></dd></div>)}</dl>
  <p className="muted">Hiệu chỉnh được lưu riêng với thời gian và không sửa tệp PDF gốc. Tiền tệ của từng ô vẫn cần được xác minh từ nguồn.</p>
  <form onSubmit={e=>{e.preventDefault();save.mutate()}}><label>Doanh nghiệp hiệu chỉnh<input value={issuer} onChange={e=>setIssuer(e.target.value)} maxLength={160}/></label><label>Kỳ hiệu chỉnh<input value={period} onChange={e=>setPeriod(e.target.value)} maxLength={80}/></label><label>Loại tài liệu hiệu chỉnh<input value={type} onChange={e=>setType(e.target.value)} maxLength={40}/></label><Button disabled={save.isPending} type="submit">Lưu hiệu chỉnh metadata</Button></form>
  {save.isSuccess&&<p role="status">Đã lưu hiệu chỉnh.</p>}{(save.error||data.error)&&<p role="alert">{(save.error||data.error)?.message}</p>}
  {data.data?.corrections.map((c,i)=><p key={i}>{c.timestamp}: {Object.entries(c.changes).map(([k,v])=>`${k}: ${v}`).join(' · ')}</p>)}
 </details>
}
