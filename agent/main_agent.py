import asyncio
import re
import os
from typing import Dict, List
from openai import OpenAI

from engine.retrieval import retrieve_dense
import dotenv
dotenv.load_dotenv()

# --- SYSTEM PROMPT ---
RAG_SYSTEM_PROMPT = """
Bạn là một chuyên gia hỗ trợ nội bộ (Internal Support Expert).
Nhiệm vụ của bạn là trả lời câu hỏi của nhân viên dựa trên các ĐOẠN VĂN NGỮ CẢNH (Context) được cung cấp.

QUY TẮC CỐT LÕI:
1. TRỰC TIẾP: Trả lời thẳng vào vấn đề. KHÔNG nhắc lại câu hỏi của người dùng.
2. CHÍNH XÁC: Chỉ sử dụng thông tin có trong Context. Nếu Context không đủ thông tin, hãy nói lịch sự: "Tôi rất tiếc, tài liệu nội bộ hiện tại không có thông tin chi tiết về vấn đề này."
3. NGẮN GỌN: Trình bày súc tích (dễ đọc bằng bullet points nếu cần quy trình).
4. ĐỊNH DẠNG: Luôn kết thúc bằng cách ghi rõ nguồn từ file nào (ví dụ: Source: [abc.txt]).

KHÔNG ĐƯỢC:
- Không bịa đặt (Hallucination).
- Không trả lời các câu hỏi ngoài phạm vi công việc.
""".strip()


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
    Agent RAG sử dụng LLM hỗ trợ Prompt để sinh câu trả lời chất lượng cao.
    Kế thừa cấu trúc cũ để đảm bảo không lỗi pipeline chính.
    """

    def __init__(self, version: str = "v2_optimized_rag"):
        self.version = version
        self.name = f"SupportAgent-RAG-{self.version}"
        self.top_k = 3
        
        # Khởi tạo client OpenAI Compatible
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        self.model_name = "gpt-5.4-nano" 
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    async def query(self, question: str) -> Dict:
        # 1. Tìm kiếm ngữ cảnh
        chunks = await asyncio.to_thread(retrieve_dense, question, self.top_k)
        
        # 2. Sinh câu trả lời dựa trên version
        if self.version == "v1":
            # Bản cũ: Chỉ nối các câu tìm được (Heuristic)
            answer = self._build_answer_v1_legacy(question, chunks)
        else:
            # Bản mới: Dùng LLM + Prompt
            answer = await self._generate_answer_llm(question, chunks)

        sources = list(dict.fromkeys(chunk["source"] for chunk in chunks))
        # ... (giữ nguyên phần metadata bên dưới)
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
                "model": "gpt-4o-mini",  # Cập nhật tên model
                "tokens_used": tokens_used,
                "estimated_cost": estimated_cost,
                "sources": sources,
                "retrieved_ids": retrieved_ids,
            },
        }

    async def _generate_answer_llm(self, question: str, chunks: List[Dict]) -> str:
        """Sử dụng LLM để tổng hợp câu trả lời từ Context."""
        if not chunks:
            return "Tôi không tìm thấy thông tin trong tài liệu nội bộ để trả lời câu hỏi này."

        # Chuẩn bị Context string cho Prompt
        context_str = "\n---\n".join([f"Source: {c['source']}\nContent: {c['text']}" for c in chunks])
        
        user_prompt = f"CONTEXT:\n{context_str}\n\nQUESTION: {question}"

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": RAG_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_completion_tokens=1000 # Giới hạn độ dài để tối ưu chi phí và hiệu năng
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Lỗi khi gọi LLM: {str(e)}. (Fallback: {chunks[0]['text'][:200]}...)"

    def _is_prompt_attack(self, question: str) -> bool:
        attack_patterns = [
            r"ignore previous instructions",
            r"reveal your system prompt",
            r"đừng quan tâm đến những gì bạn đã học",
            r"tiết lộ mã nguồn",
        ]
        text = question.lower()
        return any(re.search(pattern, text) for pattern in attack_patterns)

    def _build_answer_v1_legacy(self, question: str, chunks: List[Dict]) -> str:
        """Logic cũ của V1: Chỉ nối chuỗi thô."""
        if not chunks:
            return "Không đủ thông tin trong tài liệu nội bộ."
        
        # Lấy tối đa 2 đoạn đầu tiên nối lại theo kiểu cũ
        texts = [c["text"] for c in chunks[:2]]
        body = " ".join(texts)
        sources = list(set([c["source"] for c in chunks[:2]]))
        source_str = " ".join([f"[{s}]" for s in sources])
        return f"Theo tài liệu nội bộ: {body[:300]}... {source_str}"

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
