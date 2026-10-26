"""Separate CPU-only D2 stage boundaries on a labelled synthetic source."""
import json
import time
from scripts.benchmark_table_evidence import fixture,CASES_PATH,distribution
from app.table_evidence import context_from_snapshot,build_table_evidence,build_evidence_bundle
from app.table_evidence.compact import compact_view
from app.table_evidence.identity import canonical


def main():
    parents,raw,meta,b=fixture(json.loads(CASES_PATH.read_text())[0]); p=parents[0]
    timings={k:[] for k in ['context','evidence','bundle','compact_serialization']}
    for _ in range(25):
        start=time.perf_counter();ctx=context_from_snapshot(raw,meta,b);timings['context'].append((time.perf_counter()-start)*1000)
        start=time.perf_counter();e=build_table_evidence(p,ctx).evidence;timings['evidence'].append((time.perf_counter()-start)*1000)
        start=time.perf_counter();build_evidence_bundle([p],ctx);timings['bundle'].append((time.perf_counter()-start)*1000)
        start=time.perf_counter();canonical(compact_view(e));timings['compact_serialization'].append((time.perf_counter()-start)*1000)
    print(json.dumps({'synthetic_only':True,'stages':{k:distribution(v) for k,v in timings.items()},
        'limits':['No HTTP transport exposure at D2.','C verification/hash/parse/rechunk real-source boundaries are in retained audit v2.',
                  'Context creation reconstructs source once; each current candidate reparses the serialized full filing, a measured future optimization opportunity.',
                  'No persistent cache introduced; source limits unchanged.']},indent=2))


if __name__=='__main__':main()
