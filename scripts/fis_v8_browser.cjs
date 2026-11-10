const assert=require('node:assert/strict')
const fs=require('node:fs')
const path=require('node:path')
const {chromium}=require('../frontend/node_modules/playwright')
const root=process.env.FIS_V8_URL||'http://127.0.0.1:18110'
const holdout=process.env.FIS_V8_HOLDOUT_URL||'http://127.0.0.1:18117'
const out=process.env.FIS_V8_OUTPUT||'tmp/fis-v8/browser'
const token=fs.readFileSync('tmp/studio-runtime/access-token.txt','utf8').trim()
const chrome=path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1217/chrome-win64/chrome.exe')
const cases=JSON.parse(fs.readFileSync('reports/fis_v8/HOLDOUT_CASES.json','utf8'))
const accessions=['0000909832-26-000051','0001628280-26-058715','0000080424-26-000256','0001193125-25-256321']
const hdQuestion='Trong báo cáo Home Depot kỳ kết thúc 02/08/2026, hãy cho biết doanh thu thuần của kỳ 13 tuần và kỳ 26 tuần. Vì sao không được xem hai kỳ này tương đương?'
const riskQuestion='Hãy tóm tắt những yếu tố rủi ro hoặc bất định được Home Depot thảo luận trong filing 10-Q đang chọn.'
fs.mkdirSync(out,{recursive:true})
const evidence=[]
const save=()=>fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify(evidence,null,2))
const api=async (origin, endpoint)=>fetch(origin+'/studio'+endpoint,{headers:{Authorization:'Bearer '+token}}).then(r=>r.json())
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms))

async function ask(page,question,ids){
 await page.getByRole('textbox',{name:'Câu hỏi trợ lý'}).fill(question)
 const result=page.waitForResponse(r=>r.url().endsWith('/studio/chat')&&r.request().method()==='POST',{timeout:120000})
 await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
 const response=await result
 assert.deepEqual(response.request().postDataJSON().filing_ids.slice().sort(),ids.slice().sort())
 const reply=await response.json()
 assert.equal(response.status(),200)
 await page.locator('.message-assistant').last().waitFor()
 return reply
}

async function openEvidence(page,numeric){
 const turn=page.locator('.message-assistant').last()
 await turn.getByRole('button',{name:/Mở nguồn 1 filing/}).first().click()
 const response=page.waitForResponse(r=>r.url().endsWith('/studio/sec/evidence')&&r.request().method()==='POST',{timeout:60000})
 await page.getByRole('button',{name:/Mở trang nguồn/}).click()
 const view=await (await response).json()
 assert.equal(Boolean(view.selected_cell),numeric)
 return {accession:view.accession,location:view.locator,cell:view.selected_cell,excerpt:view.excerpt?.slice(0,450)}
}

async function openPage(browser,url){
 const page=await browser.newPage({viewport:{width:1440,height:900}})
 page.setDefaultTimeout(50000)
 await page.addInitScript(value=>sessionStorage.setItem('studio-token',value),token)
 await page.goto(url)
 return page
}

async function control(browser){
 const catalog=(await api(root,'/sec/catalog')).filings
 const ids=accessions.map(a=>catalog.find(x=>x.accession===a).filing_id)
 const page=await openPage(browser,root+'/app/#/analysis')
 try{
  const picker=page.getByRole('combobox',{name:'Tài liệu trợ lý'})
  await picker.selectOption('SEC:'+ids[0])
  await page.getByText('Nguồn (1)',{exact:true}).click()
  for(const accession of accessions.slice(1,3)){
   await page.getByRole('checkbox',{name:new RegExp(accession)}).check()
  }
  await page.getByText('Nguồn (3)',{exact:true}).click()
  const a=await ask(page,hdQuestion,ids.slice(0,3))
  assert.deepEqual(a.values,['47861','89626'])
  assert.ok(a.citations.every(c=>c.accession===accessions[1]))
  await page.screenshot({path:path.join(out,'hd-100.png')})
  const cell=await openEvidence(page,true)
  assert.equal(cell.accession,accessions[1])
  assert.equal(cell.cell.raw_value,'47,861')
  evidence.push({case:'A02',status:'PASS',answer:a.answer,view:cell})
  save()
  await page.goto(root+'/app/#/analysis')
  const b=await ask(page,riskQuestion,ids.slice(0,3))
  assert.equal(b.answer_status,'SEC_NARRATIVE_EVIDENCE')
  const disclosure=await openEvidence(page,false)
  assert.equal(disclosure.accession,accessions[1])
  evidence.push({case:'A04',status:'PASS',answer:b.answer,view:disclosure})
  save()
  await page.goto(root+'/app/#/analysis')
  await picker.selectOption('SEC:'+ids[3])
  const msft=await ask(page,'Doanh thu Microsoft quý kết thúc 30/09/2025 là bao nhiêu?',[ids[3]])
  evidence.push({case:'B04',status:msft.values?.[0]==='77673'?'PASS':'FAIL',answer:msft.answer,reason:msft.reason})
  const cdp=await page.context().newCDPSession(page)
  await cdp.send('Emulation.setPageScaleFactor',{pageScaleFactor:1.25})
  await page.screenshot({path:path.join(out,'msft-125.png')})
  await cdp.detach()
  await page.goto(root+'/app/#/library')
  await page.getByRole('button',{name:'Hồ sơ SEC',exact:true}).click()
  await page.getByText(/MSFT · 10-Q · kỳ 2025-09-30 · BM25 đã xuất bản/).first().waitFor()
  await page.screenshot({path:path.join(out,'msft-library.png')})
  save()
 }catch(e){
  evidence.push({case:'browser-control',status:'FAIL',reason:e.message.slice(0,400)})
  await page.screenshot({path:path.join(out,'control-failure.png')})
  save()
 }finally{await page.close()}
}

