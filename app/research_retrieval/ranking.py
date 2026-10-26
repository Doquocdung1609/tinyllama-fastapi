"""Canonical deduplication, explicit RRF and the frozen table-context rule."""
from app.research_retrieval.contracts import RankedCandidateV1
from app.table_evidence.identity import digest


def deduplicate(candidates):
    found={}
    for c in candidates:
        old=found.get(c.chunk_id)
        if old and (old.payload_hash,old.generation,old.manifest_hash)!=(c.payload_hash,c.generation,c.manifest_hash):
            raise ValueError('DUPLICATE_IDENTITY_CONFLICT')
        if old is None or c.score>old.score:found[c.chunk_id]=c
    return sorted(found.values(),key=lambda c:(-c.score,c.chunk_id))


def fuse(b,d,weights=(1,1),k=60):
    b,d=deduplicate(b),deduplicate(d)
    br={c.chunk_id:i+1 for i,c in enumerate(b)};dr={c.chunk_id:i+1 for i,c in enumerate(d)}
    members={c.chunk_id:c for c in [*d,*b]}
    for c in [*b,*d]:
        if c.payload_hash!=members[c.chunk_id].payload_hash:
            raise ValueError('CROSS_CHANNEL_PAYLOAD_CONFLICT')
    records=[]
    for cid,c in members.items():
        bc=weights[0]/(k+br[cid]) if cid in br else 0
        dc=weights[1]/(k+dr[cid]) if cid in dr else 0
        records.append(RankedCandidateV1(candidate=c,rank=1,score=bc+dc,b_rank=br.get(cid),d_rank=dr.get(cid),b_contribution=bc,d_contribution=dc))
    records.sort(key=lambda c:(-c.score,c.candidate.chunk_id))
    return [c.model_copy(update={'rank':i+1}) for i,c in enumerate(records)]


def single(candidates):
    return [RankedCandidateV1(candidate=c,rank=i+1,score=c.score,b_rank=i+1 if c.channel=='B' else None,
                             d_rank=i+1 if c.channel=='D' else None) for i,c in enumerate(deduplicate(candidates))]


def table_rerank(ranks,intent,evidence_lookup):
    """Same fixed top20 pool; zero bonus for absent or unresolved D2 context."""
    pool=list(ranks[:20]); maximum=max([max(0,c.score) for c in pool],default=0)
    wanted={m.canonical.casefold() for m in intent.metric_mentions if m.relationship in {'EXACT','SYNONYM'}}
    question=intent.normalized_question
    roles={r for word,r in [('fair value','FAIR_VALUE'),('carrying','CARRYING_VALUE'),('basic','BASIC_EPS'),('diluted','DILUTED_EPS')] if word in question}
    result=[]
    for c in pool:
        e=evidence_lookup(c.candidate)
        row_bonus=role_bonus=0
        if e is not None:
            if e.parent_payload_hash!=c.candidate.payload_hash or e.source_generation!=c.candidate.generation or e.manifest_hash!=c.candidate.manifest_hash:
                raise ValueError('D2_EVIDENCE_IDENTITY_MISMATCH')
            if e.status=='VERIFIED_CONTEXT':
                row_bonus=.05 if e.row_label.casefold() in wanted else 0
                actual={v.measurement_basis for v in e.cells if v.status=='VERIFIED_CONTEXT'}
                role_bonus=.05 if roles and roles<=actual else 0
        normalized=max(0,c.score)/maximum if maximum else 0
        result.append(c.model_copy(update={'score':normalized+row_bonus+role_bonus,'row_bonus':row_bonus,'role_bonus':role_bonus}))
    result.sort(key=lambda c:(-c.score,c.rank,c.candidate.chunk_id))
    return [c.model_copy(update={'rank':i+1}) for i,c in enumerate(result)]
