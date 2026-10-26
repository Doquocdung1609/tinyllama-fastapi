/* Real Chromium interaction with the opt-in local Streamlit UI. No synthetic assertions. */
const fs = require('fs');
const { chromium } = require('playwright');

async function main() {
  const url = process.env.P6_UI_URL || 'http://127.0.0.1:18502';
  const chrome = process.env.P6_CHROME_PATH;
  const output = process.env.P6_UI_OUTPUT || 'docs/topic3/milestone_d/recovery/p6/p6_ui_evidence.json';
  if (!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(url) || !chrome) throw new Error('LOCAL_URL_AND_CHROME_REQUIRED');
  const browser = await chromium.launch({ headless: true, executablePath: chrome });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const findings = { schema_version: 'topic3-p6-browser-smoke/v1', browser: 'Chromium/Chrome headless',
    local_url: url, synthetic: false, cases: [] };
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.getByText('Financial Intelligence — Research v1').waitFor({ timeout: 15000 });
    await page.getByRole('combobox', { name: 'Research workflow' }).click();
    await page.getByRole('option', { name: 'automatic_real' }).click();
    const exact = "What were P&G's net sales for the three months ended September 30, 2026?";
    await page.getByRole('textbox', { name: 'Financial question' }).fill(exact);
    let start = Date.now();
    await page.getByRole('button', { name: 'Research search' }).click();
    await page.getByText('Verified SEC source cells').waitFor({ timeout: 30000 });
    const exactText = await page.locator('body').innerText();
    if (!exactText.includes('23276000000') || !exactText.includes('SUPPORTED')) throw new Error('EXACT_UI_VALUE_MISSING');
    findings.cases.push({ id: 'exact', status: 'LIVE_VERIFIED', elapsed_ms: Date.now()-start,
      visible_value: '23276000000', visible_status: 'SUPPORTED' });
    const evidenceExpander = page.locator('[data-testid="stExpander"]').last();
    await evidenceExpander.locator('summary').click();
    const evidenceText = await evidenceExpander.innerText();
    const link = evidenceExpander.locator('a[href^="https://www.sec.gov/Archives/"]').first();
    const href = await link.getAttribute('href');
    if (!evidenceText.includes('VERIFIED_SOURCE_CELL') || !evidenceText.includes('Partial extraction') ||
        !evidenceText.includes('structural_path') || !href?.includes('/80424/')) throw new Error('CITATION_OR_WARNING_MISSING');
    findings.cases.push({ id: 'citation', status: 'LIVE_VERIFIED', source_url: href,
      verification_visible: true, locator_visible: true, partial_warning_visible: true });
    const [sourcePage] = await Promise.all([page.waitForEvent('popup', { timeout: 15000 }), link.click()]);
    await sourcePage.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => {});
    const openedUrl = sourcePage.url();
    if (!openedUrl.startsWith(href)) throw new Error('SOURCE_NAVIGATION_WRONG_URL');
    const sourceText = await sourcePage.locator('body').innerText().catch(() => '');
    findings.cases.push({ id: 'source_navigation', status: 'LIVE_VERIFIED', opened_url: openedUrl,
      source_row_visible: sourceText.includes('23,276') && sourceText.includes('22,386') });
    await sourcePage.close();
    await page.screenshot({ path: output.replace(/\.json$/, '.png'), fullPage: true });
    const comparison = 'Compare P&G net sales for the quarter ended September 30, 2025 and the quarter ended September 30, 2026.';
    await page.getByRole('textbox', { name: 'Financial question' }).fill(comparison);
    start = Date.now();
    await page.getByRole('button', { name: 'Research search' }).click();
    await page.waitForFunction(() => document.body.innerText.includes('22386000000') &&
                                   document.body.innerText.includes('23276000000'), undefined, { timeout: 30000 });
    const compareText = await page.locator('body').innerText();
    if (!compareText.includes('22386000000') || !compareText.includes('23276000000')) throw new Error('COMPARISON_UI_VALUES_MISSING');
    findings.cases.push({ id: 'comparison', status: 'LIVE_VERIFIED', elapsed_ms: Date.now()-start,
      visible_values: ['22386000000','23276000000'] });
    fs.mkdirSync(require('path').dirname(output), { recursive: true });
    fs.writeFileSync(output, JSON.stringify(findings, null, 2)+'\n');
    console.log(JSON.stringify({ status: 'PASS', cases: findings.cases.map(x=>x.id), output }));
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
