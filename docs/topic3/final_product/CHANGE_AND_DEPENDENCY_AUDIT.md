# Thay đổi và dependency

Default UI chuyển Streamlit → React; scripts/start_financial_studio.ps1 là shim React, run_financial_studio.ps1 quản lý phiên. Script cũ git-move thành start_legacy_financial_studio.ps1; product_ui/streamlit_app/shared RAG/history giữ nguyên. Streamlit bỏ khỏi requirements mặc định, optional requirements-legacy-ui. Không xóa corpus, model, frozen benchmarks hoặc code dùng chung.

Npm lockfile pin dependency thực; React19, TypeScript7, Vite8, Tailwind4, shadcn-generated Button, Radix, Lucide, TanStackQuery, Recharts, PDF.js; Vitest/TestingLibrary/Playwright cho kiểm thử. Chromium chỉ là browser test, không phải model AI. Backend dùng dependencies extraction/OCR/Qdrant đã có; pip check PASS. Lazy-load chart và PDF, entry khoảng360KB, worker PDF khoảng1,26MB. Không đặt token trong bundle.

CI backendPython3.13 hiện hữu giữ nguyên; thêm frontendNode24 npmci/test/build. Live owner-PDF/Ollama/SEC integration chỉ chạy tại máy có nguồn, không giả làm CI live test. Node24.19/Python3.12.10 thực tế trên Windows; version CI ghi trong workflow. Không tự nâng Python, thay model hoặc tải framework agent nặng.
