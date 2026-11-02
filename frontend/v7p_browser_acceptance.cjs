/* Actual Chromium smoke against local services. No response mocking or token output. */
const fs=require('fs'),path=require('path');
const {chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),base=process.env.V7P_BASE_URL||'http://127.0.0.1:18110';
 const token=fs.readFileSync(path.join(root,'tmp/studio-runtime/access-token.txt'),'utf8').trim();
 const pdf=process.env.V7P_APPLE_PDF;if(!pdf)throw new Error('V7P_APPLE_PDF required');
 const screenshots=path.join(root,'docs/topic3_v7p/screenshots');fs.mkdirSync(screenshots,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.V7P_CHROMIUM_EXECUTABLE?{executablePath:process.env.V7P_CHROMIUM_EXECUTABLE}:{})});const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(base+'/app/#/library');
  await page.getByLabel('Khóa truy cập',{exact:true}).fill(token);
  await page.getByRole('button',{name:/Mở không gian làm việc/}).click();
  await page.getByRole('heading',{name:'Thêm báo cáo tài chính'}).waitFor();
  await page.locator('#pdf-upload').setInputFiles(pdf);
  await page.getByText(path.basename(pdf),{exact:true}).first().waitFor();
  await page.screenshot({path:path.join(screenshots,'upload-selected.png'),fullPage:true});
  await page.getByRole('button',{name:'Tải lên & lập chỉ mục'}).click();
  await page.getByText(/Đã tiếp nhận tài liệu|Tài liệu trùng SHA256/).waitFor();
  await page.screenshot({path:path.join(screenshots,'upload-processing.png'),fullPage:true});
  let doc;
  for(let i=0;i<180;i++){
   const r=await page.request.get(base+'/studio/documents',{headers:{Authorization:'Bearer '+token}});
   const rows=(await r.json()).documents;doc=rows.find(d=>d.filename===path.basename(pdf));
   if(doc?.status==='FAILED')throw new Error('PDF ingestion failed: '+doc.error_code);
   if(doc?.status==='READY')break;
   await page.waitForTimeout(1000);
  }
  if(doc?.status!=='READY')throw new Error('PDF not READY within budget');
  await page.reload();await page.getByText('READY',{exact:true}).first().waitFor();
  await page.getByText('Metadata tự nhận diện · xem nguồn hoặc hiệu chỉnh').click();
  await page.getByText('2025-09-27',{exact:false}).first().waitFor();
  await page.screenshot({path:path.join(screenshots,'upload-ready-metadata.png'),fullPage:true});
  await page.getByRole('button',{name:'Trợ lý tài chính',exact:true}).click();
  await page.getByLabel('Tài liệu trợ lý').selectOption(doc.id);
  const cases=[
   ["What was Apple's net income in fiscal year 2025?",'112010'],
   ['Which geographic segment generated the highest net sales in fiscal year 2025, and how much did it generate?','178353'],
   ["Calculate Apple's year-over-year total net sales growth rate from fiscal 2024 to fiscal 2025. Show the calculation and round to two decimal places.",'6.43']
  ];
  for(let i=0;i<cases.length;i++){
   const [q,value]=cases[i];await page.getByLabel('Câu hỏi trợ lý').fill(q);
   const response=page.waitForResponse(r=>r.url().endsWith('/studio/chat')&&r.request().method()==='POST');
   await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();
   const r=await response;const body=await r.json();
   if(body.status!=='SUPPORTED'||body.values?.[0]!==value)throw new Error('Apple '+i+' failed: '+body.status+' '+body.reason);
   await page.getByRole('log').getByText('Đã xác minh ô nguồn',{exact:true}).last().waitFor();
   await page.screenshot({path:path.join(screenshots,`apple-${i+1}-chat.png`),fullPage:true});
  }
  const source=page.getByRole('log').locator('.source-button').first();await source.click();
  await page.getByText('Trang 32/',{exact:false}).first().waitFor();
  await page.locator('canvas').first().waitFor();
  await page.locator('[data-testid="pdf-page"][data-rendered="true"]').waitFor();
  if(await page.locator('.pdf-highlight.verified').count()<3)throw new Error('Missing cell/row/header highlights');
  await page.screenshot({path:path.join(screenshots,'verified-pdf-page32.png'),fullPage:true});
  await page.getByRole('button',{name:'Quay lại câu hỏi',exact:true}).click();
  await page.getByLabel('Câu hỏi trợ lý').fill("What was Apple's net income in fiscal year 2037?");
  const negative=page.waitForResponse(r=>r.url().endsWith('/studio/chat')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();
  const refused=await (await negative).json();if(refused.values?.length)throw new Error('Future year produced a number');
  await page.screenshot({path:path.join(screenshots,'future-year-refusal.png'),fullPage:true});
  async function ask(question,expected,status){
   await page.getByLabel('Câu hỏi trợ lý').fill(question);
   const response=page.waitForResponse(r=>r.url().endsWith('/studio/chat')&&r.request().method()==='POST');
   await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();const r=await response,body=await r.json();
   if(r.status()!==200||(status&&body.status!==status)||(expected&&body.values?.[0]!==expected))throw new Error('Chat follow-up failed '+body.status+' '+body.reason);
   return body;
  }
  await ask('Total net sales fiscal 2025?','416161','SUPPORTED');
  await ask('Còn năm 2024?','391035','SUPPORTED');
  await page.screenshot({path:path.join(screenshots,'followup-2024.png'),fullPage:true});
  await ask('What does the report say about risk factors?',null,'SOURCE_EXCERPTS');
  await ask('Nghiên cứu doanh nghiệp dựa trên tài liệu đã chọn',null,'SOURCE_EXCERPTS');
  await page.screenshot({path:path.join(screenshots,'sourced-company-research.png'),fullPage:true});
  await page.getByText('Tùy chọn nâng cao · chỉ gửi khi chủ động chọn',{exact:true}).click();
  await page.getByLabel('Áp dụng ràng buộc thủ công').check();
  await page.getByLabel('Chỉ tiêu trợ lý',{exact:true}).selectOption('assets');
  const conflict=await ask(cases[0][0],null,'QUERY_CONTEXT_CONFLICT');
  if(conflict.values?.length)throw new Error('Conflicting constraint produced numeric claim');
  await page.screenshot({path:path.join(screenshots,'advanced-conflict.png'),fullPage:true});
  await page.getByLabel('Áp dụng ràng buộc thủ công').uncheck();
  const available=await(await page.request.get(base+'/studio/documents',{headers:{Authorization:'Bearer '+token}})).json();
  const alternate=available.documents.find(d=>d.id!==doc.id&&d.status==='READY');
  if(alternate){
   await page.getByLabel('Tài liệu trợ lý').selectOption(alternate.id);
   if(await page.getByRole('log').getByText(cases[0][0],{exact:false}).count())throw new Error('Old issuer conversation leaked into alternate source');
   const unsupported=await ask('Doanh thu năm 2025 là bao nhiêu?');
   if(unsupported.status==='SUPPORTED'||unsupported.values?.length)throw new Error('Unverified scanned numeric answer');
   await page.screenshot({path:path.join(screenshots,'nonapple-safe-abstention.png'),fullPage:true});
   await page.getByLabel('Tài liệu trợ lý').selectOption(doc.id);
  }
  await page.getByRole('button',{name:'Kho tài liệu',exact:true}).click();
  await page.getByText('Metadata tự nhận diện · xem nguồn hoặc hiệu chỉnh',{exact:true}).click();
  await page.getByLabel('Doanh nghiệp hiệu chỉnh',{exact:true}).fill('Apple Inc.');
  await page.getByRole('button',{name:'Lưu hiệu chỉnh metadata',exact:true}).click();
  await page.getByText('Đã lưu hiệu chỉnh.',{exact:true}).waitFor();
  await page.reload();await page.getByText('Metadata tự nhận diện · xem nguồn hoặc hiệu chỉnh',{exact:true}).click();
  await page.getByText(/issuer: Apple Inc\./).first().waitFor();
  await page.screenshot({path:path.join(screenshots,'metadata-correction-persisted.png'),fullPage:true});
  await page.getByRole('button',{name:'Research Lab',exact:true}).click();
  await page.getByText('So sánh 3 phương pháp',{exact:false}).first().waitFor();
  await page.getByLabel('Nguồn dữ liệu',{exact:true}).selectOption('USER_UPLOADS');
  await page.getByLabel('Tài liệu tìm kiếm',{exact:true}).selectOption(doc.id);
  await page.getByLabel('Câu hỏi tìm kiếm',{exact:true}).fill('net income fiscal 2025');
  const compared=page.waitForResponse(r=>r.url().endsWith('/studio/compare')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'So sánh 3 phương pháp',exact:true}).click();
  const comparison=await(await compared).json();
  if(!['bm25','dense','hybrid'].every(m=>comparison.arms?.[m]?.results?.length))throw new Error('Missing real comparison arm');
  await page.getByRole('heading',{name:'Độ trễ đo được',exact:true}).waitFor();
  await page.screenshot({path:path.join(screenshots,'research-lab.png'),fullPage:true});
  await page.getByRole('button',{name:'Trợ lý tài chính',exact:true}).click();
  await page.getByText('Công cụ nâng cao và phân tích SEC',{exact:true}).click();
  await page.getByLabel('Nguồn phân tích',{exact:true}).selectOption('SEC');
  await page.getByLabel('Doanh nghiệp SEC',{exact:true}).selectOption('HD');
  await page.getByLabel('Câu hỏi phân tích',{exact:true}).fill('What were HD total assets as of August 2, 2026?');
  const secResponse=page.waitForResponse(r=>r.url().endsWith('/studio/sec/analysis')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Phân tích có bằng chứng',exact:true}).click();
  const sec=await(await secResponse).json();if(sec.status!=='SUPPORTED'||!sec.citations?.length)throw new Error('Real SEC control failed');
  const citationName=sec.citations[0].issuer.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  await page.getByRole('button',{name:new RegExp(citationName)}).last().click();
  const official=page.getByRole('link',{name:/Mở công bố SEC gốc/});await official.waitFor();
  if(await official.getAttribute('href')!==sec.citations[0].source_url)throw new Error('SEC URL/source mismatch');
  await page.screenshot({path:path.join(screenshots,'sec-verified-evidence.png'),fullPage:true});
  const popupEvent=page.waitForEvent('popup');await official.click();const popup=await popupEvent;
  await popup.waitForLoadState('domcontentloaded',{timeout:60000});
  const exactURL=popup.url()===sec.citations[0].source_url;
  const visible=await popup.locator('body').innerText();
  const secNavigation={url:popup.url(),exact_filing_url:exactURL,filing_text_visible:/home depot/i.test(visible)&&!/undeclared automated tool|access denied|request rate threshold/i.test(visible),exact_cell_landing:false};
  await popup.screenshot({path:path.join(screenshots,'sec-official-navigation.png'),fullPage:false});await popup.close();
  await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Mở điều hướng',exact:true}).click();
  await page.screenshot({path:path.join(screenshots,'mobile-navigation.png'),fullPage:true});
  if(errors.length)throw new Error('Browser page errors: '+errors.join(';'));
  const result={status:'PASS',browser:await browser.version(),document_id:doc.id,source_sha256:doc.sha256,
    apple_cases:3,future_year_refusal:true,source_pdf_page:32,followup_2024:true,narrative:true,company_research:true,
    advanced_conflict:true,metadata_correction_reload:true,alternate_source_refusal:!!alternate,
    sec_control:{status:sec.status,values:sec.values,citations:sec.citations},sec_navigation:secNavigation,
    comparison_modes:['bm25','dense','hybrid'],page_errors:errors};
  fs.writeFileSync(path.join(root,'docs/topic3_v7p/V7P_BROWSER_RESULT.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify(result));
 }catch(e){await page.screenshot({path:path.join(screenshots,'failure.png'),fullPage:true});throw e}
 finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exit(1)});
