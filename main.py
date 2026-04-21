import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional

from agent.main_agent import MainAgent
from engine.llm_judge import LLMJudge
from engine.retrieval_eval import RetrievalEvaluator
from engine.runner import BenchmarkRunner


def _safe_mean(values: List[Optional[float]]) -> float:
    valid = [value for value in values if value is not None]
    if not valid:
        return 0.0
    return sum(valid) / len(valid)


class ExpertEvaluator:
    def __init__(self):
        self._evaluator = RetrievalEvaluator(top_k=3)

    async def score(self, case, resp):
        return await self._evaluator.score(case, resp)


class MultiModelJudge:
    def __init__(self):
        self._judge = LLMJudge()

    async def evaluate_multi_judge(self, q, a, gt, response=None, test_case=None):
        return await self._judge.evaluate_multi_judge(
            q,
            a,
            gt,
            response=response,
            test_case=test_case,
        )


def _build_summary(results: List[Dict[str, Any]], agent_version: str) -> Dict[str, Any]:
    retrieval_rows = [
        row["ragas"]["retrieval"]
        for row in results
        if row["ragas"]["retrieval"].get("has_ground_truth")
    ]

    summary = {
        "metadata": {
            "version": agent_version,
            "total": len(results),
            "retrieval_evaluated_cases": len(retrieval_rows),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": {
            "avg_score": _safe_mean([row["judge"]["final_score"] for row in results]),
            "pass_rate": _safe_mean([1.0 if row["status"] == "pass" else 0.0 for row in results]),
            "hit_rate": _safe_mean([row["hit_rate"] for row in retrieval_rows]),
            "mrr": _safe_mean([row["mrr"] for row in retrieval_rows]),
            "agreement_rate": _safe_mean([row["judge"]["agreement_rate"] for row in results]),
            "avg_faithfulness": _safe_mean([row["ragas"]["faithfulness"] for row in results]),
            "avg_relevancy": _safe_mean([row["ragas"]["relevancy"] for row in results]),
            "avg_latency": _safe_mean([row["latency"] for row in results]),
            "total_tokens": int(sum(row.get("tokens_used", 0) for row in results)),
            "estimated_cost": round(sum(row.get("estimated_cost", 0.0) for row in results), 8),
        },
    }
    return summary


async def run_benchmark_with_results(agent_version: str):
    print(f"🚀 Khởi động Benchmark cho {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("❌ Thiếu data/golden_set.jsonl. Hãy chạy 'python data/synthetic_gen.py' trước.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("❌ File data/golden_set.jsonl rỗng. Hãy tạo ít nhất 1 test case.")
        return None, None

    version = "v2" if "v2" in agent_version.lower() or "optimized" in agent_version.lower() else "v1"
    runner = BenchmarkRunner(
        MainAgent(version=version),
        ExpertEvaluator(),
        MultiModelJudge(),
    )
    results = await runner.run_all(dataset, batch_size=5)
    summary = _build_summary(results, agent_version)
    return results, summary


async def run_benchmark(version):
    _, summary = await run_benchmark_with_results(version)
    return summary


async def main():
    v1_summary = await run_benchmark("Agent_V1_Base")
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized")

    if not v1_summary or not v2_summary:
        print("❌ Không thể chạy Benchmark. Kiểm tra lại data/golden_set.jsonl.")
        return

    print("\n📊 --- KẾT QUẢ SO SÁNH (REGRESSION) ---")
    delta = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]
    print(f"V1 Score: {v1_summary['metrics']['avg_score']:.4f}")
    print(f"V2 Score: {v2_summary['metrics']['avg_score']:.4f}")
    print(f"Delta: {'+' if delta >= 0 else ''}{delta:.4f}")

    v2_summary["regression"] = {
        "baseline_version": v1_summary["metadata"]["version"],
        "candidate_version": v2_summary["metadata"]["version"],
        "avg_score_delta": round(delta, 4),
        "hit_rate_delta": round(v2_summary["metrics"]["hit_rate"] - v1_summary["metrics"]["hit_rate"], 4),
        "agreement_rate_delta": round(v2_summary["metrics"]["agreement_rate"] - v1_summary["metrics"]["agreement_rate"], 4),
        "decision": "release" if delta > 0 else "rollback",
    }

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    if delta > 0:
        print("✅ QUYẾT ĐỊNH: CHẤP NHẬN BẢN CẬP NHẬT (APPROVE)")
    else:
        print("❌ QUYẾT ĐỊNH: TỪ CHỐI (BLOCK RELEASE)")


if __name__ == "__main__":
    asyncio.run(main())
