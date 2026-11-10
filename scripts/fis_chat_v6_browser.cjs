const assert=require('node:assert/strict')
const fs=require('node:fs')
const path=require('node:path')
const {chromium}=require('../frontend/node_modules/playwright')
const out=path.resolve('tmp/chat-v6')
fs.mkdirSync(out,{recursive:true})
const q=JSON.parse(fs.readFileSync('reports/chat_v6/queries.json','utf8').replace(/^\uFEFF/,''))
const token=fs.readFileSync('tmp/studio-runtime/access-token.txt','utf8').trim()
const doc='4a92af827aaf1e73e017544d0ff20d0d'
const url='http://127.0.0.1:18112'
const chrome=path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1217/chrome-win64/chrome.exe')

async function ask(page,question){
 await page.getByRole('textbox',{name:'Câu hỏi trợ lý'}).fill(question)
 const pending=page.waitForResponse(r=>r.url().endsWith('/studio/chat')&&r.request().method()==='POST')
 await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
 const response=await pending
 assert.equal(response.status(),200)
 const result=await response.json()
 const request=response.request().postDataJSON()
 assert.ok(!request.evidence_context)
 const progress=await fetch(url+'/studio/chat/progress/'+request.progress_id,{headers:{Authorization:'Bearer '+token}}).then(r=>r.json())
 assert.equal(progress.pages_read,24)
 assert.equal(progress.tasks_done,result.task_results.length)
 await page.locator('.message-assistant').last().locator('table').first().waitFor()
 return result
}

async function main(){
 const browser=await chromium.launch({executablePath:chrome})
 const page=await browser.newPage({viewport:{width:1440,height:900}})
 await page.addInitScript(t=>sessionStorage.setItem('studio-token',t),token)
 const records={}
 try{
  await page.goto(url+'/app/#/analysis')
  await page.getByRole('combobox',{name:'Tài liệu trợ lý'}).selectOption(doc)
  let reply=await ask(page,q.inventory)
  assert.equal(reply.page_map.length,24)
  assert.deepEqual(reply.page_map.map(p=>p.page),Array.from({length:24},(_,i)=>i+1))
  assert.equal(await page.locator('.message-assistant').last().locator('table').first().locator('tbody tr').count(),24)
  assert.equal(reply.task_results[0].operands[0].raw,'58.147.857.000.000')
  assert.equal(reply.page_map[19].printed_page,19)
  await page.screenshot({path:path.join(out,'inventory-100.png')})
  records.inventory={rows:24,citations:reply.citations.length,printedPage:reply.page_map[19].printed_page}
  reply=await ask(page,q.checks)
  assert.equal(reply.task_results.length,6)
  assert.deepEqual(reply.task_results.map(t=>t.task),['equation','cash','income','shares','notes','explain'])
  assert.deepEqual(reply.values,[])
  assert.ok(reply.task_results.some(t=>t.checks.some(c=>c.mode==='CANDIDATE_RECONCILIATION')))
  assert.ok(reply.task_results.every(t=>t.checks.every(c=>c.mode!=='VERIFIED_CALCULATION')))
  assert.equal(await page.locator('.message-assistant').last().locator('tbody tr').count(),6)
  await page.screenshot({path:path.join(out,'six-checks-100.png')})
  const cdp=await page.context().newCDPSession(page)
  await cdp.send('Emulation.setPageScaleFactor',{pageScaleFactor:1.25})
  assert.equal(await page.evaluate(()=>visualViewport.scale),1.25)
  await page.screenshot({path:path.join(out,'six-checks-125.png')})
  await cdp.send('Emulation.setPageScaleFactor',{pageScaleFactor:1})
  await cdp.detach()
  records.checks=reply.task_results.map(t=>({task:t.task,status:t.status,pages:t.operands.map(c=>c.page)}))
  reply=await ask(page,q.capital)
  assert.match(reply.answer,/58\.147\.857\.000\.000/)
  assert.match(reply.answer,/trang PDF 20 \(trang in 19\)/)
  assert.deepEqual(reply.values,[])
  const cell=reply.task_results[0].operands[0]
  assert.equal(cell.review_status,'AUTOMATED_EXTRACTION')
  await page.locator('.message-assistant').last().getByRole('button',{name:'Mở nguồn 1 trang 20'}).first().click()
  await page.getByRole('button',{name:'Mở trang nguồn 20'}).click()
  await page.locator('[data-rendered="true"] canvas[aria-label="Trang PDF 20"]').waitFor()
  await page.getByRole('combobox',{name:'Tỷ lệ PDF'}).selectOption('1.25')
  const highlight=page.getByTestId('source-highlight').first()
  await highlight.scrollIntoViewIfNeeded()
  const box=await highlight.boundingBox()
  assert.ok(box.width>60&&box.height<20)
  records.capital={page:20,period:cell.period_end,sourceBox:cell.box,highlight:box}
  await page.screenshot({path:path.join(out,'capital-source-125.png')})
  fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify(records,null,2))
  console.log(JSON.stringify(records))
 }catch(error){
  await page.screenshot({path:path.join(out,'browser-failure.png')})
  throw error
 }finally{await browser.close()}
}
main().catch(error=>{console.error(error);process.exitCode=1})
