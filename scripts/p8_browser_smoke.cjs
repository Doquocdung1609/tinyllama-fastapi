/* Real browser exercise of opt-in HD instant-balance search and citation panel. */
const fs=require('fs');const {chromium}=require('playwright');
async function main(){
 const url=process.env.P8_UI_URL||'http://127.0.0.1:18522';const chrome=process.env.P8_CHROME_PATH;
 const output=process.env.P8_UI_OUTPUT||'docs/topic3/milestone_d/recovery/p8/p8_browser_results.json';
 if(!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(url)||!chrome)throw Error('LOCAL_UI_AND_CHROME_REQUIRED');
 const browser=await chromium.launch({headless:true,executablePath:chrome});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 try{
  await page.goto(url,{waitUntil:'domcontentloaded',timeout:15000});
  await page.getByText('Financial Intelligence — Research v1').waitFor({timeout:15000});
  await page.getByRole('combobox',{name:'Research workflow'}).click();
  await page.getByRole('option',{name:'automatic_real'}).click();
  await page.waitForFunction(()=>document.querySelector('textarea')?.value.includes("P&G's net sales"),null,{timeout:10000});
  await page.getByRole('textbox',{name:'Financial question'}).fill('What were HD total assets as of August 2, 2026?');
  await page.getByRole('textbox',{name:'Financial question'}).press('Tab');
  await page.getByRole('button',{name:'Research search'}).click();
  await page.waitForFunction(()=>document.body.innerText.includes('109384000000')&&document.body.innerText.includes('SUPPORTED'),null,{timeout:30000})
   .catch(async e=>{console.error('UI_BODY', (await page.locator('body').innerText()).slice(-2500));throw e});
  const evidence=page.locator('[data-testid="stExpander"]').last();await evidence.locator('summary').click();
  const locatorText=evidence.getByText('Structural locator:',{exact:false});
  for(let attempt=0;attempt<4 && !await locatorText.isVisible();attempt++){
   await evidence.locator('summary').click();await page.waitForTimeout(300);
  }
  if(!await locatorText.isVisible())throw Error('EVIDENCE_PANEL_NOT_VISIBLE');
  const panel=await evidence.innerText();
  const details=['0001628280-26-058715','Total assets','109,384','2026-08-02','Structural locator:','not a verified row anchor'];
  if(details.some(x=>!panel.includes(x)))throw Error('HD_CITATION_PANEL_INCOMPLETE:'+details.filter(x=>!panel.includes(x))+':'+panel.slice(0,1200));
  const link=evidence.locator('a[href^="https://www.sec.gov/Archives/"]').first();const href=await link.getAttribute('href');
  if(href.includes('#'))throw Error('UNVERIFIED_FRAGMENT');
  const [popup]=await Promise.all([page.waitForEvent('popup',{timeout:15000}),link.click()]);
  await popup.waitForLoadState('domcontentloaded',{timeout:15000}).catch(()=>{});
  const popupText=await popup.locator('body').innerText().catch(()=>'');
  const exactFiling=popup.url()===href;if(!exactFiling)throw Error('WRONG_FILING');
  await popup.close();
  await page.screenshot({path:output.replace(/\.json$/,'.png'),fullPage:true});
  await page.getByRole('textbox',{name:'Financial question'}).fill('Compare HD total assets as of February 1, 2026 and as of August 2, 2026.');
  await page.getByRole('button',{name:'Research search'}).click();
  await page.waitForFunction(()=>document.body.innerText.includes('105095000000')&&document.body.innerText.includes('109384000000'),null,{timeout:30000});
  const result={schema_version:'topic3-p8-browser/v1',exact_value_visible:true,comparison_values_visible:true,
   citation_fields_visible:true,copyable_citation_json_visible:await evidence.locator('code').count()>0,
   correct_filing_opened:exactFiling,source_url:href,table_visible_in_popup:popupText.includes('CONSOLIDATED BALANCE SHEETS'),
   row_visible_in_popup:popupText.includes('TOTAL ASSETS')&&popupText.includes('109,384'),
   exact_cell_browser_confirmed:false,manual_locator_guidance_visible:true};
  fs.mkdirSync(require('path').dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify({exact:true,comparison:true,filing:exactFiling,row:result.row_visible_in_popup}));
 }finally{await browser.close();}
}main().catch(e=>{console.error(e);process.exitCode=1});
