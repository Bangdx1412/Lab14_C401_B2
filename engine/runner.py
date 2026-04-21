import asyncio
import time
from typing import Any, Dict, List


class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge

    async def run_single_test(self, test_case: Dict[str, Any], case_index: int = 0) -> Dict[str, Any]:
        run_started = time.perf_counter()

        try:
            agent_started = time.perf_counter()
            response = await self.agent.query(test_case["question"])
            agent_latency = time.perf_counter() - agent_started

            ragas_scores = await self.evaluator.score(test_case, response)
            judge_result = await self._run_judge(test_case, response)

            metadata = response.get("metadata", {})
            tokens_used = int(metadata.get("tokens_used", 0) or 0)
            cost_estimate = float(metadata.get("estimated_cost", tokens_used * 0.0))
            total_latency = time.perf_counter() - run_started
            status = "pass" if judge_result["final_score"] >= 3.0 else "fail"

            return {
                "case_index": case_index,
                "test_case": test_case["question"],
                "expected_answer": test_case.get("expected_answer", ""),
                "agent_response": response.get("answer", ""),
                "latency": round(total_latency, 4),
                "agent_latency": round(agent_latency, 4),
                "ragas": ragas_scores,
                "judge": judge_result,
                "status": status,
                "retrieved_ids": response.get("retrieved_ids", []),
                "sources": metadata.get("sources", []),
                "tokens_used": tokens_used,
                "estimated_cost": round(cost_estimate, 8),
            }
        except Exception as exc:
            return {
                "case_index": case_index,
                "test_case": test_case.get("question", ""),
                "expected_answer": test_case.get("expected_answer", ""),
                "agent_response": "",
                "latency": round(time.perf_counter() - run_started, 4),
                "agent_latency": 0.0,
                "ragas": {
                    "faithfulness": 0.0,
                    "relevancy": 0.0,
                    "retrieval": {
                        "has_ground_truth": False,
                        "expected_ids": [],
                        "retrieved_ids": [],
                        "hit_rate": None,
                        "mrr": None,
                    },
                },
                "judge": {
                    "final_score": 0.0,
                    "agreement_rate": 0.0,
                    "individual_scores": {},
                    "reasoning": str(exc),
                },
                "status": "error",
                "retrieved_ids": [],
                "sources": [],
                "tokens_used": 0,
                "estimated_cost": 0.0,
                "error": str(exc),
            }

    async def _run_judge(self, test_case: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        question = test_case["question"]
        answer = response.get("answer", "")
        expected_answer = test_case.get("expected_answer", "")

        try:
            return await self.judge.evaluate_multi_judge(
                question,
                answer,
                expected_answer,
                response=response,
                test_case=test_case,
            )
        except TypeError:
            # Keep compatibility with the simpler judge contract used by main.py.
            return await self.judge.evaluate_multi_judge(
                question,
                answer,
                expected_answer,
            )

    async def run_all(self, dataset: List[Dict[str, Any]], batch_size: int = 5) -> List[Dict[str, Any]]:
        semaphore = asyncio.Semaphore(max(1, batch_size))

        async def _bounded_run(index: int, case: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                return await self.run_single_test(case, case_index=index)

        tasks = [asyncio.create_task(_bounded_run(index, case)) for index, case in enumerate(dataset)]
        results = await asyncio.gather(*tasks)
        return sorted(results, key=lambda item: item["case_index"])
