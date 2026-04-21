"""
Retrieval worker for the benchmark pipeline.

This module prefers ChromaDB retrieval when the vector store is available, and
falls back to lexical retrieval over local docs so Stage 2 can still run in an
offline lab environment.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from functools import lru_cache

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

load_dotenv()

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3
DOC_ID_BY_SOURCE = {
    "it_helpdesk_faq.txt": "doc_it_faq",
    "access_control_sop.txt": "doc_access_control",
    "hr_leave_policy.txt": "doc_hr_leave",
    "policy_refund_v4.txt": "doc_refund",
    "sla_p1_2026.txt": "doc_sla",
}


def _tokenize(text: str) -> list[str]:
    normalized = text.lower()
    tokens: list[str] = []
    current: list[str] = []

    for char in normalized:
        if char.isalnum() or char == "_":
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []

    if current:
        tokens.append("".join(current))

    return tokens


def _score_overlap(query: str, text: str) -> float:
    query_tokens = _tokenize(query)
    text_tokens = _tokenize(text)
    if not query_tokens or not text_tokens:
        return 0.0

    query_token_set = set(query_tokens)
    text_token_set = set(text_tokens)
    overlap = len(query_token_set & text_token_set)
    if overlap == 0:
        return 0.0

    query_bigrams = set(zip(query_tokens, query_tokens[1:]))
    text_bigrams = set(zip(text_tokens, text_tokens[1:]))
    bigram_overlap = len(query_bigrams & text_bigrams)

    coverage = overlap / len(query_token_set)
    return round(coverage + (0.35 * bigram_overlap) + (0.05 * overlap), 4)


def _chunk_document(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    chunks = []
    section_heading = ""
    subsection_heading = ""
    pending_question = ""

    for line in lines:
        if line.startswith("==="):
            section_heading = line.strip("= ").strip()
            subsection_heading = ""
            pending_question = ""
            continue

        if len(line) < 90 and line.endswith(":"):
            subsection_heading = line
            pending_question = ""
            continue

        if line.startswith("Q:"):
            pending_question = line
            continue

        prefixes = [value for value in (section_heading, subsection_heading, pending_question) if value]
        if line.startswith("A:") and prefixes:
            chunks.append(" ".join(prefixes + [line]))
            pending_question = ""
            continue

        chunk = " ".join(prefixes + [line]).strip()
        chunks.append(chunk)

    return chunks or [text.strip()]


@lru_cache(maxsize=1)
def _load_local_chunks() -> list[dict]:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "data", "docs")
    loaded_chunks = []

    for filename, doc_id in DOC_ID_BY_SOURCE.items():
        path = os.path.join(docs_dir, filename)
        if not os.path.exists(path):
            continue

        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        for index, chunk_text in enumerate(_chunk_document(text)):
            loaded_chunks.append(
                {
                    "text": chunk_text,
                    "source": filename,
                    "score": 0.0,
                    "metadata": {
                        "doc_id": doc_id,
                        "chunk_index": index,
                    },
                }
            )

    return loaded_chunks


def _retrieve_lexical(query: str, top_k: int) -> list:
    ranked = []
    for chunk in _load_local_chunks():
        score = _score_overlap(query, chunk["text"])
        if score <= 0:
            continue
        ranked.append(
            {
                "text": chunk["text"],
                "source": chunk["source"],
                "score": score,
                "metadata": dict(chunk["metadata"]),
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:top_k]


def _post_json(url: str, headers: dict[str, str], payload: dict, timeout: int) -> dict | None:
    try:
        import requests
    except ImportError:
        requests = None

    if requests is not None:
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if response.status_code == 200:
                return response.json()
        except Exception:
            return None
        return None

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def _get_embedding_fn():
    """
    Return an embedding function if the environment supports it.
    """
    jina_key = os.getenv("JINA_API_KEY")

    if jina_key:
        def embed_jina(text: str) -> list | None:
            url = "https://api.jina.ai/v1/embeddings"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {jina_key}",
            }
            data = {
                "model": "jina-embeddings-v5-text-small",
                "input": [text],
                "task": "retrieval.query",
                "dimensions": 1024,
            }
            try:
                payload = _post_json(url, headers=headers, payload=data, timeout=20)
                if payload:
                    return payload["data"][0]["embedding"]
            except Exception:
                return None
            return None

        return embed_jina

    provider = os.getenv("EMBEDDING_PROVIDER", "local").lower()

    if provider == "openai":
        try:
            from openai import OpenAI
        except ImportError:
            pass
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                client = OpenAI(api_key=api_key)

                def embed_openai(text: str) -> list:
                    resp = client.embeddings.create(input=text, model="text-embedding-3-small")
                    return resp.data[0].embedding

                return embed_openai

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        pass
    else:
        model_name = os.getenv("LOCAL_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        model = SentenceTransformer(model_name)

        def embed_local(text: str) -> list:
            return model.encode([text])[0].tolist()

        return embed_local

    return lambda text: None


def _get_collection():
    try:
        import chromadb
    except ImportError:
        return None

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chroma_path = os.path.join(base_dir, "chroma_db")
    if not os.path.exists(chroma_path):
        return None

    client = chromadb.PersistentClient(path=chroma_path)
    try:
        return client.get_collection("day09_docs")
    except Exception:
        return None


def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Prefer dense retrieval with ChromaDB, but always keep a lexical fallback.
    """
    collection = _get_collection()
    embed = _get_embedding_fn()

    if collection is not None:
        query_embedding = embed(query)
        if query_embedding is not None:
            try:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    include=["documents", "distances", "metadatas"],
                )

                chunks = []
                for rank, (doc, dist, meta) in enumerate(
                    zip(
                        results["documents"][0],
                        results["distances"][0],
                        results["metadatas"][0],
                    )
                ):
                    source = os.path.basename(str(meta.get("source", "unknown")))
                    chunks.append(
                        {
                            "text": doc,
                            "source": source,
                            "score": round(1 - dist, 4),
                            "metadata": {
                                **meta,
                                "doc_id": meta.get("doc_id") or DOC_ID_BY_SOURCE.get(source),
                                "rank": rank,
                            },
                        }
                    )

                if chunks:
                    return chunks
            except Exception as exc:
                print(f"Warning: Chroma query failed, using lexical fallback. Detail: {exc}")

    return _retrieve_lexical(query, top_k)