async function independent(browser,test){
 const page=await openPage(browser,holdout+'/app/#/library')
 const record={case:test.ticker,expected:test}
 const start=Date.now()
 try{
  await page.getByRole('button',{name:'Hồ sơ SEC',exact:true}).click()
  await page.getByRole('textbox',{name:'Tìm công ty SEC'}).fill(test.ticker)
  await page.getByRole('combobox',{name:'Loại filing SEC'}).selectOption(test.form)
  await page.getByLabel('Kỳ báo cáo SEC').fill(test.report_end)
  const discovery=page.waitForResponse(r=>r.url().includes('/sec/library/discover?'))
  await page.getByRole('button',{name:'Tìm trên EDGAR'}).click()
  const d=await discovery
  record.discovery_ms=Date.now()-start
  record.discovery_status=d.status()
  if(!d.ok()) throw Error(JSON.stringify(await d.json()))
  const filing=(await d.json()).filings.find(f=>f.accession_number===test.accession)
  if(!filing) throw Error('Official accession not returned')
  const importStart=Date.now()
  const imported=page.waitForResponse(r=>r.url().endsWith('/sec/library/import'))
  await page.locator('article').filter({hasText:test.accession}).getByRole('button',{name:'Thêm vào kho SEC'}).click()
  const job=await (await imported).json()
  const deadline=Date.now()+180000
  let item
  while(Date.now()<deadline){
   item=(await api(holdout,'/sec/library')).filings.find(f=>f.id===job.id)
   if(['READY','LEXICAL_READY','RETRYABLE','FAILED'].includes(item?.status))break
   await wait(2500)
  }
  record.import={id:job.id,state:item?.status,reason:item?.reason,progress:item?.progress,elapsed_ms:Date.now()-importStart}
  record.events=(await api(holdout,'/sec/library/jobs/'+job.id+'/events')).events
  if(!['READY','LEXICAL_READY'].includes(item?.status))throw Error('Filing not published: '+(item?.reason||item?.status))
  await page.screenshot({path:path.join(out,test.ticker+'-import.png')})
  await page.locator('article').filter({hasText:test.accession}).getByRole('button',{name:'Hỏi báo cáo này'}).click()
  for(const type of ['numeric','narrative']){
   const t=Date.now()
   const result=await ask(page,test[type],[filing.filing_id])
   record[type]={seconds:(Date.now()-t)/1000,answer:result.answer,status:result.answer_status,values:result.values,reason:result.reason,
                 sourceCells:result.source_cells,citations:result.citations?.map(c=>({accession:c.accession,section:c.section,text:c.text}))}
  }
  record.status='EXECUTED'
 }catch(e){
  record.status='BLOCKED'
  record.reason=e.message.slice(0,450)
  await page.screenshot({path:path.join(out,test.ticker+'-failure.png')})
 }finally{evidence.push(record);save();await page.close()}
}

async function main(){
 const browser=await chromium.launch({executablePath:chrome})
 try{
  if(process.env.FIS_V8_SKIP_CONTROL!=='1') await control(browser)
  if(process.env.FIS_V8_SKIP_HOLDOUT!=='1') for(const test of cases) await independent(browser,test)
  console.log(evidence.map(x=>[x.case,x.status,x.reason]))
 }finally{await browser.close()}
}
main().catch(error=>{console.error(error);process.exitCode=1})
