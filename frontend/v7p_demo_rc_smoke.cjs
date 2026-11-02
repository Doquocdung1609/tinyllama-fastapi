/* Fresh real-service demo smoke. Only the upload sample is source-derived. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),base='http://127.0.0.1:18110',token=fs.readFileSync(path.join(root,'tmp/studio-runtime/access-token.txt'),'utf8').trim();
 const browser=await chromium.launch({headless:true,...(process.env.V7P_CHROMIUM_EXECUTABLE?{executablePath:process.env.V7P_CHROMIUM_EXECUTABLE}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(45000);
 const headers={Authorization:'Bearer '+token},cases=[],errors=[],shots=path.join(root,'docs/topic3_v7p/screenshots');let uploaded,created=false,passed=false;
 page.on('pageerror',e=>errors.push(e.message));
 const capture=(id,input,output,extra={})=>cases.push({scenario:id,input,output,browser_result:'PASS',...extra});
 const cite=a=>(a.citations||[]).map(c=>({document_id:c.document_id,source_sha256:c.source_sha256,page:c.page,row_label:c.row_label,period:c.period_end||c.period||c.report_period,source_location:c.source_location}));
 async function ask(q){
  await page.getByLabel('Câu hỏi trợ lý').fill(q);const pending=page.waitForResponse(r=>r.url().endsWith('/studio/chat')&&r.request().method()==='POST',{timeout:120000});
  await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();const r=await pending;assert.equal(r.status(),200);const a=await r.json();assert.deepEqual(r.request().postDataJSON().constraints,{});return a;
 }
 try{
  await page.goto(base+'/app/#/library');await page.getByLabel('Khóa truy cập',{exact:true}).fill(token);await page.getByRole('button',{name:/Mở không gian làm việc/}).click();
  const docs=(await(await page.request.get(base+'/studio/documents',{headers})).json()).documents;
  const apple=docs.find(d=>d.sha256==='3eb270b22acb7d8d8e9c32a43dc221dec3345f8e4bca02755fdbc1ee16c823de'),hpg=docs.find(d=>d.filename.includes('hpg'));
  assert(apple&&hpg&&apple.status==='READY'&&hpg.status==='READY');
  // New, bounded upload uses real original pages1/32, clearly not the full filing.
  const sample=path.join(root,'tmp/topic3/v7p-demo-upload-2pages.pdf');await page.locator('#pdf-upload').setInputFiles(sample);
  await page.getByText(path.basename(sample),{exact:true}).first().waitFor();
  const uploadEvent=page.waitForResponse(r=>r.url().endsWith('/studio/documents')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Tải lên & lập chỉ mục',exact:true}).click();const upload=await uploadEvent;assert.equal(upload.status(),202);uploaded=await upload.json();created=!uploaded.duplicate;
  assert(![apple.id,hpg.id].includes(uploaded.id));const stages=[];
  for(let i=0;i<180;i++){
   uploaded=await(await page.request.get(base+'/studio/documents/'+uploaded.id,{headers})).json();
   if(stages.at(-1)!==uploaded.stage)stages.push(uploaded.stage);
   if(uploaded.status==='READY'||uploaded.status==='FAILED')break;await page.waitForTimeout(1000);
  }
  assert.equal(uploaded.status,'READY');assert.equal(uploaded.pages,2);
  await page.reload();await page.getByRole('heading',{name:'Thêm báo cáo tài chính'}).waitFor();await page.getByText('READY',{exact:true}).first().waitFor();
  await page.getByText('Metadata tự nhận diện · xem nguồn hoặc hiệu chỉnh',{exact:true}).click();
  const correction='Apple Inc. · nhãn hiệu chỉnh demo';await page.getByLabel('Doanh nghiệp hiệu chỉnh',{exact:true}).fill(correction);
  await page.getByRole('button',{name:'Lưu hiệu chỉnh metadata',exact:true}).click();await page.getByText('Đã lưu hiệu chỉnh.',{exact:true}).waitFor();
  const duplicate=await page.request.post(base+'/studio/documents',{headers,multipart:{file:{name:path.basename(sample),mimeType:'application/pdf',buffer:fs.readFileSync(sample)}}});assert.equal(duplicate.status(),202);
  const duplicated=await duplicate.json();assert(duplicated.duplicate);assert.equal(duplicated.issuer,correction);
  await page.reload();await page.getByText('Metadata tự nhận diện · xem nguồn hoặc hiệu chỉnh',{exact:true}).click();await page.getByText('issuer: '+correction,{exact:false}).waitFor();
  await page.screenshot({path:path.join(shots,'rc-upload-ready.png'),fullPage:true});
  capture(6,'Upload with no issuer/year/form inputs',{status:uploaded.status,pages:uploaded.pages,chunks:uploaded.chunks,source_sha256:uploaded.sha256,stages,explicit_correction_retained:true},{limitation:'SOURCE_DERIVED_TWO_PAGE_SAMPLE from original Apple pages1/32; not the complete original report. No financial QA claim made on this sample.'});
  await page.getByRole('button',{name:'Trợ lý tài chính',exact:true}).click();await page.getByLabel('Tài liệu trợ lý').selectOption(apple.id);
  for(const [id,q,value] of [[1,"What was Apple's net income in fiscal year 2025?",'112010'],[2,'Which geographic segment generated the highest net sales in fiscal year 2025, and how much did it generate?','178353'],[3,"Calculate Apple's year-over-year total net sales growth rate from fiscal 2024 to fiscal 2025. Show the calculation and round to two decimal places.",'6.43']]){
   const a=await ask(q);assert.equal(a.status,'SUPPORTED');assert.deepEqual(a.values,[value]);assert.deepEqual(a.warnings,[]);capture(id,q,{status:a.status,values:a.values,unit:a.unit,verification:a.verification_status,citations:cite(a)});
   if(id===1){
    await page.getByRole('log').locator('.source-button').last().click();await page.getByText('Trang 32/',{exact:false}).first().waitFor();await page.locator('[data-testid="pdf-page"][data-rendered="true"]').waitFor();assert(await page.locator('.pdf-highlight.verified').count()>=3);
    await page.getByRole('button',{name:'Quay lại câu hỏi',exact:true}).click();assert.equal(await page.getByLabel('Tài liệu trợ lý').inputValue(),apple.id);await page.getByRole('log').getByText('112.010 triệu USD',{exact:true}).waitFor();
   }
  }
  const follow=await ask('Còn năm 2024?');assert.deepEqual(follow.values,['391035']);capture(7,'Còn năm 2024?',{status:follow.status,values:follow.values,period:follow.period,citations:cite(follow)});
  await page.screenshot({path:path.join(shots,'rc-financial-chat.png'),fullPage:true});
  const refusals=[];for(const q of ["What was Microsoft's net income in fiscal year 2025?","What was Apple's net income in fiscal year 2037?"]){const a=await ask(q);assert.notEqual(a.status,'SUPPORTED');assert(!a.values?.length);refusals.push({question:q,status:a.status,reason:a.reason,values:a.values})}capture(8,'Wrong company and FY2037',refusals);
  await page.getByLabel('Tài liệu trợ lý').selectOption(hpg.id);const h=await ask('Doanh thu năm 2025 là bao nhiêu?');assert.notEqual(h.status,'SUPPORTED');assert(!h.values?.length);
  const found=await(await page.request.post(base+'/studio/query',{headers,data:{query:'doanh thu bán hàng',document_ids:[hpg.id],source:'USER_UPLOADS',mode:'bm25',search_profile:'auto'}})).json();assert(found.results.length>0);
  capture(9,'Search and ask existing HPG scanned PDF',{status:hpg.status,pages:hpg.pages,chunks:hpg.chunks,retrieved:found.results.length,source_sha256:hpg.sha256,numeric_status:h.status,reason:h.reason,values:h.values},{limitation:'Existing OCR/index revalidated, not rebuilt; unsupported numeric mapping remains refused.'});
  await page.getByText('Công cụ nâng cao và phân tích SEC',{exact:true}).click();await page.getByLabel('Nguồn phân tích',{exact:true}).selectOption('SEC');await page.getByLabel('Doanh nghiệp SEC',{exact:true}).selectOption('HD');
  const question='What were HD total assets as of August 2, 2026?';await page.getByLabel('Câu hỏi phân tích',{exact:true}).fill(question);
  const secEvent=page.waitForResponse(r=>r.url().endsWith('/studio/sec/analysis')&&r.request().method()==='POST',{timeout:120000});await page.getByRole('button',{name:'Phân tích có bằng chứng',exact:true}).click();const a=await(await secEvent).json();assert.equal(a.status,'SUPPORTED');assert.deepEqual(a.values,['109384000000']);
  await page.locator('.metric-value').getByText('109.384 triệu USD',{exact:true}).waitFor();
  const sourceEvent=page.waitForResponse(r=>r.url().endsWith('/studio/sec/evidence')&&r.request().method()==='POST',{timeout:120000});await page.getByRole('button',{name:/HOME DEPOT/}).last().click();const v=await(await sourceEvent).json();assert.equal(v.status,'VERIFIED_LOCAL_SEC_SNAPSHOT');
  assert.equal(await page.getByTestId('sec-selected-value').innerText(),'109.384 triệu USD');assert.equal(await page.getByTestId('sec-selected-cell').innerText(),'109,384');await page.getByText('Số dư tại ngày: 2026-08-02',{exact:true}).waitFor();assert.equal(await page.getByText(v.source_sha256,{exact:true}).isVisible(),false);
  assert.equal(await page.getByText(/Kỳ filing/).count(),0);await page.getByText(/Kỳ báo cáo kết thúc: 2026-08-02/).waitFor();
  const colors=await page.evaluate(()=>({cell:getComputedStyle(document.querySelector('.sec-selected-cell')).backgroundColor,column:getComputedStyle(document.querySelector('tr:not(.sec-selected-row) td.sec-selected-column')).backgroundColor,row:getComputedStyle(document.querySelector('.sec-selected-row td:not(.sec-selected-cell):not(.sec-selected-column)')).backgroundColor}));
  assert.deepEqual(colors,{cell:'rgb(187, 247, 208)',column:'rgb(224, 242, 254)',row:'rgb(255, 247, 237)'});
  await page.screenshot({path:path.join(shots,'rc-sec-viewer-desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),false);await page.screenshot({path:path.join(shots,'rc-sec-viewer-mobile.png'),fullPage:true});await page.setViewportSize({width:1440,height:1000});
  capture(4,question,{status:a.status,values:a.values,unit:a.unit,display:'109.384 triệu USD',viewer_status:v.status,source_sha256:v.source_sha256,filing_date:v.filing_date,report_period:v.report_period,period:v.selected_cell.period_end,source_locator:v.locator,colors});
  const link=page.getByRole('link',{name:'Mở bản công bố trên SEC.gov',exact:true});assert.equal(await link.getAttribute('href'),v.official_url);await page.getByText(/SEC.gov có thể hạn chế truy cập tự động/).waitFor();
  const popupEvent=page.waitForEvent('popup');await link.click();const external=await popupEvent;await external.waitForLoadState('domcontentloaded',{timeout:60000});const body=await external.locator('body').innerText();const denied=/undeclared automated tool|access denied|request rate threshold/i.test(body);
  capture(5,'Open registered SEC.gov link',{url:external.url(),correct_url:external.url()===v.official_url,external_access:denied?'EXTERNAL_ACCESS_BLOCKED':/home depot/i.test(body)?'FILING_TEXT_VISIBLE':'NOT_VERIFIED',exact_cell_landing:false},{limitation:'No stealth/retries or exact external cell-landing claim.'});await external.close();
  await page.getByRole('button',{name:'Quay lại câu hỏi',exact:true}).click();assert.equal(await page.getByLabel('Câu hỏi phân tích',{exact:true}).inputValue(),question);await page.locator('.metric-value').getByText('109.384 triệu USD',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Research Lab',exact:true}).click();await page.getByRole('button',{name:'So sánh 3 phương pháp',exact:true}).waitFor();await page.getByText('Kết quả đã đo trước đây — không phải truy vấn vừa chạy.',{exact:true}).waitFor();await page.getByText(/Nhãn tạm thời không phải đánh giá độc lập của con người/).waitFor();capture(10,'Open Research Lab',{accessible:true,benchmark_not_executed:true},{limitation:'Interactive product comparison is not a newly scored frozen benchmark; integrity audit recorded separately.'});
  assert.deepEqual(errors,[]);assert.equal(cases.length,10);passed=true;
 }catch(e){await page.screenshot({path:path.join(shots,'rc-smoke-failure.png'),fullPage:true});throw e}
 finally{
  if(created&&uploaded){const r=await page.request.delete(base+'/studio/documents/'+uploaded.id+'?confirm='+uploaded.id,{headers});assert.equal(r.status(),200)}
  if(passed)fs.writeFileSync(path.join(root,'docs/topic3_v7p/V7P_RELEASE_CANDIDATE_RESULTS.json'),JSON.stringify({status:'PASS',browser:await browser.version(),scenarios:cases.sort((a,b)=>a.scenario-b.scenario),page_errors:errors,new_upload_sample_removed:created},null,2));
  await browser.close();
 }
 console.log(JSON.stringify({status:'PASS',scenarios:cases.length,page_errors:errors}));
})().catch(e=>{console.error(e.message);process.exit(1)});
