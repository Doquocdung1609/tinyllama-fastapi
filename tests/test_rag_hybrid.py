from app.services import rag_service


class Provider:
    def embed(self, texts):
        return [[0.1, 0.2] for _ in texts]


class Point:
    def __init__(self, score, payload):
        self.score = score
        self.payload = payload


def test_hybrid_retrieval_rescues_exact_vietnamese_terms(monkeypatch):
    correct = {"filename": "finance.pdf", "document_id": "doc", "page": 155,
               "chunk_id": "correct", "text": "Căn cứ loại hình đổi mới tài chính, ba loại gồm đổi mới sản phẩm, đổi mới chuyển đổi rủi ro và đổi mới quy trình."}
    wrong = Point(.92, {"filename": "finance.pdf", "document_id": "doc", "page": 87,
                         "chunk_id": "wrong", "text": "Thông tin chung về doanh nghiệp."})
    monkeypatch.setattr(rag_service, "get_embedding_provider", lambda: Provider())
    monkeypatch.setattr(rag_service.qdrant_service, "search", lambda vector, limit, document_id=None: [wrong])
    monkeypatch.setattr(rag_service, "chunks_for", lambda document_id=None: [correct])
    monkeypatch.setattr(rag_service, "generate", lambda prompt, **kwargs: "Ba loại đổi mới (finance.pdf, trang 155).")

    result = rag_service.query("Ba loại đổi mới tài chính là gì?", 3, .5, "doc")

    assert result["sources"][0]["page"] == 155
    assert result["sources"][0]["lexical_score"] > 0
    assert result["retrieval_method"] == "weighted_rrf_semantic_lexical"
    assert result["sources"][0]["lexical_rank"] == 1
    assert result["selected_evidence"][0]["chunk_id"] == "correct"
    assert "Bằng chứng trực tiếp" in result["final_prompt"]


