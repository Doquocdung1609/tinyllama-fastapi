/* Real React browser execution. No intercepted or mocked network responses. */
const {chromium,expect}=require('../../frontend/node_modules/@playwright/test');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
const out=path.join(root,'deliverables/FAITH_R_FIS_DEMO_20261110');
const base='http://127.0.0.1:18110';
const record=process.argv.includes('--record');
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const token=fs.readFileSync(path.join(root,'tmp/studio-runtime/access-token.txt'),'utf8').replace(/^\uFEFF/,'').trim();
const ids={apple:'3eb270b22acb7d8d8e9c32a43dc221de',bidv:'2bed2b3c312c8149e6a2ff6ab80c694a',hpg:'4a92af827aaf1e73e017544d0ff20d0d',
 cost:'SEC:sec:0000909832:0000909832-26-000051',hd:'SEC:sec:0000354950:0001628280-26-058715'};
const results=[],scenes=[],errors=[];
let page,context,sceneNo=0;
const hold=async(seconds=4)=>{if(record)await pause(seconds*1000)};
async function nav(name){await page.getByRole('button',{name,exact:true}).first().click();await hold(3)}
async function scroll(selector='html',direction=1,steps=6){
 const area=page.locator(selector).first();
 for(let i=0;i<steps;i++){await area.evaluate((el,d)=>el.scrollBy({top:d*380,behavior:'smooth'}),direction);await hold(2)}
}
async function tour(){await scroll('html',1,8);await scroll('html',-1,8)}
async function type(label,text){
 const input=page.getByLabel(label,{exact:true});await input.fill('');
 if(record)await input.pressSequentially(text,{delay:35});else await input.fill(text);
 await hold(2);
}
async function test(id,fn){
 const started=Date.now();
 try{const detail=await fn();results.push({id,scene:sceneNo,status:detail.status||'PASS',elapsed_ms:Date.now()-started,...detail});}
 catch(e){results.push({id,scene:sceneNo,status:'FAIL',elapsed_ms:Date.now()-started,reason:e.message.split('\n').slice(0,4).join(' ')});console.log(id+' FAIL '+e.message.split('\n')[0]);}
 fs.writeFileSync(path.join(out,record?'RECORDED_CASE_RESULTS.json':'E2E_CASE_RESULTS.json'),JSON.stringify(results,null,2));
}
async function choose(id){
 await nav('Trợ lý tài chính');
 await page.getByLabel('Tài liệu trợ lý',{exact:true}).locator('option[value="'+id+'"]').waitFor({state:'attached'});
 await page.getByLabel('Tài liệu trợ lý',{exact:true}).selectOption(id);await hold(3);
}
async function ask(id,q,validate){
 await test(id,async()=>{
  await type('Câu hỏi trợ lý',q);
  const pending=page.waitForResponse(r=>r.url().endsWith('/studio/chat')&&r.request().method()==='POST',{timeout:180000});
  await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();
  const response=await pending,data=await response.json();
  await page.locator('.message-assistant').last().waitFor();
  await hold(9);await scroll('.chat-messages',1,3);
  const correct=response.status()===200&&validate(data);
  return {status:correct?'PASS':'PARTIAL',http_status:response.status(),question:q,
   selected_sources:response.request().postDataJSON().document_ids,filing_ids:response.request().postDataJSON().filing_ids,
   product_status:data.answer_status||data.status,answer:data.answer,values:data.values,
   citations:(data.citations||[]).map(c=>({page:c.page,unit:c.unit,period:c.period,source_sha256:c.source_sha256,box:c.box,filing_id:c.filing_id})),
   reason:correct?'Content checked against the supplied development expectation':'Response did not satisfy all requested evidence checks'};
 });
}
async function citation(id,index=0){
 await test(id,async()=>{
  const turn=page.locator('.message-assistant').last();
  const refs=turn.locator('button[aria-label^="Mở nguồn "]');
  const sec=(await refs.nth(index).getAttribute('aria-label')).includes('filing');
  await refs.nth(index).click();
  const open=page.getByRole('button',{name:/^Mở trang nguồn/}).first();
  await open.click();await page.waitForURL(/#\/viewer/);
  const pdf=page.getByTestId('pdf-page');
  if(!sec){await expect(pdf).toHaveAttribute('data-rendered','true',{timeout:30000});await page.getByTestId('source-highlight').first().waitFor();await hold(7);await scroll('.pdf-scroll',1,2);await scroll('.pdf-scroll',-1,2);}
  else{await page.locator('.sec-source-view, .sec-viewer, table').first().waitFor({timeout:20000});await hold(7);await scroll('html',1,4);await scroll('html',-1,4);}
  await page.screenshot({path:path.join(out,'scene-'+sceneNo+'-source.png')});
  await page.getByRole('button',{name:'Quay lại câu hỏi',exact:true}).click();
  return {status:'PASS',viewer:'Local authenticated source viewer rendered'};
 });
}
async function search(method){
 await test('BIDV-SEARCH-'+method,async()=>{
  await page.getByRole('button',{name:method,exact:true}).click();
  const pending=page.waitForResponse(r=>r.url().endsWith('/studio/query'),{timeout:180000});
  await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click();
  const response=await pending,data=await response.json();
  await page.locator('.evidence-hit').first().waitFor();await hold(5);
  const first=page.locator('.hit-trace summary').first();await first.click();await hold(4);
  await tour();
  return {status:response.status()===200&&data.results.length>0?'PASS':'FAIL',http_status:response.status(),
   method,pages:data.results.map(r=>r.page),selected_sources:response.request().postDataJSON().document_ids,
   result_count:data.results.length,verified_value_count:data.verified_value_count,
   results:data.results.map(r=>({page:r.page,text:r.text,chunk_id:r.chunk_id,source_sha256:r.source_sha256}))};
 });
}
async function compare(id){
 await type('Câu hỏi tìm kiếm','Lợi nhuận sau thuế chưa phân phối');
 await page.getByLabel('Nguồn dữ liệu',{exact:true}).selectOption('USER_UPLOADS');
 await page.getByLabel('Tài liệu tìm kiếm',{exact:true}).selectOption(ids.bidv);
 await test(id,async()=>{
  const pending=page.waitForResponse(r=>r.url().endsWith('/studio/compare'),{timeout:180000});
  await page.getByRole('button',{name:'So sánh 4 phương pháp',exact:true}).click();
  const response=await pending,data=await response.json();
  await page.locator('.compare-col .hit').first().waitFor();await hold(5);await tour();
  return {status:response.status()===200&&Object.keys(data.arms||{}).length===3&&data.faith_r?.results.length?'PASS':'PARTIAL',
   http_status:response.status(),arms:Object.fromEntries(Object.entries({...data.arms,faith_r:data.faith_r}).map(([k,v])=>[k,{count:v?.results.length,latency_ms:v?.latency_ms}])),errors:data.arm_errors};
 });
}
const definitions=[
 ['01-introduction','Tổng quan FIS',55,async()=>{await page.goto(base+'/app/#/overview');await page.getByRole('heading',{name:'Chào mừng đến Financial Intelligence Studio'}).waitFor();await hold(7);for(const name of ['Trợ lý tài chính','Kho tài liệu','Bằng chứng & Nguồn','Research Lab','Cài đặt / Trạng thái']){await page.getByRole('button',{name,exact:true}).first().hover();await hold(2)}await tour()}],
 ['02-library','Kho tài liệu PDF',85,async()=>{await nav('Kho tài liệu');await page.getByText('NASDAQ_AAPL_2025.pdf',{exact:false}).first().waitFor();await tour();await page.getByText('NASDAQ_AAPL_2025.pdf',{exact:false}).first().scrollIntoViewIfNeeded();await hold(8)}],
 ['03-evidence','Tìm kiếm BIDV qua bốn phương pháp',145,async()=>{await nav('Bằng chứng & Nguồn');await page.getByLabel('Nguồn dữ liệu',{exact:true}).selectOption('USER_UPLOADS');await page.getByLabel('Tài liệu tìm kiếm',{exact:true}).selectOption(ids.bidv);await page.getByLabel('Số kết quả tối đa').selectOption('5');await type('Câu hỏi tìm kiếm','Lợi nhuận sau thuế chưa phân phối');for(const m of ['BM25','Dense','Hybrid RRF','FAITH-R'])await search(m);
 await test('BIDV-SEARCH-SOURCE',async()=>{await page.locator('.evidence-hit').first().getByRole('button',{name:/Mở trang nguồn/}).click();await expect(page.getByTestId('pdf-page')).toHaveAttribute('data-rendered','true',{timeout:30000});await page.getByTestId('source-highlight').first().waitFor();await hold(10);await scroll('.pdf-scroll',1,3);await page.getByRole('button',{name:'Quay lại câu hỏi',exact:true}).click();return {status:'PASS'}})}],
 ['04-comparison','So sánh bốn phương pháp',85,async()=>{await nav('Research Lab');await compare('COMPARE-FOUR')}],
 ['05-apple-en','Chat Apple bằng tiếng Anh',105,async()=>{await choose(ids.apple);await ask('APPLE-01',"What was Apple's net income in fiscal year 2025? Please include the unit and source.",d=>/112[.,]010/.test(d.answer)&&d.citations?.some(c=>c.page===32));await citation('APPLE-01-SOURCE');if(!record){await page.getByRole('button',{name:'Bắt đầu hội thoại mới',exact:true}).click();await ask('APPLE-02','Which geographic segment generated the highest net sales in fiscal year 2025, and how much did it generate?',d=>/Americas/.test(d.answer)&&/178[.,]353/.test(d.answer));await citation('APPLE-02-SOURCE')}await page.getByRole('button',{name:'Bắt đầu hội thoại mới',exact:true}).click();await ask('APPLE-GROWTH-EN',"Calculate Apple's year-over-year total net sales growth rate from fiscal 2024 to fiscal 2025. Show the calculation and round to two decimal places.",d=>/6[.,]43/.test(d.answer)&&d.citations?.length>=2);await citation('APPLE-GROWTH-EN-SOURCE')}],
 ['06-apple-vi','Chat Apple bằng tiếng Việt và tính toán',85,async()=>{await choose(ids.apple);await ask('APPLE-03','Nếu cứ 100 USD doanh thu Apple năm 2025 thì khoảng bao nhiêu USD đến từ dịch vụ?',d=>/26[.,]23/.test(d.answer)&&d.citations?.length>=2);const last=results.at(-1);if(last.status!=='PASS')await ask('APPLE-GROWTH',"Calculate Apple's year-over-year total net sales growth rate from fiscal 2024 to fiscal 2025. Show the calculation and round to two decimal places.",d=>/6[.,]43/.test(d.answer));await citation('APPLE-CALC-SOURCE');await ask('APPLE-FUTURE',"What were Apple's FY2026 total net sales according to the FY2025 10-K selected in this conversation?",d=>!d.values?.length&&/2026/.test(d.answer))}],
 ['07-bidv-chat','Chat BIDV hai phạm vi',65,async()=>{await choose(ids.bidv);await ask('BIDV-CHAT','Mức điều chỉnh lợi nhuận sau thuế chưa phân phối của BIDV trong báo cáo riêng và hợp nhất năm 2024 khác nhau bao nhiêu? Nêu hai số điều chỉnh và dẫn trang nguồn.',d=>d.answer.includes('1.114')&&d.citations?.some(c=>c.page===4)&&d.citations?.some(c=>c.page===7));await citation('BIDV-CHAT-SOURCE')}],
 ['08-hpg','PDF scan Hòa Phát và giới hạn OCR',65,async()=>{await choose(ids.hpg);await ask('HPG-OCR','Trong báo cáo tài chính riêng của Hòa Phát tại ngày 31/12/2025, nợ phải trả của công ty mẹ là bao nhiêu? Nêu đơn vị và trang nguồn.',d=>d.answer.includes('4.239.852.223.395')||(/OCR|đối chiếu|xác minh/i.test(d.answer)&&d.citations?.some(c=>c.page===4)));await citation('HPG-OCR-SOURCE')}],
 ['09-sec','Chat SEC Costco',100,async()=>{await choose(ids.cost);await ask('SEC-COST-01',"According to Costco's 10-Q ending May 10, 2026, what was total revenue for the 12-week period? Include the unit and source.",d=>d.answer.includes('70.527')&&d.citations?.length>0);await ask('SEC-COST-02','Trong báo cáo Costco kỳ 12 tuần kết thúc ngày 10/05/2026, hãy tính biên lợi nhuận hoạt động bằng lợi nhuận hoạt động chia cho tổng doanh thu. Nêu hai số và công thức.',d=>/3[.,]99/.test(d.answer)&&d.citations?.length>=2);await citation('SEC-COST-SOURCE')}],
 ['10-missing-source','Kiểm soát nguồn chưa chọn',55,async()=>{await choose(ids.cost);await ask('SEC-MISSING-AMAZON','Trong Amazon 10-K FY2024, doanh thu AWS chiếm bao nhiêu phần trăm tổng doanh thu hợp nhất?',d=>!d.values?.length&&/nguồn|chọn|khớp|Amazon|AMZN/i.test(d.answer))}],
 ['11-research','Research Lab',75,async()=>{await nav('Research Lab');await compare('RESEARCH-LIVE');await page.locator('.compare-col').last().scrollIntoViewIfNeeded();await hold(6)}],
 ['12-status','Trạng thái dịch vụ và kết thúc',50,async()=>{await nav('Cài đặt / Trạng thái');await page.getByRole('heading',{name:'Dịch vụ và chỉ mục'}).waitFor();await tour();await page.goto(base+'/app/#/overview');await hold(8)}],
];
(async()=>{
 fs.mkdirSync(path.join(out,'scenes'),{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1217/chrome-win64/chrome.exe')});
 try{
  for(const [key,title,target,fn] of definitions){
   sceneNo++;console.log('START '+key+' '+new Date().toISOString());
   context=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1,
    ...(record?{recordVideo:{dir:path.join(out,'scenes'),size:{width:1920,height:1080}}}:{})});
   await context.addInitScript(t=>sessionStorage.setItem('studio-token',t),token);
   page=await context.newPage();page.setDefaultTimeout(25000);
   page.on('pageerror',e=>errors.push({scene:sceneNo,message:e.message}));
   const started=Date.now();
   await page.goto(base+'/app/#/overview');
   try{await fn();if(record){while(Date.now()-started<target*1000){await scroll(page.url().includes('/analysis')?'.chat-messages':'html',1,2);await hold(7);if(Date.now()-started<target*1000){await scroll(page.url().includes('/analysis')?'.chat-messages':'html',-1,2);await hold(7)}}}}
   catch(e){results.push({id:key,status:'FAIL',reason:e.message.split('\n')[0]});console.log('SCENE ERROR '+e.message.split('\n')[0])}
   const video=record?page.video():null;await context.close();
   if(video){const file=path.join(out,'scenes',key+'.webm');await video.saveAs(file);await video.delete();scenes.push({key,title,file:path.basename(file),duration_wall_ms:Date.now()-started});}
   fs.writeFileSync(path.join(out,record?'RECORDED_CASE_RESULTS.json':'E2E_CASE_RESULTS.json'),JSON.stringify({cases:results,page_errors:errors},null,2));
   fs.writeFileSync(path.join(out,'SCENES.json'),JSON.stringify(scenes,null,2));
   console.log('END '+key+' '+results.filter(r=>r.status==='FAIL').length+' failures');
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
