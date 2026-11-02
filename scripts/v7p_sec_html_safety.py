"""Own and stop only an isolated synthetic HTML safety test service."""
import os,secrets,subprocess,sys,time
from pathlib import Path
import requests

def main():
    env=os.environ.copy();root=Path.cwd()/'tmp/topic3'/('a7-html-safety-'+secrets.token_hex(4));env['V7P_SYNTHETIC_SAFETY_ROOT']=str(root)
    env['STUDIO_API_TOKEN']=env['V7P_SYNTHETIC_TOKEN']=secrets.token_urlsafe(32)
    root.parent.mkdir(parents=True,exist_ok=True)
    process=subprocess.Popen([sys.executable,'-m','uvicorn','scripts.v7p_sec_safety_server:app','--host','127.0.0.1','--port','18113'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            if process.poll() is not None:raise RuntimeError('SYNTHETIC_SERVER_START_FAILED')
            try:
                if requests.get('http://127.0.0.1:18113/docs',timeout=1).status_code==200:break
            except requests.RequestException:pass
            time.sleep(.5)
        node=os.getenv('V7P_NODE','node');subprocess.run([node,'frontend/v7p_sec_html_safety.cjs'],env=env,check=True,timeout=120)
    finally:process.terminate();process.wait(timeout=15)

if __name__=='__main__':main()