def test_no_matching_context_returns_without_generation(monkeypatch):
    monkeypatch.setattr(rag_service, "get_embedding_provider", lambda: Provider())
    monkeypatch.setattr(rag_service.qdrant_service, "search", lambda vector, limit, document_id=None: [])
    monkeypatch.setattr(rag_service, "chunks_for", lambda document_id=None: [])
    monkeypatch.setattr(rag_service, "generate", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not generate")))

    result = rag_service.query("Giá Bitcoin năm 2026?", 3, .95, "doc")

    assert result["sources"] == []
    assert "không cung cấp đủ thông tin" in result["answer"]
    assert result["timings"]["generation_ms"] < 10


def test_document_filter_is_forwarded(monkeypatch):
    seen = {}
    monkeypatch.setattr(rag_service, "get_embedding_provider", lambda: Provider())
    monkeypatch.setattr(rag_service, "chunks_for", lambda document_id=None: [])
    def search(vector, limit, document_id=None):
        seen["document_id"] = document_id
        return []
    monkeypatch.setattr(rag_service.qdrant_service, "search", search)
    rag_service.query("Câu hỏi", 1, .9, "chosen-doc")
    assert seen["document_id"] == "chosen-doc"


def test_missing_numeric_anchor_rejects_high_semantic_match(monkeypatch):
    unrelated = {"filename": "finance.pdf", "document_id": "doc", "page": 10,
                 "chunk_id": "unrelated", "text": "Bitcoin và các công nghệ tài chính."}
    monkeypatch.setattr(rag_service, "get_embedding_provider", lambda: Provider())
    monkeypatch.setattr(rag_service.qdrant_service, "search",
                        lambda vector, limit, document_id=None: [Point(.95, unrelated)])
    monkeypatch.setattr(rag_service, "chunks_for", lambda document_id=None: [unrelated])
    monkeypatch.setattr(rag_service, "generate", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not generate")))

    result = rag_service.query("Giá Bitcoin ngày 31/12/2026 là bao nhiêu?", 3, .55, "doc")

    assert result["sources"] == []
    assert "không cung cấp đủ thông tin" in result["answer"]


def test_context_expands_adjacent_chunks_without_changing_retrieval_scores():
    chunks = [
        {"chunk_id": "a", "chunk_index": 10, "document_id": "doc", "text": "items one to three"},
        {"chunk_id": "b", "chunk_index": 11, "document_id": "doc", "text": "items four to eight"},
    ]
    retrieved = [{**chunks[0], "score": .8}]

    expanded = rag_service._context_with_neighbors(retrieved, chunks)

    assert [item["chunk_id"] for item in expanded] == ["a", "b"]
    assert expanded[1]["context_role"] == "adjacent"
    assert "score" not in expanded[1]


def test_lexical_ranking_ignores_output_directives_and_rewards_phrases():
    exact = {"chunk_id": "exact", "page": 155,
             "text": "Căn cứ vào loại hình đổi mới trong tài chính, có thể phân chia ba loại hình đổi mới tài chính."}
    directive_noise = {"chunk_id": "noise", "page": 2,
                       "text": "Tài liệu hướng dẫn trả lời ngắn gọn và trích trang."}

    ranked = rag_service._lexical_candidates(
        "Ba loại đổi mới tài chính căn cứ theo loại hình là gì? Trả lời ngắn gọn và trích trang tài liệu.",
        [directive_noise, exact])

    assert ranked[0]["chunk_id"] == "exact"
    assert "loại hình" in ranked[0]["matched_phrases"]
    assert rag_service._content_question("Câu hỏi? Trả lời ngắn gọn và trích trang tài liệu.") == "câu hỏi"


def test_prompt_budget_never_cuts_a_chunk_mid_text():
    first = {"chunk_id": "a", "chunk_index": 1, "document_id": "doc",
             "text": "A" * 200, "token_estimate": 50, "score": 1.0, "lexical_score": .9}
    too_large = {"chunk_id": "b", "chunk_index": 2, "document_id": "doc",
                 "text": "B" * 1000, "token_estimate": 250, "score": .9, "lexical_score": .8}

    selection = rag_service._select_prompt_context([first, too_large], [first, too_large], token_budget=100)

    assert [item["chunk_id"] for item in selection["included_prompt_context"]] == ["a"]
    assert selection["included_prompt_context"][0]["text"] == first["text"]
    assert any(item["chunk_id"] == "b" and item["exclusion_code"] == "DIRECT_BUDGET_RESERVED"
               for item in selection["excluded_chunks"])


def test_prompt_context_skips_duplicate_windows_and_reaches_real_neighbors():
    repeated = "Nội dung trang 245 nói về các vấn đề thực tiễn của AI."
    chunks = [
        {"chunk_id": "p245-a", "chunk_index": 10, "document_id": "doc", "page": 245,
         "text": repeated, "token_estimate": 20, "lexical_score": .9, "matched_phrases": ["thực tiễn"]},
        {"chunk_id": "p245-b", "chunk_index": 11, "document_id": "doc", "page": 245,
         "text": repeated, "token_estimate": 20},
        {"chunk_id": "p246", "chunk_index": 12, "document_id": "doc", "page": 246,
         "text": "Kiểm toán, thiên vị và quản lý dữ liệu.", "token_estimate": 20},
        {"chunk_id": "p247", "chunk_index": 13, "document_id": "doc", "page": 247,
         "text": "Sai lệch khái niệm cần được giám sát.", "token_estimate": 20},
    ]

    selection = rag_service._select_prompt_context([chunks[0], chunks[1]], chunks, token_budget=300)
    included_ids = [item["chunk_id"] for item in selection["included_prompt_context"]]

    assert included_ids == ["p245-a", "p246"]
    assert any(item["chunk_id"] == "p245-b" and
               item["exclusion_reason"] == "duplicate or overlapping content"
               for item in selection["excluded_chunks"])


def test_ai_alias_and_bilingual_terms_are_preserved_for_retrieval():
    content = rag_service._content_question("Open Banking, cloud và AI liên hệ thế nào?")

    assert "ngân hàng mở" in content
    assert "điện toán đám mây" in content
    assert "ai" in rag_service._terms("AI")


def test_roman_numbered_evidence_is_rendered_as_distinct_items():
    text = "Hai yếu tố: (i) biến động và giải pháp quản lý mới và (ii) biện pháp ứng phó pháp lý."

    formatted = rag_service._format_evidence_text(text)

    assert "\n(i) biến động" in formatted
    assert "\n(ii) biện pháp" in formatted
    assert formatted.replace("\n", " ") == text


def test_definition_and_requested_chapter_are_general_ranking_signals():
    chunks = [
        {"page": 14, "text": "CHƯƠNG 1. ĐỔI MỚI\n1.1 Khái niệm đổi mới\nĐổi mới là việc sử dụng tri thức mới."},
        {"page": 65, "text": "CHƯƠNG 3. NGUỒN GỐC ĐỔI MỚI"},
        {"page": 87, "text": "Năng lực cốt lõi của doanh nghiệp"},
    ]
    chapter_range = rag_service._chapter_range("Theo chương 1, đổi mới là gì?", chunks)

    assert chapter_range == (14, 64)
    exact = rag_service._answer_likelihood(chunks[0], "Theo chương 1, đổi mới là gì?", chapter_range)
    wrong = rag_service._answer_likelihood(chunks[2], "Theo chương 1, đổi mới là gì?", chapter_range)
    assert exact > wrong
    assert rag_service._definition_subject("Tài chính vi mô được định nghĩa là gì?") == "tài chính vi mô"


def test_ambiguous_count_query_selects_multiple_classification_schemes(monkeypatch):
    chunks = [
        {"filename": "finance.pdf", "document_id": "doc", "page": 73, "chunk_index": 10,
         "chunk_id": "noise", "text": "R&D không mấy coi trọng đối tác trong đổi mới.",
         "token_estimate": 20},
        {"filename": "finance.pdf", "document_id": "doc", "page": 155, "chunk_index": 20,
         "chunk_id": "three", "text": "Có thể phân chia ba loại hình đổi mới tài chính: sản phẩm, chuyển đổi rủi ro và quy trình.",
         "token_estimate": 30},
        {"filename": "finance.pdf", "document_id": "doc", "page": 156, "chunk_index": 21,
         "chunk_id": "eight", "text": "Căn cứ chức năng, đổi mới tài chính có thể phân chia thành 8 loại.",
         "token_estimate": 25},
        {"filename": "finance.pdf", "document_id": "doc", "page": 156, "chunk_index": 22,
         "chunk_id": "eight-list", "text": "1. Chuyển giao rủi ro. 2. Định giá rủi ro. 3. Thanh khoản.",
         "token_estimate": 25},
    ]
    monkeypatch.setattr(rag_service, "get_embedding_provider", lambda: Provider())
    monkeypatch.setattr(rag_service.qdrant_service, "search", lambda *args, **kwargs: [])
    monkeypatch.setattr(rag_service, "chunks_for", lambda document_id=None: chunks)
    generated_prompts = []
    def fake_generate(prompt, **kwargs):
        generated_prompts.append(prompt)
        if len(generated_prompts) == 1:
            return "Theo chức năng có 8 loại [E2]."
        return "Theo loại hình có ba loại [E1]. Theo chức năng có 8 loại [E2]."
    monkeypatch.setattr(rag_service, "generate", fake_generate)

    result = rag_service.query("đổi mới tài chính có mấy loại", 5, .55, "doc")

    assert [item["page"] for item in result["selected_evidence"][:2]] == [155, 156]
    assert "ba loại hình đổi mới tài chính" in result["initial_prompt"]
    assert "phân chia thành 8 loại" in result["initial_prompt"]
    assert "Số lượng: 3 loại" in result["final_prompt"]
    assert "Số lượng: 8 loại" in result["final_prompt"]
    assert "trang 155" in result["answer"] and "trang 156" in result["answer"]
    assert [item["evidence_id"] for item in result["supporting_sources"]] == ["E1", "E2"]
    assert result["citation_validation"]["citation_valid"] is True
    assert result["generation_validation"]["retry_performed"] is True
    assert result["generation_validation"]["missing_counts_initial"] == ["3"]
    assert result["generation_validation"]["missing_counts_final"] == []
    assert all(item.get("exclusion_code") and item.get("exclusion_stage")
               for item in result["excluded_chunks"])
    assert any(item["exclusion_code"] == "BELOW_SCORE_THRESHOLD"
               for item in result["excluded_chunks"])
    assert len(generated_prompts) == 2


def test_count_signal_requires_financial_innovation_as_classified_subject():
    question = "đổi mới tài chính có mấy loại"
    direct = {"text": "Đổi mới tài chính có thể phân chia thành 8 loại theo chức năng."}
    other_subject = {"text": "Tác động của quy định đối với đổi mới tài chính có thể được phân loại theo ba cách."}

    assert rag_service._classification_count_match(direct, question) is True
    assert rag_service._classification_count_match(other_subject, question) is False


def test_enumeration_item_number_does_not_satisfy_missing_count_check():
    facts = [{"count": "3"}, {"count": "8"}]
    answer = "Có 8 loại: 1. Rủi ro; 2. Định giá; 3. Thanh khoản."

    assert [item["count"] for item in rag_service._missing_classification_counts(answer, facts)] == ["3"]


def test_count_facts_extract_criterion_from_included_source():
    included = [{"text": "Căn cứ vào chức năng đối với hệ thống tài chính, đổi mới tài chính có thể phân chia thành 8 loại.",
                 "page": 156, "chunk_id": "c", "prompt_position": 1}]

    facts = rag_service._classification_count_facts(included, "đổi mới tài chính có mấy loại")

    assert facts[0]["criterion"] == "chức năng đối với hệ thống tài chính"
    assert facts[0]["count"] == "8"


def test_citation_resolution_removes_repeated_page_label():
    included = [{"filename": "finance.pdf", "page": 155, "chunk_id": "c1"}]

    answer, validation = rag_service._resolve_evidence_citations(
        "Theo loại hình có 3 loại. E-ID: E1, trang: 155.", included)

    assert answer == "Theo loại hình có 3 loại. [finance.pdf, trang 155]."
    assert validation["citation_valid"] is True


def test_direct_budget_precedes_and_caps_adjacent_evidence():
    direct = [
        {"chunk_id": f"d{i}", "chunk_index": i * 10, "document_id": "doc", "page": i,
         "text": f"Bằng chứng trực tiếp {i}", "token_estimate": 30,
         "lexical_score": .9 - i * .01, "score": 1 - i * .01}
        for i in range(1, 4)
    ]
    chunks = list(direct)
    for item in direct:
        for offset in range(1, 5):
            chunks.append({"chunk_id": f"n{item['chunk_index'] + offset}",
                           "chunk_index": item["chunk_index"] + offset,
                           "document_id": "doc", "page": item["page"],
                           "text": f"{offset}. Nội dung liền kề {item['chunk_id']}",
                           "token_estimate": 20})

    selection = rag_service._select_prompt_context(direct, chunks, token_budget=400)

    roles = [item["context_role"] for item in selection["included_prompt_context"]]
    assert roles[:3] == ["selected_evidence"] * 3
    assert len(selection["adjacent_context"]) <= 2
    assert selection["direct_tokens_used"] <= selection["direct_token_budget"]
    assert all("exclusion_code" in item and "exclusion_stage" in item
               for item in selection["excluded_chunks"])


def test_deterministic_claim_grounding_keeps_supported_and_removes_invented_cause():
    included = [{"text": "Người mua bảo vệ trả phí định kỳ cho người bán bảo vệ để chuyển giao rủi ro tín dụng bằng CDS.",
                 "page": 157, "chunk_id": "cds", "filename": "finance.pdf"}]
    draft = ("CDS giúp ngân hàng chuyển giao rủi ro tín dụng vì người mua bảo vệ trả phí cho người bán. "
             "CDS tạo rủi ro hệ thống do nhiều khoản thanh toán lớn bị kích hoạt cùng lúc.")

    answer, audit = rag_service._ground_draft_answer(draft, included)

    assert "trả phí" in answer and "[E1]" in answer
    assert "thanh toán lớn" not in answer
    assert "chưa cung cấp bằng chứng trực tiếp" in answer
    assert audit["kept_claims"] == 1 and audit["removed_count"] == 1


def test_analytical_query_is_split_into_retrieval_facets():
    facets = rag_service._query_facets(
        "Vì sao CDS giúp chuyển giao rủi ro nhưng vẫn ảnh hưởng đến hệ thống tài chính?")

    assert [name for name, _ in facets] == ["clause_1", "clause_2"]
    assert "cds" in facets[0][1]
    assert "hệ thống tài chính" in facets[1][1]


def test_grounding_deduplicates_labels_and_removes_foreign_suffix():
    included = [{"text": "Đổi mới sản phẩm là tạo ra sản phẩm mới. Đổi mới quy trình là cách thức mới.",
                 "page": 155, "chunk_id": "kinds", "filename": "finance.pdf"}]
    draft = ("Đổi mới sản phẩm: tạo ra sản phẩm mới.\n"
             "Đổi mới sản phẩm: tạo ra sản phẩm mới.\n"
             "Đổi mới quy trình là cách thức mới, como procesamiento y negociación.")

    answer, audit = rag_service._ground_draft_answer(draft, included)

    assert answer.count("Đổi mới sản phẩm") == 1
    assert "como" not in answer
    assert "Đổi mới quy trình" in answer
    assert any(item["reason"] == "DUPLICATE_CLAIM" for item in audit["removed_claims"])


def test_claim_audit_keeps_trailing_evidence_id_with_whole_line():
    included = [{"text": "Đổi mới sản phẩm tạo ra sản phẩm mới.", "page": 155,
                 "chunk_id": "product", "filename": "finance.pdf"}]

    audit = rag_service._claim_citation_audit(
        "Đổi mới sản phẩm tạo ra sản phẩm mới. [E1]", included)

    assert audit["claims"][0]["valid_evidence_ids"] == ["E1"]
    assert audit["claims"][0]["status"] == "SUPPORTED"


def test_grounding_stops_after_requested_numbered_items():
    included = [{"text": "(i) Alpha chủ động. (ii) Beta phòng thủ. Nội dung khác về gamma.", "page": 1,
                 "chunk_id": "list", "filename": "list.pdf"}]
    answer, audit = rag_service._ground_draft_answer(
        "(i) Alpha chủ động.\n(ii) Beta phòng thủ.\nNội dung khác về gamma.", included,
        "Hãy nêu hai hình thức chính.")

    assert "Alpha" in answer and "Beta" in answer
    assert "gamma" not in answer
    assert any(item["reason"] == "OUTSIDE_REQUESTED_ENUMERATION"
               for item in audit["removed_claims"])
