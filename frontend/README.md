# Financial Intelligence Studio — React

React/TypeScript/Vite, tiếng Việt là mặc định; Python giữ retrieval và Decimal. Xem [Windows quickstart](../docs/topic3/final_product/WINDOWS_QUICKSTART.md), [acceptance](../docs/topic3/final_product/FINAL_PRODUCT_ACCEPTANCE.md).

`npm ci`, `npm run test`, `npm run build`; development dùng launcher PowerShell ở repo root. Real browser tests: `npx playwright test` với API8110/UI5173, local token và hai owner PDFs thật. Thiếu nguồn sẽ SKIP; không dùng fixture thay nguồn thật.

Không có token trong VITE env/bundle. PDF.js và chart lazy-load. Không tính số tài chính trong JavaScript, chuỗi Decimal từ Python được giữ nguyên.
