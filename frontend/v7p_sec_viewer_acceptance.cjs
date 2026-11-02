/* Real SEC answer -> authenticated local source -> displayed exact cell. */
const fs=require('fs'),path=require('path'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),base='http://127.0.0.1:18110';
 const browser=await chromium.launch({headless:true,...(process.env.V7P_CHROMIUM_EXECUTABLE?{executablePath:process.env.V7P_CHROMIUM_EXECUTABLE}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1000},permissions:['clipboard-read','clipboard-write']});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const out=path.join(root,'docs/topic3_v7p/screenshots');
 try{
  await page.goto(base+'/app/#/analysis');await page.getByLabel('Khóa truy cập',{exact:true}).fill(fs.readFileSync(path.join(root,'tmp/studio-runtime/access-token.txt'),'utf8').trim());
  await page.getByRole('button',{name:/Mở không gian làm việc/}).click();
  await page.getByText('Công cụ nâng cao và phân tích SEC',{exact:true}).click();
  await page.getByLabel('Nguồn phân tích',{exact:true}).selectOption('SEC');await page.getByLabel('Doanh nghiệp SEC',{exact:true}).selectOption('HD');
  await page.getByLabel('Câu hỏi phân tích',{exact:true}).fill('What were HD total assets as of August 2, 2026?');
  const answerEvent=page.waitForResponse(r=>r.url().endsWith('/studio/sec/analysis')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Phân tích có bằng chứng',exact:true}).click();const answer=await(await answerEvent).json();
  if(answer.status!=='SUPPORTED'||answer.values?.[0]!=='109384000000')throw Error('Real SEC answer failed');
  const sourceEvent=page.waitForResponse(r=>r.url().endsWith('/studio/sec/evidence')&&r.request().method()==='POST',{timeout:90000});
  await page.getByRole('button',{name:/HOME DEPOT/}).last().click();
  const response=await sourceEvent,view=await response.json();
  if(response.status()!==200||view.status!=='VERIFIED_LOCAL_SEC_SNAPSHOT'||view.source_sha256!=='3d638bc025ef9643317d539f63c3891c8db9b47e35a8edd8040928704d0703f1')throw Error('Source snapshot not verified');
  const selected=page.getByTestId('sec-selected-cell');await selected.waitFor();if(await selected.innerText()!=='109,384')throw Error('Wrong displayed physical cell');
  if(await selected.getAttribute('data-source-column')!=='4'||await selected.locator('..').getAttribute('data-source-row')!=='14')throw Error('Wrong row/column');
  await page.getByRole('heading',{name:'CONSOLIDATED BALANCE SHEETS',exact:true}).waitFor();
  await page.getByText('August 2, 2026',{exact:true}).first().waitFor();await page.getByText('105,095',{exact:true}).waitFor();
  await page.getByText('Provenance và locator',{exact:true}).click();await page.getByText(view.source_sha256,{exact:true}).waitFor();
  await page.screenshot({path:path.join(out,'a7-local-hd-source-desktop.png'),fullPage:true});
  await page.getByRole('button',{name:'Sao chép citation SEC',exact:true}).click();await page.getByText('Đã sao chép citation.',{exact:true}).waitFor();
  const copied=await page.evaluate(()=>navigator.clipboard.readText());if(!copied.includes('row 14 col 4')||!copied.includes('0001628280-26-058715'))throw Error('Citation copy lost locator');
  await page.getByRole('button',{name:'Quay lại câu hỏi',exact:true}).click();
  if(await page.getByLabel('Câu hỏi phân tích',{exact:true}).inputValue()!=='What were HD total assets as of August 2, 2026?')throw Error('Back navigation lost question');
  await page.getByRole('button',{name:/HOME DEPOT/}).last().click();await page.getByTestId('sec-selected-cell').waitFor();
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'a7-local-hd-source-mobile.png'),fullPage:true});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2);if(overflow)throw Error('Mobile page overflows outside table');
  const link=page.getByRole('link',{name:'Mở bản công bố trên SEC.gov',exact:true});if(await link.getAttribute('href')!==view.official_url)throw Error('Official URL mismatch');
  const opened=page.waitForEvent('popup');await link.click();const official=await opened;await official.waitForLoadState('domcontentloaded',{timeout:60000});
  const text=await official.locator('body').innerText();const visible=/home depot/i.test(text)&&/total assets/i.test(text)&&!/undeclared automated tool|access denied/i.test(text);
  const external={status:visible?'PASS':'EXTERNAL_ACCESS_BLOCKED',url:official.url(),correct_url:official.url()===view.official_url,filing_content_visible:visible,exact_cell_landing:false};
  await official.screenshot({path:path.join(out,'a7-official-sec-navigation.png'),fullPage:false});await official.close();
  if(errors.length)throw Error(errors.join(';'));
  const result={browser:await browser.version(),local_status:'PASS',external,source_sha256:view.source_sha256,accession:view.accession,table_id:view.table.id,row:14,column:4,displayed_value:await selected.innerText(),period:view.selected_cell.period_end,unit:view.selected_cell.unit,multiplier:view.selected_cell.multiplier,back_navigation:true,citation_copy:true,mobile_table_scroll:true,page_errors:errors};
  fs.writeFileSync(path.join(root,'docs/topic3_v7p/V7P_REAL_SEC_VIEWER_BROWSER_RESULTS.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }catch(e){await page.screenshot({path:path.join(out,'a7-browser-failure.png'),fullPage:true});throw e}finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exit(1)});
