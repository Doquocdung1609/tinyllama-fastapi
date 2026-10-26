/* Browser-observed SEC navigation, with distinct filing/table/row/cell states. */
const fs = require('fs');
const { chromium } = require('playwright');

async function main() {
  const url = process.env.P7_UI_URL || 'http://127.0.0.1:18512';
  const chrome = process.env.P7_CHROME_PATH;
  const output = process.env.P7_UI_OUTPUT || 'docs/topic3/milestone_d/recovery/p7/p7_browser_evidence.json';
  if (!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(url) || !chrome) throw new Error('LOCAL_UI_AND_CHROME_REQUIRED');
  const browser = await chromium.launch({headless: true, executablePath: chrome});
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
  try {
    await page.goto(url, {waitUntil: 'domcontentloaded', timeout: 15000});
    await page.getByText('Financial Intelligence — Research v1').waitFor({timeout: 15000});
    await page.getByRole('combobox', {name: 'Research workflow'}).click();
    await page.getByRole('option', {name: 'automatic_real'}).click();
    await page.getByRole('textbox', {name: 'Financial question'}).fill("What were P&G's net sales for the three months ended September 30, 2026?");
    await page.getByRole('button', {name: 'Research search'}).click();
    await page.getByText('Verified SEC source cells').waitFor({timeout: 30000});
    const expander = page.locator('[data-testid="stExpander"]').last();
    await expander.locator('summary').click();
    const panel = await expander.innerText();
    const guidance = panel.includes('not a verified row anchor') && panel.includes('Locate the row manually');
    if (!guidance || !panel.includes('23,276') || !panel.includes('2026-09-30') || !panel.includes('structural_path'))
      throw new Error('VERIFIED_LOCATOR_GUIDANCE_MISSING: ' + panel.slice(0, 1400));
    const link = expander.locator('a[href^="https://www.sec.gov/Archives/"]').first();
    const href = await link.getAttribute('href');
    if (href.includes('#')) throw new Error('UNVERIFIED_SEC_FRAGMENT');
    const [popup] = await Promise.all([page.waitForEvent('popup', {timeout: 15000}), link.click()]);
    await popup.waitForLoadState('domcontentloaded', {timeout: 15000}).catch(() => {});
    const opened = popup.url();
    const text = await popup.locator('body').innerText().catch(() => '');
    const filingOpened = opened === href;
    if (!filingOpened) throw new Error('INCORRECT_SEC_FILING_URL');
    const result = {schema_version: 'topic3-p7-browser-navigation/v1', local_ui: url,
      exact_answer_visible: (await page.locator('body').innerText()).includes('23276000000'),
      citation_url: href, opened_url: opened, correct_filing_opened: filingOpened,
      verified_row_anchor_claimed: false, manual_locator_guidance_visible: guidance,
      correct_table_visible_in_popup: text.includes('CONSOLIDATED STATEMENTS OF EARNINGS') && text.includes('NET SALES'),
      exact_row_visible_in_popup: text.includes('NET SALES') && text.includes('23,276') && text.includes('22,386'),
      exact_cell_confirmed_by_browser: false,
      popup_text_length: text.length};
    fs.mkdirSync(require('path').dirname(output), {recursive: true});
    fs.writeFileSync(output, JSON.stringify(result, null, 2)+'\n');
    await page.screenshot({path: output.replace(/\.json$/, '.png'), fullPage: true});
    console.log(JSON.stringify({filing: result.correct_filing_opened, guidance,
      table: result.correct_table_visible_in_popup, row: result.exact_row_visible_in_popup}));
    await popup.close();
  } finally { await browser.close(); }
}
main().catch(e => { console.error(e); process.exitCode = 1; });
