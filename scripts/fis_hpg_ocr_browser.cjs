const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require('../frontend/node_modules/playwright')

const output = path.resolve('tmp/ocr-hpg-repair')
const token = fs.readFileSync('tmp/studio-runtime/access-token.txt', 'utf8').trim()
const { document_id: id } = require('../reports/hpg_ocr/visual_gold.json')
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

async function pageFor(browser, port, viewport, route) {
  const page = await browser.newPage({ viewport })
  await page.addInitScript(value => sessionStorage.setItem('studio-token', value), token)
  await page.goto('http://127.0.0.1:' + port + '/app/#/' + route)
  return page
}

async function viewer(browser, port, viewport, number) {
  const docs = await fetch('http://127.0.0.1:' + port + '/studio/documents', { headers }).then(r => r.json())
  const page = await pageFor(browser, port, viewport, 'library')
  await page.getByRole('row').filter({ hasText: docs.documents.find(d => d.id === id).filename })
    .getByRole('button', { name: 'Xem nguồn' }).click()
  await page.getByRole('spinbutton', { name: 'Đến trang PDF' }).fill(String(number))
  await page.locator('[data-rendered="true"] canvas[aria-label="Trang PDF ' + number + '"]').waitFor()
  return page
}

async function main() {
  const executablePath = path.join(process.env.LOCALAPPDATA, 'ms-playwright/chromium-1217/chrome-win64/chrome.exe')
  const browser = await chromium.launch({ executablePath })
  const desktop = { width: 1440, height: 900 }
  try {
    await check('baseline-page3-desktop', async () => {
      const page = await viewer(browser, 18110, desktop, 3)
      await page.locator('summary').filter({ hasText: /Dòng.*bảng/ }).click()
      await page.getByRole('combobox', { name: 'Dòng bảng' }).locator('option').nth(1).waitFor({ state: 'attached' })
      await page.screenshot({ path: path.join(output, 'browser-before-p3.png'), fullPage: true })
      await page.close()
    })
    await check('baseline-page5-desktop', async () => {
      const page = await viewer(browser, 18110, desktop, 5)
      await page.screenshot({ path: path.join(output, 'browser-before-p5.png'), fullPage: true })
      await page.close()
    })
    await check('candidate-page3-desktop', async () => {
      const page = await viewer(browser, 18111, desktop, 3)
      await page.getByText('Kiểm định OCR trên ảnh gốc', { exact: true }).click()
      await page.getByText(/PP-OCRv6_small/).first().waitFor()
      await page.getByText('Dòng / bảng và kiểm chứng số liệu', { exact: true }).click()
      const row = page.getByRole('combobox', { name: 'Dòng bảng' })
      await row.selectOption({ label: await row.locator('option').filter({ hasText: '59.554.496.946' }).first().textContent() })
      await page.getByRole('button', { name: /59\.554\.496\.946.*01\/01\/2025.*VND/ }).click()
      const overlay = page.getByTestId('source-highlight')
      await overlay.scrollIntoViewIfNeeded()
      const box = await overlay.boundingBox()
      assert.ok(box && box.width > 0 && box.height > 0)
      const downloading = page.waitForEvent('download')
      await page.getByRole('button', { name: 'Xuất TXT UTF-8' }).click()
      const download = await downloading
      const bytes = fs.readFileSync(await download.path())
      assert.deepEqual([...bytes.subarray(0, 3)], [239, 187, 191])
      const evidence = await fetch('http://127.0.0.1:18111/studio/documents/' + id + '/pages/3/evidence', { headers }).then(r => r.json())
      assert.equal(new TextDecoder('utf-8', { fatal: true }).decode(bytes), evidence.text)
      await page.screenshot({ path: path.join(output, 'browser-after-p3.png'), fullPage: true })
      await page.close()
      return { highlight: box, utf8Matches: true }
    })
    await check('candidate-page5-mobile-rotation', async () => {
      const page = await viewer(browser, 18111, { width: 390, height: 844 }, 5)
      const canvas = page.getByRole('img', { name: 'Trang PDF 5' }).or(page.locator('canvas[aria-label="Trang PDF 5"]'))
      const initial = await canvas.boundingBox()
      await page.getByRole('button', { name: 'Đọc đúng chiều OCR' }).click()
      await page.waitForFunction(height => document.querySelector('canvas[aria-label="Trang PDF 5"]').clientHeight !== height, initial.height)
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), 390)
      const widePage = await viewer(browser, 18111, desktop, 5)
      await widePage.getByRole('button', { name: 'Đọc đúng chiều OCR' }).click()
      await widePage.getByText('Dòng / bảng và kiểm chứng số liệu', { exact: true }).click()
      const row = widePage.getByRole('combobox', { name: 'Dòng bảng' })
      await row.selectOption({ label: await row.locator('option').filter({ hasText: '343.200.043.936' }).first().textContent() })
      await widePage.getByRole('button', { name: /343\.200\.043\.936.*FY 2025.*VND/ }).click()
      await widePage.getByTestId('source-highlight').scrollIntoViewIfNeeded()
      await widePage.screenshot({ path: path.join(output, 'browser-after-p5.png'), fullPage: true })
      await widePage.close()
      await page.screenshot({ path: path.join(output, 'browser-after-p5-mobile.png'), fullPage: true })
      await page.close()
    })
    await check('candidate-chat-to-citation', async () => {
      const page = await pageFor(browser, 18111, desktop, 'analysis')
      await page.getByRole('combobox', { name: 'Tài liệu trợ lý' }).selectOption(id)
      await page.getByRole('textbox', { name: 'Câu hỏi trợ lý' }).fill('Nợ phải trả công ty mẹ là bao nhiêu tại ngày 31/12/2025?')
      const pending = page.waitForResponse(r => r.url().endsWith('/studio/chat') && r.request().method() === 'POST')
      await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
      const reply = await (await pending).json()
      assert.equal(reply.status, 'SUPPORTED')
      assert.deepEqual(reply.values, ['4239852223395'])
      assert.equal(reply.citations[0].page, 4)
      await page.getByRole('button', { name: /Mở nguồn 1 trang/ }).first().waitFor()
      await page.screenshot({ path: path.join(output, 'browser-chat-p4.png') })
      await page.getByRole('button', { name: /Mở nguồn 1 trang/ }).first().click()
      await page.getByRole('button', { name: /Mở trang nguồn/ }).click()
      await page.locator('[data-rendered="true"] canvas[aria-label="Trang PDF 4"]').waitFor()
      const highlight = page.getByTestId('source-highlight').first()
      await highlight.scrollIntoViewIfNeeded()
      assert.ok((await highlight.boundingBox()).width > 0)
      await page.screenshot({ path: path.join(output, 'browser-citation-p4.png'), fullPage: true })
      await page.close()
      return { page: 4, value: reply.values[0] }
    })
  } finally {
    await browser.close()
  }
  console.log(results)
  if (results.some(result => result.status === 'FAIL')) process.exitCode = 1
}
main().catch(error => { console.error(error); process.exitCode = 1 })
