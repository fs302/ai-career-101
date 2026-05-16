import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from careers.roles import CareerRole
from commons.env import load_dotenv
from llms.openai_compatible import OpenAICompatibleChatModel
from llms.providers import get_provider


CAREERS = [
    "室内设计师",
    "眼科医生",
    "字幕翻译师",
    "营销广告策划",
    "游戏策划",
    "游戏美工",
    "插画师",
    "营养师",
    "咖啡师",
    "同声传译师",
]


PROMPT = """请为职业导师系统生成一个结构化角色卡。
职业：{career}

目标用户是刚进入该职业的新手。角色必须帮助新人快速适应职业要求，采用导师+情景演练模式。

请只返回 JSON 对象，字段必须包括：
id, name, category, tagline, profile, supports_image, mentor_goal, boundaries, rules, workflow, deliverables, onboarding_checklist, scenarios, starter_questions。

要求：
- id 使用英文 snake_case。
- supports_image 是 boolean。
- boundaries/rules/workflow/deliverables/onboarding_checklist/scenarios/starter_questions 都是中文字符串数组，每个数组 3-5 项。
- 医疗相关职业必须明确不能诊断、处方或替代线下就医。
- 字幕翻译师和同声传译师必须避免角色重叠。
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate role YAML files with the configured LLM provider.")
    parser.add_argument("--provider", default="sjtu")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "careers" / "roles"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    model = OpenAICompatibleChatModel(provider=get_provider(args.provider))
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    for career in CAREERS:
        response = model.invoke(PROMPT.format(career=career), temperature=0.2)
        data = json.loads(response)
        role = CareerRole.from_dict(data)
        path = output_dir / f"{role.id}.yaml"
        if path.exists() and not args.overwrite:
            print(f"skip existing: {path}")
            continue
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"wrote: {path}")


if __name__ == "__main__":
    main()
