import {test,expect} from '@playwright/test'
import {readFileSync,mkdirSync} from 'node:fs'
import {resolve} from 'node:path'

test('prebuilt FastAPI serves React, PDF.js worker and authenticated source',async({page})=>{
 test.skip(process.env.RUN_PREBUILT_E2E!=='1','Explicit prebuilt runtime required')
 const repo=resolve(import.meta.dirname,'../..')
 const token=readFileSync(resolve(repo,'tmp/studio-runtime/access-token.txt'),'utf-8').replace(/^\uFEFF/,'').trim()
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message))
 await page.addInitScript(t=>sessionStorage.setItem('studio-token',t),token)
 await page.goto('http://127.0.0.1:8110/app/#/library')
 await expect(page.getByRole('heading',{name:'Kho tài liệu tài chính'})).toBeVisible()
 await page.getByRole('row').filter({hasText:'BIDV'}).getByRole('button',{name:'Xem nguồn'}).click()
 await page.getByLabel('Đến trang PDF').fill('6')
 await expect(page.getByTestId('pdf-page')).toHaveAttribute('data-rendered','true',{timeout:30000})
 await expect(page.locator('.textLayer span').first()).toBeAttached()
 const shots=resolve(repo,'docs/topic3/final_product/screenshots/react');mkdirSync(shots,{recursive:true})
 await page.screenshot({path:shots+'/20-prebuilt-pdf-viewer.png',fullPage:true})
 expect(errors).toEqual([])
 expect((await page.request.get('http://127.0.0.1:8110/app/favicon.svg')).status()).toBe(200)
})
