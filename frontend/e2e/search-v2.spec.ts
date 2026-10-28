import {test,expect} from '@playwright/test'
import {readFileSync,mkdirSync,writeFileSync,existsSync} from 'node:fs'
import {resolve} from 'node:path'

const repo=resolve(import.meta.dirname,'../..'),folder=resolve(repo,'docs/search_v2/screenshots')
const tokenFile=resolve(repo,'tmp/studio-runtime/access-token.txt')
test.use({baseURL:'http://127.0.0.1:8110/app/'})
test('owner sources: fresh OCR, row retrieval, guards, baseline comparison and module MIME',async({page})=>{
 test.skip(process.env.RUN_SEARCH_V2_LIVE!=='1'||!existsSync(tokenFile),'Explicit isolated live Search V2 smoke required')
 const token=readFileSync(tokenFile,'utf-8').replace(/^\uFEFF/,'').trim(),headers={Authorization:'Bearer '+token}
 const fixtures=JSON.parse(readFileSync(resolve(repo,'docs/topic3/final_product/SOURCE_REVIEW_FIXTURES.json'),'utf-8'))
 const hpg=process.env.HPG_PDF||'C:/Users/Admin/Downloads/20260130-hpg-bao-cao-tai-chinh-rieng-cong-ty-me-va-giai-trinh-q4-2025.pdf'
 const bidv=process.env.BIDV_PDF||'C:/Users/Admin/Downloads/20251023+-+BID+-+CBTT+Dieu+chinh+BCTC+2024+theo+ket+qua+KTNN.pdf'
 test.skip(!existsSync(hpg)||!existsSync(bidv),'Original owner PDF sources required')
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));mkdirSync(folder,{recursive:true})
 await page.addInitScript(t=>sessionStorage.setItem('studio-token',t),token)
 await page.goto('/app/#/library')
 for(const [file,issuer,period,type] of [[hpg,'Công ty mẹ Hòa Phát','2025-12-31','Báo cáo tài chính riêng'],[bidv,'BIDV','2024-12-31','Điều chỉnh báo cáo tài chính']]){
  await page.getByLabel('Chọn PDF').setInputFiles(file)
  await page.getByLabel('Doanh nghiệp tài liệu').fill(issuer);await page.getByLabel('Kỳ tài liệu').fill(period)
  await page.getByLabel('Loại báo cáo',{exact:false}).selectOption(type)
  await page.getByRole('button',{name:'Tải lên & lập chỉ mục',exact:true}).click()
  await expect.poll(async()=>{const r=await page.request.get('/studio/documents',{headers,maxRetries:1});const d=(await r.json()).documents.find((d:{issuer:string})=>d.issuer===issuer);if(d?.status==='FAILED')throw new Error('Real ingestion failed: '+d.error_code);return d?.status},{timeout:550000,intervals:[1000,2000]}).toBe('READY')
 }
 const docs=(await (await page.request.get('/studio/documents',{headers})).json()).documents
 // Explicit replay of already visually reviewed source annotations bound to exact raw SHA.
 // This is test setup only; product uploads never auto-certify OCR cells.
 for(const f of fixtures.reviews){
  expect(docs.find((d:{id:string})=>d.id===f.document_id).sha256).toBe(f.source_sha256)
  const e=await (await page.request.get(`/studio/documents/${f.document_id}/pages/${f.page}/evidence`,{headers})).json()
  const row=e.tables.find((r:{cells:{text:string}[]})=>r.cells[f.column_index]?.text===f.source_display)
  expect(row).toBeTruthy()
  const response=await page.request.post(`/studio/documents/${f.document_id}/facts/review`,{headers,data:{page:f.page,row_id:row.id,column_index:f.column_index,metric:f.metric,period:f.period,column_label:f.column_label,statement_scope:f.statement_scope,unit:f.unit,convention:f.convention,basis:f.basis,source_image_reviewed:true}})
  expect(response.status()).toBe(200)
 }
 await page.getByRole('button',{name:'Tìm kiếm tài chính',exact:true}).click()
 await page.getByLabel('Tài liệu tìm kiếm').selectOption('4a92af827aaf1e73e017544d0ff20d0d')
 await page.getByLabel('Cấu hình tìm kiếm').selectOption('production_v2')
 await page.getByLabel('Câu hỏi tìm kiếm').fill('Tổng tài sản của Công ty mẹ Hòa Phát tại ngày 31/12/2025 là bao nhiêu?')
 await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click()
 await expect(page.locator('article.hit').first()).toContainText('98.670.778.691.605',{timeout:30000})
 await expect(page.locator('article.hit').first()).toContainText('Trang PDF 3')
 await page.screenshot({path:folder+'/01-v2-source-row.png',fullPage:true})
 const worker=page.waitForResponse(r=>r.url().includes('pdf.worker')&&r.url().includes('.mjs'))
 await page.getByRole('button',{name:'Mở bằng chứng',exact:false}).first().click()
 await expect(page.getByTestId('pdf-page')).toHaveAttribute('data-rendered','true',{timeout:30000})
 expect((await worker).headers()['content-type']).toMatch(/javascript/)
 await expect(page.locator('.pdf-highlight.verified').first()).toBeVisible()
 await page.screenshot({path:folder+'/02-exact-source-highlight.png',fullPage:true})
 await page.getByRole('button',{name:'Tìm kiếm tài chính',exact:true}).click()
 await page.getByLabel('Câu hỏi tìm kiếm').fill('Tổng tài sản công ty mẹ Hòa Phát năm 2031 là bao nhiêu?')
 await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click()
 await expect(page.getByText('Chưa tìm thấy bằng chứng đủ tin cậy',{exact:true})).toBeVisible()
 await expect(page.getByText('Chọn một kết quả để xem ngữ cảnh.',{exact:true})).toBeVisible()
 await page.screenshot({path:folder+'/03-abstention-no-stale-preview.png',fullPage:true})
 await page.getByRole('button',{name:'Đánh giá & So sánh',exact:true}).click()
 await page.getByLabel('Câu hỏi tìm kiếm').fill('Tổng tài sản của Công ty mẹ Hòa Phát tại ngày 31/12/2025 là bao nhiêu?')
 await page.getByRole('button',{name:'So sánh 3 phương pháp',exact:true}).click()
 await expect(page.getByRole('heading',{name:'Giao nhau và phạm vi đánh giá'})).toBeVisible({timeout:30000})
 await expect(page.getByText('Chạy lại bộ test sau sửa lỗi',{exact:false})).toBeVisible()
 await page.waitForTimeout(1200)
 await page.screenshot({path:folder+'/04-unchanged-baselines-and-benchmark.png',fullPage:true})
 expect(errors).toEqual([])
 const report=await (await page.request.get('/studio/evaluation/search-v2',{headers})).json()
 expect(report.status).toBe('PROVISIONAL_SOURCE_ANNOTATED_NOT_LOCKED')
 const adversarial=await page.request.post('/studio/query',{headers,data:{source:'USER_UPLOADS',document_ids:['4a92af827aaf1e73e017544d0ff20d0d'],mode:'bm25',search_profile:'production_v2',query:'Total assets of Apple separate as of 31/12/2025'}})
 expect((await adversarial.json()).results).toEqual([])
 writeFileSync(resolve(repo,'tmp/react-search-v2/prebuilt-evidence.json'),JSON.stringify({documents:docs,browser_errors:errors,worker_mime:'PASS',source_review_method:'hash-bound replay of visually reviewed7sourcecells;not automatic product verification'},null,2))
})
