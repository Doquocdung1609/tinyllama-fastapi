"""Evaluate the preregistered synthetic fixture; this is not real SEC QA evidence."""
import hashlib,json,secrets,statistics,sys,time
from pathlib import Path
from tempfile import TemporaryDirectory
from app.research_qa.backend import DemoResearchBackend

CASES=Path('docs/topic3/milestone_d/autonomous_execution/D4_SYNTHETIC_QA_CASES_v1.json')

def main():
    source=CASES.read_bytes();frozen=json.loads(source)
    with TemporaryDirectory() as temp:
        backend=DemoResearchBackend(Path(temp)/'synthetic-demo')
        results=[]
        for case in frozen['cases']:
            before=time.perf_counter()
            r=backend.query(case['question'],{},'B',case['operation'])
            latency=(time.perf_counter()-before)*1000
            answer=r['answer'];claims=answer['claims'];supported=answer['status']=='SUPPORTED'
            value=claims[0]['result_values'][0] if claims else None
            unit=claims[0]['unit'] if claims else None
            citation_ok=bool(claims) and all(o['source_url']=='https://example.invalid/synthetic-d4.htm' and o['structural_path'] for o in claims[0]['operands'])
            correct=supported and value==case.get('expected_answer') and unit==case.get('expected_unit') and citation_ok
            results.append({'id':case['id'],'answerable':case['answerable'],'status':answer['status'],'retrieval_status':r['retrieval_status'],
                'value':value,'unit':unit,'citation_ok':citation_ok,'correct':bool(correct),'latency_ms':round(latency,3),
                'expected_failure_observed':(not case['answerable'] and (case['expected_failure'] in answer['reasons'] or r['retrieval_status']==case['expected_failure']))})
    answerable=[x for x in results if x['answerable']];answered=[x for x in answerable if x['status']=='SUPPORTED']
    summary={'identity':'d4-synthetic-qa-evaluation/v1','fixture_sha256':hashlib.sha256(source).hexdigest(),
        'python':sys.version.split()[0],'question_count':len(results),'answerable':len(answerable),'answered':len(answered),
        'answer_coverage':len(answered)/len(answerable),'conditional_correctness':sum(x['correct'] for x in answered)/len(answered) if answered else None,
        'all_question_correctness':sum(x['correct'] for x in results)/len(results),
        'appropriate_abstention':sum(x['expected_failure_observed'] for x in results if not x['answerable']),
        'false_abstentions':len(answerable)-len(answered),'unsupported_claims':sum(x['status']=='SUPPORTED' and not x['correct'] for x in results),
        'latency_p50_ms':round(statistics.median(x['latency_ms'] for x in results),3),'latency_max_ms':max(x['latency_ms'] for x in results),
        'cases':results,'limitations':['Synthetic only','No human SEC adjudication','No LLM','In-process coordinator timing, not HTTP latency']}
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
