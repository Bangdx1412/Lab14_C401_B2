import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence


DOC_SOURCE_TO_ID = {
    "support/helpdesk-faq.md": "doc_it_faq",
    "it_helpdesk_faq.txt": "doc_it_faq",
    "support/helpdesk-faq.txt": "doc_it_faq",
    "it/access-control-sop.md": "doc_access_control",
    "access_control_sop.txt": "doc_access_control",
    "it/access-control-sop.txt": "doc_access_control",
    "hr/leave-policy-2026.pdf": "doc_hr_leave",
    "hr_leave_policy.txt": "doc_hr_leave",
    "policy/refund-v4.pdf": "doc_refund",
    "policy_refund_v4.txt": "doc_refund",
    "support/sla-p1-2026.pdf": "doc_sla",
    "sla_p1_2026.txt": "doc_sla",
}


def _normalize_source(source: str) -> str:
    return source.strip().replace("\\", "/").lower()


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _tokenize(text: str) -> List[str]:
    normalized = _normalize_text(text)
    tokens: List[str] = []
    current: List[str] = []

    for char in normalized:
        if char.isalnum() or char == "_":
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []

    if current:
        tokens.append("".join(current))

    return tokens


def _safe_mean(values: Sequence[Optional[float]]) -> float:
    valid = [value for value in values if value is not None]
    if not valid:
        return 0.0
    return sum(valid) / len(valid)


class RetrievalEvaluator:
    def __init__(self, top_k: int = 3):
        self.top_k = top_k

    def calculate_hit_rate(
        self,
        expected_ids: List[str],
        retrieved_ids: List[str],
        top_k: int = 3,
    ) -> float:
        top_retrieved = retrieved_ids[:top_k]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    async def score(self, test_case: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        return self.score_case(test_case, response)

    def score_case(self, test_case: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        expected_ids = self._expected_ids(test_case)
        retrieved_ids = self._retrieved_ids(response)
        expected_answer = test_case.get("expected_answer", "")
        answer = response.get("answer", "")
        contexts = response.get("contexts", [])
        question = test_case.get("question", "")

        retrieval = self._score_retrieval(expected_ids, retrieved_ids)
        faithfulness = self._score_faithfulness(answer, expected_answer, contexts)
        relevancy = self._score_relevancy(question, answer, expected_answer)

        return {
            "faithfulness": round(faithfulness, 4),
            "relevancy": round(relevancy, 4),
            "retrieval": retrieval,
        }

    async def evaluate_batch(self, dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        per_case = []
        for item in dataset:
            response = item.get("response", {})
            if not response and "retrieved_ids" in item:
                response = {"retrieved_ids": item.get("retrieved_ids", [])}
            per_case.append(self.score_case(item, response))

        retrieval_scores = [entry["retrieval"] for entry in per_case if entry["retrieval"]["has_ground_truth"]]
        return {
            "avg_hit_rate": round(_safe_mean([entry["hit_rate"] for entry in retrieval_scores]), 4),
            "avg_mrr": round(_safe_mean([entry["mrr"] for entry in retrieval_scores]), 4),
            "avg_faithfulness": round(_safe_mean([entry["faithfulness"] for entry in per_case]), 4),
            "avg_relevancy": round(_safe_mean([entry["relevancy"] for entry in per_case]), 4),
            "evaluated_cases": len(retrieval_scores),
        }

    def _score_retrieval(self, expected_ids: List[str], retrieved_ids: List[str]) -> Dict[str, Any]:
        if not expected_ids:
            return {
                "has_ground_truth": False,
                "expected_ids": [],
                "retrieved_ids": retrieved_ids[: self.top_k],
                "hit_rate": None,
                "mrr": None,
            }

        return {
            "has_ground_truth": True,
            "expected_ids": expected_ids,
            "retrieved_ids": retrieved_ids[: self.top_k],
            "hit_rate": round(self.calculate_hit_rate(expected_ids, retrieved_ids, top_k=self.top_k), 4),
            "mrr": round(self.calculate_mrr(expected_ids, retrieved_ids), 4),
        }

    def _expected_ids(self, test_case: Dict[str, Any]) -> List[str]:
        if isinstance(test_case.get("expected_retrieval_ids"), list):
            return [str(item) for item in test_case["expected_retrieval_ids"] if item]

        metadata = test_case.get("metadata", {})
        ground_truth_id = metadata.get("ground_truth_id")
        if ground_truth_id:
            return [str(ground_truth_id)]
        return []

    def _retrieved_ids(self, response: Dict[str, Any]) -> List[str]:
        ids: List[str] = []

        for value in self._iter_retrieval_candidates(response):
            if isinstance(value, str):
                normalized = _normalize_source(value)
                ids.append(DOC_SOURCE_TO_ID.get(normalized, value))

        return list(dict.fromkeys(ids))

    def _iter_retrieval_candidates(self, response: Dict[str, Any]) -> Iterable[str]:
        direct_ids = response.get("retrieved_ids", [])
        if isinstance(direct_ids, list):
            yield from [item for item in direct_ids if isinstance(item, str)]

        metadata = response.get("metadata", {})
        if isinstance(metadata, dict):
            sources = metadata.get("sources", [])
            if isinstance(sources, list):
                yield from [item for item in sources if isinstance(item, str)]

            metadata_ids = metadata.get("retrieved_ids", [])
            if isinstance(metadata_ids, list):
                yield from [item for item in metadata_ids if isinstance(item, str)]

        chunks = response.get("chunks", [])
        if isinstance(chunks, list):
            for chunk in chunks:
                if not isinstance(chunk, dict):
                    continue
                chunk_meta = chunk.get("metadata", {})
                if isinstance(chunk_meta, dict) and chunk_meta.get("doc_id"):
                    yield str(chunk_meta["doc_id"])
                source = chunk.get("source")
                if isinstance(source, str):
                    yield source

    def _score_faithfulness(
        self,
        answer: str,
        expected_answer: str,
        contexts: Sequence[str],
    ) -> float:
        answer_tokens = _tokenize(answer)
        if not answer_tokens:
            return 0.0

        support_text = " ".join(contexts)
        if expected_answer:
            support_text = f"{support_text} {expected_answer}".strip()

        support_tokens = set(_tokenize(support_text))
        if not support_tokens:
            return 0.0

        supported = sum(1 for token in answer_tokens if token in support_tokens)
        return supported / len(answer_tokens)

    def _score_relevancy(self, question: str, answer: str, expected_answer: str) -> float:
        expected_f1 = self._token_f1(answer, expected_answer) if expected_answer else 0.0
        question_overlap = self._question_overlap(question, answer)

        if expected_answer:
            return min(1.0, (0.7 * expected_f1) + (0.3 * question_overlap))
        return question_overlap

    def _question_overlap(self, question: str, answer: str) -> float:
        question_tokens = set(_tokenize(question))
        answer_tokens = set(_tokenize(answer))
        if not question_tokens or not answer_tokens:
            return 0.0
        return len(question_tokens & answer_tokens) / len(question_tokens)

    def _token_f1(self, text_a: str, text_b: str) -> float:
        tokens_a = _tokenize(text_a)
        tokens_b = _tokenize(text_b)
        if not tokens_a or not tokens_b:
            return 0.0

        overlap = sum((Counter(tokens_a) & Counter(tokens_b)).values())
        if overlap == 0:
            return 0.0

        precision = overlap / len(tokens_a)
        recall = overlap / len(tokens_b)
        return (2 * precision * recall) / (precision + recall)
