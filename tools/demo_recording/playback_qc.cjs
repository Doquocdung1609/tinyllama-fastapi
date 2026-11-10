const {chromium}=require('../../frontend/node_modules/@playwright/test');
const fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'deliverables/FAITH_R_FIS_DEMO_20261110');
(async()=>{
 const browser=await chromium.launch({executablePath:path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1217/chrome-win64/chrome.exe')});
 const checks=[];
 try{
  const page=await browser.newPage({viewport:{width:1920,height:1080}});
  await page.goto(pathToFileURL(path.join(out,'FAITH_R_FIS_FULL_DEMO.mp4')).href);
  await page.waitForFunction(()=>document.querySelector('video')?.readyState>=2,{timeout:60000});
  const metadata=await page.locator('video').evaluate(v=>({duration:v.duration,width:v.videoWidth,height:v.videoHeight}));
  for(const fraction of [0.02,0.5,0.98]){
   const time=metadata.duration*fraction;
   await page.locator('video').evaluate((v,t)=>{v.currentTime=t},time);
   await page.waitForFunction(t=>Math.abs(document.querySelector('video').currentTime-t)<1&&document.querySelector('video').readyState>=2,time);
   await page.locator('video').evaluate(v=>v.play());
   await page.waitForFunction(t=>document.querySelector('video').currentTime>t+1,time);
   await page.locator('video').evaluate(v=>v.pause());
   const metrics=await page.locator('video').evaluate(v=>({time:v.currentTime,error:v.error?.code||null,decoded_frames:v.getVideoPlaybackQuality().totalVideoFrames}));
   await page.screenshot({path:path.join(out,'playback-'+Math.round(fraction*100)+'.png')});
   checks.push(metrics);
  }
  fs.writeFileSync(path.join(out,'PLAYBACK_QC.json'),JSON.stringify({metadata,checks},null,2));
  console.log(JSON.stringify({metadata,checks}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
