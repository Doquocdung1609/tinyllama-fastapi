import {chromium,expect} from '@playwright/test'
import fs from 'node:fs/promises'
import {fileURLToPath} from 'node:url'
const root=new URL('../../',import.meta.url),out=new URL('reports/fis_product_v3/',root),before=JSON.parse(await fs.readFile(new URL('before.json',out),'utf8'))
const token=(await fs.readFile(new URL('tmp/studio-runtime/access-token.txt',root),'utf8')).replace(/^\uFEFF/,'').trim()
const browser=await chromium.launch({headless:true,executablePath:'C:/Users/Admin/AppData/Local/ms-playwright/chromium-1217/chrome-win64/chrome.exe'})
const page=await browser.newPage({viewport:{width:1366,height:768}});await page.addInitScript(t=>sessionStorage.setItem('studio-token',t),token)
const checks=[],traces=[]
const expected=[['-2575','-3.85'],['64377'],['26.23'],['38.60','104.89'],['151790','178353','26563']]
try{
 await page.goto('http://127.0.0.1:18110/app/#/analysis');await page.getByLabel('Tài liệu trợ lý',{exact:true}).selectOption('3eb270b22acb7d8d8e9c32a43dc221de')
 for(let i=0;i<5;i++){
  await page.getByRole('button',{name:'Bắt đầu hội thoại mới',exact:true}).click();await page.getByLabel('Câu hỏi trợ lý',{exact:true}).fill(before.records[i].request.question)
  const pending=page.waitForResponse(r=>r.url().endsWith('/studio/chat'),{timeout:180000});await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();const response=await pending,r=await response.json();traces.push({id:'A'+(i+1),http:response.status(),response:r})
  expect(r.values).toEqual(expected[i]);expect(r.semantic_question_coverage.status).toBe('COMPLETE');await expect(page.locator('.message-assistant').last()).toContainText(r.answer.slice(0,30));checks.push({id:'A'+(i+1),status:'PASS',values:r.values})
  await page.screenshot({path:fileURLToPath(new URL(`core-A${i+1}-1366.png`,out))})
  if(i===0){await page.setViewportSize({width:1920,height:1080});await page.screenshot({path:fileURLToPath(new URL('core-A1-1920.png',out))});await page.setViewportSize({width:1366,height:768})}
  if(i===2){
   for(let j=0;j<r.citations.length;j++){
    const c=r.citations[j];await page.locator('.message-assistant').last().getByRole('button',{name:`Mở nguồn ${j+1} trang ${c.page}`,exact:true}).first().click();await page.getByRole('dialog').getByRole('button',{name:`Mở trang nguồn ${c.page}`,exact:true}).click();await expect(page.getByLabel('Đến trang PDF',{exact:true})).toHaveValue(String(c.page));await expect(page.getByTestId('pdf-page')).toHaveAttribute('data-rendered','true',{timeout:90000});expect(await page.getByTestId('source-highlight').count()).toBeGreaterThan(0);await page.screenshot({path:fileURLToPath(new URL(`core-A3-source-${j+1}-page-${c.page}.png`,out))});checks.push({id:'A3-citation-'+(j+1),status:'PASS',page:c.page});await page.getByRole('button',{name:'Quay lại câu hỏi',exact:true}).click()
   }
  }
  if(i===3){await page.locator('.calculation-details').last().getByText('Các bước tính · Đã kiểm chứng độc lập',{exact:true}).click();await expect(page.locator('.calculation-details').last()).toContainText('104,89');await page.screenshot({path:fileURLToPath(new URL('core-A4-verified-math.png',out))});checks.push({id:'A4-expand-calculation',status:'PASS'})}
 }
}catch(e){checks.push({id:'core-browser',status:'FAIL',error:String(e)});await page.screenshot({path:fileURLToPath(new URL('core-browser-failure.png',out))});throw e}
finally{await fs.writeFile(new URL('core-browser.json',out),JSON.stringify({mocked:false,zoom:1,checks,traces},null,2));await browser.close();console.log(JSON.stringify(checks))}
