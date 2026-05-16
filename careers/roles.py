from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml


ROLE_DIR = Path(__file__).resolve().parent / "roles"


@dataclass(frozen=True)
class CareerRole:
    id: str
    name: str
    category: str
    tagline: str
    profile: str
    supports_image: bool
    mentor_goal: str
    boundaries: List[str]
    rules: List[str]
    workflow: List[str]
    deliverables: List[str]
    onboarding_checklist: List[str]
    scenarios: List[str]
    starter_questions: List[str]
    tools: List[str]
    workflows: List[Dict[str, Any]]
    artifacts: List[Dict[str, Any]]
    benchmark: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CareerRole":
        required = [
            "id",
            "name",
            "category",
            "tagline",
            "profile",
            "supports_image",
            "mentor_goal",
            "boundaries",
            "rules",
            "workflow",
            "deliverables",
            "onboarding_checklist",
            "scenarios",
            "starter_questions",
        ]
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError(f"Role config missing fields: {', '.join(missing)}")

        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            category=str(data["category"]),
            tagline=str(data["tagline"]),
            profile=str(data["profile"]),
            supports_image=bool(data["supports_image"]),
            mentor_goal=str(data["mentor_goal"]),
            boundaries=list(data["boundaries"]),
            rules=list(data["rules"]),
            workflow=list(data["workflow"]),
            deliverables=list(data["deliverables"]),
            onboarding_checklist=list(data["onboarding_checklist"]),
            scenarios=list(data["scenarios"]),
            starter_questions=list(data["starter_questions"]),
            tools=list(data.get("tools", [])),
            workflows=list(data.get("workflows", [])),
            artifacts=list(data.get("artifacts", [])),
            benchmark=dict(data.get("benchmark", {})),
        )

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "tagline": self.tagline,
            "supports_image": self.supports_image,
            "starter_questions": self.starter_questions,
            "tools": self.tools,
        }


def load_roles(role_dir: Path = ROLE_DIR) -> Dict[str, CareerRole]:
    roles: Dict[str, CareerRole] = {}
    for path in sorted(role_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        role = CareerRole.from_dict(data)
        if role.id in roles:
            raise ValueError(f"Duplicate role id: {role.id}")
        roles[role.id] = role

    if not roles:
        raise ValueError(f"No role configs found in {role_dir}")
    return roles
