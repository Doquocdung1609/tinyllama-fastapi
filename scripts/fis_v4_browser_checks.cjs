const assert=require('node:assert/strict')
const fs=require('node:fs')
const path=require('node:path')
const {chromium}=require('../frontend/node_modules/playwright')
const runtime=path.resolve(__dirname,'../tmp/studio-runtime')
const url=process.env.STUDIO_BROWSER_URL||'http://127.0.0.1:18110'
const token=fs.readFileSync(path.join(runtime,'access-token.txt'),'utf8').trim()
const chrome=path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1217/chrome-win64/chrome.exe')

async function main(){
 const browser=await chromium.launch({headless:true,executablePath:chrome})
 const records=[]
 const output=process.env.STUDIO_BROWSER_OUTPUT||path.join(runtime,'v4-browser')
 fs.mkdirSync(output,{recursive:true})
 try{
  const catalog=await fetch(url+'/studio/sec/catalog',{headers:{Authorization:'Bearer '+token}}).then(r=>r.json())
  const docs=(await fetch(url+'/studio/documents',{headers:{Authorization:'Bearer '+token}}).then(r=>r.json())).documents
  const apple=docs.find(d=>d.filename.includes('AAPL')), bidv=docs.find(d=>[d.filename,d.issuer].join(' ').toUpperCase().includes('BIDV'))
  const pg=catalog.filings.filter(f=>f.ticker==='PG')
  const send=async(page,question)=>{
   await page.getByRole('textbox',{name:'Câu hỏi trợ lý'}).fill(question)
   const pending=page.waitForResponse(r=>r.url().endsWith('/studio/chat')&&r.request().method()==='POST',{timeout:90000})
   await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
   const response=await pending
   assert.equal(response.status(),200)
   const reply=await response.json()
   await page.locator('.message-assistant').last().waitFor()
   return reply
  }
  const openPage=async(viewport)=>{
   const page=await browser.newPage({viewport})
   await page.addInitScript(value=>sessionStorage.setItem('studio-token',value),token)
   await page.goto(url+'/app/#/analysis',{waitUntil:'domcontentloaded'})
   await page.locator('select[aria-label="Tài liệu trợ lý"] option').filter({hasText:'AAPL'}).first().waitFor({state:'attached',timeout:45000})
   return page
  }
  if(process.env.STUDIO_BROWSER_NATIVE_CONTROLS==='1'){
   for(const [name,doc,question,value,pages] of [
    ['Apple',apple,'Doanh thu Services Apple FY2025 là bao nhiêu?','109158',[32]],
    ['BIDV',bidv,'Năm 2024, lợi nhuận sau thuế chưa phân phối: mức điều chỉnh của riêng ngân hàng và hợp nhất khác nhau bao nhiêu?','1114',[4,7]]
   ]){
    const page=await openPage({width:1440,height:900})
    try{
     await page.getByRole('combobox',{name:'Tài liệu trợ lý'}).selectOption(doc.id)
     const reply=await send(page,question)
     assert.equal(reply.status,'SUPPORTED')
     assert.deepEqual(reply.values,[value])
     assert.deepEqual(reply.citations.map(c=>c.page).sort((a,b)=>a-b),pages)
     await page.getByRole('button',{name:/Mở nguồn 1 trang/}).first().click()
     await page.getByRole('button',{name:/Mở trang nguồn/}).click()
     await page.locator('[data-rendered="true"] canvas[aria-label="Trang PDF '+reply.citations[0].page+'"]').waitFor()
     await page.getByTestId('source-highlight').first().scrollIntoViewIfNeeded()
     await page.screenshot({path:path.join(output,name+'-citation.png')})
     records.push({case:name,status:'PASS',value,pages})
    }catch(e){records.push({case:name,status:'FAIL',reason:e.message.slice(0,700)})}
    await page.close()
   }
  }
  let page=await openPage({width:1366,height:768})
  try{
   await page.getByRole('combobox',{name:'Tài liệu trợ lý'}).selectOption(apple.id)
   await page.locator('.chat-source-picker summary').click()
   await page.locator('.chat-source-options label').filter({hasText:bidv.filename}).getByRole('checkbox').check()
   await page.locator('.chat-source-picker summary').click()
   assert.equal(await page.locator('.chat-selected-sources li').count(),2)
   const reply=await send(page,'Tìm bảng cân đối kế toán trong các PDF đang chọn và dẫn nguồn.')
   assert.deepEqual(new Set(reply.citations.map(c=>c.document_id)),new Set([apple.id,bidv.id]))
   await page.screenshot({path:path.join(output,'pdf-1366.png')})
   await page.reload({waitUntil:'domcontentloaded'})
   await page.locator('.chat-selected-sources li').nth(1).waitFor()
   await page.getByRole('button',{name:/Mở nguồn 1 trang/}).first().click()
   await page.getByRole('button',{name:/Mở trang nguồn/}).click()
   await page.locator('canvas').first().waitFor({timeout:45000})
   await page.screenshot({path:path.join(output,'pdf-citation.png')})
   records.push({case:'pdf-multi',status:'PASS',files:[apple.filename,bidv.filename],pages:reply.citations.map(c=>c.page)})
  }catch(e){records.push({case:'pdf-multi',status:'FAIL',reason:e.message.slice(0,700)})}
  await page.close()
  page=await openPage({width:1920,height:1080})
  try{
   assert.equal(pg.length,2)
   await page.getByRole('combobox',{name:'Tài liệu trợ lý'}).selectOption('SEC:'+pg[0].filing_id)
   await page.locator('.chat-source-picker summary').click()
   await page.locator('.chat-source-options label').filter({hasText:pg[1].accession}).getByRole('checkbox').check()
   await page.locator('.chat-source-picker summary').click()
   const reply=await send(page,'Compare PG net sales for the three months ended 2026-03-31 and 2026-09-30')
   assert.equal(reply.status,'SUPPORTED',reply.reason)
   assert.equal(new Set(reply.citations.map(c=>c.generation)).size,2)
   await page.screenshot({path:path.join(output,'sec-1920.png')})
   for(const [i,c] of reply.citations.entries()){
    const body=await fetch(url+'/studio/sec/evidence',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({reference:c.source_reference})}).then(r=>r.json())
    assert.equal(body.accession,c.accession)
    assert.ok(body.selected_cell)
    if(i===0){
     await page.getByRole('button',{name:/Mở nguồn 1 filing/}).first().click()
     await page.getByRole('button',{name:/Mở trang nguồn/}).click()
     await page.getByText(c.accession,{exact:false}).first().waitFor()
     await page.screenshot({path:path.join(output,'sec-citation.png')})
    }
   }
   records.push({case:'sec-federation',status:'PASS',accessions:reply.citations.map(c=>c.accession)})
  }catch(e){records.push({case:'sec-federation',status:'FAIL',reason:e.message.slice(0,700)})}
  await page.close()
  page=await openPage({width:390,height:844})
  try{
   await page.getByRole('combobox',{name:'Tài liệu trợ lý'}).selectOption(apple.id)
   await page.locator('.chat-source-picker summary').click()
   await page.locator('.chat-source-options label').filter({hasText:bidv.filename}).getByRole('checkbox').check()
   await page.locator('.chat-source-picker summary').click()
   assert.equal(await page.locator('.chat-selected-sources li').count(),2)
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth))
   await page.screenshot({path:path.join(output,'pdf-mobile.png')})
   records.push({case:'mobile-picker',status:'PASS'})
  }catch(e){records.push({case:'mobile-picker',status:'FAIL',reason:e.message.slice(0,700)})}
 }finally{
  fs.writeFileSync(path.join(output,'results.json'),JSON.stringify(records,null,2))
  console.log(JSON.stringify(records))
  if(records.some(record=>record.status==='FAIL'))process.exitCode=1
  await browser.close()
 }
}
main().catch(e=>{console.error(e.message);process.exitCode=1})
