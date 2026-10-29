import {test,expect} from '@playwright/test'
import {readFileSync,existsSync,mkdirSync} from 'node:fs'
import {resolve} from 'node:path'

const repo=resolve(import.meta.dirname,'../..'),folder=resolve(repo,'docs/search_v3r2/screenshots')
test.use({actionTimeout:30000,baseURL:'http://127.0.0.1:8110/app/',channel:'chrome'})
test('Prebuilt V3R2: source cell, related-only retrieval, same-scope comparison and stale response',async({page})=>{
 const tokenPath=resolve(repo,'tmp/studio-runtime/access-token.txt')
 test.skip(process.env.RUN_SEARCH_V3R2_LIVE!=='1'||!existsSync(tokenPath),'Explicit owned V3 live run required')
 const token=readFileSync(tokenPath,'utf-8').replace(/^\uFEFF/,'').trim()
 const headers={Authorization:'Bearer '+token};mkdirSync(folder,{recursive:true})
 await expect.poll(async()=>{const r=await page.request.get('/studio/search-preparation',{headers});return (await r.json()).status},{timeout:180000}).toBe('READY')
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message))
 await page.addInitScript(t=>{sessionStorage.clear();sessionStorage.setItem('studio-token',t)},token)
 await page.goto('/app/#/search')
 const docs=(await (await page.request.get('/studio/documents',{headers})).json()).documents
 const doc=docs.find((d:{issuer:string})=>d.issuer==='CEO Group');expect(doc?.status).toBe('READY')
 await page.getByLabel('Tài liệu tìm kiếm',{exact:true}).selectOption(doc.id)
 await page.getByLabel('Cấu hình tìm kiếm').selectOption('production_v3r2')
 await page.getByLabel('Câu hỏi tìm kiếm').fill('Tổng tài sản CEO hợp nhất ngày 31/12/2025')
 await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click()
 await expect(page.locator('article.hit').first()).toContainText('8.728.184.945.992',{timeout:60000})
 await expect(page.locator('article.hit').first()).toContainText('Trang PDF 2')
 await page.screenshot({path:folder+'/01-reviewed-source-row.png',fullPage:true})
 const worker=page.waitForResponse(r=>r.url().includes('pdf.worker')&&r.url().includes('.mjs'))
 await page.getByRole('button',{name:'Mở bằng chứng',exact:false}).first().click()
 await expect(page.getByTestId('pdf-page')).toHaveAttribute('data-rendered','true',{timeout:60000})
 expect((await worker).headers()['content-type']).toMatch(/javascript/)
 await expect(page.locator('.pdf-highlight.verified').first()).toBeVisible()
 await page.screenshot({path:folder+'/02-source-highlight.png',fullPage:true})
 await page.getByRole('button',{name:'Tìm kiếm tài chính',exact:true}).click()
 await page.getByLabel('Câu hỏi tìm kiếm').fill('Tổng tài sản CEO hợp nhất năm 2037')
 await expect(page.getByText('Chọn một kết quả để xem ngữ cảnh.',{exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click()
 await expect(page.locator('article.hit').first()).toBeVisible({timeout:60000})
 await expect(page.getByText('Chưa tìm thấy bằng chứng đủ tin cậy',{exact:true})).toBeVisible()
 await expect(page.locator('article.hit').first()).not.toContainText('Bằng chứng ô đã đối chiếu, phù hợp yêu cầu')
 await page.screenshot({path:folder+'/03-related-not-numeric-answer.png',fullPage:true})
 await page.getByRole('button',{name:'Đánh giá & So sánh',exact:true}).click()
 await page.getByLabel('Câu hỏi tìm kiếm').fill('Tổng tài sản CEO hợp nhất ngày 31/12/2025')
 await page.getByRole('button',{name:'So sánh 3 phương pháp',exact:true}).click()
 await expect(page.getByRole('heading',{name:'Search V3 · cùng câu hỏi và phạm vi'})).toBeVisible({timeout:60000})
 await page.screenshot({path:folder+'/04-eight-arm-protocol-and-live-comparison.png',fullPage:true})
 await page.getByRole('button',{name:'Tìm kiếm tài chính',exact:true}).click()
 // Hold a real response, change the query, then deliver it: it must not repopulate old evidence.
 let release!:()=>void,seen!:()=>void
 const held=new Promise<void>(r=>release=r),observed=new Promise<void>(r=>seen=r)
 await page.route('**/studio/query',async route=>{const response=await route.fetch();seen();await held;await route.fulfill({response})})
 await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click();await observed
 await page.getByLabel('Câu hỏi tìm kiếm').fill('Câu hỏi mới chưa thực thi')
 release();await expect(page.getByRole('button',{name:'Tìm kiếm',exact:true})).toBeEnabled()
 await expect(page.locator('article.hit')).toHaveCount(0)
 await expect(page.getByText('Chọn một kết quả để xem ngữ cảnh.',{exact:true})).toBeVisible()
 await page.screenshot({path:folder+'/05-stale-response-rejected.png',fullPage:true})
 expect(errors).toEqual([])
})

test('Prebuilt V3R2: a matching unreviewed row is a candidate, not reviewed evidence',async({page})=>{
 const tokenPath=resolve(repo,'tmp/studio-runtime/access-token.txt')
 test.skip(process.env.RUN_SEARCH_V3R2_LIVE!=='1'||!existsSync(tokenPath),'Explicit owned V3 live run required')
 const token=readFileSync(tokenPath,'utf-8').replace(/^\uFEFF/,'').trim()
 await page.addInitScript(t=>{sessionStorage.clear();sessionStorage.setItem('studio-token',t)},token)
 await page.goto('/app/#/search')
 const response=await page.request.get('/studio/documents',{headers:{Authorization:'Bearer '+token}})
 const doc=(await response.json()).documents.find((d:{issuer:string})=>d.issuer==='CEO Group')
 await page.getByLabel('Tài liệu tìm kiếm',{exact:true}).selectOption(doc.id)
 await page.getByLabel('Cấu hình tìm kiếm').selectOption('production_v3r2')
 await page.getByLabel('Câu hỏi tìm kiếm').fill('Tiền và các khoản tương đương tiền CEO hợp nhất ngày 31/12/2025')
 await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click()
 await expect(page.locator('article.hit').first()).toContainText('Dòng chỉ tiêu phù hợp; số liệu chưa xác minh',{timeout:60000})
 await page.screenshot({path:folder+'/06-candidate-row-not-reviewed.png',fullPage:true})
})


test('Prebuilt V3R2: mixed-PDF SEM recovery and persistent coverage warning',async({page})=>{
 const tokenPath=resolve(repo,'tmp/studio-runtime/access-token.txt')
 test.skip(process.env.RUN_SEARCH_V3R2_LIVE!=='1'||!existsSync(tokenPath),'Owned V3R live run required')
 const token=readFileSync(tokenPath,'utf-8').replace(/^\uFEFF/,'').trim()
 await page.addInitScript(t=>{sessionStorage.clear();sessionStorage.setItem('studio-token',t)},token)
 const docs=(await (await page.request.get('/studio/documents',{headers:{Authorization:'Bearer '+token}})).json()).documents
 const sem=docs.find((d:{issuer:string})=>d.issuer==='Samsung Electro-Mechanics');expect(sem).toBeTruthy()
 await page.goto('/app/#/search')
 await page.getByLabel('Nguồn dữ liệu').selectOption('USER_UPLOADS')
 await page.getByLabel('Tài liệu tìm kiếm',{exact:true}).selectOption(sem.id)
 await page.getByLabel('Cấu hình tìm kiếm').selectOption('production_v3r2')
 await page.getByLabel('Câu hỏi tìm kiếm').fill('Total assets Samsung Electro-Mechanics consolidated December 31, 2025')
 await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click()
 await expect(page.locator('article.hit').first()).toContainText('14,595895.255468',{timeout:60000})
 await expect(page.getByText('Chưa tìm thấy bằng chứng đủ tin cậy',{exact:true})).toBeVisible()
 await page.locator('article.hit').first().locator('summary').click();await expect(page.locator('article.hit').first()).toContainText('Dấu phân cách cần kiểm tra');await expect(page.locator('article.hit').first()).toContainText('KRW');await page.screenshot({path:folder+'/07-sem-recovered-unreviewed.png',fullPage:true})
 await page.getByRole('button',{name:'Mở bằng chứng',exact:false}).first().click()
 await expect(page.getByTestId('pdf-page')).toHaveAttribute('data-rendered','true',{timeout:60000})
 await expect(page.getByLabel('Lớp chữ OCR có thể chọn')).toBeVisible()
 await expect(page.getByText('Lớp chữ PDF + OCR theo vùng · số liệu ứng viên cần đối chiếu')).toBeVisible()
 await page.screenshot({path:folder+'/08-sem-original-source.png',fullPage:true})
 await page.getByRole('button',{name:'Kho tài liệu',exact:true}).click();await page.getByLabel('Tài liệu theo dõi').selectOption(sem.id)
 await expect(page.getByText('Cảnh báo độ phủ trích xuất').first()).toBeVisible()
 await expect(page.getByText(/Trang hoàn tất 88\/88/)).toBeVisible({timeout:60000})
 await page.screenshot({path:folder+'/09-real-coverage-warning.png',fullPage:true})
})

 test('Prebuilt V3R2: ACB repairs and bounded PDF navigation',async({page})=>{
 const tokenPath=resolve(repo,'tmp/studio-runtime/access-token.txt');test.skip(process.env.RUN_SEARCH_V3R2_LIVE!=='1'||!existsSync(tokenPath),'Owned R2 run required');
 const token=readFileSync(tokenPath,'utf-8').replace(/^\uFEFF/,'').trim();const headers={Authorization:'Bearer '+token};
 await page.addInitScript(t=>{sessionStorage.clear();sessionStorage.setItem('studio-token',t)},token);
 const docs=(await (await page.request.get('/studio/documents',{headers})).json()).documents;
 const acb=docs.find((d:{issuer:string})=>d.issuer==='Asia Commercial Bank ACB');expect(acb).toBeTruthy();
 await page.goto('/app/#/search');await page.getByLabel('Nguồn dữ liệu').selectOption('USER_UPLOADS');
 await page.getByLabel('Tài liệu tìm kiếm',{exact:true}).selectOption(acb.id);await page.getByLabel('Cấu hình tìm kiếm').selectOption('production_v3r2');
 for(const [query,value] of [['Owners equity ACB consolidated December 31, 2022','58,438,663'],['Profit before tax ACB consolidated full year 2022','17,114,208'],['Profit after tax ACB consolidated full year 2022','13,688,193']]){
 await page.getByLabel('Câu hỏi tìm kiếm').fill(query);await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click();
 await expect(page.locator('article.hit').filter({hasText:value}).first()).toBeVisible({timeout:60000});
 await expect(page.locator('article.hit').first()).not.toContainText('Bằng chứng ô đã đối chiếu, phù hợp yêu cầu');
 }
 await page.locator('article.hit').first().locator('summary').click();await expect(page.locator('article.hit').first()).toContainText('VND million');await expect(page.locator('article.hit').first()).toContainText('Cần đối chiếu ảnh nguồn');await page.screenshot({path:folder+'/10-acb-repaired-original-values.png',fullPage:true});
 await page.getByRole('button',{name:'Mở bằng chứng',exact:false}).first().click();await expect(page.getByTestId('pdf-page')).toHaveAttribute('data-rendered','true',{timeout:60000});
 await page.screenshot({path:folder+'/11-acb-original-pdf.png',fullPage:true});
 for(let i=0;i<10;i++){
 await page.getByRole('button',{name:'Trang sau',exact:true}).click();await expect(page.getByTestId('pdf-page')).toHaveAttribute('data-rendered','true',{timeout:60000});
 await page.getByRole('button',{name:'Trang trước',exact:true}).click();await expect(page.getByTestId('pdf-page')).toHaveAttribute('data-rendered','true',{timeout:60000});
 }
 await page.screenshot({path:folder+'/12-after-twenty-page-transitions.png',fullPage:true});
 const status=await page.request.get('/studio/resource-status',{headers});expect(status.ok()).toBeTruthy();expect((await status.json()).max_active_observed).toBeLessThanOrEqual(1);
 });
