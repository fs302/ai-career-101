from pathlib import Path
from typing import Any, Dict, Optional

import yaml


REVIEWS_DIR = Path(__file__).resolve().parent / "reviews"


def list_manual_reviews(reviews_dir: Path = REVIEWS_DIR) -> list[Dict[str, Any]]:
    if not reviews_dir.exists():
        return []
    reviews = []
    for path in sorted(reviews_dir.glob("*.yaml"), reverse=True):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        data["_path"] = str(path)
        reviews.append(data)
    return reviews


def latest_manual_review(source_run_id: Optional[str] = None, reviews_dir: Path = REVIEWS_DIR) -> Optional[Dict[str, Any]]:
    for review in list_manual_reviews(reviews_dir):
        if source_run_id is None or review.get("source_run_id") == source_run_id:
            return review
    return None
