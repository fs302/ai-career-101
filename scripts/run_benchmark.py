import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from base.career_agent import CareerAgentService
from benchmark.config import DEFAULT_BENCHMARK_MODELS
from benchmark.output_storage import OutputStorage
from benchmark.runner import BenchmarkRunner
from benchmark.storage import BenchmarkStorage


def parse_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI-Career-101 dynamic benchmark and save a local snapshot.")
    parser.add_argument("--phase", choices=["generate", "evaluate", "all"], default="all",
                        help="Phase to run: 'generate' (Phase 1), 'evaluate' (Phase 2), or 'all' (both)")
    parser.add_argument("--run-id", help="Run ID for Phase 2 (evaluate)")
    parser.add_argument("--judge-model", default="glm-5.1",
                        help="Judge model for Phase 2 evaluation")
    parser.add_argument("--roles", help="Comma-separated role ids. Defaults to all roles.")
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_BENCHMARK_MODELS),
        help="Comma-separated model ids.",
    )
    parser.add_argument("--cases", help="Comma-separated case ids. Defaults to all matching cases.")
    parser.add_argument("--case-limit-per-role", type=int, help="Limit cases per role for a faster snapshot.")
    parser.add_argument("--no-llm-judge", action="store_true", help="Use heuristic scoring only.")
    args = parser.parse_args()

    service = CareerAgentService()
    output_storage = OutputStorage()
    runner = BenchmarkRunner(
        roles=service.roles,
        agent_service=service,
        storage=BenchmarkStorage(),
        output_storage=output_storage,
    )

    if args.phase == "generate":
        result = runner.generate_outputs(
            role_ids=parse_csv(args.roles),
            model_ids=parse_csv(args.models),
            case_ids=parse_csv(args.cases),
            case_limit_per_role=args.case_limit_per_role,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.phase == "evaluate":
        if not args.run_id:
            print("Error: --run-id is required for Phase 2 (evaluate)")
            sys.exit(1)
        result = runner.evaluate_outputs(
            run_id=args.run_id,
            judge_model_id=args.judge_model,
            use_llm_judge=not args.no_llm_judge,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # Phase "all": run both phases in one shot (backward compatible)
        result = runner.run(
            role_ids=parse_csv(args.roles),
            model_ids=parse_csv(args.models),
            case_ids=parse_csv(args.cases),
            case_limit_per_role=args.case_limit_per_role,
            use_llm_judge=not args.no_llm_judge,
        )
        print(json.dumps({"run_id": result["run_id"], "created_at": result["created_at"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
