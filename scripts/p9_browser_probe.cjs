/* Browser evidence for the opt-in Streamlit page; never invent a SEC row anchor. */
const fs=require('fs');
const {chromium}=require('playwright');

async function main(){
 const url=process.env.P9_UI_URL,output=process.env.P9_UI_OUTPUT,chrome=process.env.P9_CHROME_PATH;
 if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(url)||!output||!chrome)throw Error('P9_LOCAL_UI_CONFIG_REQUIRED');
 const browser=await chromium.launch({headless:true,executablePath:chrome});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 try{
  await page.goto(url,{waitUntil:'domcontentloaded',timeout:20000});
  await page.getByText('Financial Intelligence — Research v1').waitFor({timeout:20000});
  await page.getByRole('combobox',{name:'Research workflow'}).click();
  await page.getByRole('option',{name:'automatic_real'}).click();
  await page.waitForFunction(()=>document.querySelector('textarea')?.value.includes("P&G's net sales"),null,{timeout:15000});
  await page.getByRole('textbox',{name:'Financial question'}).fill('What were HD total assets as of August 2, 2026?');
  await page.getByRole('textbox',{name:'Financial question'}).press('Tab');
  await page.getByRole('button',{name:'Research search'}).click();
  await page.waitForFunction(()=>document.body.innerText.includes('109384000000')&&document.body.innerText.includes('SUPPORTED'),null,{timeout:45000});
  const evidence=page.locator('[data-testid="stExpander"]').filter({hasText:'HOME DEPOT'}).last();
  await evidence.waitFor({timeout:15000});
  const summary=evidence.locator('summary');
  if(await summary.getAttribute('aria-expanded')!=='true')await summary.click();
  await evidence.getByText('Structural locator:',{exact:false}).waitFor({state:'visible',timeout:15000});
  const panel=await evidence.innerText();
  const details=['0001628280-26-058715','TOTAL ASSETS','109,384','2026-08-02','Structural locator:','not a verified row anchor'];
  if(details.some(x=>!panel.toUpperCase().includes(x.toUpperCase())))throw Error('P9_CITATION_PANEL_INCOMPLETE:'+details.filter(x=>!panel.toUpperCase().includes(x.toUpperCase())));
  const link=evidence.locator('a[href^="https://www.sec.gov/Archives/"]').first();
  const href=await link.getAttribute('href');if(href.includes('#'))throw Error('UNVERIFIED_FRAGMENT');
  const [popup]=await Promise.all([page.waitForEvent('popup',{timeout:20000}),link.click()]);
  await popup.waitForLoadState('domcontentloaded',{timeout:20000}).catch(()=>{});
  const popupText=await popup.locator('body').innerText().catch(()=>'');
  const exactFiling=popup.url()===href;if(!exactFiling)throw Error('WRONG_SEC_FILING');
  await popup.close();
  await page.getByRole('textbox',{name:'Financial question'}).fill('Compare HD total assets as of February 1, 2026 and as of August 2, 2026.');
  await page.getByRole('button',{name:'Research search'}).click();
  await page.waitForFunction(()=>document.body.innerText.includes('105095000000')&&document.body.innerText.includes('109384000000'),null,{timeout:45000});
  const result={schema_version:'topic3-p9-browser/v1',real_sec_exact_value_visible:true,
   real_sec_comparison_visible:true,citation_panel_visible:true,
   copyable_json_visible:await evidence.locator('code').count()>0,
   official_filing_opened:exactFiling,source_url:href,
   table_visible_in_popup:popupText.includes('CONSOLIDATED BALANCE SHEETS'),
   row_visible_in_popup:popupText.includes('TOTAL ASSETS')&&popupText.includes('109,384'),
   exact_cell_browser_confirmed:false,unverified_anchor_disclosed:panel.includes('not a verified row anchor')};
  fs.mkdirSync(require('path').dirname(output),{recursive:true});
  await page.screenshot({path:output.replace(/\.json$/,'.png'),fullPage:true});
  fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result));
 }catch(error){
  fs.mkdirSync(require('path').dirname(output),{recursive:true});
  await page.screenshot({path:output.replace(/\.json$/,'.failure.png'),fullPage:true}).catch(()=>{});
  console.error('P9_UI_DOM', (await page.locator('body').innerText().catch(()=>'' )).slice(-3500));
  throw error;
 }finally{await browser.close();}
}
main().catch(error=>{console.error(error);process.exitCode=1});
