export type Mode='bm25'|'dense'|'hybrid'
export type Source='VIETNAM'|'US_SEC'|'ALL'|'USER_UPLOADS'
export type Doc={id:string;filename:string;issuer:string;report_period:string;document_type:string;status:string;stage:string;pages:number;chunks:number;sha256:string;error_code?:string}
export type Evidence={evidence_id?:string;evidence_match?:string;row_id?:string;statement_scope?:string;document_type?:string;chunk_id?:string;parent_id?:string;document_id?:string;page?:number;rank?:number;text:string;issuer?:string;filename?:string;report_period?:string;source_sha256?:string;source_kind?:string;source_url?:string;source_location?:unknown;bm25_rank?:number;dense_rank?:number;provenance_status?:string;box?:number[];verification?:string;row_label?:string;column_label?:string;unit?:string;period?:string;extraction_method?:string}
export type Fact=Evidence & {id:string;metric:string;period:string;statement_scope:string;basis:string;value:string;base_value:string;source_display:string;currency:string;page:number;document_id:string;text:string}
export type SearchParams={search_profile?:"baseline"|"production_v2";query:string;mode:Mode;source:Source;top_k:number;document_ids:string[];issuer:string;period:string}
export type SearchResult={evidence_status?:string;evidence_reason?:string;status:string;results:Evidence[];generation:string;latency_ms:number;mode:Mode;source_errors:{source:string;reason:string}[]}
export type Ready={api:string;workspace:{ready_documents:number;total_documents:number;ready_chunks:number;model:string;dimension:number;disk_free_bytes:number};ocr:{status:string;languages:string[]};ollama:{status:string;models:string[]};sec:{status:string;reason?:string;parents?:number;dense_vectors?:number;generation?:string;filings:{issuer:string;ticker:string;report_period:string;form:string;chunks:number;source_url:string;accession:string}[]};resources:{available_ram_bytes:number}}
export type Cell={column_index:number;text:string;box:number[]|null;confidence:number|null;verification:string}
export type TableRow={id:string;row_label:string;cells:Cell[];box:number[];structure_status:string}
export type PageEvidence={page:number;width:number;height:number;method:string;original_rotation:number;pdf_type:string;engine:Record<string,unknown>;text:string;lines:{text:string;box:number[];words:{text:string;box:number[];confidence:number|null}[]}[];tables:TableRow[];evidence_sha256:string}
export type Extraction={pages_completed:number;pages_total:number;pdf_type:string;table_status:string;search_ready:boolean;pages:{page:number;status:string;method:string;error?:string;table_rows:number}[]}
export type Answer={status:string;answer?:string;reason?:string;values?:string[];unit?:string;formula?:string;citations?:Evidence[];operands?:{value:string;period:string;unit:string;normalized_value:string;normalized_unit:string}[]}
export type ResearchEvent={stage:string;status:string;label:string;data:unknown}
export type Job={id:string;status:string;error?:string;events:ResearchEvent[]}

export class ApiError extends Error{status:number;constructor(status:number,message:string){super(message);this.status=status}}
export function getToken(){return sessionStorage.getItem('studio-token')||''}
export async function api<T>(path:string,init:RequestInit={}):Promise<T>{
 const response=await fetch('/studio'+path,{...init,headers:{...(init.body instanceof FormData?{}:{'Content-Type':'application/json'}),Authorization:'Bearer '+getToken(),...init.headers},signal:init.signal||AbortSignal.timeout(120000)})
 if(!response.ok){const data=await response.json().catch(()=>({}));throw new ApiError(response.status,data.detail?.code||data.detail||`HTTP_${response.status}`)}
 return response.json()
}
export async function pdfBytes(id:string){const r=await fetch(`/studio/documents/${encodeURIComponent(id)}/file`,{headers:{Authorization:'Bearer '+getToken()}});if(!r.ok)throw new ApiError(r.status,'Không mở được PDF hoặc nguồn đã thay đổi.');return r.arrayBuffer()}
export const post=<T>(path:string,body:unknown)=>api<T>(path,{method:'POST',body:JSON.stringify(body)})
export function evidenceId(e:Evidence){return e.evidence_id||e.chunk_id||e.parent_id||`${e.document_id}:${e.page}:${e.text}`}
export function citation(e:Evidence){return `${e.issuer||e.filename||'Tài liệu'} · ${e.period||e.report_period||'Kỳ chưa xác định'} · ${e.page?`trang PDF ${e.page}`:'SEC HTML, vị trí cấu trúc'}\n${e.text||e.row_label||''}\nSHA256: ${e.source_sha256||'Xem metadata nguồn'}`}
