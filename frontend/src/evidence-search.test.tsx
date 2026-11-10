import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {render,screen,fireEvent,cleanup,waitFor} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import EvidenceSearch from './EvidenceSearch'
import type {SearchParams,SearchResult} from './api'
import {api,post} from './api'
import {useState} from 'react'
vi.mock('./api',()=>({api:vi.fn(),post:vi.fn(),evidenceId:(e:{text:string})=>e.text}))
const initial:SearchParams={query:'retained earnings',mode:'hybrid',source:'USER_UPLOADS',top_k:5,document_ids:['d'],issuer:'',period:'',search_profile:'faith_r_product_v1'}
function Harness(){const [params,setParams]=useState(initial),[result,setResult]=useState<SearchResult|null>(null);return <EvidenceSearch params={params} setParams={setParams} result={result} setResult={setResult} selected={null} select={()=>{}} open={()=>{}}/>}
function show(){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><Harness/></QueryClientProvider>)}
beforeEach(()=>{sessionStorage.clear();vi.clearAllMocks();vi.mocked(api).mockImplementation(async p=>p==='/documents'?{documents:[{id:'d',issuer:'BIDV',filename:'BIDV.pdf',report_period:'2024',status:'READY'}]} as never:{status:'UNAVAILABLE'} as never);vi.mocked(post).mockResolvedValue({status:'READY',results:[],returned_count:0,requested_top_k:5,candidate_count:0,latency_ms:1,source_errors:[],retrieval_status:'NO_RESULTS'})})
afterEach(cleanup)
describe('single Search form and honest retrieval choices',()=>{
 it('has one input even with filters open and submits raw BM25 Top10',async()=>{show();await screen.findByText('BIDV · 2024 · BIDV.pdf');fireEvent.click(screen.getByRole('button',{name:'Bộ lọc'}));expect(screen.getAllByLabelText('Câu hỏi tìm kiếm')).toHaveLength(1);fireEvent.click(screen.getByRole('button',{name:'BM25'}));fireEvent.change(screen.getByLabelText('Số kết quả tối đa'),{target:{value:'10'}});fireEvent.click(screen.getByRole('button',{name:'Tìm kiếm'}));await waitFor(()=>expect(post).toHaveBeenCalled());expect(vi.mocked(post).mock.calls[0][1]).toMatchObject({mode:'bm25',search_profile:'baseline',top_k:10})})
 it('Dense and Hybrid stay raw; FAITH-R selects its compound pipeline',async()=>{show();fireEvent.click(screen.getByRole('button',{name:'Dense'}));fireEvent.click(screen.getByRole('button',{name:'Tìm kiếm'}));await waitFor(()=>expect(post).toHaveBeenCalledTimes(1));expect(vi.mocked(post).mock.calls[0][1]).toMatchObject({mode:'dense',search_profile:'baseline'});await screen.findByText('Không tìm thấy nguồn trong phạm vi này');fireEvent.click(screen.getByRole('button',{name:'FAITH-R'}));fireEvent.click(screen.getByRole('button',{name:'Tìm kiếm'}));await waitFor(()=>expect(post).toHaveBeenCalledTimes(2));expect(vi.mocked(post).mock.calls[1][1]).toMatchObject({mode:'hybrid',search_profile:'faith_r_product_v1'})})
 it('does not show a no-evidence warning for retrieved unverified rows or an empty numeric table',async()=>{vi.mocked(post).mockResolvedValue({status:'READY',results:[{text:'Retained earnings | 10 | 2 | 12',rank:1,page:4,source_cells:[{text:'10'},{text:'2'},{text:'12'}]}],returned_count:1,requested_top_k:5,candidate_count:20,matching_evidence_count:1,verified_value_count:0,latency_ms:10,source_errors:[],evidence_status:'RELATED_UNVERIFIED_EVIDENCE',retrieval_status:'RESULTS_FOUND'});show();fireEvent.click(screen.getByRole('button',{name:'Tìm kiếm'}));await screen.findByText('1 / tối đa 5');expect(screen.queryByText('Chưa tìm thấy bằng chứng đủ tin cậy')).toBeNull();expect(screen.queryByRole('table')).toBeNull();expect(screen.queryByText(/BM25 #—/)).toBeNull()})
})

describe('SEC source selection',()=>{
 it('shows SEC while its catalog is unavailable and prevents an unscoped search',async()=>{
  show()
  fireEvent.change(screen.getByLabelText('Nguồn dữ liệu'),{target:{value:'US_SEC'}})
  await screen.findByText(/Chưa tải được hồ sơ SEC sẵn sàng/)
  expect(screen.getByRole<HTMLButtonElement>('button',{name:'Tìm kiếm'}).disabled).toBe(true)
  expect(post).not.toHaveBeenCalled()
 })
 it('sends the selected personal SEC filing and uses BM25 for a lexical-only index',async()=>{
  const filingId='sec:0000789019:0001193125-25-256321'
  vi.mocked(api).mockImplementation(async p=>p==='/sec/catalog'?{status:'READY',filings:[
   {filing_id:filingId,ticker:'MSFT',form:'10-Q',report_period:'2025-09-30',accession:'0001193125-25-256321',ownership:'USER_PRODUCT',dense_ready:false}
  ]} as never:{documents:[]} as never)
  show()
  fireEvent.change(screen.getByLabelText('Nguồn dữ liệu'),{target:{value:'US_SEC'}})
  await screen.findByRole('option',{name:/MSFT.*0001193125-25-256321.*BM25/})
  fireEvent.change(screen.getByLabelText('Tài liệu SEC tìm kiếm'),{target:{value:filingId}})
  expect(screen.getByRole<HTMLButtonElement>('button',{name:'Hybrid RRF'}).disabled).toBe(true)
  fireEvent.click(screen.getByRole('button',{name:'Tìm kiếm'}))
  await waitFor(()=>expect(post).toHaveBeenCalledWith('/query',expect.objectContaining({
   source:'US_SEC',filing_ids:[filingId],document_ids:[],mode:'bm25',search_profile:'faith_r_product_v1'
  })))
 })
})
