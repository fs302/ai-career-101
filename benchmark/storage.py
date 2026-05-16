import json
from pathlib import Path
from typing import Any, Dict, List


RUNS_DIR = Path(__file__).resolve().parents[1] / "data" / "benchmark_runs"


class BenchmarkStorage:
    def __init__(self, runs_dir: Path = RUNS_DIR):
        self.runs_dir = runs_dir

    def save_run(self, run: Dict[str, Any]) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        path = self.runs_dir / f"{run['run_id']}.json"
        path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_run(self, run_id: str) -> Dict[str, Any]:
        path = self.runs_dir / f"{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Benchmark run not found: {run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def list_runs(self) -> List[Dict[str, Any]]:
        if not self.runs_dir.exists():
            return []
        runs = []
        for path in sorted(self.runs_dir.glob("*.json"), reverse=True):
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        return runs
