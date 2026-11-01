from app.product.topic3_lab import historical_experiment


def test_recorded_lab_preserves_method_and_corpus_boundaries():
    result = historical_experiment()
    assert result['status'] == 'RECORDED_EXPERIMENT_NOT_LIVE'
    assert result['human_gold'] is False
    assert len(result['questions']) == 6
    assert 'AUTHOR_SPLADE' in result['unavailable_live_modes']
    positive = next(q for q in result['questions'] if q['answerable'])
    arms = {arm['name']: arm for arm in positive['arms']}
    assert len(arms) == 8
    assert arms['R2_SPLADE']['family'] == 'AUTHOR_METHOD_REPRODUCTION'
    assert arms['R6_AUTHOR_DETERMINISTIC_STAGE2']['family'] == 'AUTHOR_CODE_DETERMINISTIC_NOT_NEURAL'
    assert arms['I1_STRUCTURE_BM25']['family'] == 'PROJECT_IMPROVEMENT_DIFFERENT_CHUNK_COUNT'
    assert all(arm['query_ms'] >= 0 for arm in arms.values())
