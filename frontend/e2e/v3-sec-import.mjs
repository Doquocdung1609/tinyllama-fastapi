import {chromium} from '@playwright/test'
import fs from 'node:fs/promises'
const root=new URL('../../',import.meta.url),out=new URL('reports/fis_product_v3/',root)
const token=(await fs.readFile(new URL('tmp/studio-runtime/access-token.txt',root),'utf8')).replace(/^\uFEFF/,'').trim()
const browser=await chromium.launch({headless:true,executablePath:'C:/Users/Admin/AppData/Local/ms-playwright/chromium-1217/chrome-win64/chrome.exe'})
const page=await browser.newPage({viewport:{width:1366,height:768}});await page.addInitScript(t=>sessionStorage.setItem('studio-token',t),token)
const traces=[];page.on('response',async r=>{if(r.url().includes('/studio/sec/library')&&!r.url().endsWith('/contact'))traces.push({url:r.url(),status:r.status(),body:await r.json()})})
await page.goto('http://127.0.0.1:18110/app/#/library');await page.getByRole('button',{name:'Hồ sơ SEC',exact:true}).click()
await page.getByLabel('Tìm công ty SEC').fill('PG')
const search=page.waitForResponse(r=>r.url().includes('/sec/library/discover'),{timeout:100000});await page.getByRole('button',{name:'Tìm trên EDGAR',exact:true}).click();const result=await search
let added=null
if(result.ok()){
 const body=await result.json();const target=body.filings[1];
 if(target){const wait=page.waitForResponse(r=>r.url().endsWith('/sec/library/import'));await page.locator('article').filter({hasText:target.accession_number}).getByRole('button',{name:'Thêm vào kho SEC',exact:true}).click();added=await (await wait).json()}
}
await page.screenshot({path:new URL('sec-discovery-import.png',out).pathname.replace(/^\/([A-Z]:)/,'$1'),fullPage:true})
await fs.writeFile(new URL('sec-browser-import.json',out),JSON.stringify({mocked:false,added,traces},null,2));console.log(JSON.stringify({status:result.status(),added}));await browser.close()
