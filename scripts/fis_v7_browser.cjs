const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require('../frontend/node_modules/playwright')

const url = process.env.FIS_V7_URL || 'http://127.0.0.1:18114'
const out = process.env.FIS_V7_OUTPUT || 'tmp/fis-v7/browser'
const token = fs.readFileSync('tmp/studio-runtime/access-token.txt', 'utf8').trim()
const questions = JSON.parse(fs.readFileSync('reports/fis_v7/questions.json', 'utf8'))
const v6 = JSON.parse(fs.readFileSync('reports/chat_v6/queries.json', 'utf8').replace(/^\uFEFF/, ''))
const bid = '2bed2b3c312c8149e6a2ff6ab80c694a'
const hpg = '4a92af827aaf1e73e017544d0ff20d0d'
const chrome = path.join(process.env.LOCALAPPDATA, 'ms-playwright/chromium-1217/chrome-win64/chrome.exe')
fs.mkdirSync(out, { recursive: true })

async function ask(page, question, ids) {
  await page.getByRole('textbox', { name: 'Câu hỏi trợ lý' }).fill(question)
  const pending = page.waitForResponse(r => r.url().endsWith('/studio/chat') && r.request().method() === 'POST')
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  const response = await pending
  assert.equal(response.status(), 200)
  const request = response.request().postDataJSON()
  assert.deepEqual(request.document_ids.slice().sort(), ids.slice().sort())
  assert.ok(!request.evidence_context)
  const reply = await response.json()
  await page.locator('.message-assistant').last().waitFor()
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).waitFor()
  return { ids, status: reply.status, answerStatus: reply.answer_status, reason: reply.reason,
    answer: reply.answer, values: reply.values, candidateValues: reply.candidate_values,
    pageMap: reply.page_map?.length, tasks: reply.task_results?.map(t => t.status),
    session: reply.session_id,
    citations: (reply.citations || []).map(c => ({ page: c.page, box: c.box, doc: c.document_id, column: c.basis, value: c.value_raw, state: c.review_status || c.verification_status })) }
}

async function openCell(page, citation, index = 1) {
  assert.ok(citation.box?.length === 4)
  await page.locator('.message-assistant').last().getByRole('button', { name: `Mở nguồn ${index} trang ${citation.page}` }).first().click()
  await page.getByRole('button', { name: `Mở trang nguồn ${citation.page}` }).click()
  await page.locator(`[data-rendered="true"] canvas[aria-label="Trang PDF ${citation.page}"]`).waitFor()
  const highlight = page.getByTestId('source-highlight').first()
  await highlight.scrollIntoViewIfNeeded()
  const rendered = await highlight.boundingBox()
  assert.ok(rendered.width > 12 && rendered.height < 45)
  return rendered
}

async function main() {
  const browser = await chromium.launch({ executablePath: chrome })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  page.setDefaultTimeout(45000)
  await page.addInitScript(t => sessionStorage.setItem('studio-token', t), token)
  const records = []
  const save = () => fs.writeFileSync(path.join(out, 'browser.json'), JSON.stringify(records, null, 2))
  const select = async id => {
    await page.goto(url + '/app/#/analysis')
    await page.getByRole('combobox', { name: 'Tài liệu trợ lý' }).selectOption(id)
  }
  try {
    await select(bid)
    for (let i = 0; i < 9; i++) {
      records.push({ test: 'B0' + (i + 1), ...await ask(page, questions[i], [bid]) })
      save()
    }
    await page.screenshot({ path: path.join(out, 'bidv-chat-100.png') })
    records[8].highlight = await openCell(page, records[8].citations[0])
    await page.screenshot({ path: path.join(out, 'bidv-citation-p4.png') })
    save()
    await select(bid)
    const only = await ask(page, questions[14], [bid])
    records.push({ test: 'C06', ...only })
    assert.equal(only.reason, 'QUESTION_COMPANY_SCOPE_CONFLICT')
    await page.getByText('Nguồn (1)', { exact: true }).click()
    await page.getByRole('checkbox', { name: /HPG/ }).check()
    await page.getByText('Nguồn (2)', { exact: true }).click()
    const compare = await ask(page, questions[9], [bid, hpg])
    records.push({ test: 'C01', ...compare })
    assert.equal(compare.answerStatus, 'CANDIDATE_RECONCILIATION')
    assert.equal(new Set(compare.citations.map(c => c.doc)).size, 2)
    await page.screenshot({ path: path.join(out, 'multi-pdf-100.png') })
    await page.reload()
    await page.locator('.chat-selected-sources li').nth(1).waitFor()
    await page.locator('.message-assistant').last().getByText('Đối chiếu sơ bộ.', { exact: true }).waitFor()
    records.push({ test: 'C09-restored', ids: [bid, hpg], status: 'PASS' })
    for (let i = 10; i <= 16; i++) {
      records.push({ test: i === 14 ? 'C09-mismatch' : `C0${i - 8}`, ...await ask(page, questions[i], [bid, hpg]) })
      save()
    }
    const cdp = await page.context().newCDPSession(page)
    await cdp.send('Emulation.setPageScaleFactor', { pageScaleFactor: 1.25 })
    await page.screenshot({ path: path.join(out, 'multi-pdf-125.png') })
    await cdp.send('Emulation.setPageScaleFactor', { pageScaleFactor: 1 })
    await cdp.detach()
    await select(hpg)
    const inventory = await ask(page, v6.inventory, [hpg])
    assert.equal(inventory.pageMap, 24)
    records.push({ test: 'HPG-inventory', ...inventory })
    const checks = await ask(page, v6.checks, [hpg])
    assert.equal(checks.tasks.length, 6)
    records.push({ test: 'HPG-checks', ...checks })
    const capital = await ask(page, v6.capital, [hpg])
    records.push({ test: 'HPG-capital', ...capital, highlight: await openCell(page, capital.citations[0]) })
    await page.screenshot({ path: path.join(out, 'hpg-citation-p20.png') })
    save()
    await select(hpg)
    await page.reload()
    await page.getByRole('combobox', { name: 'Tài liệu trợ lý' }).selectOption(hpg)
    records.push({ test: 'C09-HPG-only-after-reload',
      ...await ask(page, 'Tổng tài sản công ty mẹ Hòa Phát tại 31/12/2025 là bao nhiêu?', [hpg]) })
    save()
  } catch (error) {
    await page.screenshot({ path: path.join(out, 'failure.png') })
    throw error
  } finally {
    await browser.close()
  }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
