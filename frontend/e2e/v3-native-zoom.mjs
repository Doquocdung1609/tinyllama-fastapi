import {chromium} from '@playwright/test'
import fs from 'node:fs/promises'
import {fileURLToPath} from 'node:url'
const root=new URL('../../',import.meta.url),profile=new URL('tmp/studio-runtime/chrome-native125/',root),out=new URL('reports/fis_product_v3/',root)
await fs.mkdir(new URL('Default/',profile),{recursive:true})
await fs.writeFile(new URL('Default/Preferences',profile),JSON.stringify({partition:{default_zoom_level:Math.log(1.25)/Math.log(1.2)}}))
const extension=new URL('zoom-extension/',profile);await fs.mkdir(extension,{recursive:true})
await fs.writeFile(new URL('manifest.json',extension),JSON.stringify({manifest_version:3,name:'Local FIS native zoom verification',version:'1.0',permissions:['tabs'],background:{service_worker:'zoom.js'}}))
await fs.writeFile(new URL('zoom.js',extension),"chrome.tabs.onUpdated.addListener((id,info,tab)=>{if(info.status==='complete'&&tab.url?.startsWith('http://127.0.0.1:18110/'))chrome.tabs.setZoom(id,1.25)})")
const token=(await fs.readFile(new URL('tmp/studio-runtime/access-token.txt',root),'utf8')).replace(/^\uFEFF/,'').trim()
const context=await chromium.launchPersistentContext(fileURLToPath(profile),{headless:process.env.FIS_ZOOM_HEADFUL!=='1',executablePath:'C:/Users/Admin/AppData/Local/ms-playwright/chromium-1217/chrome-win64/chrome.exe',viewport:null,ignoreDefaultArgs:['--disable-extensions'],args:['--window-size=1366,768','--disable-extensions-except='+fileURLToPath(extension),'--load-extension='+fileURLToPath(extension)]})
const saved=JSON.parse(await fs.readFile(new URL('core-browser.json',out),'utf8')).traces[0].response
await context.addInitScript(({token,sid})=>{sessionStorage.setItem('studio-token',token);sessionStorage.setItem('active-financial-chat',sid);sessionStorage.setItem('active-document','3eb270b22acb7d8d8e9c32a43dc221de')},{token,sid:saved.session_id})
const page=await context.newPage();await page.goto('http://127.0.0.1:18110/app/#/analysis');await page.getByLabel('Tài liệu trợ lý',{exact:true}).waitFor();await page.locator('.message-assistant').last().waitFor();await page.waitForTimeout(400)
const workers=context.serviceWorkers();let tabZooms=[];if(workers.length){tabZooms=await workers[0].evaluate(async()=>{const tabs=await chrome.tabs.query({}),results=[];for(const tab of tabs)if(tab.url?.startsWith('http://127.0.0.1:18110/')){await chrome.tabs.setZoom(tab.id,1.25);results.push(await chrome.tabs.getZoom(tab.id))}return results});await page.waitForTimeout(500)}
const measurement=await page.evaluate(()=>({innerWidth,innerHeight,outerWidth,outerHeight,devicePixelRatio,visualViewportScale:visualViewport.scale,bodyOverflow:document.documentElement.scrollHeight>innerHeight+2,composer:document.querySelector('.chat-composer').getBoundingClientRect().toJSON(),conversation:document.querySelector('.chat-messages').getBoundingClientRect().toJSON()}))
await page.screenshot({path:fileURLToPath(new URL('native-125-percent.png',out))})
await fs.writeFile(new URL('native-zoom.json',out),JSON.stringify({method:'Chromium extension chrome.tabs.setZoom(1.25), no CSS zoom or emulation',requested_zoom:1.25,applied:tabZooms.length>0&&tabZooms.every(z=>z===1.25),native_tab_zoom:tabZooms,service_workers:workers.length,measurement},null,2))
console.log(JSON.stringify({native_tab_zoom:tabZooms,measurement}));await context.close()
