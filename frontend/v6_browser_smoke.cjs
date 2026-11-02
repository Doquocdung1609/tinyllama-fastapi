const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const root = path.resolve(__dirname, '..');
  const token = fs.readFileSync(path.join(root, 'tmp/studio-runtime/access-token.txt'), 'utf8').trim();
  const browser = await chromium.launch({headless: true});
  const page = await browser.newPage({viewport: {width: 1440, height: 900}, deviceScaleFactor: 1});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(value => sessionStorage.setItem('studio-token', value), token);
  await page.goto('http://127.0.0.1:18110/app/#/compare', {waitUntil: 'networkidle'});
  const section = page.locator('details').filter({has: page.getByText('V6 · đối chiếu từng câu phát triển đã lưu')});
  await section.locator('summary').click();
  await section.getByLabel('Câu hỏi V6 đã lưu').selectOption('AMZN_FY2024');
  await section.getByText('RECORDED_EXPOSED_DEVELOPMENT').waitFor();
  const rows = section.locator('tbody tr');
  const a4 = await rows.filter({has: page.locator('td').filter({hasText: /^A4$/})}).first().innerText();
  const a4r = await rows.filter({hasText: 'A4R · sửa sau khi thấy lỗi'}).first().innerText();
  if (!a4.includes('NO') || !a4r.includes('YES')) throw new Error('Development labels changed');
  const sec = await section.locator('a[href^="https://www.sec.gov/"]').first().getAttribute('href');
  const screenshot = path.join(root, 'docs/topic3_v6/V6_RESEARCH_LAB_SCREEN.png');
  await section.screenshot({path: screenshot});
  await section.getByLabel('Câu hỏi V6 đã lưu').selectOption('INTC_FY2024');
  const intel = await rows.filter({hasText: 'A4R · sửa sau khi thấy lỗi'}).first().innerText();
  if (!intel.includes('UNJUDGED')) throw new Error('Unknown label concealed');
  if (errors.length) throw new Error(errors.join('; '));
  console.log(JSON.stringify({status: 'PASS', amazon_a4: 'NO', amazon_a4r: 'YES',
    intel_a4r: 'UNJUDGED', official_sec_link: sec, page_errors: errors.length, screenshot}));
  await browser.close();
})().catch(error => {console.error(error.message); process.exit(1)});
