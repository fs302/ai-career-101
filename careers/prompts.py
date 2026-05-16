from careers.roles import CareerRole


def _format_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _format_optional_section(title: str, lines: list[str]) -> str:
    if not lines:
        return ""
    return f"\n{title}：\n{_format_list(lines)}\n"


def build_system_prompt(role: CareerRole) -> str:
    tool_lines = [f"{tool_id}" for tool_id in role.tools]
    workflow_lines = []
    for workflow in role.workflows:
        name = workflow.get("name") or workflow.get("id") or "workflow"
        steps = workflow.get("steps", [])
        step_text = " -> ".join(str(step.get("tool") or step.get("type") or step) for step in steps)
        workflow_lines.append(f"{name}: {step_text}" if step_text else str(name))
    artifact_lines = []
    for artifact in role.artifacts:
        artifact_lines.append(str(artifact.get("name") or artifact.get("id") or artifact))

    return f"""你是「{role.name}」职业导师，服务对象是刚进入该职业或即将转岗的新手。

身份定位：
{role.profile}

新人适应目标：
{role.mentor_goal}

职业边界：
{_format_list(role.boundaries)}

核心规则：
{_format_list(role.rules)}

工作流程：
{_format_list(role.workflow)}

常用交付物：
{_format_list(role.deliverables)}
{_format_optional_section("可用工具", tool_lines)}
{_format_optional_section("配置化工作流", workflow_lines)}
{_format_optional_section("产出物模板", artifact_lines)}

新人上手清单：
{_format_list(role.onboarding_checklist)}

情景演练方向：
{_format_list(role.scenarios)}

回复要求：
- 使用中文，语气专业、直接、可执行。
- 优先帮助用户形成职业判断、工作步骤和下一步行动。
- 当用户问题模糊时，先给一个可执行的默认路径，再列出需要补充的信息。
- 对新人常见错误要主动提醒，但避免空泛说教。
- 如果提供了图片上下文，只把它作为辅助观察，明确哪些结论来自图片，哪些是推断。
"""


def build_user_prompt(message: str, image_context: str | None = None) -> str:
    if not image_context:
        return message

    return f"""用户问题：
{message}

图片上下文：
{image_context}
"""
