import {chromium,expect} from '@playwright/test'
import fs from 'node:fs/promises'
import {fileURLToPath} from 'node:url'
const root=new URL('../../',import.meta.url),out=new URL('reports/fis_product_v3/',root)
const token=(await fs.readFile(new URL('tmp/studio-runtime/access-token.txt',root),'utf8')).replace(/^\uFEFF/,'').trim()
const browser=await chromium.launch({headless:true,executablePath:'C:/Users/Admin/AppData/Local/ms-playwright/chromium-1217/chrome-win64/chrome.exe'})
const context=await browser.newContext({viewport:{width:1366,height:768}});await context.addInitScript(t=>sessionStorage.setItem('studio-token',t),token)
const page=await context.newPage(),traces=[],checks=[]
page.on('response',async r=>{if(/\/studio\/(chat|query|sec\/evidence)$/.test(r.url()))traces.push({url:r.url(),http:r.status(),body:await r.json()})})
try{
 await page.goto('http://127.0.0.1:18110/app/#/library');await page.getByRole('button',{name:'Hồ sơ SEC',exact:true}).click()
 await expect(page.getByRole('heading',{name:'Kho SEC · 4 filing sẵn sàng'})).toBeVisible()
 await page.locator('article').filter({hasText:'2026-03-31'}).getByRole('button',{name:'Hỏi báo cáo này',exact:true}).click()
 await expect(page.getByLabel('Tài liệu trợ lý',{exact:true})).toHaveValue('SEC:sec:0000080424:0000080424-26-000060')
 const q='PG net sales for the three months ended March 31, 2026'
 await page.getByLabel('Câu hỏi trợ lý',{exact:true}).fill(q)
 const pending=page.waitForResponse(r=>r.url().endsWith('/studio/chat'),{timeout:180000});await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();const r=await (await pending).json()
 expect(r.values).toEqual(['21235000000']);await expect(page.locator('.message-assistant').last()).toContainText('21,235,000,000 USD');checks.push({name:'Imported PG direct numeric answer',status:'PASS',values:r.values})
 await page.screenshot({path:fileURLToPath(new URL('sec-imported-chat.png',out))})
 await page.locator('.message-assistant').last().getByRole('button',{name:/Mở nguồn 1 trang/}).first().click();await expect(page.getByRole('dialog')).toContainText('HTML/iXBRL')
 await page.getByRole('dialog').getByRole('button',{name:/Mở trang nguồn/}).click()
 await expect(page.locator('.sec-selected-cell')).toContainText('21,235',{timeout:120000});checks.push({name:'Signed SEC citation opens original HTML row/cell',status:'PASS'})
 await page.screenshot({path:fileURLToPath(new URL('sec-imported-html-highlight.png',out))})
 await page.getByRole('button',{name:'Quay lại câu hỏi',exact:true}).click();await expect(page.locator('.message-assistant').last()).toContainText('21,235,000,000');checks.push({name:'SEC citation return preserves conversation',status:'PASS'})
 await page.getByRole('button',{name:'Bằng chứng & Nguồn',exact:true}).first().click();await page.getByLabel('Nguồn dữ liệu',{exact:true}).selectOption('US_SEC');await page.getByLabel('Tài liệu SEC tìm kiếm').selectOption('sec:0000080424:0000080424-26-000060');await page.getByLabel('Câu hỏi tìm kiếm',{exact:true}).fill(q);await page.getByRole('button',{name:'FAITH-R',exact:true}).click()
 const found=page.waitForResponse(r=>r.url().endsWith('/studio/query'),{timeout:180000});await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click();const results=await (await found).json();expect(results.results.length).toBeGreaterThan(0);expect(results.results.every(h=>h.filing_id==='sec:0000080424:0000080424-26-000060')).toBe(true);checks.push({name:'Search selects exact imported filing',status:'PASS',returned_count:results.returned_count})
 await page.screenshot({path:fileURLToPath(new URL('sec-imported-search.png',out))})
}catch(e){checks.push({name:'SEC live browser',status:'FAIL',error:String(e)});await page.screenshot({path:fileURLToPath(new URL('sec-browser-failure.png',out))});throw e}
finally{await fs.writeFile(new URL('sec-browser-viewer.json',out),JSON.stringify({mocked:false,checks,traces},null,2));await browser.close();console.log(JSON.stringify(checks))}
