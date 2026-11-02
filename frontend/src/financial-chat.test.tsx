import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest'
import {render,screen,fireEvent,waitFor,cleanup,act} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import FinancialChat from './FinancialChat'
import {api,post} from './api'
vi.mock('./api',()=>({api:vi.fn(),post:vi.fn()}))
const docs=['a','b'].map(name=>({id:name.repeat(32),filename:name+'.pdf',issuer:name,report_period:'2025',status:'READY',pages:2}))
function show(){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><FinancialChat selected={null} open={()=>{}}/></QueryClientProvider>)}
beforeEach(()=>{sessionStorage.clear();vi.clearAllMocks();vi.mocked(api).mockResolvedValue({documents:docs})})
afterEach(cleanup)
describe('financial chat request and source safety',()=>{
 it('sends no dropdown defaults in ordinary auto mode',async()=>{
  vi.mocked(post).mockResolvedValue({session_id:'c'.repeat(32),status:'SOURCE_EXCERPTS',answer:'Synthetic UI fixture',values:[]})
  show();await screen.findByText('a.pdf · a · 2025')
  fireEvent.change(screen.getByLabelText('Câu hỏi trợ lý'),{target:{value:'Net income 2025?'}})
  fireEvent.click(screen.getByRole('button',{name:'Gửi câu hỏi'}))
  await waitFor(()=>expect(post).toHaveBeenCalled())
  expect(vi.mocked(post).mock.calls[0][1]).toMatchObject({document_ids:['a'.repeat(32)],constraints:{}})
  expect(vi.mocked(post).mock.calls[0][1]).not.toHaveProperty('metric')
 })
 it('discards an old document response after source switch',async()=>{
  let finish:(v:unknown)=>void=()=>{}
  vi.mocked(post).mockImplementation(()=>new Promise(resolve=>{finish=resolve}))
  show();await screen.findByText('a.pdf · a · 2025')
  fireEvent.change(screen.getByLabelText('Câu hỏi trợ lý'),{target:{value:'Question for source A'}})
  fireEvent.click(screen.getByRole('button',{name:'Gửi câu hỏi'}))
  await waitFor(()=>expect(post).toHaveBeenCalled())
  fireEvent.change(screen.getByLabelText('Tài liệu trợ lý'),{target:{value:'b'.repeat(32)}})
  await act(async()=>finish({session_id:'c'.repeat(32),status:'SOURCE_EXCERPTS',answer:'STALE_SOURCE_A',values:[]}))
  expect(screen.queryByText('STALE_SOURCE_A')).not.toBeInTheDocument()
  expect(sessionStorage.getItem('active-document')).toBe('b'.repeat(32))
 })
})