def run(state: dict) -> dict:
    task = state.get("task", "")
    top_k = state.get("retrieval_top_k", DEFAULT_TOP_K)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "error": None,
    }

    try:
        chunks = retrieve_dense(task, top_k=top_k)
        sources = list(dict.fromkeys(chunk["source"] for chunk in chunks))

        state["retrieved_chunks"] = chunks
        state["retrieved_sources"] = sources
        worker_io["output"] = {
            "chunks_count": len(chunks),
            "sources": sources,
        }
        state["history"].append(
            f"[{WORKER_NAME}] retrieved {len(chunks)} chunks from {sources}"
        )
    except Exception as exc:
        worker_io["error"] = {"code": "RETRIEVAL_FAILED", "reason": str(exc)}
        state["retrieved_chunks"] = []
        state["retrieved_sources"] = []
        state["history"].append(f"[{WORKER_NAME}] ERROR: {exc}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 50)
    print("Retrieval Worker - Standalone Test")
    print("=" * 50)

    test_queries = [
        "SLA ticket P1 là bao lâu?",
        "Điều kiện được hoàn tiền là gì?",
        "Ai phê duyệt cấp quyền Level 3?",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        result = run({"task": query})
        chunks = result.get("retrieved_chunks", [])
        print(f"  Retrieved: {len(chunks)} chunks")
        for chunk in chunks[:2]:
            print(f"    [{chunk['score']:.3f}] {chunk['source']}: {chunk['text'][:80]}...")
        print(f"  Sources: {result.get('retrieved_sources', [])}")

    print("\nretrieval_worker test done.")
