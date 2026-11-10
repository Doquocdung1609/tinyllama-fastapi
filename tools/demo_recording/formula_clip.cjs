const {chromium}=require('../../frontend/node_modules/@playwright/test');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'deliverables/FAITH_R_FIS_DEMO_20261110');
const hold=ms=>new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{
 const file=path.join(out,'SCENES.json'),scenes=JSON.parse(fs.readFileSync(file,'utf8'));
 if(scenes.some(s=>s.key==='06b-formula'))return;
 const b=await chromium.launch({executablePath:path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1217/chrome-win64/chrome.exe')});
 try{
  const c=await b.newContext({viewport:{width:1920,height:1080},recordVideo:{dir:path.join(out,'scenes'),size:{width:1920,height:1080}}});
  await c.addInitScript(t=>sessionStorage.setItem('studio-token',t),fs.readFileSync(path.join(root,'tmp/studio-runtime/access-token.txt'),'utf8').trim());
  const p=await c.newPage();
  const token=fs.readFileSync(path.join(root,'tmp/studio-runtime/access-token.txt'),'utf8').trim();
  const response=await p.request.get('http://127.0.0.1:18110/studio/chat/sessions?q=Calculate&limit=5',{headers:{Authorization:'Bearer '+token}});
  const session=(await response.json()).sessions.find(item=>item.message_count===2);
  if(!session)throw Error('No authentic saved calculation session');
  const saved=await p.request.get('http://127.0.0.1:18110/studio/chat/sessions/'+session.id,{headers:{Authorization:'Bearer '+token}});
  await c.addInitScript(id=>{
   sessionStorage.setItem('active-financial-chat',id);
   sessionStorage.setItem('active-document','3eb270b22acb7d8d8e9c32a43dc221de');
  },session.id);
  await p.goto('http://127.0.0.1:18110/app/#/analysis');
  await p.locator('.calculation-details').last().waitFor();
  const data={answer:await p.locator('.message-assistant').last().innerText(),restored_session:session.id};
  await hold(5000);
  const details=p.locator('.calculation-details').last();
  await details.locator('summary').click();await details.scrollIntoViewIfNeeded();await hold(12000);
  await p.screenshot({path:path.join(out,'formula-open.png')});
  await p.locator('.chat-messages').evaluate(el=>el.scrollBy({top:260,behavior:'smooth'}));await hold(8000);
  await p.locator('.chat-messages').evaluate(el=>el.scrollBy({top:-200,behavior:'smooth'}));await hold(5000);
  const video=p.video();await c.close();
  const name='06b-formula.webm';await video.saveAs(path.join(out,'scenes',name));await video.delete();
  scenes.splice(scenes.findIndex(s=>s.key==='07-bidv-chat'),0,{key:'06b-formula',title:'Mở các bước tính Apple',file:name});
  fs.writeFileSync(file,JSON.stringify(scenes,null,2));
  fs.writeFileSync(path.join(out,'FORMULA_QC.json'),JSON.stringify({http_status:response.status(),answer:data.answer,restored_session:data.restored_session,visible:true},null,2));
  console.log('Formula visible and recorded');
 }finally{await b.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
