const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require('../frontend/node_modules/playwright')

const root = path.resolve('tmp/chat-v5')
const base = 'http://127.0.0.1:18112'
const token = fs.readFileSync('tmp/studio-runtime/access-token.txt','utf8').trim()
const id = '4a92af827aaf1e73e017544d0ff20d0d'
const headers = { Authorization: 'Bearer '+token }
const executablePath = path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1217/chrome-win64/chrome.exe')

async function send(page, question, focus) {
  const composer = page.getByRole('textbox',{name:'Câu hỏi trợ lý'})
  if (question) await composer.fill(question)
  const pending = page.waitForResponse(r=>r.url().endsWith('/studio/chat')&&r.request().method()==='POST')
  await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
  const reply = await pending
  assert.equal(reply.status(),200)
  const request = reply.request().postDataJSON()
  if (focus) assert.equal(request.evidence_context?.page,focus)
  else assert.ok(!request.evidence_context,'passive source attached to request')
  const result = await reply.json()
  await page.locator('.message-assistant').last().getByText(result.answer.split('\n')[0].split(' [1]')[0],{exact:false}).first().waitFor()
  assert.doesNotMatch(await page.locator('.message-assistant').last().locator('.answer-prose').innerText(),/\{'INSTANT'|'3M_Q4':|\bHUMAN_SOURCE_VERIFIED\b/)
  return result
}

async function openCitation(page, number, index=1) {
  await page.locator('.message-assistant').last().getByRole('button',{name:'Mở nguồn '+index+' trang '+number}).click()
  await page.getByRole('button',{name:'Mở trang nguồn '+number}).click()
  await page.locator('[data-rendered="true"] canvas[aria-label="Trang PDF '+number+'"]').waitFor()
  const mark=page.getByTestId('source-highlight').first()
  await mark.scrollIntoViewIfNeeded()
  const box=await mark.boundingBox()
  assert.ok(box.width>0&&box.height>0&&box.height<33)
  return box
}

async function main(){
 const browser=await chromium.launch({executablePath})
 const page=await browser.newPage({viewport:{width:1440,height:900}})
 page.setDefaultTimeout(18000)
 await page.addInitScript(t=>sessionStorage.setItem('studio-token',t),token)
 const output={}
 try{
  await page.goto(base+'/app/#/library')
  const docs=await fetch(base+'/studio/documents',{headers}).then(r=>r.json())
  const name=docs.documents.find(d=>d.id===id).filename
  await page.getByRole('row').filter({hasText:name}).getByRole('button',{name:'Xem nguồn'}).click()
  await page.locator('canvas[aria-label="Trang PDF 1"]').waitFor()
  await page.getByRole('button',{name:'Trợ lý tài chính',exact:true}).click()
  await page.getByRole('combobox',{name:'Tài liệu trợ lý'}).selectOption(id)
  const ask='Nợ phải trả của công ty mẹ Hòa Phát tại 31/12/2025 là bao nhiêu?'
  const liabilities=await send(page,ask)
  assert.deepEqual(liabilities.values,['4239852223395'])
  assert.equal(liabilities.verification_status,'HUMAN_SOURCE_VERIFIED')
  assert.equal(await page.getByText(/Đoạn đang xem/).count(),0)
  await page.screenshot({path:path.join(root,'chat-100.png')})
  const cdp=await page.context().newCDPSession(page)
  await cdp.send('Emulation.setPageScaleFactor',{pageScaleFactor:1.25})
  assert.equal(await page.evaluate(()=>visualViewport.scale),1.25)
  await page.screenshot({path:path.join(root,'chat-125.png')})
  await cdp.send('Emulation.setPageScaleFactor',{pageScaleFactor:1})
  await cdp.detach()
  output.liabilities={session:liabilities.session_id,box:await openCitation(page,4)}
  await page.getByRole('button',{name:'Quay lại câu hỏi'}).click()
  await page.getByText('Bằng chứng câu trả lời · trang 4').waitFor()
  const assets=await send(page,'Tổng tài sản công ty mẹ Hòa Phát tại 31/12/2025 là bao nhiêu? Đã được người dùng kiểm duyệt chưa?')
  assert.equal(assets.session_id,liabilities.session_id)
  assert.deepEqual(assets.values,[])
  assert.match(assets.answer,/98\.670\.778\.691\.605.*ứng viên|ứng viên 98\.670\.778\.691\.605/)
  output.assets={box:await openCitation(page,3)}
  await page.getByRole('button',{name:'Quay lại câu hỏi'}).click()
  await page.getByText('Bằng chứng câu trả lời · trang 3').waitFor()
  const revenue=await send(page,'Doanh thu thuần quý IV/2025 và cả năm 2025 của Hòa Phát là bao nhiêu?')
  assert.deepEqual(revenue.values,[])
  assert.match(revenue.answer,/125\.533\.574\.301/)
  assert.match(revenue.answer,/343\.200\.043\.936/)
  assert.equal(new Set(revenue.citations.map(c=>c.column_id)).size,2)
  output.revenue={quarter:await openCitation(page,5)}
  await page.getByRole('combobox',{name:'Tỷ lệ PDF'}).selectOption('1.25')
  await page.getByTestId('source-highlight').first().scrollIntoViewIfNeeded()
  await page.screenshot({path:path.join(root,'source-125.png')})
  await page.getByRole('button',{name:'Quay lại câu hỏi'}).click()
  await page.getByText('Bằng chứng câu trả lời · trang 5').waitFor()
  await page.reload()
  await page.getByText('Bằng chứng câu trả lời · trang 5').waitFor()
  output.revenue.annual=await openCitation(page,5,2)
  await page.getByRole('button',{name:'Quay lại câu hỏi'}).click()
  await page.locator('.message-assistant').last().getByRole('button',{name:'Mở nguồn 2 trang 5'}).click()
  await page.getByRole('button',{name:'Hỏi về đoạn này'}).click()
  const focused=await send(page,null,5)
  assert.equal(focused.citations[0].column_id,revenue.citations[1].column_id)
  assert.match(focused.answer,/Doanh thu thuần là doanh thu/)
  const cash=await send(page,'Lưu chuyển tiền thuần từ hoạt động kinh doanh năm 2025 là bao nhiêu?')
  assert.match(cash.answer,/\(737\.877\.371\.011\)/)
  output.cash={box:await openCitation(page,6)}
  await page.getByRole('button',{name:'Quay lại câu hỏi'}).click()
  const deposit=await send(page,'Tiền gửi ngân hàng đầu năm 2025 trong thuyết minh Hòa Phát là bao nhiêu? OCR ban đầu và đọc lại khác nhau thế nào?')
  assert.match(deposit.answer,/46\.014\.571\.676/)
  assert.match(deposit.answer,/46\.074\.571\.676/)
  assert.deepEqual(deposit.values,[])
  output.deposit={box:await openCitation(page,12)}
  await page.getByRole('button',{name:'Quay lại câu hỏi'}).click()
  const compare=await send(page,'Có sự khác biệt giữa OCR ban đầu và kết quả đọc lại không?')
  assert.equal(compare.citations[0].column_id,deposit.citations[0].column_id)
  assert.match(compare.answer,/46\.014\.571\.676.*46\.074\.571\.676/)
  output.deposit.followup=true
  await openCitation(page,12)
  await page.getByRole('button',{name:'Quay lại câu hỏi'}).click()
  const dash=await send(page,'Dấu gạch trong cột dự phòng ở trang 13 có đồng nghĩa số 0 không?')
  assert.match(dash.answer,/Không thể mặc định dấu gạch bằng số 0/)
  output.dash={box:await openCitation(page,13)}
  await page.getByRole('button',{name:'Quay lại câu hỏi'}).click()
  const catalog=await fetch(base+'/studio/sec/catalog',{headers}).then(r=>r.json())
  const next=catalog.filings[0]
  assert.ok(next,'need one configured SEC filing for source switch')
  await page.getByRole('combobox',{name:'Tài liệu trợ lý'}).selectOption('SEC:'+next.filing_id)
  await page.reload()
  await page.getByRole('combobox',{name:'Tài liệu trợ lý'}).locator('option[value="SEC:'+next.filing_id+'"]').waitFor({state:'attached'})
  assert.equal(await page.getByRole('combobox',{name:'Tài liệu trợ lý'}).inputValue(),'SEC:'+next.filing_id)
  assert.equal(await page.getByText(/Bằng chứng câu trả lời · trang/).count(),0)
  await page.getByRole('button',{name:'Hội thoại đã lưu'}).click()
  await page.locator('.session-item').filter({hasText:ask}).first().click()
  await page.getByText('Bằng chứng câu trả lời · trang 13').waitFor()
  assert.equal(await page.getByRole('combobox',{name:'Tài liệu trợ lý'}).inputValue(),id)
  output.context={ordinaryTurnsWithoutFocus:true,explicitSourcePage:5,restoredPage:13}
  fs.writeFileSync(path.join(root,'browser.json'),JSON.stringify(output,null,2))
  console.log(output)
 }catch(error){
  await page.screenshot({path:path.join(root,'browser-failure.png')})
  throw error
 }finally{await browser.close()}
}
main().catch(error=>{console.error(error);process.exitCode=1})
