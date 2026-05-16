import json
from pathlib import Path
from typing import Any, Dict, List, Optional


OUTPUTS_DIR = Path(__file__).resolve().parents[1] / "data" / "benchmark_outputs"


class OutputStorage:
    """Stores raw model outputs before evaluation."""

    def __init__(self, outputs_dir: Path = OUTPUTS_DIR):
        self.outputs_dir = outputs_dir

    def save_outputs(self, run_id: str, outputs: List[Dict[str, Any]]) -> None:
        """Save raw model outputs for a run."""
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        path = self.outputs_dir / f"{run_id}.json"
        path.write_text(json.dumps(outputs, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_outputs(self, run_id: str) -> List[Dict[str, Any]]:
        """Load raw model outputs for a run."""
        path = self.outputs_dir / f"{run_id}.json"
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def get_output_status(self, run_id: str) -> str:
        """Check if outputs exist for a run."""
        path = self.outputs_dir / f"{run_id}.json"
        if not path.exists():
            return "pending"
        outputs = json.loads(path.read_text(encoding="utf-8"))
        if not outputs:
            return "pending"
        return "generated"

    def count_outputs(self, run_id: str) -> int:
        """Count number of outputs for a run."""
        outputs = self.load_outputs(run_id)
        return len(outputs)

    def get_output_summary(self, run_id: str) -> Dict[str, Any]:
        """Get summary of outputs for a run."""
        outputs = self.load_outputs(run_id)
        if not outputs:
            return {
                "run_id": run_id,
                "status": "pending",
                "total": 0,
                "roles": [],
                "models": [],
                "cases": [],
            }
        roles = set(o.get("role_id") for o in outputs)
        models = set(o.get("model_id") for o in outputs)
        cases = set(o.get("case_id") for o in outputs)
        return {
            "run_id": run_id,
            "status": "generated",
            "total": len(outputs),
            "roles": sorted(roles),
            "models": sorted(models),
            "cases": sorted(cases),
        }

    def delete_outputs(self, run_id: str) -> bool:
        """Delete outputs for a run."""
        path = self.outputs_dir / f"{run_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False