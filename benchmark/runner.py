from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional
from uuid import uuid4

import yaml

from benchmark.config import DEFAULT_BENCHMARK_MODELS
from benchmark.output_storage import OutputStorage
from benchmark.reviews import latest_manual_review
from benchmark.scoring import DEFAULT_DIMENSIONS, blend_scores, heuristic_scores, judge_prompt, parse_judge_scores, weighted_total
from benchmark.storage import BenchmarkStorage


CASE_DIR = Path(__file__).resolve().parent / "cases"


# Run status constants
STATUS_PENDING = "pending"
STATUS_GENERATING = "generating"
STATUS_GENERATED = "generated"
STATUS_EVALUATING = "evaluating"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


class BenchmarkRunner:
    def __init__(
        self,
        roles: Dict[str, object],
        agent_service,
        storage: BenchmarkStorage,
        output_storage: Optional[OutputStorage] = None,
        case_dir: Path = CASE_DIR,
    ):
        self.roles = roles
        self.agent_service = agent_service
        self.storage = storage
        self.output_storage = output_storage or OutputStorage()
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
        latest_run = runs[0] if runs else None
        manual_review = latest_manual_review(latest_run.get("run_id") if latest_run else None) or latest_manual_review()
        manual_items = (manual_review or {}).get("reviews", {})
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
                "codex_review": None,
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
            review_item = manual_items.get(role_id)
            if review_item:
                row["codex_review"] = {
                    "score": review_item.get("codex_score"),
                    "grade": review_item.get("grade"),
                    "verdict": review_item.get("verdict"),
                    "strengths": review_item.get("strengths", []),
                    "weaknesses": review_item.get("weaknesses", []),
                    "recommended_fix": review_item.get("recommended_fix"),
                }
            matrix.append(row)
        return {
            "runs": [
                {
                    "run_id": run["run_id"],
                    "created_at": run["created_at"],
                    "evaluated_at": run.get("evaluated_at"),
                    "status": run.get("status"),
                }
                for run in runs[:10]
            ],
            "matrix": matrix,
            "dimensions": list(DEFAULT_DIMENSIONS),
            "models": DEFAULT_BENCHMARK_MODELS,
            "manual_review": {
                "review_id": manual_review.get("review_id"),
                "reviewer": manual_review.get("reviewer"),
                "reviewed_at": manual_review.get("reviewed_at"),
                "source_run_id": manual_review.get("source_run_id"),
                "source_model_id": manual_review.get("source_model_id"),
                "method": manual_review.get("method"),
                "summary": manual_review.get("summary", {}),
            }
            if manual_review
            else None,
        }

    def generate_outputs(
        self,
        role_ids: Optional[Iterable[str]] = None,
        model_ids: Optional[Iterable[str]] = None,
        case_ids: Optional[Iterable[str]] = None,
        case_limit_per_role: Optional[int] = None,
        progress_callback: Optional[Callable[[dict], None]] = None,
    ) -> dict:
        """Phase 1: Generate model outputs without evaluation."""
        selected_roles = list(role_ids or self.roles.keys())
        selected_models = list(model_ids or DEFAULT_BENCHMARK_MODELS)
        selected_case_ids = set(case_ids or [])
        cases = self._select_cases(selected_roles, selected_case_ids, case_limit_per_role)
        if not cases:
            raise ValueError("No benchmark cases matched the request")

        run_id = uuid4().hex
        run = {
            "run_id": run_id,
            "status": STATUS_GENERATING,
            "config": {
                "roles": selected_roles,
                "models": selected_models,
                "case_ids": list(selected_case_ids) if selected_case_ids else None,
                "case_limit_per_role": case_limit_per_role,
                "judge_model": None,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "outputs_generated_at": None,
            "evaluated_at": None,
            "results": [],
        }
        self.storage.save_run(run)

        outputs = []
        total_tasks = len(selected_roles) * len(selected_models) * len(cases)
        completed_tasks = 0

        for role_id in selected_roles:
            print(f"\n[{completed_tasks}/{total_tasks}] Processing role: {role_id}")
            role = self.roles.get(role_id)
            if role is None:
                continue
            role_cases = [case for case in cases if case["role_id"] == role_id]
            if not role_cases:
                continue
            for model_id in selected_models:
                for case in role_cases:
                    output = self._generate_single_output(role, model_id, case)
                    outputs.append(output)
                    completed_tasks += 1
                    print(f"  [{completed_tasks}/{total_tasks}] {model_id}: {case['id']}")
                    if progress_callback:
                        progress_callback({
                            "phase": "generate",
                            "completed": completed_tasks,
                            "total": total_tasks,
                            "current": f"{role_id}/{model_id}/{case['id']}",
                        })

        run["status"] = STATUS_GENERATED
        run["outputs_generated_at"] = datetime.now(timezone.utc).isoformat()
        self.storage.save_run(run)
        self.output_storage.save_outputs(run_id, outputs)

        return {
            "run_id": run_id,
            "status": STATUS_GENERATED,
            "total_outputs": len(outputs),
            "config": run["config"],
        }

    def evaluate_outputs(
        self,
        run_id: str,
        judge_model_id: str,
        use_llm_judge: bool = True,
        progress_callback: Optional[Callable[[dict], None]] = None,
    ) -> dict:
        """Phase 2: Evaluate previously generated outputs."""
        outputs = self.output_storage.load_outputs(run_id)
        if not outputs:
            raise ValueError(f"No outputs found for run: {run_id}")

        run = self.storage.load_run(run_id)
        run["status"] = STATUS_EVALUATING
        run["config"]["judge_model"] = judge_model_id
        self.storage.save_run(run)

        # Group outputs by role_id and model_id
        grouped = {}
        for output in outputs:
            key = f"{output['role_id']}::{output['model_id']}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(output)

        results = []
        total_tasks = len(outputs)
        completed_tasks = 0
        print(f"\n=== Starting Evaluation with {judge_model_id} ===")

        for key, role_model_outputs in grouped.items():
            role_id, model_id = key.split("::", 1)
            role = self.roles.get(role_id)
            if role is None:
                continue

            print(f"\n[{completed_tasks}/{total_tasks}] Evaluating role: {role_id}, model: {model_id}")
            weights = role.benchmark.get("dimensions") or DEFAULT_DIMENSIONS
            case_results = []

            for output in role_model_outputs:
                case_result = self._evaluate_single_output(role, output, judge_model_id, weights, use_llm_judge)
                case_results.append(case_result)
                completed_tasks += 1
                print(f"  [{completed_tasks}/{total_tasks}] {output.get('case_id', 'unknown')}")
                if progress_callback:
                    progress_callback({
                        "phase": "evaluate",
                        "completed": completed_tasks,
                        "total": total_tasks,
                        "current": f"{role_id}/{model_id}/{output.get('case_id', 'unknown')}",
                    })

            completion = round(sum(item["total"] for item in case_results) / len(case_results), 3)
            tool_use_score = round(sum(item["scores"].get("tool_use", 0) for item in case_results) / len(case_results), 3)
            safety_score = round(sum(item["scores"].get("safety_boundary", 0) for item in case_results) / len(case_results), 3)
            main_failure = self._main_failure(case_results)

            results.append({
                "role_id": role_id,
                "role_name": role.name,
                "model_id": model_id,
                "completion": completion,
                "tool_use_score": tool_use_score,
                "safety_score": safety_score,
                "main_failure": main_failure,
                "recommended_fix": self._recommended_fix(main_failure),
                "case_results": case_results,
            })

        run["status"] = STATUS_COMPLETED
        run["evaluated_at"] = datetime.now(timezone.utc).isoformat()
        run["results"] = results
        self.storage.save_run(run)

        return {
            "run_id": run_id,
            "status": STATUS_COMPLETED,
            "judge_model": judge_model_id,
            "total_evaluated": len(outputs),
            "results_count": len(results),
        }

    def _generate_single_output(self, role, model_id: str, case: dict) -> dict:
        """Generate a single model output for a case."""
        result = self.agent_service.chat(
            role_id=role.id,
            message=case["prompt"],
            session_id=f"benchmark-{uuid4().hex}",
            text_model=model_id,
            max_tokens=900,
        )
        return {
            "role_id": role.id,
            "role_name": role.name,
            "model_id": model_id,
            "case_id": case["id"],
            "prompt": case["prompt"],
            "answer": result.answer,
            "used_tools": result.used_tools,
            "expected_keywords": case.get("expected_keywords", []),
            "required_tools": case.get("required_tools", []),
            "risk_flags": case.get("risk_flags", []),
            "rubric_notes": case.get("rubric_notes", ""),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _evaluate_single_output(self, role, output: dict, judge_model_id: str, weights: dict, use_llm_judge: bool) -> dict:
        """Evaluate a single output."""
        required_tools = output.get("required_tools", [])
        used_tools = output.get("used_tools", [])
        rule_scores = heuristic_scores(output["answer"], output.get("expected_keywords", []), required_tools, used_tools)
        judge_scores = self._llm_judge_from_output(role, output, judge_model_id, weights) if use_llm_judge else {}
        scores = blend_scores(rule_scores, judge_scores)

        return {
            "case_id": output["case_id"],
            "prompt": output["prompt"],
            "answer": output["answer"],
            "expected_keywords": output.get("expected_keywords", []),
            "required_tools": required_tools,
            "risk_flags": output.get("risk_flags", []),
            "rubric_notes": output.get("rubric_notes", ""),
            "scores": scores,
            "rule_scores": rule_scores,
            "llm_judge_scores": judge_scores,
            "total": weighted_total(scores, weights),
            "judge": "mixed-rules-llm-v1" if judge_scores else "heuristic-v1",
        }

    def get_run_status(self, run_id: str) -> dict:
        """Get current status and progress of a run."""
        try:
            run = self.storage.load_run(run_id)
        except FileNotFoundError:
            return {"error": "Run not found"}

        output_summary = self.output_storage.get_output_summary(run_id)
        evaluated_count = 0
        if run.get("results"):
            evaluated_count = sum(len(r.get("case_results", [])) for r in run["results"])

        return {
            "run_id": run_id,
            "status": run.get("status", STATUS_PENDING),
            "config": run.get("config", {}),
            "judge_model": run.get("config", {}).get("judge_model"),
            "created_at": run.get("created_at"),
            "outputs_generated_at": run.get("outputs_generated_at"),
            "evaluated_at": run.get("evaluated_at"),
            "outputs_count": output_summary.get("total", 0),
            "evaluated_count": evaluated_count,
            "roles": output_summary.get("roles", []),
            "models": output_summary.get("models", []),
        }

    def run(
        self,
        role_ids: Optional[Iterable[str]] = None,
        model_ids: Optional[Iterable[str]] = None,
        case_ids: Optional[Iterable[str]] = None,
        case_limit_per_role: Optional[int] = None,
        use_llm_judge: bool = True,
    ) -> dict:
        selected_roles = list(role_ids or self.roles.keys())
        selected_models = list(model_ids or DEFAULT_BENCHMARK_MODELS)
        selected_case_ids = set(case_ids or [])
        cases = self._select_cases(selected_roles, selected_case_ids, case_limit_per_role)
        if not cases:
            raise ValueError("No benchmark cases matched the request")

        run = {
            "run_id": uuid4().hex,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": STATUS_GENERATING,
            "config": {
                "roles": selected_roles,
                "models": selected_models,
                "case_ids": list(selected_case_ids) if selected_case_ids else None,
                "case_limit_per_role": case_limit_per_role,
                "judge_model": None if not use_llm_judge else "same-as-tested-model",
            },
            "results": [],
        }
        self.storage.save_run(run)
        for role_id in selected_roles:
            role = self.roles.get(role_id)
            if role is None:
                raise ValueError(f"Unknown role_id: {role_id}")
            role_cases = [case for case in cases if case["role_id"] == role_id]
            if not role_cases:
                continue
            for model_id in selected_models:
                print(f"Running benchmark: {role_id} / {model_id} / {len(role_cases)} cases", flush=True)
                case_results = [self._run_case(role, model_id, case, use_llm_judge=use_llm_judge) for case in role_cases]
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
                print(f"Completed benchmark: {role_id} / {model_id} => {completion}", flush=True)
        run["status"] = STATUS_COMPLETED
        run["evaluated_at"] = datetime.now(timezone.utc).isoformat()
        self.storage.save_run(run)
        return run

    def get_run(self, run_id: str) -> dict:
        return self.storage.load_run(run_id)

    def _select_cases(
        self,
        selected_roles: List[str],
        selected_case_ids: set[str],
        case_limit_per_role: Optional[int],
    ) -> List[dict]:
        selected = []
        for role_id in selected_roles:
            role_cases = [
                case
                for case in self.load_cases()
                if case["role_id"] == role_id and (not selected_case_ids or case["id"] in selected_case_ids)
            ]
            if case_limit_per_role:
                role_cases = role_cases[:case_limit_per_role]
            selected.extend(role_cases)
        return selected

    def _run_case(self, role, model_id: str, case: dict, use_llm_judge: bool = True) -> dict:
        required_tools = case.get("required_tools", [])
        weights = role.benchmark.get("dimensions") or DEFAULT_DIMENSIONS
        try:
            result = self.agent_service.chat(
                role_id=role.id,
                message=case["prompt"],
                session_id=f"benchmark-{uuid4().hex}",
                text_model=model_id,
                max_tokens=900,
            )
            answer = result.answer
            used_tools = result.used_tools
            error = None
        except Exception as exc:
            answer = ""
            used_tools = []
            error = f"{exc.__class__.__name__}: {exc}"

        rule_scores = heuristic_scores(answer, case.get("expected_keywords", []), required_tools, used_tools)
        if error:
            rule_scores = {key: min(value, 0.2) for key, value in rule_scores.items()}
        judge_scores = self._llm_judge(role, case, answer, weights, model_id) if use_llm_judge and not error else {}
        scores = blend_scores(rule_scores, judge_scores)
        return {
            "case_id": case["id"],
            "prompt": case["prompt"],
            "answer": answer,
            "expected_keywords": case.get("expected_keywords", []),
            "required_tools": required_tools,
            "used_tools": used_tools,
            "risk_flags": case.get("risk_flags", []),
            "rubric_notes": case.get("rubric_notes", ""),
            "scores": scores,
            "rule_scores": rule_scores,
            "llm_judge_scores": judge_scores,
            "total": weighted_total(scores, weights),
            "judge": "mixed-rules-llm-v1" if judge_scores else "heuristic-v1",
            "error": error,
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

    def _llm_judge_from_output(self, role, output: dict, judge_model_id: str, weights: dict) -> dict:
        """Evaluate output using LLM judge (for two-phase workflow)."""
        router = getattr(self.agent_service, "model_router", None)
        if router is None:
            return {}
        try:
            content = router.invoke(
                judge_prompt(role.name, output["prompt"], output["answer"], weights),
                model_id=judge_model_id,
                temperature=0.0,
            )
        except Exception:
            return {}
        return parse_judge_scores(content, weights)
