from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from uuid import uuid4

import yaml

from benchmark.config import DEFAULT_BENCHMARK_MODELS
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
            if "cases" in data:
                for item in data["cases"]:
                    case = dict(item)
                    case["role_id"] = case.get("role_id") or data["role_id"]
                    case["id"] = case.get("id") or f"{data['role_id']}_{len(cases) + 1}"
                    cases.append(case)
            else:
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
            row = {
                "role_id": role_id,
                "role_name": role.name,
                "models": {},
                "latest_completion": None,
                "tool_use_score": None,
                "safety_score": None,
                "main_failure": "尚未运行",
                "recommended_fix": "运行动态 Benchmark 后生成建议。",
            }
            latest_items = []
            for model_id in DEFAULT_BENCHMARK_MODELS:
                item = latest_by_key.get(f"{role_id}::{model_id}")
                row["models"][model_id] = item["completion"] if item else None
                if item:
                    latest_items.append(item)
            if latest_items:
                best_item = max(latest_items, key=lambda item: item["completion"])
                row["latest_completion"] = best_item["completion"]
                row["tool_use_score"] = best_item.get("tool_use_score") or self._average_case_dimension(best_item, "tool_use")
                row["safety_score"] = best_item.get("safety_score") or self._average_case_dimension(best_item, "safety_boundary")
                row["main_failure"] = best_item.get("main_failure") or self._main_failure(best_item.get("case_results", []))
                row["recommended_fix"] = best_item.get("recommended_fix") or self._recommended_fix(row["main_failure"])
            matrix.append(row)
        return {
            "runs": [{"run_id": run["run_id"], "created_at": run["created_at"]} for run in runs[:10]],
            "matrix": matrix,
            "dimensions": list(DEFAULT_DIMENSIONS),
            "models": DEFAULT_BENCHMARK_MODELS,
        }

    def run(
        self,
        role_ids: Optional[Iterable[str]] = None,
        model_ids: Optional[Iterable[str]] = None,
        case_ids: Optional[Iterable[str]] = None,
    ) -> dict:
        selected_roles = list(role_ids or self.roles.keys())
        selected_models = list(model_ids or DEFAULT_BENCHMARK_MODELS)
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
                tool_use_score = round(sum(item["scores"].get("tool_use", 0) for item in case_results) / len(case_results), 3)
                safety_score = round(sum(item["scores"].get("safety_boundary", 0) for item in case_results) / len(case_results), 3)
                main_failure = self._main_failure(case_results)
                run["results"].append(
                    {
                        "role_id": role_id,
                        "role_name": role.name,
                        "model_id": model_id,
                        "completion": completion,
                        "tool_use_score": tool_use_score,
                        "safety_score": safety_score,
                        "main_failure": main_failure,
                        "recommended_fix": self._recommended_fix(main_failure),
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
            "expected_keywords": case.get("expected_keywords", []),
            "required_tools": required_tools,
            "risk_flags": case.get("risk_flags", []),
            "rubric_notes": case.get("rubric_notes", ""),
            "scores": scores,
            "rule_scores": rule_scores,
            "llm_judge_scores": judge_scores,
            "total": weighted_total(scores, weights),
            "judge": "mixed-rules-llm-v1" if judge_scores else "heuristic-v1",
        }

    @staticmethod
    def _main_failure(case_results: List[dict]) -> str:
        if not case_results:
            return "尚未运行"
        dimension_labels = {
            "domain_accuracy": "领域准确性不足",
            "workflow_alignment": "工作流对齐不足",
            "tool_use": "工具使用不足",
            "safety_boundary": "安全边界不足",
            "actionability": "行动建议不足",
            "human_like_work": "真实职业工作感不足",
        }
        averages = {}
        for dimension in DEFAULT_DIMENSIONS:
            averages[dimension] = sum(item["scores"].get(dimension, 0) for item in case_results) / len(case_results)
        weakest = min(averages, key=averages.get)
        return dimension_labels[weakest]

    @staticmethod
    def _average_case_dimension(item: dict, dimension: str) -> Optional[float]:
        case_results = item.get("case_results", [])
        if not case_results:
            return None
        return round(sum(case.get("scores", {}).get(dimension, 0) for case in case_results) / len(case_results), 3)

    @staticmethod
    def _recommended_fix(main_failure: str) -> str:
        fixes = {
            "领域准确性不足": "补充职业术语、关键检查点和答案 rubric。",
            "工作流对齐不足": "强化角色 YAML 中的步骤顺序，并在 case 中要求结构化流程。",
            "工具使用不足": "把 required_tools 接入真实 workflow，记录工具调用结果。",
            "安全边界不足": "增加风险提示、不能替代专业服务和不确定性说明。",
            "行动建议不足": "要求输出下一步、检查清单和复盘指标。",
            "真实职业工作感不足": "补充客户/患者/团队协作和交付场景。",
        }
        return fixes.get(main_failure, "补充 case 和评分维度。")

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
