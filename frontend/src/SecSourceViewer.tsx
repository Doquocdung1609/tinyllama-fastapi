import {useEffect,useRef,useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {post} from './api'
import type {Evidence} from './api'
import {sourceAmount} from './source-display'

const sourceErrors:Record<string,string>={
 SOURCE_BYTES_NOT_AVAILABLE:'Không tìm thấy bytes snapshot gốc trong kho đã cấu hình. Không thay bằng một filing khác.',
 SOURCE_HASH_MISMATCH:'Bytes nguồn đã thay đổi so với hash đăng ký. Bằng chứng này đã bị chặn.',
 SOURCE_LOCATOR_UNRESOLVED:'Không đối chiếu được đúng hàng, cột hoặc kỳ của citation. Không tạo highlight hay số liệu thay thế.',
 SOURCE_IDENTITY_MISMATCH:'Danh tính filing hoặc membership không khớp nguồn đã đăng ký.',
 SOURCE_GENERATION_MISMATCH:'Generation hoặc manifest đã thay đổi. Hãy chạy lại câu hỏi trong nguồn phù hợp.',
 UNREGISTERED_SOURCE_REFERENCE:'Tham chiếu nguồn không hợp lệ hoặc thuộc workspace khác. Hãy lấy citation mới.',
 SOURCE_EVIDENCE_BUDGET:'Nguồn hoặc bảng vượt giới hạn hiển thị an toàn hiện tại.',
 SOURCE_VIEW_BUSY:'Một nguồn khác đang được xác minh. Hãy chờ và kiểm tra lại.'
}

type PhysicalCell={column:number;text:string;colspan:number;rowspan:number}
export type SecView={status:string;issuer:string;form:string;accession:string;report_period:string;filing_date?:string|null;fiscal_year?:number|null;source_sha256:string;normalized_sha256:string;official_url:string;generation:string;manifest_hash:string;parent_id:string;rendering:string;warnings:string[];excerpt:string;locator_limitation?:string;locator:unknown;
 selected_cell:null|{row:number;column:number;row_label:string;raw_value:string;value?:string;period_start?:string|null;period_end:string;effective_value?:string;unit:string;multiplier:string;period_kind:string;fact_name:string;header_path:string[];warnings:string[]};
 table:null|{id:string;caption:string|null;statement:string|null;section:string|null;rows:{index:number;cells:PhysicalCell[]}[];selected_row:number;header_row_count:number;total_source_rows:number;footnotes:string[];warnings:string[]}}

export function SafeSecEvidence({data}:{data:SecView}){
 const selected=useRef<HTMLTableCellElement>(null),[copied,setCopied]=useState(false)
 useEffect(()=>{selected.current?.scrollIntoView({block:'nearest',inline:'nearest'})},[data])
 const cell=data.selected_cell
 const warnings=[...new Set([...data.warnings,...(data.table?.warnings||[]),...(cell?.warnings||[])])]
 const warningText:Record<string,string>={
  PARTIAL_TABLE_EXTRACTION:'Một số bảng trong báo cáo chưa được trích xuất đầy đủ. Chỉ ô đang chọn được đối chiếu theo phạm vi hiển thị.',
  FILING_PARTIAL_EXTRACTION_OUTSIDE_SELECTED_TABLE:'Các phần khác của báo cáo còn giới hạn trích xuất; xác minh ô đang chọn không chứng nhận toàn bộ báo cáo.'
 }
 let official:string|undefined
 try{const u=new URL(data.official_url);if(u.protocol==='https:'&&u.hostname==='www.sec.gov'&&!u.username&&!u.password)official=u.href}catch{/* no unsafe navigation */}
 const citation=`${data.issuer} · ${data.form} · ${data.accession}\n${cell?`${cell.row_label}: ${cell.raw_value} ${cell.unit} × ${cell.multiplier} · ${cell.period_kind} ${cell.period_end}`:data.excerpt}\n${official||''}\nSHA256 ${data.source_sha256}\n${data.table?.id||''} row ${cell?.row??data.table?.selected_row} col ${cell?.column??'unknown'}`
 return <section className="card sec-source-viewer" aria-label="Nguồn SEC đã xác minh">
  <h2>{data.issuer}</h2><p><strong>{data.form}</strong> · Accession {data.accession}</p>
  <p>Kỳ báo cáo kết thúc: {data.report_period}{data.filing_date?` · Ngày nộp SEC: ${data.filing_date}`:''}{data.fiscal_year?` · Năm tài chính theo metadata: FY${data.fiscal_year}`:''}</p>
  <p role="status" className="sec-verification-status"><strong>{data.status==='VERIFIED_LOCAL_SEC_SNAPSHOT'?'Đã kiểm tra tính toàn vẹn tệp SEC gốc':'Đã kiểm tra tệp SEC · vị trí hiển thị còn giới hạn'}</strong></p>
  <p className="muted">Đây là bảng/văn bản dẫn xuất an toàn từ HTML gốc đã xác minh, với ngữ cảnh được giới hạn. Không chạy script hay tải tài nguyên ngoài. Xác minh tệp gốc không đồng nghĩa toàn bộ báo cáo đã được phân tích đầy đủ.</p>
  {cell&&<div className="answer"><h3>{cell.row_label}: <span data-testid="sec-selected-value">{sourceAmount(cell.value??cell.raw_value,cell.unit,cell.multiplier)||`${cell.raw_value} ${cell.unit} × ${cell.multiplier}`}</span></h3><p>{cell.period_kind==='INSTANT'?'Số dư tại ngày':cell.period_kind==='DURATION'?'Kỳ phát sinh':'Kỳ nguồn'}: {cell.period_start?`${cell.period_start} → `:''}{cell.period_end}</p><p>Ô được tô xanh đã được đối chiếu với hàng, cột, kỳ và đơn vị nguồn.</p><details><summary>Giá trị gốc và đơn vị</summary><p>Giá trị hiển thị gốc: {cell.raw_value} · {cell.unit} × {cell.multiplier}</p>{cell.effective_value&&<p>Giá trị chuẩn hóa từ backend: {cell.effective_value} {cell.unit}</p>}<p>Tiêu đề cột gốc: {cell.header_path.join(' / ')}</p></details><small>Hàng chọn: vàng nhạt · Cột kỳ: xanh lam nhạt · Ô chính xác: xanh lá, viền xanh đậm.</small></div>}
  {data.table?<><h3>{data.table.statement||data.table.caption||data.table.section||'Bảng nguồn SEC'}</h3><p className="muted">Bảng có {data.table.total_source_rows} hàng trong nguồn; đang hiển thị tiêu đề và các hàng lân cận có giới hạn.</p>
   <div className="sec-table-wrap" tabIndex={0} aria-label="Bảng SEC có thể cuộn"><table className="sec-source-table"><tbody>{data.table.rows.map(row=><tr key={row.index} data-source-row={row.index} className={row.index===data.table!.selected_row?'sec-selected-row':''}><th scope="row" className="sec-row-index">{row.index}</th>{row.cells.map(c=>{
    const col=cell&&c.column<=cell.column&&cell.column<c.column+c.colspan
    const exact=!!col&&row.index===cell?.row&&c.column===cell.column
    return <td key={c.column} ref={exact?selected:undefined} colSpan={c.colspan} rowSpan={c.rowspan} data-source-column={c.column} data-testid={exact?'sec-selected-cell':undefined} className={exact?'sec-selected-cell':col?'sec-selected-column':''}>{c.text}</td>
   })}</tr>)}</tbody></table></div>{data.table.footnotes.map((n,i)=><p key={i} className="muted">{n}</p>)}</>:<blockquote className="quote">{data.excerpt}</blockquote>}
  {data.locator_limitation&&<p role="status">Giới hạn locator: {data.locator_limitation}. Không xác nhận điều hướng ô số.</p>}
  {[...new Set(warnings.map(w=>warningText[w]||'Nguồn có giới hạn trích xuất hoặc ngữ cảnh; xem chẩn đoán kỹ thuật để biết chi tiết.'))].map((w,i)=><p className="notice" key={i}>{w}</p>)}
  <div className="row" style={{marginTop:16}}>{official&&<a href={official} target="_blank" rel="noopener noreferrer">Mở bản công bố trên SEC.gov</a>}<button className="source-button" onClick={async()=>{try{await navigator.clipboard.writeText(citation);setCopied(true)}catch{setCopied(false)}}}>Sao chép citation SEC</button>{copied&&<span role="status">Đã sao chép citation.</span>}</div>
  <p className="muted">SEC.gov có thể hạn chế truy cập tự động. Viewer nội bộ không chứng minh trang ngoài đã mở được hoặc hạ cánh đúng ô.</p>
  <details><summary>Provenance và locator</summary><p>Thông tin kỹ thuật · chỉ số hàng/cột bắt đầu từ 0.</p><dl className="kv"><dt>Raw SHA256</dt><dd className="sec-digest">{data.source_sha256}</dd><dt>Normalized SHA256</dt><dd className="sec-digest">{data.normalized_sha256}</dd><dt>Generation</dt><dd className="sec-digest">{data.generation}</dd><dt>Manifest</dt><dd className="sec-digest">{data.manifest_hash}</dd><dt>Bảng nguồn</dt><dd>{data.table?.id||'Không có bảng'}</dd><dt>Parent</dt><dd>{data.parent_id}</dd><dt>Fact</dt><dd>{cell?.fact_name||'Không chọn fact số'}</dd><dt>Mã cảnh báo gốc</dt><dd>{warnings.join(' · ')||'Không có'}</dd></dl><pre>{JSON.stringify(data.locator,null,2)}</pre></details>
 </section>
}

export default function SecSourceViewer({evidence}:{evidence:Evidence}){
 const view=useQuery({queryKey:['sec-source-view',evidence.source_reference],queryFn:()=>post<SecView>('/sec/evidence',{reference:evidence.source_reference}),enabled:!!evidence.source_reference,retry:false,gcTime:0,staleTime:0})
 if(!evidence.source_reference)return <section className="notice" role="alert">Citation cũ chưa có tham chiếu nguồn xác thực. Hãy chạy lại câu hỏi SEC để lấy citation mới; không dùng URL do client gửi để mở tệp.</section>
 if(view.error)return <section className="notice" role="alert"><h2>Không thể xác minh nguồn SEC</h2><p>{sourceErrors[view.error.message]||'Chưa thể xác minh nguồn hiện tại; hãy kiểm tra kho dữ liệu và kết nối API.'}</p><p>Không hiển thị lại ô đã xác minh cũ khi bytes/nguồn/locator không còn hợp lệ.</p><details><summary>Chi tiết trạng thái</summary>{view.error.message}</details><button onClick={()=>view.refetch()}>Kiểm tra lại nguồn</button></section>
 if(!view.data)return <p role="status">Đang xác minh bytes nguồn và định vị bảng SEC…</p>
 return <SafeSecEvidence data={view.data}/>
}
