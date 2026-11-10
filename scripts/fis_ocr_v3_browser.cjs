const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require('../frontend/node_modules/playwright')

const output = path.resolve('tmp/ocr-v3')
const url = 'http://127.0.0.1:18112'
const id = '4a92af827aaf1e73e017544d0ff20d0d'
const token = fs.readFileSync('tmp/studio-runtime/access-token.txt', 'utf8').trim()
const headers = { Authorization: 'Bearer ' + token }
const results = []

async function check(name, test) {
  try {
    results.push({ name, status: 'PASS', ...await test() })
  } catch (error) {
    results.push({ name, status: 'FAIL', reason: error.message })
  }
  fs.writeFileSync(path.join(output, 'browser.json'), JSON.stringify(results, null, 2))
}

async function open(browser, route, viewport = { width: 1440, height: 900 }) {
  const page = await browser.newPage({ viewport })
  await page.addInitScript(value => sessionStorage.setItem('studio-token', value), token)
  await page.goto(url + '/app/#/' + route)
  return page
}

async function api(route) {
  const reply = await fetch(url + '/studio' + route, { headers })
  assert.equal(reply.status, 200)
  return reply.json()
}

async function openPdf(browser, viewport) {
  const page = await open(browser, 'library', viewport)
  const doc = (await api('/documents')).documents.find(doc => doc.id === id)
  await page.getByRole('row').filter({ hasText: doc.filename }).getByRole('button', { name: 'Xem nguồn' }).click()
  return page
}

async function goTo(page, n) {
  await page.getByRole('spinbutton', { name: 'Đến trang PDF' }).fill(String(n))
  await page.locator('[data-rendered="true"] canvas[aria-label="Trang PDF ' + n + '"]').waitFor()
  await page.getByRole('combobox', { name: 'Dòng bảng' }).locator('option').nth(1).waitFor({ state: 'attached' })
}

async function chooseCell(page, name, cell) {
  const picker = page.getByRole('combobox', { name: 'Dòng bảng' })
  const option = picker.locator('option').filter({ hasText: name }).first()
  await picker.selectOption({ label: await option.textContent() })
  await page.getByRole('button', { name: cell }).click()
  await page.getByTestId('source-highlight').scrollIntoViewIfNeeded()
}

