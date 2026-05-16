from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from uuid import uuid4

import yaml

from benchmark.scoring import DEFAULT_DIMENSIONS, blend_scores, heuristic_scores, judge_prompt, parse_judge_scores, weighted_total
from benchmark.storage import BenchmarkStorage


CASE_DIR = Path(__file__).resolve().parent / "cases"


class BenchmarkRunner:
    def __init__(self, roles: Dict[str, object], agent_service, storage: BenchmarkStorage, case_dir: Path = CASE_DIR):
        self.roles = roles
        self.agent_service = agent_service
        self.storage = storage
        self.case_dir = case_dir

    def load_cases(self) -> List[dict]:
        cases = []
        for path in sorted(self.case_dir.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            data["id"] = data.get("id") or path.stem
            cases.append(data)
        return cases

    def summary(self) -> dict:
        runs = self.storage.list_runs()
        latest_by_key = {}
        for run in runs:
            for item in run.get("results", []):
                key = f"{item['role_id']}::{item['model_id']}"
                if key not in latest_by_key:
                    latest_by_key[key] = item
        matrix = []
        for role_id, role in self.roles.items():
            row = {"role_id": role_id, "role_name": role.name, "models": {}}
            for model_id in ["minimax-m2.7", "deepseek-v3.2", "deepseek-reasoner"]:
                item = latest_by_key.get(f"{role_id}::{model_id}")
                row["models"][model_id] = item["completion"] if item else None
            matrix.append(row)
        return {
            "runs": [{"run_id": run["run_id"], "created_at": run["created_at"]} for run in runs[:10]],
            "matrix": matrix,
            "dimensions": list(DEFAULT_DIMENSIONS),
        }

    def run(
        self,
        role_ids: Optional[Iterable[str]] = None,
        model_ids: Optional[Iterable[str]] = None,
        case_ids: Optional[Iterable[str]] = None,
    ) -> dict:
        selected_roles = list(role_ids or ["interpreter", "nutritionist", "interior_designer"])
        selected_models = list(model_ids or ["minimax-m2.7"])
        selected_case_ids = set(case_ids or [])
        cases = [
            case
            for case in self.load_cases()
            if case["role_id"] in selected_roles and (not selected_case_ids or case["id"] in selected_case_ids)
        ]
        if not cases:
            raise ValueError("No benchmark cases matched the request")

        run = {
            "run_id": uuid4().hex,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "results": [],
        }
        for role_id in selected_roles:
            role = self.roles.get(role_id)
            if role is None:
                raise ValueError(f"Unknown role_id: {role_id}")
            role_cases = [case for case in cases if case["role_id"] == role_id]
            if not role_cases:
                continue
            for model_id in selected_models:
                case_results = [self._run_case(role, model_id, case) for case in role_cases]
                completion = round(sum(item["total"] for item in case_results) / len(case_results), 3)
                run["results"].append(
                    {
                        "role_id": role_id,
                        "role_name": role.name,
                        "model_id": model_id,
                        "completion": completion,
                        "case_results": case_results,
                    }
                )
        self.storage.save_run(run)
        return run

    def get_run(self, run_id: str) -> dict:
        return self.storage.load_run(run_id)

    def _run_case(self, role, model_id: str, case: dict) -> dict:
        result = self.agent_service.chat(
            role_id=role.id,
            message=case["prompt"],
            session_id=f"benchmark-{uuid4().hex}",
            text_model=model_id,
        )
        required_tools = case.get("required_tools", [])
        # Chat tool calls are implicit in the workflow result; attachment-free cases use declared tool alignment.
        used_tools = required_tools if case.get("assume_tools_used", True) else []
        weights = role.benchmark.get("dimensions") or DEFAULT_DIMENSIONS
        rule_scores = heuristic_scores(result.answer, case.get("expected_keywords", []), required_tools, used_tools)
        judge_scores = self._llm_judge(role, case, result.answer, weights, model_id)
        scores = blend_scores(rule_scores, judge_scores)
        return {
            "case_id": case["id"],
            "prompt": case["prompt"],
            "answer": result.answer,
            "scores": scores,
            "rule_scores": rule_scores,
            "llm_judge_scores": judge_scores,
            "total": weighted_total(scores, weights),
            "judge": "mixed-rules-llm-v1" if judge_scores else "heuristic-v1",
        }

    def _llm_judge(self, role, case: dict, answer: str, weights: dict, model_id: str) -> dict:
        router = getattr(self.agent_service, "model_router", None)
        if router is None:
            return {}
        try:
            content = router.invoke(
                judge_prompt(role.name, case["prompt"], answer, weights),
                model_id=model_id,
                temperature=0.0,
            )
        except Exception:
            return {}
        return parse_judge_scores(content, weights)
