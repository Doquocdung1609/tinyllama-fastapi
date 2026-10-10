from app.services.pdf_service import extract_pdf
from pathlib import Path
import json
for n in ['B_mixed_text_table.pdf','C_financial_statement.pdf','I_multipage_table.pdf','J_mixed_vi_en.pdf','D_bar_line_charts.pdf','E_pie_chart.pdf','F_process_diagram.pdf','G_scanned_document.pdf','H_multi_column.pdf']:
 p=Path('tests/fixtures/pdfs')/n; pages=extract_pdf(p,'audit',n)
 print('\n',n)
 for pg in pages:
  print('PAGE',pg['page'],'strategy',pg['diagnostics'].get('strategy'),'multi',pg['diagnostics'].get('multi_column'),'ocr',pg['diagnostics'].get('ocr_status'))
  for t in pg.get('tables',[]): print('TABLE',json.dumps(t,ensure_ascii=False)[:1200])
  for c in pg.get('charts',[]): print('CHART',json.dumps(c,ensure_ascii=False)[:1200])
  for f in pg.get('figures',[]): print('FIG',json.dumps(f,ensure_ascii=False)[:900])

