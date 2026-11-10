/* Post-A7 real Apple/HPG UI regression; no response mocking. */
const fs=require('fs'),path=require('path'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),base='http://127.0.0.1:18110',token=fs.readFileSync(path.join(root,'tmp/studio-runtime/access-token.txt'),'utf8').trim();
 const browser=await chromium.launch({headless:true,...(process.env.V7P_CHROMIUM_EXECUTABLE?{executablePath:process.env.V7P_CHROMIUM_EXECUTABLE}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});await page.goto(base+'/app/#/analysis');
  await page.getByLabel('Khóa truy cập',{exact:true}).fill(token);await page.getByRole('button',{name:/Mở không gian làm việc/}).click();
  const docs=(await(await page.request.get(base+'/studio/documents',{headers:{Authorization:'Bearer '+token}})).json()).documents;
  const apple=docs.find(d=>d.sha256==='3eb270b22acb7d8d8e9c32a43dc221dec3345f8e4bca02755fdbc1ee16c823de');
  await page.getByLabel('Tài liệu trợ lý').selectOption(apple.id);const cases=[];
  for(const [question,value] of [["What was Apple's net income in fiscal year 2025?",'112010'],['Which geographic segment generated the highest net sales in fiscal year 2025, and how much did it generate?','178353'],["Calculate Apple's year-over-year total net sales growth rate from fiscal 2024 to fiscal 2025. Show the calculation and round to two decimal places.",'6.43']]){
   await page.getByLabel('Câu hỏi trợ lý').fill(question);const event=page.waitForResponse(r=>r.url().endsWith('/studio/chat')&&r.request().method()==='POST',{timeout:120000});
   await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();const a=await(await event).json();
   if(a.status!=='SUPPORTED'||a.values?.[0]!==value||a.warnings?.length||!a.citations.every(c=>c.evidence_id?.startsWith('pdfcell_')))throw Error('Apple post-A7 consistency failed');
   cases.push({question,status:a.status,values:a.values,unit:a.unit,warnings:a.warnings,citations:a.citations,retrieved_excerpt_verification:a.retrieved_excerpt_verification});
  }
  await page.getByRole('log').locator('.source-button').first().click();await page.getByText('Trang 32/',{exact:false}).first().waitFor();await page.locator('[data-testid="pdf-page"][data-rendered="true"]').waitFor();
  if(await page.locator('.pdf-highlight.verified').count()<3)throw Error('PDF cell/header/row navigation regressed');
  await page.screenshot({path:path.join(root,'docs/topic3_v7p/screenshots/a7-apple-pdf-regression.png'),fullPage:true});
  const hpg=docs.find(d=>d.filename.includes('hpg'));if(!hpg||hpg.status!=='READY')throw Error('Existing HPG not READY');
  const h=await page.request.post(base+'/studio/chat',{headers:{Authorization:'Bearer '+token},data:{question:'Doanh thu năm 2025 là bao nhiêu?',document_ids:[hpg.id]}});const refused=await h.json();if(h.status()!==200||refused.status==='SUPPORTED'||refused.values?.length)throw Error('HPG unsafe numeric claim');
  const result={browser:await browser.version(),apple_cases:cases,source_page:32,verified_highlights:await page.locator('.pdf-highlight.verified').count(),hpg:{document_id:hpg.id,status:hpg.status,pages:hpg.pages,chunks:hpg.chunks,numeric_status:refused.status,values:refused.values},status:'PASS'};
  fs.writeFileSync(path.join(root,'docs/topic3_v7p/V7P_A7_PDF_REGRESSION.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({status:'PASS',apple:3,hpg_safe_refusal:true,pdf_page:32}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exit(1)});
