import {afterEach,beforeEach,expect,it,vi} from 'vitest'
import {render,screen,cleanup,waitFor} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import SecSourceViewer,{SafeSecEvidence} from './SecSourceViewer'
import type {SecView} from './SecSourceViewer'
import {post} from './api'
vi.mock('./api',()=>({post:vi.fn()}))
beforeEach(()=>{HTMLElement.prototype.scrollIntoView=vi.fn();vi.clearAllMocks()})
afterEach(cleanup)
const data:SecView={status:'VERIFIED_LOCAL_SEC_SNAPSHOT',issuer:'Synthetic issuer',form:'10-Q',accession:'synthetic',report_period:'2026-08-02',source_sha256:'a'.repeat(64),normalized_sha256:'b'.repeat(64),official_url:'https://www.sec.gov/Archives/example.htm',generation:'g',manifest_hash:'m',parent_id:'p',rendering:'SAFE_TEXT_ONLY',warnings:[],excerpt:'',locator:{row:2,column:1},selected_cell:{row:2,column:1,row_label:'Total assets',raw_value:'109,384',period_end:'2026-08-02',unit:'USD',multiplier:'1000000',period_kind:'INSTANT',fact_name:'us-gaap:Assets',header_path:['August 2, 2026'],warnings:[]},table:{id:'t',statement:'Balance sheet',caption:null,section:null,selected_row:2,header_row_count:1,total_source_rows:3,warnings:[],footnotes:[],rows:[{index:0,cells:[{column:0,text:'Metric',colspan:1,rowspan:1},{column:1,text:'August 2, 2026',colspan:1,rowspan:1}]},{index:2,cells:[{column:0,text:'Total assets',colspan:1,rowspan:1},{column:1,text:'109,384',colspan:1,rowspan:1}]}]}}
it('renders source text and exact physical-cell highlight, not active HTML',()=>{
 const unsafe='<script>window.SEC_PWNED=1</script><img src="https://evil.invalid" onerror="alert(1)">&lt;script&gt;'
 const d={...data,excerpt:unsafe,table:{...data.table!,caption:unsafe,rows:[...data.table!.rows,{index:3,cells:[{column:0,text:unsafe,colspan:1,rowspan:1}]}]}}
 const {container}=render(<SafeSecEvidence data={d}/>);expect(screen.getByTestId('sec-selected-cell').textContent).toBe('109,384')
 expect(container.querySelector('script,img,iframe,object')).toBeNull();expect(screen.getByText(unsafe)).toBeTruthy()
 expect(screen.getByRole('link').getAttribute('rel')).toBe('noopener noreferrer')
})
it('never turns a dangerous official URL into a clickable link',()=>{
 render(<SafeSecEvidence data={{...data,official_url:'javascript:alert(1)'}}/>);expect(screen.queryByRole('link')).toBeNull()
})
it('hides stale verified data after a failed source revalidation',async()=>{
 vi.mocked(post).mockResolvedValue(data);const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
 render(<QueryClientProvider client={client}><SecSourceViewer evidence={{text:'',source_reference:'signed-test-reference'}}/></QueryClientProvider>)
 await screen.findByTestId('sec-selected-cell');vi.mocked(post).mockRejectedValue(new Error('SOURCE_HASH_MISMATCH'))
 await client.invalidateQueries({queryKey:['sec-source-view']});await waitFor(()=>expect(screen.queryByTestId('sec-selected-cell')).toBeNull())
 expect(screen.getByRole('alert').textContent).toContain('SOURCE_HASH_MISMATCH')
})
