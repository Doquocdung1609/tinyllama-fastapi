const {chromium}=require('../../frontend/node_modules/@playwright/test');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'deliverables/FAITH_R_FIS_DEMO_20261110');
const hold=ms=>new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{
 const listing=path.join(out,'SCENES.json');
 if(fs.existsSync(listing)&&JSON.parse(fs.readFileSync(listing,'utf8')).some(scene=>scene.key==='02b-metadata')){
  console.log('Metadata supplementary recording already present');return;
 }
 const b=await chromium.launch({executablePath:path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1217/chrome-win64/chrome.exe')});
 try{
  const c=await b.newContext({viewport:{width:1920,height:1080},recordVideo:{dir:path.join(out,'scenes'),size:{width:1920,height:1080}}});
  await c.addInitScript(t=>sessionStorage.setItem('studio-token',t),fs.readFileSync(path.join(root,'tmp/studio-runtime/access-token.txt'),'utf8').trim());
  const p=await c.newPage();
  await p.goto('http://127.0.0.1:18110/app/#/library');
  await p.getByRole('button',{name:'Mở rộng điều hướng',exact:true}).click();
  await hold(5000);
  await p.locator('summary').filter({hasText:'Metadata thủ công'}).click();
  await hold(7000);
  const auto=p.locator('summary').filter({hasText:'Metadata tự nhận diện'}).first();
  await auto.scrollIntoViewIfNeeded();await auto.click();await hold(7000);
  await p.mouse.wheel(0,420);await hold(7000);
  await p.mouse.wheel(0,-650);await hold(5000);
  const video=p.video();await c.close();
  const name='02b-metadata.webm';await video.saveAs(path.join(out,'scenes',name));await video.delete();
  const file=path.join(out,'SCENES.json'),scenes=JSON.parse(fs.readFileSync(file,'utf8'));
  scenes.splice(2,0,{key:'02b-metadata',title:'Metadata và thanh điều hướng',file:name});
  fs.writeFileSync(file,JSON.stringify(scenes,null,2));console.log('Metadata supplementary recording saved');
 }finally{await b.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