async function main() {
  const executablePath = path.join(process.env.LOCALAPPDATA, 'ms-playwright/chromium-1217/chrome-win64/chrome.exe')
  const browser = await chromium.launch({ executablePath })
  const shot = (page, name) => page.screenshot({ path: path.join(output, 'browser-' + name + '.png'), fullPage: true })
  try {
    await check('search-assets-opens-exact-cell', async () => {
      const page = await open(browser, 'search')
      await page.getByRole('combobox', { name: 'Tài liệu tìm kiếm' }).selectOption(id)
      await page.getByRole('button', { name: 'FAITH-R', exact: true }).click()
      await page.getByRole('textbox', { name: 'Câu hỏi tìm kiếm' }).fill('Tổng cộng tài sản công ty mẹ là bao nhiêu tại ngày 31/12/2025?')
      const pending = page.waitForResponse(r => r.url().endsWith('/studio/query') && r.request().method() === 'POST')
      await page.getByRole('button', { name: 'Tìm kiếm', exact: true }).click()
      const result = await (await pending).json()
      assert.equal(result.results[0].page, 3)
      assert.ok(result.results[0].column_id)
      await page.locator('.evidence-hit').first().getByRole('button', { name: 'Mở trang nguồn' }).click()
      await page.locator('[data-rendered="true"] canvas[aria-label="Trang PDF 3"]').waitFor()
      const overlay = page.getByTestId('source-highlight').first()
      await overlay.scrollIntoViewIfNeeded()
      const box = await overlay.boundingBox()
      assert.ok(box.width > 0 && box.height > 0 && box.height < 30)
      await shot(page, 'assets-citation')
      await page.close()
      return { rank: 1, page: 3, cell: result.results[0].column_id, box }
    })
    await check('review-quarter-and-full-year', async () => {
      const page = await openPdf(browser)
      await goTo(page, 5)
      await chooseCell(page, 'Doanh thu thuần', /125\.533\.574\.301.*Q4 2025/)
      await page.getByRole('combobox', { name: 'Chỉ tiêu xác minh' }).waitFor()
      assert.equal(await page.getByRole('combobox', { name: 'Chỉ tiêu xác minh' }).inputValue(), 'net_revenue')
      assert.equal(await page.locator('input[type=date]').first().inputValue(), '2025-10-01')
      await shot(page, 'quarter')
      await page.getByRole('button', { name: /343\.200\.043\.936.*FY 2025/ }).click()
      assert.equal(await page.locator('input[type=date]').first().inputValue(), '2025-01-01')
      await page.getByRole('combobox', { name: 'Chỉ tiêu xác minh' }).selectOption('assets')
      await page.getByText(/Ô này thiếu căn cứ hoặc chỉ tiêu/).waitFor()
      assert.equal(await page.getByRole('button', { name: 'Lưu kết quả đối chiếu' }).isDisabled(), true)
      await page.close()
    })
    await check('review-negative-operating-cash-flow', async () => {
      const page = await openPdf(browser)
      await goTo(page, 6)
      await chooseCell(page, /Lưu chuyển tiền thuần từ hoạt động kinh doanh/, /\([\d.]+\).*FY 2025/)
      assert.equal(await page.getByRole('combobox', { name: 'Chỉ tiêu xác minh' }).inputValue(), 'operating_cashflow')
      await shot(page, 'negative-cash')
      await page.close()
    })
    await check('review-deposit-disagreement', async () => {
      const page = await openPdf(browser)
      await goTo(page, 12)
      await chooseCell(page, /Tiền gửi ngân hang/i, /46\.074\.571\.676.*01\/01\/2025/)
      const comparison = page.getByRole('definition').filter({ hasText: '46.014.571.676' })
      await comparison.waitFor()
      await page.getByRole('button', { name: 'Ô bất đồng tiếp theo' }).click()
      await shot(page, 'deposit')
      await page.close()
    })
    await check('review-printed-dash-mobile', async () => {
      const page = await openPdf(browser, { width: 390, height: 844 })
      await goTo(page, 13)
      await chooseCell(page, /Điện máy Gia dụng/i, /^- · 01\/01\/2025 Dự phòng/)
      await page.getByText(/Dấu gạch in/).waitFor()
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), 390)
      await shot(page, 'dash-mobile')
      await page.close()
    })
    await check('chat-liabilities-respects-review-ledger', async () => {
      const facts = (await api('/documents/' + id + '/facts')).facts
      const confirmed = facts.find(f => f.metric === 'liabilities' && f.period === '2025-12-31'
        && f.review_status === 'HUMAN_SOURCE_VERIFIED')
      const page = await open(browser, 'analysis')
      await page.getByRole('combobox', { name: 'Tài liệu trợ lý' }).selectOption(id)
      await page.getByRole('textbox', { name: 'Câu hỏi trợ lý' }).fill('Nợ phải trả công ty mẹ là bao nhiêu tại ngày 31/12/2025?')
      const pending = page.waitForResponse(r => r.url().endsWith('/studio/chat') && r.request().method() === 'POST')
      await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
      const reply = await (await pending).json()
      assert.deepEqual(reply.values, confirmed ? [confirmed.value] : [])
      assert.equal(reply.status, confirmed ? 'SUPPORTED' : 'SOURCE_EXCERPTS')
      if (confirmed) assert.deepEqual(reply.citations[0].box, confirmed.box)
      assert.equal(reply.citations[0].page, 4)
      await page.getByRole('button', { name: /Mở nguồn 1 trang/ }).first().click()
      await page.getByRole('button', { name: /Mở trang nguồn/ }).click()
      await page.locator('[data-rendered="true"] canvas[aria-label="Trang PDF 4"]').waitFor()
      await page.getByTestId('source-highlight').first().scrollIntoViewIfNeeded()
      await shot(page, 'chat-liabilities')
      await page.close()
      return { responseStatus: reply.status, citations: reply.citations.length }
    })
  } finally {
    await browser.close()
  }
  console.log(results)
  if (results.some(result => result.status === 'FAIL')) process.exitCode = 1
}
main().catch(error => { console.error(error); process.exitCode = 1 })
