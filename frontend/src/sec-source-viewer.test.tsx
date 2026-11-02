import {afterEach,beforeEach,expect,it,vi} from 'vitest'
import {render,screen,cleanup,waitFor} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import SecSourceViewer,{SafeSecEvidence} from './SecSourceViewer'
import type {SecView} from './SecSourceViewer'
import {post} from './api'
import {sourceAmount,singleSourceAmount} from './source-display'
import {analysisResponseScope} from './analysis-scope'
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
it.each([
 ['109,384','USD','1000000','109.384 triệu USD'],
 ['(125.50)','USD','1000','-125,50 nghìn USD'],
 ['-0.0100','USD','1','-0,0100 USD'],
 ['+125.50','USD','1','+125,50 USD'],
 ['123456789012345678901234567890.12','VND','1','123.456.789.012.345.678.901.234.567.890,12 VND'],
 ['2.400','USD','1000000000','2,400 tỷ USD'],
 ['1,23','USD','1000000',null],['1.234,56','USD','1',null],['12','UNKNOWN','1',null],['12','USD','7',null]
])('formats source strings without changing precision or units: %s', (raw,unit,scale,expected)=>{
 expect(sourceAmount(raw,unit,scale)).toBe(expected)
})
it('distinguishes report end, filing date, instant and raw technical details',()=>{
 render(<SafeSecEvidence data={{...data,filing_date:'2026-08-25',warnings:['PARTIAL_TABLE_EXTRACTION']}}/>)
 expect(screen.getByTestId('sec-selected-value').textContent).toBe('109.384 triệu USD')
 expect(screen.getByText(/Kỳ báo cáo kết thúc: 2026-08-02.*Ngày nộp SEC: 2026-08-25/)).toBeTruthy()
 expect(screen.getByText('Số dư tại ngày: 2026-08-02')).toBeTruthy()
 expect(screen.queryByText(/Kỳ filing/)).toBeNull()
 const diagnostic=screen.getByText('Provenance và locator').closest('details')!
 expect(diagnostic.open).toBe(false);expect(diagnostic.textContent).toContain('PARTIAL_TABLE_EXTRACTION')
 expect(screen.getByText(/Một số bảng trong báo cáo chưa được trích xuất đầy đủ/)).toBeTruthy()
})
it('shows a duration range without substituting fiscal or filing dates',()=>{
 render(<SafeSecEvidence data={{...data,selected_cell:{...data.selected_cell!,period_kind:'DURATION',period_start:'2026-07-01',period_end:'2026-09-30'}}}/>)
 expect(screen.getByText('Kỳ phát sinh: 2026-07-01 → 2026-09-30')).toBeTruthy()
})
it('only formats an extracted answer when its exact source operand agrees',()=>{
 const cells=[{raw_value:'109,384',unit:'USD',multiplier:'1000000',effective_value:'109384000000'}]
 expect(singleSourceAmount(['109384000000'],'USD',cells)).toBe('109.384 triệu USD')
 expect(singleSourceAmount(['7'],'USD',cells)).toBeNull()
 expect(singleSourceAmount(['109384000000'],'VND',cells)).toBeNull()
 expect(singleSourceAmount(['109384000000'],'USD',[...cells,...cells])).toBeNull()
})
it('keeps SEC history independent of unrelated PDF selection while enforcing its own scope',()=>{
 const a={question:'Total assets?',operation:'EXTRACT',document_ids:['pdf-a']},b={...a,document_ids:['pdf-b']}
 expect(analysisResponseScope('SEC',a,'HD')).toBe(analysisResponseScope('SEC',b,'HD'))
 expect(analysisResponseScope('SEC',a,'HD')).not.toBe(analysisResponseScope('SEC',a,'PG'))
 expect(analysisResponseScope('SEC',a,'HD')).not.toBe(analysisResponseScope('SEC',{...a,operation:'ABS_CHANGE'},'HD'))
 expect(analysisResponseScope('PDF',a,'')).not.toBe(analysisResponseScope('PDF',b,''))
})
it('uses the verified signed Decimal when iXBRL sign is not printed in the raw cell',()=>{
 render(<SafeSecEvidence data={{...data,selected_cell:{...data.selected_cell!,raw_value:'125',value:'-125',effective_value:'-125000000'}}}/>)
 expect(screen.getByTestId('sec-selected-value').textContent).toBe('-125 triệu USD')
})
