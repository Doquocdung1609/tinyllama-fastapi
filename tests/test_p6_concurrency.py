"""Read/publication overlap on a synthetic, owned temporary lexical index only."""
from concurrent.futures import ThreadPoolExecutor
from app.financial_query import resolve_financial_query
from app.research_qa.backend import DemoResearchBackend


def test_pinned_read_survives_other_generation_publication(tmp_path):
    backend=DemoResearchBackend(tmp_path/'synthetic-owned')
    query='CIK 202 net sales 10-K FY2025'
    resolution=resolve_financial_query(query,{},backend.catalog)
    assert resolution.status.value=='RESOLVED'
    scope=resolution.resolved_scope
    lexical=backend.adapter.lexical
    new_generation='c'*64
    records=list(lexical.records(scope.generation_id))
    def reader():
        seen=[]
        for _ in range(16):
            with backend.adapter.pin(scope):
                hits=backend.adapter.search(query,scope,'B',5,30)
            seen.extend(h.generation for h in hits)
        return seen
    def publisher():
        lexical.start(scope.dataset_id,new_generation,{'synthetic_p6_test':True})
        lexical.add(new_generation,records)
        lexical.seal(new_generation)
        lexical.publish(scope.dataset_id,new_generation)
        return lexical.generation(scope.dataset_id)['generation']
    with ThreadPoolExecutor(max_workers=2) as pool:
        read_future=pool.submit(reader)
        published_future=pool.submit(publisher)
        seen=read_future.result(timeout=30)
        published=published_future.result(timeout=30)
    assert seen and set(seen)=={scope.generation_id}
    assert published==new_generation
    assert lexical.generation(scope.dataset_id,scope.generation_id)['state']=='READY'
