import {chromium} from '@playwright/test'
import fs from 'node:fs/promises'
const root=new URL('../../',import.meta.url),out=new URL('reports/fis_product_v3/',root)
await fs.mkdir(out,{recursive:true})
const phase=process.argv[2]||'before', token=(await fs.readFile(new URL('tmp/studio-runtime/access-token.txt',root),'utf8')).replace(/^\uFEFF/,'').trim()
const browser=await chromium.launch({headless:true,executablePath:'C:/Users/Admin/AppData/Local/ms-playwright/chromium-1217/chrome-win64/chrome.exe'})
const context=await browser.newContext({viewport:{width:1366,height:768}})
await context.addInitScript(t=>sessionStorage.setItem('studio-token',t),token)
const page=await context.newPage(),traces=[],layouts=[]
page.on('response',async r=>{if(r.url().endsWith('/studio/chat'))traces.push(await r.json())})
await page.goto('http://127.0.0.1:18110/app/#/analysis')
await page.getByLabel('Tài liệu trợ lý',{exact:true}).selectOption('3eb270b22acb7d8d8e9c32a43dc221de')
await page.getByRole('button',{name:'Bắt đầu hội thoại mới',exact:true}).click()
const q='Biên lợi nhuận gộp Services FY2025 cao hơn Products bao nhiêu điểm phần trăm? Nếu dùng phần trăm tăng tương đối thì có giống nhau không?'
await page.getByLabel('Câu hỏi trợ lý',{exact:true}).fill(q)
const response=page.waitForResponse(r=>r.url().endsWith('/studio/chat'),{timeout:150000})
await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();await response
await page.locator('.message-assistant').last().waitFor()
for(const [width,height] of [[1366,768],[1920,1080],[1280,720],[390,844]]){
 await page.setViewportSize({width,height});await page.waitForTimeout(250)
 layouts.push(await page.evaluate(()=>{const r=document.querySelector('.chat-messages').getBoundingClientRect(),c=document.querySelector('.chat-composer').getBoundingClientRect(),app=document.querySelector('.chat-workspace').getBoundingClientRect();return {width:innerWidth,height:innerHeight,zoom:visualViewport.scale,conversation_px:r.height,app_px:app.height,ratio:r.height/app.height,overlap:r.bottom>c.top+1,body_overflow:document.documentElement.scrollHeight>innerHeight+2}}))
 await page.screenshot({path:new URL(`${phase}-chat-${width}.png`,out).pathname.replace(/^\/([A-Z]:)/,'$1')})
}
await fs.writeFile(new URL(`${phase}-browser.json`,out),JSON.stringify({mocked:false,layouts,traces},null,2))
await browser.close();console.log(JSON.stringify(layouts))
