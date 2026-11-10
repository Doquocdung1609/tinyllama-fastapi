const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const {chromium} = require('playwright');

const root = path.resolve(__dirname, '..');
const base = 'http://127.0.0.1:18110';
const token = fs.readFileSync(path.join(root, 'tmp/studio-runtime/access-token.txt'), 'utf8').trim();
const out = path.join(root, 'reports/fis_v8_1');
const questions = [
  ['F01', 'Tôi chọn ba filing COST, HD và PG. Hãy chỉ sử dụng Home Depot để tính tỷ suất lợi nhuận hoạt động của kỳ 13 tuần, nêu doanh thu, lợi nhuận hoạt động, đơn vị và hai ô nguồn.', 'SUPPORTED', 1, 2],
  ['F02', 'Trong Microsoft 10-Q kỳ 30/09/2025, hãy so sánh doanh thu, lợi nhuận hoạt động và lợi nhuận ròng giữa kỳ hiện tại và cùng kỳ năm trước. Nêu chênh lệch và tỷ lệ thay đổi riêng từng chỉ tiêu.', 'SUPPORTED', 3, 6],
  ['F03', 'Theo Microsoft 10-Q, công ty có những rủi ro liên quan đến cạnh tranh và an ninh mạng nào? Hãy giải thích bằng tiếng Việt, dẫn đúng đoạn nguồn và phân biệt thông tin được công bố với nhận định của bạn.', 'SOURCE_EXCERPTS', 2, 2],
  ['F04', 'Trong Amazon 10-K FY2024, doanh thu của AWS chiếm bao nhiêu phần trăm tổng doanh thu hợp nhất?', 'NEEDS_CLARIFICATION', 0, 0],
  ['F05', 'Chỉ chọn PepsiCo 10-Q kỳ 15/06/2024. Hãy tính mức thay đổi doanh thu của kỳ 12 tuần và kỳ 24 tuần so với các kỳ tương ứng năm trước.', 'NEEDS_CLARIFICATION', 0, 0],
  ['F06', 'Tôi chọn COST, HD và PG. Hãy so sánh tỷ suất lợi nhuận hoạt động của từng doanh nghiệp theo kỳ ngắn nhất trong filing tương ứng. Nêu rõ vì sao các kỳ 12 tuần, 13 tuần và ba tháng không hoàn toàn đồng nhất.', 'SUPPORTED', 3, 6],
];

(async () => {
  fs.mkdirSync(out, {recursive:true});
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage({viewport:{width:1440,height:900}});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const records = [];
  try {
    await page.goto(base + '/app/#/library');
    const login = page.getByLabel('Khóa truy cập', {exact:true});
    if (await login.count()) {
      await login.fill(token);
      await page.getByRole('button', {name:/Mở không gian làm việc/}).click();
    }
    await page.getByRole('button',{name:'Trợ lý tài chính',exact:true}).click();
    await page.getByLabel('Tài liệu trợ lý').waitFor();
    const options = await page.getByLabel('Tài liệu trợ lý').locator('option').evaluateAll(nodes => nodes.map(n => ({value:n.value,label:n.textContent})));
    const ids = {};
    for (const issuer of ['COST','HD','PG','MSFT']) {
      const entry = options.find(item => item.label.startsWith('SEC · ' + issuer + ' ·'));
      assert(entry, `Missing selected SEC issuer ${issuer}`);
      ids[issuer] = entry.value;
    }
    await page.getByLabel('Tài liệu trợ lý').selectOption(ids.COST);
    await page.locator('.chat-source-picker summary').click();
    for (const issuer of ['HD','PG','MSFT']) {
      await page.locator('.chat-source-options label').filter({hasText:'SEC · '+issuer+' ·'}).locator('input').check();
    }
    await page.locator('.chat-source-picker summary').click();
    assert.equal(await page.locator('.chat-selected-sources li').count(), 4);
    for (const [id,question,status,answered,citations] of questions) {
      await page.getByLabel('Câu hỏi trợ lý').fill(question);
      const responsePromise = page.waitForResponse(response => response.url().endsWith('/studio/chat') && response.request().method()==='POST', {timeout:120000});
      await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();
      const response = await responsePromise;
      assert.equal(response.status(), 200, id);
      const request = response.request().postDataJSON();
      assert.deepEqual(request.filing_ids.slice().sort(), Object.values(ids).map(value => value.slice(4)).sort(), id+' source scope');
      const answer = await response.json();
      assert.equal(answer.status, status, id);
      assert.equal(answer.answer_completeness.completed, answered, id);
      assert.equal(answer.citations.length, citations, id);
      await page.locator('.chat-exchange').last().locator('.message-user p').getByText(question,{exact:true}).waitFor();
      if (id==='F03') assert.match(await page.locator('.chat-exchange').last().innerText(), /cạnh tranh|an ninh mạng/i);
      if (id==='F05') assert.equal(answer.calculation_steps?.length || 0, 0);
      records.push({id,status,answered,requested:answer.answer_completeness.required,citations,selected_filing_ids:request.filing_ids,ui_visible:true,answer:answer.answer});
      if (id==='F01' || id==='F03' || id==='F06') {
        await page.locator('.chat-messages').evaluate(node => {node.scrollTop = node.scrollHeight});
        await page.screenshot({path:path.join(out, id+'-react.png'),fullPage:true});
      }
    }
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(out,'react_acceptance.json'), JSON.stringify({status:'PASS',browser:browser.version(),api_port:18110,records,page_errors:errors},null,2));
    console.log(JSON.stringify({status:'PASS',cases:records.map(({id,status,answered,citations})=>({id,status,answered,citations})),page_errors:errors}));
  } catch (error) {
    await page.screenshot({path:path.join(out,'react_failure.png'),fullPage:true});
    throw error;
  } finally { await browser.close(); }
})().catch(error => {console.error(error.stack);process.exit(1)});
