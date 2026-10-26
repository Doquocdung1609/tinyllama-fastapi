"""Bounded single-process P6 latency/RSS probe; read-only isolated snapshot."""
import argparse
import json
from pathlib import Path
from statistics import median
from time import perf_counter
import platform
import sys
import psutil
from app.research_qa.backend import ResearchBackend


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();backend=ResearchBackend(args.root)
    question="What were P&G's net sales for the three months ended September 30, 2026?"
    process=psutil.Process();before=process.memory_info().rss;rows=[]
    for index in range(7):
        start=perf_counter();response=backend.query(question,{},'B','EXTRACT',5,False,'automatic_real')
        if response['answer']['status']!='SUPPORTED' or response['answer']['result_values']!=['23276000000']:
            raise AssertionError('P6_REAL_SOURCE_RESULT_CHANGED')
        rows.append({'run':index+1,'cold_in_process':index==0,'http':False,
                     'wall_ms':round((perf_counter()-start)*1000,3),
                     'stages_ms':{k:round(v,3) for k,v in response['timings_ms'].items()},
                     'original_bm25_rank':response['column_refinement']['original_bm25_rank']})
    times=sorted(r['wall_ms'] for r in rows)
    result={'schema_version':'topic3-p6-performance/v1','python':sys.version.split()[0],
            'os':platform.platform(),'fixture':'real SEC P&G 10-Q, isolated read-only snapshot',
            'generation':backend.adapter.freeze['generation'],'manifest_hash':backend.adapter.freeze['manifest_hash'],
            'candidate_budget':64,'runs':rows,'p50_ms':median(times),'p95_nearest_rank_ms':times[-1],
            'rss_before_bytes':before,'rss_after_bytes':process.memory_info().rss,
            'limitations':['single process','no API transport','cold means first call in this process, not cold disk']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'runs':len(rows),'p50_ms':result['p50_ms'],'p95_ms':result['p95_nearest_rank_ms']}))


if __name__=='__main__':main()
