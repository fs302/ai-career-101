import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


RUNS_DIR = Path(__file__).resolve().parents[1] / "data" / "benchmark_runs"
SNAPSHOTS_DIR = Path(__file__).resolve().parent / "snapshots"


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
        runs = []
        paths = []
        if self.runs_dir.exists():
            paths.extend(self.runs_dir.glob("*.json"))
        if SNAPSHOTS_DIR.exists():
            paths.extend(SNAPSHOTS_DIR.glob("*.json"))
        paths = sorted(paths, key=lambda path: path.stat().st_mtime, reverse=True)
        for path in paths:
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        runs_by_id = {}
        for run in runs:
            runs_by_id[run["run_id"]] = run
        return sorted(runs_by_id.values(), key=lambda run: run.get("created_at", ""), reverse=True)

    def update_run_status(self, run_id: str, status: str, **kwargs) -> Dict[str, Any]:
        """Update run status and optional fields."""
        run = self.load_run(run_id)
        run["status"] = status
        for key, value in kwargs.items():
            run[key] = value
        self.save_run(run)
        return run

    def get_run_status(self, run_id: str) -> str:
        """Get current status of a run."""
        run = self.load_run(run_id)
        return run.get("status", "unknown")
