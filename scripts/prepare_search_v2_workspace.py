"""Copy a stopped owner workspace into a new experiment; never overwrite a target."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path

def inventory(root):
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

def prepare(source,destination):
 source=Path(source).resolve(strict=True);destination=Path(destination).resolve()
 repo=Path(__file__).resolve().parents[1]
 if not destination.is_relative_to(repo/'studio_workspace') or not destination.name.startswith('search-v2-'):
  raise ValueError('EXPERIMENT_DESTINATION_MUST_BE_REPO_STUDIO_WORKSPACE_SEARCH_V2')
 if destination.exists() or source==destination or destination.is_relative_to(source):raise ValueError('NEW_DISTINCT_DESTINATION_REQUIRED')
 marker=source/'ownership.json'
 if not marker.is_file():raise ValueError('SOURCE_WORKSPACE_OWNERSHIP_MISSING')
 sys.path.insert(0,str(repo))
 from app.product.workspace import OWNER
 if json.loads(marker.read_text(encoding='utf-8')) .get('owner')!=OWNER:raise ValueError('SOURCE_WORKSPACE_OWNERSHIP_INVALID')
 # Launcher-managed active source copies are explicitly disallowed.
 state=repo/'tmp/studio-runtime/processes.json'
 if state.exists():
  import psutil
  live=json.loads(state.read_text(encoding='utf-8-sig'))
  if Path(live.get('workspace','')).resolve()==source:
   from datetime import datetime
   for record in live.get('processes',[]):
    if psutil.pid_exists(record['pid']) and abs(psutil.Process(record['pid']).create_time()-datetime.fromisoformat(record['created']).timestamp())<1:raise ValueError('STOP_SOURCE_APPLICATION_BEFORE_COPY')
 if sum(p.stat().st_size for p in source.rglob('*') if p.is_file())+256*1024*1024>shutil.disk_usage(str(destination.parent)).free:raise ValueError('INSUFFICIENT_EXPERIMENT_DISK')
 before=inventory(source);shutil.copytree(source,destination)
 if before!=inventory(source) or before!=inventory(destination):raise ValueError('SOURCE_CHANGED_DURING_COPY_KEEP_TARGET_FOR_INSPECTION')
 data={'purpose':'SEARCH_V2_ISOLATED_EXPERIMENT','source':str(source),'source_inventory':before}
 (destination/'search-v2-experiment.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
 return {'copied_files':len(before),'destination':str(destination)}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--destination',required=True);a=p.parse_args();print(json.dumps(prepare(a.source,a.destination)))
