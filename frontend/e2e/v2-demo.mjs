import {chromium,expect} from '@playwright/test'
import fs from 'node:fs/promises'
import {fileURLToPath} from 'node:url'
const root=new URL('../../',import.meta.url),out=new URL('reports/faith_r_product_v2/',root)
const token=(await fs.readFile(new URL('tmp/studio-runtime/access-token.txt',root),'utf8')).replace(/^\uFEFF/,'').trim()
const browser=await chromium.launch({headless:true,executablePath:'C:/Users/Admin/AppData/Local/ms-playwright/chromium-1217/chrome-win64/chrome.exe'})
const context=await browser.newContext({viewport:{width:1366,height:768}});await context.addInitScript(token=>sessionStorage.setItem('studio-token',token),token)
const page=await context.newPage(),checks=[],errors=[],traces=[]
page.on('pageerror',e=>errors.push(e.message))
page.on('response',async r=>{if(/\/studio\/(chat$|query$|compare$)/.test(r.url())){let body;try{body=await r.json()}catch{}traces.push({url:r.url(),status:r.status(),body})}})
const screenshot=async name=>page.screenshot({path:fileURLToPath(new URL(name+'.png',out))})
const check=(name,data)=>checks.push({name,status:'PASS',...data})
async function ask(q){
 const promise=page.waitForResponse(r=>r.url().endsWith('/studio/chat')&&r.request().method()==='POST',{timeout:180000})
 await page.getByLabel('Câu hỏi trợ lý',{exact:true}).fill(q);await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click()
 const response=await promise;expect(response.status()).toBe(200);const body=await response.json()
 await expect(page.getByLabel('Câu hỏi trợ lý',{exact:true})).toHaveValue('');await expect(page.locator('.message-assistant').last()).toContainText(body.answer.slice(0,35));return body
}
async function choose(id){await page.getByLabel('Tài liệu trợ lý',{exact:true}).selectOption(id)}
async function source(button,expectedPage,name){
 await button.first().click();await expect(page.getByLabel('Đến trang PDF',{exact:true})).toHaveValue(String(expectedPage))
 await expect(page.getByTestId('pdf-page')).toHaveAttribute('data-rendered','true',{timeout:90000})
 const boxes=await page.getByTestId('source-highlight').evaluateAll(nodes=>nodes.map(n=>({class:n.className,left:parseFloat(n.style.left),top:parseFloat(n.style.top),width:parseFloat(n.style.width),height:parseFloat(n.style.height)})))
 expect(boxes.length).toBeGreaterThan(0);expect(boxes.every(b=>b.width>0&&b.height>0&&b.left>=0&&b.top>=0)).toBe(true)
 const notice=await page.locator('.kv').innerText();check(name,{page:expectedPage,boxes,notice});await screenshot(name)
}
try{
 await page.goto('http://127.0.0.1:18110/app/#/analysis')
 await choose('2bed2b3c312c8149e6a2ff6ab80c694a')
 let a=await ask('Tìm dòng lợi nhuận sau thuế chưa phân phối năm 2024.');expect(a.citations.map(c=>c.page)).toEqual([4,7]);check('BIDV row locations',{answer:a.answer})
 a=await ask('Hai mức điều chỉnh của riêng ngân hàng và hợp nhất chênh lệch bao nhiêu?');expect(a.values).toEqual(['1114']);expect(a.independent_verification.status).toBe('VERIFIED')
 await page.locator('.message-assistant').last().getByText('Các bước tính · Đã kiểm chứng độc lập',{exact:true}).click();await screenshot('after-bidv-desktop');check('BIDV direct Decimal answer',{session_id:a.session_id})
 await source(page.locator('.message-assistant').last().getByRole('button',{name:'Mở nguồn 2 trang 4',exact:true}),4,'bidv-page4-cell')
 await page.getByLabel('Tỷ lệ PDF',{exact:true}).selectOption('1.25');await expect(page.getByTestId('pdf-page')).toHaveAttribute('data-rendered','true');check('PDF zoom',{zoom:1.25})
 await page.getByLabel('Xoay trang 90 độ',{exact:true}).click();await expect(page.getByTestId('pdf-page')).toHaveAttribute('data-rendered','true');check('PDF rotation',{rotation:90})
 await page.getByRole('button',{name:'Quay lại câu hỏi',exact:true}).click();await expect(page.locator('.message-assistant').last()).toContainText('1.114')
 await source(page.locator('.message-assistant').last().getByRole('button',{name:'Mở nguồn 1 trang 7',exact:true}),7,'bidv-page7-cell')
 await page.getByRole('button',{name:'Quay lại câu hỏi',exact:true}).click()
 await page.getByLabel('Đổi tên hội thoại',{exact:true}).click();await page.getByLabel('Tên hội thoại',{exact:true}).fill('V2 Browser · BIDV source demo');await page.getByRole('button',{name:'Lưu tên',exact:true}).click()
 await page.reload();await expect(page.locator('.message-assistant').last()).toContainText('1.114');check('Reload durable renamed session',{session_id:a.session_id})
 await choose('4a92af827aaf1e73e017544d0ff20d0d');expect(await page.locator('.message-assistant').count()).toBe(0)
 a=await ask('Đây là báo cáo tài chính riêng công ty mẹ hay báo cáo hợp nhất? Hãy dẫn trang nguồn.');expect(a.answer_status).toBe('SOURCE_SUPPORTED_NON_NUMERIC');expect(a.answer).toContain('riêng');await screenshot('after-hpg-identity-desktop')
 a=await ask('Lợi nhuận sau thuế của công ty mẹ Hòa Phát quý IV năm 2025 là bao nhiêu?');expect(a.values).toEqual([]);expect(a.answer_status).toBe('REQUIRES_SOURCE_REVIEW');check('HPG honest OCR limitation',{answer:a.answer})
 await source(page.locator('.message-assistant').last().getByRole('button',{name:/Mở nguồn 1 trang 5/}).first(),5,'hpg-page5-ocr-warning')
 await expect(page.getByText('Highlight chưa xác minh:',{exact:false}).first()).toBeVisible();await page.getByRole('button',{name:'Quay lại câu hỏi',exact:true}).click()
 await choose('3eb270b22acb7d8d8e9c32a43dc221de');expect(await page.locator('.message-assistant').count()).toBe(0)
 a=await ask("What were Apple's FY2025 total net sales?");expect(a.values).toEqual(['416161'])
 a=await ask('And in FY2024? How much did it grow in dollars and percent?');expect(a.values).toEqual(['25126','6.43'])
 await page.locator('.message-assistant').last().getByText('Các bước tính · Đã kiểm chứng độc lập',{exact:true}).click();await screenshot('after-apple-desktop')
 await source(page.locator('.message-assistant').last().getByRole('button',{name:'Mở nguồn 1 trang 32',exact:true}).first(),32,'apple-page32-cell')
 await page.getByRole('button',{name:'Quay lại câu hỏi',exact:true}).click();await page.setViewportSize({width:390,height:844});await expect(page.getByRole('button',{name:'Mở điều hướng',exact:true})).toBeVisible();await expect(page.locator('.sidebar')).not.toBeInViewport();await page.locator('.message-assistant').last().scrollIntoViewIfNeeded();await screenshot('after-apple-mobile')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);check('Mobile 390 layout',{width:390})
 await page.setViewportSize({width:1366,height:768});await page.getByRole('button',{name:'Bằng chứng & Nguồn',exact:true}).click()
 await page.getByLabel('Tài liệu tìm kiếm',{exact:true}).first().selectOption('2bed2b3c312c8149e6a2ff6ab80c694a')
 await page.getByLabel('Câu hỏi tìm kiếm',{exact:true}).first().fill('Tìm dòng lợi nhuận sau thuế chưa phân phối năm 2024.')
 let response=page.waitForResponse(r=>r.url().endsWith('/studio/query')&&r.request().method()==='POST',{timeout:180000});await page.getByRole('button',{name:'Tìm kiếm',exact:true}).first().click();let s=await (await response).json();expect(s.financial_evidence.citations.map(c=>c.page)).toEqual([4,7]);await screenshot('after-search')
 await page.getByRole('button',{name:'Hỏi về nguồn này',exact:true}).first().click();await expect(page.getByText(/Đoạn đang xem · trang 4/)).toBeVisible();check('Search to Chat source handoff',{page:4})
 await page.getByRole('button',{name:'Research Lab',exact:true}).click();await page.getByLabel('Cấu hình tìm kiếm',{exact:true}).selectOption('auto');await page.getByLabel('Nguồn dữ liệu',{exact:true}).selectOption('USER_UPLOADS');await page.getByLabel('Tài liệu tìm kiếm',{exact:true}).selectOption('2bed2b3c312c8149e6a2ff6ab80c694a');await page.getByLabel('Câu hỏi tìm kiếm',{exact:true}).fill('Tìm dòng lợi nhuận sau thuế chưa phân phối năm 2024.')
 response=page.waitForResponse(r=>r.url().endsWith('/studio/compare'),{timeout:180000});await page.getByRole('button',{name:'So sánh 3 phương pháp',exact:true}).click();const lab=await (await response).json();expect(Object.keys(lab.arms)).toEqual(['bm25','dense','hybrid']);expect(lab.quality_metrics).toBeNull();expect(lab.candidate.financial_evidence.citations.map(c=>c.page)).toEqual([4,7]);await screenshot('after-research-lab');check('Live baseline and FAITH-R Lab',{generation:lab.generation,candidate:lab.candidate.search_profile})
 await page.setViewportSize({width:390,height:844});await expect(page.locator('.sidebar')).not.toBeInViewport();await page.locator('.compare-col').first().scrollIntoViewIfNeeded();await screenshot('after-research-lab-mobile');check('Mobile Research Lab',{width:390})
 expect(errors).toEqual([])
}catch(e){checks.push({name:'Browser execution',status:'FAIL',error:String(e)});await screenshot('browser-failure');throw e}
finally{await fs.writeFile(new URL('browser-demo.json',out),JSON.stringify({mocked:false,browser:'Chromium 1217 via repository Playwright',checks,page_errors:errors,traces},null,2));await browser.close();console.log(JSON.stringify({checks:checks.length,failures:checks.filter(c=>c.status==='FAIL')}))}
