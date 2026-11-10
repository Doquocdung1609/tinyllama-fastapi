"""Bounded live resource sampling; no command lines or credentials recorded."""
import json,time,psutil
from pathlib import Path
out=Path(__file__).resolve().parents[1]/'reports/fis_product_v3/resources.json'
samples=[]
for _ in range(90):
    vm=psutil.virtual_memory();rss=0
    for p in psutil.process_iter(['name','cmdline']):
        try:
            cmd=' '.join(p.info['cmdline'] or [])
            if 'uvicorn main:app' in cmd and '18110' in cmd and 'python' in (p.info['name'] or '').lower():rss+=p.memory_info().rss
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    samples.append({'timestamp':time.time(),'available_ram_bytes':vm.available,'api_rss_bytes':rss})
    out.write_text(json.dumps({'sampling_interval_seconds':2,'sampled_window_only':True,'api_rss_peak_sampled':max(s['api_rss_bytes'] for s in samples),'samples':samples},indent=2),encoding='utf-8')
    time.sleep(2)
