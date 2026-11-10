import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest'
import {render,screen,fireEvent,waitFor,cleanup,act} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import FinancialChat from './FinancialChat'
import {api,post} from './api'
vi.mock('./api',async importOriginal=>({...await importOriginal<typeof import('./api')>(),api:vi.fn(),post:vi.fn()}))
const docs=['a','b'].map(name=>({id:name.repeat(32),filename:name+'.pdf',issuer:name,report_period:'2025',status:'READY',pages:2}))
function show(){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><FinancialChat open={()=>{}}/></QueryClientProvider>)}
beforeEach(()=>{sessionStorage.clear();vi.clearAllMocks();vi.mocked(api).mockResolvedValue({documents:docs})})
afterEach(cleanup)
describe('financial chat request and source safety',()=>{
 it('sends no dropdown defaults in ordinary auto mode',async()=>{
  vi.mocked(post).mockResolvedValue({session_id:'c'.repeat(32),status:'SOURCE_EXCERPTS',answer:'Synthetic UI fixture',values:[]})
  show();await screen.findByText('a · 2025 · a.pdf')
  fireEvent.change(screen.getByLabelText('Câu hỏi trợ lý'),{target:{value:'Net income 2025?'}})
  fireEvent.click(screen.getByRole('button',{name:'Gửi câu hỏi'}))
  await waitFor(()=>expect(post).toHaveBeenCalled())
  expect(vi.mocked(post).mock.calls[0][1]).toMatchObject({document_ids:['a'.repeat(32)],constraints:{}})
  expect(vi.mocked(post).mock.calls[0][1]).not.toHaveProperty('metric')
  expect(vi.mocked(post).mock.calls[0][1]).not.toHaveProperty('evidence_context')
 })
 it('discards an old document response after source switch',async()=>{
  let finish:(v:unknown)=>void=()=>{}
  vi.mocked(post).mockImplementation(()=>new Promise(resolve=>{finish=resolve}))
  show();await screen.findByText('a · 2025 · a.pdf')
  fireEvent.change(screen.getByLabelText('Câu hỏi trợ lý'),{target:{value:'Question for source A'}})
  fireEvent.click(screen.getByRole('button',{name:'Gửi câu hỏi'}))
  await waitFor(()=>expect(post).toHaveBeenCalled())
  fireEvent.change(screen.getByLabelText('Tài liệu trợ lý'),{target:{value:'b'.repeat(32)}})
  await act(async()=>finish({session_id:'c'.repeat(32),status:'SOURCE_EXCERPTS',answer:'STALE_SOURCE_A',values:[]}))
  expect(screen.queryByText('STALE_SOURCE_A')).not.toBeInTheDocument()
  expect(sessionStorage.getItem('active-document')).toBe('b'.repeat(32))
 })
 it('reopens server history after remount and preserves citation destination',async()=>{
  const open=vi.fn();const sid='c'.repeat(32)
  vi.mocked(api).mockImplementation(async path=>{
   if(path==='/documents')return {documents:docs} as never
   if(path.startsWith('/chat/sessions'))return {sessions:[{id:sid,title:'Saved thread',updated_at:'2026-11-04T00:00:00Z',document_ids:[docs[0].id],message_count:2}],has_more:false} as never
   if(path==='/chat/'+sid)return {id:sid,title:'Saved thread',document_ids:[docs[0].id],turns:[{question:'Find source row',response:{status:'SOURCE_EXCERPTS',answer:'Source row [1]',citations:[{document_id:docs[0].id,page:7,text:'Exact retained source',box:[1,2,30,40]}]}}]} as never
   return {filings:[],status:'UNAVAILABLE'} as never
  })
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><FinancialChat open={open}/></QueryClientProvider>)
  fireEvent.click(await screen.findByRole('button',{name:/Saved thread/}))
  fireEvent.click(await screen.findByRole('button',{name:'Mở nguồn 1 trang 7'}))
  fireEvent.click(await screen.findByRole('button',{name:'Mở trang nguồn 7'}))
  expect(open).toHaveBeenCalledWith(expect.objectContaining({document_id:docs[0].id,page:7,box:[1,2,30,40]}))
  expect(sessionStorage.getItem('active-financial-chat')).toBe(sid)
 })
 it('renders source markup as text and sends with Enter',async()=>{
  vi.mocked(post).mockResolvedValue({session_id:'c'.repeat(32),status:'SOURCE_EXCERPTS',answer:'<script>bad()</script> [1]',citations:[{page:4,text:'Fixture source'}]})
  show();await screen.findByText('a · 2025 · a.pdf')
  const field=screen.getByLabelText('Câu hỏi trợ lý');fireEvent.change(field,{target:{value:'Find source'}});fireEvent.keyDown(field,{key:'Enter'})
  await screen.findByText('<script>bad()</script>',{exact:false})
  expect(document.querySelector('.answer-prose script')).toBeNull()
  expect(vi.mocked(post).mock.calls).toHaveLength(1)
 })
 it('shows audited calculation steps and keeps operand citations clickable',async()=>{
  vi.mocked(post).mockResolvedValue({session_id:'c'.repeat(32),status:'SUPPORTED',answer:'Growth 25% [1]',answer_explanation:'Exact original operands.',independent_verification:{status:'VERIFIED'},calculation_steps:[{calculation_id:'x',title:'Growth',formula:'(current − previous) / previous × 100',result:'25.00',unit:'%',rounding:'ROUND_HALF_UP',substitution:[{value:'125',period:'2025',scope:'CONSOLIDATED',basis:'AS_REPORTED',unit:'MILLION_USD',citation:'[1]'}]}],citations:[{page:2,text:'Original cell'}]})
  show();await screen.findByText('a · 2025 · a.pdf')
  fireEvent.change(screen.getByLabelText('Câu hỏi trợ lý'),{target:{value:'Growth?'}});fireEvent.click(screen.getByRole('button',{name:'Gửi câu hỏi'}))
  expect(await screen.findByText('Các bước tính · Đã kiểm chứng độc lập')).toBeInTheDocument()
  expect(screen.getByText('Exact original operands.')).toBeInTheDocument()
  expect(screen.getByText('Kết quả: 25,00 %')).toBeInTheDocument()
 })

 it('uses only an explicit pending selection and cleans up a historical dictionary answer',async()=>{
  const focus={document_id:docs[0].id,page:4,row_id:'r',column_id:'c',text:'Nợ phải trả'}
  vi.mocked(post).mockResolvedValue({session_id:'d'.repeat(32),status:'SUPPORTED',
   verification_status:'HUMAN_SOURCE_VERIFIED',answer:"{'INSTANT': '31/12/2025', 'FY': 'Cả năm 2025'}",
   values:['1234'],citations:[{...focus,period:'31/12/2025',unit:'VND',row_label:'Nợ phải trả'}]})
  render(<QueryClientProvider client={new QueryClient()}><FinancialChat focus={focus} open={()=>{}}/></QueryClientProvider>)
  await screen.findByText('a · 2025 · a.pdf')
  fireEvent.click(screen.getByRole('button',{name:'Gửi câu hỏi'}))
  await waitFor(()=>expect(post).toHaveBeenCalled())
  expect(vi.mocked(post).mock.calls[0][1]).toMatchObject({evidence_context:{intent:'USER_SOURCE_FOCUS',page:4,column_id:'c'}})
  expect(await screen.findByText(/là 1.234 đồng/)).toBeInTheDocument()
  expect(screen.queryByText(/'INSTANT'/)).not.toBeInTheDocument()
 })

})
