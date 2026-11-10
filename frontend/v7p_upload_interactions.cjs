/* Supplemental real browser drag/drop + file chooser, no upload duplication. */
const fs=require('fs'),path=require('path'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),file=process.env.V7P_APPLE_PDF;if(!file)throw Error('V7P_APPLE_PDF required');
 const browser=await chromium.launch({headless:true,...(process.env.V7P_CHROMIUM_EXECUTABLE?{executablePath:process.env.V7P_CHROMIUM_EXECUTABLE}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});await page.goto('http://127.0.0.1:18110/app/#/library');
  await page.getByLabel('Khóa truy cập',{exact:true}).fill(fs.readFileSync(path.join(root,'tmp/studio-runtime/access-token.txt'),'utf8').trim());
  await page.getByRole('button',{name:/Mở không gian làm việc/}).click();await page.getByRole('heading',{name:'Thêm báo cáo tài chính'}).waitFor();
  const transfer=await page.evaluateHandle(({name,b64})=>{const t=new DataTransfer();t.items.add(new File([Uint8Array.from(atob(b64),c=>c.charCodeAt(0))],name,{type:'application/pdf'}));return t},{name:path.basename(file),b64:fs.readFileSync(file).toString('base64')});
  await page.getByRole('group',{name:'Khu vực tải PDF'}).dispatchEvent('drop',{dataTransfer:transfer});
  await page.getByText('ĐÃ CHỌN, CHƯA TẢI LÊN',{exact:false}).waitFor();
  await page.getByRole('button',{name:'Bỏ tệp đã chọn',exact:true}).click();await page.getByText('Chưa chọn tệp',{exact:true}).waitFor();
  const chooser=page.waitForEvent('filechooser');await page.getByRole('button',{name:'Chọn tệp PDF',exact:true}).click();await(await chooser).setFiles(file);
  await page.getByText(path.basename(file),{exact:true}).first().waitFor();
  await page.screenshot({path:path.join(root,'docs/topic3_v7p/screenshots/upload-dragdrop-filechooser.png'),fullPage:true});
  fs.writeFileSync(path.join(root,'docs/topic3_v7p/V7P_UPLOAD_INTERACTIONS.json'),JSON.stringify({status:'PASS',browser:await browser.version(),drag_drop_event_with_real_pdf:true,remove_selection:true,filechooser_event_with_real_pdf:true,metadata_not_required:true,upload_not_submitted:true},null,2));
  console.log('PASS: real PDF drag/drop, remove selection, filechooser selection');
 }finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exit(1)});
