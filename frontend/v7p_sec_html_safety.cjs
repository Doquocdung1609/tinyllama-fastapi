const fs=require('fs'),path=require('path'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),base='http://127.0.0.1:18113',token=process.env.V7P_SYNTHETIC_TOKEN;
 const browser=await chromium.launch({headless:true,...(process.env.V7P_CHROMIUM_EXECUTABLE?{executablePath:process.env.V7P_CHROMIUM_EXECUTABLE}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});const unsafeRequests=[],dialogs=[];
  page.on('request',r=>{if(!r.url().startsWith(base))unsafeRequests.push(r.url())});page.on('dialog',async d=>{dialogs.push(d.message());await d.dismiss()});
  await page.goto(base+'/app/');await page.getByLabel('Khóa truy cập',{exact:true}).fill(token);await page.getByRole('button',{name:/Mở không gian làm việc/}).click();
  const fixture=await(await page.request.get(base+'/studio/security-fixture',{headers:{Authorization:'Bearer '+token}})).json();
  await page.evaluate(f=>{sessionStorage.setItem('selected-evidence',JSON.stringify({source_kind:'SEC',text:f.label,source_reference:f.reference}));},fixture);
  await page.goto(base+'/app/#/viewer');await page.reload();await page.getByTestId('sec-selected-cell').waitFor();
  await page.getByText('Encoded <script>window.SEC_PWNED=4</script>',{exact:true}).waitFor();
  const active=await page.locator('.sec-source-viewer script,.sec-source-viewer img,.sec-source-viewer iframe,.sec-source-viewer [onclick],.sec-source-viewer a[href^="javascript:"]').count();
  if(active||dialogs.length||unsafeRequests.length||await page.evaluate(()=>window.SEC_PWNED))throw Error('Unsafe HTML activated');
  await page.screenshot({path:path.join(root,'docs/topic3_v7p/screenshots/a7-synthetic-html-safety.png'),fullPage:true});
  await page.request.post(base+'/studio/security-fixture/tamper',{headers:{Authorization:'Bearer '+token}});await page.reload();
  await page.getByRole('alert').filter({hasText:'SOURCE_HASH_MISMATCH'}).waitFor();
  if(await page.getByTestId('sec-selected-cell').count())throw Error('Stale verified cell remained visible');
  await page.screenshot({path:path.join(root,'docs/topic3_v7p/screenshots/a7-synthetic-tamper-refusal.png'),fullPage:true});
  const result={status:'PASS',label:fixture.label,browser:await browser.version(),active_html_nodes:active,unsafe_network_requests:unsafeRequests,dialogs,script_executed:false,encoded_payload_rendered_as_text:true,tampered_source_hidden:true};
  fs.writeFileSync(path.join(root,'docs/topic3_v7p/V7P_SEC_HTML_SAFETY_BROWSER.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exit(1)});
