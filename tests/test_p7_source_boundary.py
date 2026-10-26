"""Permanent regression for a forged research member filing identity."""
import pytest
from app.table_evidence.real_source import validate_frozen_parent_membership
from app.research_retrieval.snapshot import FrozenResearchSnapshot
from types import SimpleNamespace


def test_frozen_member_filing_must_equal_authenticated_parent():
    frozen = {'filing_id': 'sec:0000354950:0001628280-26-058715'}
    payload = {'filing_id': 'sec:0000080424:0000080424-26-000256'}
    with pytest.raises(ValueError, match='FROZEN_PARENT_FILING_ID_MISMATCH'):
        validate_frozen_parent_membership(frozen, payload)


def test_research_snapshot_refuses_nonready_generation_before_search():
    class FailedLexical:
        def generation(self, dataset, generation):return {'state': 'FAILED'}
        def search(self, *args):return []
    snapshot = object.__new__(FrozenResearchSnapshot)
    snapshot.lexical = FailedLexical()
    scope = SimpleNamespace(dataset_id='synthetic', generation_id='f' * 64,
                            cik='0000000202', eligible_filing_ids=('synthetic-filing',))
    with pytest.raises(ValueError, match='RESEARCH_GENERATION_NOT_READY'):
        snapshot.search('net sales', scope, 'B', 5, 30)
