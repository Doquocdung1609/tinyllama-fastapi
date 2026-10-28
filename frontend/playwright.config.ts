import {defineConfig} from '@playwright/test'
export default defineConfig({testDir:'./e2e',timeout:600000,workers:1,use:{baseURL:'http://127.0.0.1:5173',viewport:{width:1600,height:1000},trace:'retain-on-failure'},reporter:[['list']],outputDir:'test-results'})
