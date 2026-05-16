import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from base.career_agent import CareerAgentService
from benchmark.config import DEFAULT_BENCHMARK_MODELS
from benchmark.runner import BenchmarkRunner
from benchmark.storage import BenchmarkStorage


def parse_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI-Career-101 dynamic benchmark and save a local snapshot.")
    parser.add_argument("--roles", help="Comma-separated role ids. Defaults to all roles.")
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_BENCHMARK_MODELS),
        help="Comma-separated model ids.",
    )
    parser.add_argument("--cases", help="Comma-separated case ids. Defaults to all matching cases.")
    args = parser.parse_args()

    service = CareerAgentService()
    runner = BenchmarkRunner(
        roles=service.roles,
        agent_service=service,
        storage=BenchmarkStorage(),
    )
    result = runner.run(
        role_ids=parse_csv(args.roles),
        model_ids=parse_csv(args.models),
        case_ids=parse_csv(args.cases),
    )
    print(json.dumps({"run_id": result["run_id"], "created_at": result["created_at"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
