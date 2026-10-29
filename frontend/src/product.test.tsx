import {describe,it,expect,vi,afterEach} from 'vitest'
import {render,screen,cleanup} from '@testing-library/react'
import {Highlight,formatDecimal} from './Studio'
import {api,ApiError,citation} from './api'
import {rotatedBox} from './geometry'
afterEach(()=>{cleanup();vi.unstubAllGlobals();sessionStorage.clear()})
describe('Vietnamese financial presentation integrity',()=>{
 it('rotates only measured source rectangles, preserving original page geometry',()=>{
  expect(rotatedBox([30,240,80,280],90,200,300)).toEqual([20,30,60,80])
  expect(rotatedBox([20,30,60,80],180,200,300)).toEqual([140,220,180,270])
 })
 it('preserves large Decimal strings and never rounds by JS Number',()=>{
  expect(formatDecimal('2760906964000000000000000000')).toBe('2.760.906.964.000.000.000.000.000.000')
  expect(formatDecimal('-1234.56')).toBe('-1.234,56')
 })
 it('highlights source text without interpreting markup',()=>{
  const {container}=render(<Highlight text={'Tài sản <img src=x onerror=alert(1)>'} query={'Tài <img'}/>)
  expect(container.querySelector('img')).toBeNull()
  expect(screen.getByText('Tài')).toBeInTheDocument()
 })
 it('keeps actual PDF page and source hash in citations',()=>{
  expect(citation({text:'Tổng tài sản',page:6,issuer:'BIDV',source_sha256:'fixture-hash'})).toContain('trang PDF 6')
  expect(citation({text:'SEC excerpt'})).toContain('SEC HTML')
 })
 it('sends auth header, never a token in the URL',async()=>{
  sessionStorage.setItem('studio-token','fixture-session-token')
  const mock=vi.fn().mockResolvedValue({ok:true,json:async()=>({status:'READY'})});vi.stubGlobal('fetch',mock)
  await api('/documents')
  expect(mock.mock.calls[0][0]).toBe('/studio/documents')
  expect(mock.mock.calls[0][1].headers.Authorization).toBe('Bearer fixture-session-token')
 })
 it('keeps authentication failures distinct from empty results',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:401,json:async()=>({detail:{code:'STUDIO_UNAUTHORIZED'}})}))
  await expect(api('/documents')).rejects.toBeInstanceOf(ApiError)
 })
})
