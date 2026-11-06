const fs=require('node:fs')
const path=require('node:path')
const assert=require('node:assert/strict')
const {chromium}=require('../frontend/node_modules/playwright')
const base=process.env.FIS_V8_2_URL||'http://127.0.0.1:18110'
const token=fs.readFileSync('tmp/studio-runtime/access-token.txt','utf8').trim()
const out=process.env.FIS_V8_2_OUTPUT||'tmp/fis-v8-2/browser'
const questions=JSON.parse(fs.readFileSync('reports/fis_v8_2/questions.json','utf8'))
const pinned=['0000909832-26-000051','0001628280-26-058715','0000080424-26-000256','0001193125-25-256321','0000950170-25-061046']
const expected={A01:['3.99','4.07'],A02:['48.87','46.58','2.29'],A03a:['14.29'],A03b:['25.51']}
const old=[
 ['F01','Tôi chọn ba filing COST, HD và PG. Hãy chỉ sử dụng Home Depot để tính tỷ suất lợi nhuận hoạt động của kỳ 13 tuần, nêu doanh thu, lợi nhuận hoạt động, đơn vị và hai ô nguồn.','SUPPORTED',1,2],
 ['F02','Trong Microsoft 10-Q kỳ 30/09/2025, hãy so sánh doanh thu, lợi nhuận hoạt động và lợi nhuận ròng giữa kỳ hiện tại và cùng kỳ năm trước. Nêu chênh lệch và tỷ lệ thay đổi riêng từng chỉ tiêu.','SUPPORTED',3,6],
 ['F03','Theo Microsoft 10-Q, công ty có những rủi ro liên quan đến cạnh tranh và an ninh mạng nào? Hãy giải thích bằng tiếng Việt, dẫn đúng đoạn nguồn và phân biệt thông tin được công bố với nhận định của bạn.','SOURCE_EXCERPTS',2,2],
 ['F04','Trong Amazon 10-K FY2024, doanh thu của AWS chiếm bao nhiêu phần trăm tổng doanh thu hợp nhất?','NEEDS_CLARIFICATION',0,0],
 ['F05','Chỉ chọn PepsiCo 10-Q kỳ 15/06/2024. Hãy tính mức thay đổi doanh thu của kỳ 12 tuần và kỳ 24 tuần so với các kỳ tương ứng năm trước.','NEEDS_CLARIFICATION',0,0],
 ['F06','Tôi chọn COST, HD và PG. Hãy so sánh tỷ suất lợi nhuận hoạt động của từng doanh nghiệp theo kỳ ngắn nhất trong filing tương ứng. Nêu rõ vì sao các kỳ 12 tuần, 13 tuần và ba tháng không hoàn toàn đồng nhất.','SUPPORTED',3,6]
]
const chrome=path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1217/chrome-win64/chrome.exe')
fs.mkdirSync(out,{recursive:true})
const records=[]
const save=()=>fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(records,null,2))
async function select(page,accessions){
 await page.goto(base+'/app/#/analysis')
 const select=page.getByRole('combobox',{name:'Tài liệu trợ lý'})
 const primary=select.locator('option').filter({hasText:accessions[0]})
 await primary.waitFor({state:'attached'})
 const selected=await primary.getAttribute('value')
 await select.selectOption(selected)
 await page.getByText('Nguồn (1)',{exact:true}).click()
 const ids=[selected.slice(4)]
 for(const accession of accessions.slice(1)){
  const option=select.locator('option').filter({hasText:accession})
  ids.push((await option.getAttribute('value')).slice(4))
  await page.getByRole('checkbox',{name:new RegExp(accession)}).check()
 }
 await page.getByText('Nguồn ('+accessions.length+')',{exact:true}).click()
 return ids
}
async function ask(page,question,ids){
 await page.getByRole('textbox',{name:'Câu hỏi trợ lý'}).fill(question)
 const pending=page.waitForResponse(r=>r.url().endsWith('/studio/chat')&&r.request().method()==='POST',{timeout:120000})
 await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
 const response=await pending
 const request=response.request().postDataJSON()
 assert.deepEqual(request.filing_ids.slice().sort(),ids.slice().sort())
 const answer=await response.json()
 assert.equal(response.status(),200)
 await page.locator('.chat-exchange').last().locator('.message-user p').getByText(question,{exact:true}).waitFor()
 return {request,answer}
}
async function main(){
 const browser=await chromium.launch({executablePath:chrome})
 try{
  for(const group of [questions,old]){
   const page=await browser.newPage({viewport:{width:1440,height:900}})
   page.setDefaultTimeout(50000)
   await page.addInitScript(t=>sessionStorage.setItem('studio-token',t),token)
   const ids=await select(page,group===old?pinned.slice(0,4):pinned)
   let previous
   for(const [id,question,status,count,refs] of group){
    try{
     const {request,answer}=await ask(page,question,ids)
     if(group===old){
      assert.equal(answer.status,status)
      assert.equal(answer.answer_completeness.completed,count)
      assert.equal(answer.citations.length,refs)
     }else if(id==='A04'){
      assert.equal(answer.answer_completeness.required,3)
      assert.deepEqual(new Set(answer.topic_results.map(t=>t.topic)),new Set(['LEGAL','SECURITY','COMPETITION']))
     }else{
      assert.deepEqual(answer.values,expected[id])
      assert.equal(answer.answer_completeness.completed,answer.answer_completeness.required)
      if(id==='A02'){
       assert.deepEqual(answer.source_cells.map(c=>c.period_end),['2025-09-30','2025-09-30','2024-09-30','2024-09-30'])
       assert.ok(answer.source_cells.every(c=>c.accession===pinned[3]))
      }
      if(id==='A03b'){
       assert.equal(request.session_id,previous)
       assert.equal(answer.sec_followup.overrides.duration,'SHORTEST_REPORTED')
       assert.equal(answer.sec_followup.overrides.issuer,'PG')
      }
     }
     previous=answer.session_id
     records.push({id,status:'PASS',answer:answer.answer,coverage:answer.answer_completeness,
                   values:answer.values,selected:request.filing_ids,citations:answer.citations.length})
     if(group!==old&&id!=='A03a') await page.screenshot({path:path.join(out,id+'.png')})
    }catch(error){records.push({id,status:'FAIL',reason:error.message.slice(0,500)})}
    save()
   }
   await page.close()
  }
  console.log(records.map(r=>[r.id,r.status,r.reason]))
  if(records.some(r=>r.status==='FAIL'))process.exitCode=1
 }finally{await browser.close()}
}
main().catch(error=>{console.error(error);process.exitCode=1})
