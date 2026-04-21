import asyncio
import re
from typing import Dict, List

from engine.retrieval import retrieve_dense


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


def _split_sentences(text: str) -> List[str]:
    cleaned = text.replace("\r", "\n")
    parts = re.split(r"(?<=[.!?])\s+|\n+", cleaned)
    return [part.strip(" -") for part in parts if part.strip()]


class MainAgent:
    """
    Local benchmark agent dùng retrieval lexical + synthesis heuristic.
    Không phụ thuộc API ngoài để Stage 2 có thể chạy ổn định trong môi trường lab.
    """

    def __init__(self, version: str = "v2"):
        normalized_version = version.lower()
        self.version = "v2" if "v2" in normalized_version or "optimized" in normalized_version else "v1"
        self.name = f"SupportAgent-{self.version}"
        self.top_k = 2 if self.version == "v1" else 3

    async def query(self, question: str) -> Dict:
        await asyncio.sleep(0)
        chunks = await asyncio.to_thread(retrieve_dense, question, self.top_k)
        answer = self._build_answer(question, chunks)

        sources = list(dict.fromkeys(chunk["source"] for chunk in chunks))
        retrieved_ids = [
            chunk.get("metadata", {}).get("doc_id")
            for chunk in chunks
            if chunk.get("metadata", {}).get("doc_id")
        ]
        contexts = [chunk["text"] for chunk in chunks]
        tokens_used = len(_tokenize(question)) + len(_tokenize(answer)) + sum(len(_tokenize(ctx)) for ctx in contexts)
        estimated_cost = round(tokens_used * 0.0000005, 8)

        return {
            "answer": answer,
            "contexts": contexts,
            "chunks": chunks,
            "retrieved_ids": retrieved_ids,
            "metadata": {
                "model": f"local-rag-{self.version}",
                "tokens_used": tokens_used,
                "estimated_cost": estimated_cost,
                "sources": sources,
                "retrieved_ids": retrieved_ids,
            },
        }

    def _build_answer(self, question: str, chunks: List[Dict]) -> str:
        if self._is_prompt_attack(question):
            return (
                "Tôi không thể làm theo yêu cầu ghi đè hướng dẫn hoặc tiết lộ dữ liệu nội bộ. "
                "Vui lòng hỏi câu hỏi nghiệp vụ cụ thể trong phạm vi tài liệu nội bộ."
            )

        if not chunks:
            return "Không đủ thông tin trong tài liệu nội bộ để trả lời câu hỏi này."

        top_score = chunks[0].get("score", 0.0)
        if top_score < 0.08:
            return "Không đủ thông tin trong tài liệu nội bộ để trả lời chính xác. Vui lòng cung cấp thêm ngữ cảnh."

        selected_sentences = self._select_supporting_sentences(question, chunks)
        if not selected_sentences:
            selected_sentences = [chunks[0]["text"][:280].strip()]

        if self.version == "v1":
            body = selected_sentences[0]
            cited_sources = chunks[:1]
        else:
            body = " ".join(selected_sentences[:2])
            cited_sources = chunks[: min(2, len(chunks))]

        unique_sources = list(dict.fromkeys(chunk["source"] for chunk in cited_sources))
        citation_text = " ".join(f"[{source}]" for source in unique_sources)
        return f"Theo tài liệu nội bộ, {body} {citation_text}".strip()

    def _select_supporting_sentences(self, question: str, chunks: List[Dict]) -> List[str]:
        query_tokens = set(_tokenize(question))
        ranked: List[tuple[float, float, str]] = []

        for chunk in chunks:
            chunk_score = float(chunk.get("score", 0.0))
            for sentence in _split_sentences(chunk.get("text", "")):
                sentence_tokens = set(_tokenize(sentence))
                if not sentence_tokens:
                    continue

                overlap = len(query_tokens & sentence_tokens)
                if overlap == 0 and chunk_score < 0.2:
                    continue

                coverage = overlap / max(1, len(query_tokens))
                score = (0.7 * coverage) + (0.3 * chunk_score)
                ranked.append((score, coverage, sentence))

        ranked.sort(key=lambda item: item[0], reverse=True)

        selected: List[str] = []
        seen = set()
        limit = 1 if self.version == "v1" else 2
        for _, coverage, sentence in ranked:
            normalized = _normalize_text(sentence)
            if normalized in seen:
                continue
            seen.add(normalized)
            selected.append(sentence)
            if coverage >= 0.6:
                break
            if len(selected) >= limit:
                break
        return selected

    def _is_prompt_attack(self, question: str) -> bool:
        lowered = _normalize_text(question)
        attack_markers = [
            "ignore previous instructions",
            "ignore all instructions",
            "system prompt",
            "reveal internal",
            "bypass policy",
            "jailbreak",
            "api key",
            "password dump",
        ]
        return any(marker in lowered for marker in attack_markers)


if __name__ == "__main__":
    agent = MainAgent()

    async def test():
        resp = await agent.query("Làm thế nào để đổi mật khẩu?")
        print(resp)

    asyncio.run(test())
