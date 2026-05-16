from careers.prompts import build_system_prompt
from careers.roles import load_roles


def test_loads_ten_roles_with_unique_ids():
    roles = load_roles()
    assert len(roles) == 10
    assert len(set(roles)) == 10


def test_public_role_shape():
    role = load_roles()["interior_designer"]
    data = role.to_public_dict()
    assert set(data) == {
        "id",
        "name",
        "category",
        "tagline",
        "supports_image",
        "starter_questions",
        "tools",
    }
    assert data["supports_image"] is True
    assert "vision.describe" in data["tools"]


def test_system_prompt_contains_training_sections():
    role = load_roles()["nutritionist"]
    prompt = build_system_prompt(role)
    assert "身份定位" in prompt
    assert "新人适应目标" in prompt
    assert "职业边界" in prompt
    assert "工作流程" in prompt
    assert "可用工具" in prompt
    assert "营养师" in prompt


def test_roles_include_workflow_tool_and_benchmark_schema():
    roles = load_roles()
    for role in roles.values():
        assert role.tools
        assert role.workflows
        assert role.artifacts
        assert role.benchmark.get("dimensions")
