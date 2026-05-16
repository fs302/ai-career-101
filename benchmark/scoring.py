import json
from typing import Dict, Iterable


DEFAULT_DIMENSIONS = {
    "domain_accuracy": 0.22,
    "workflow_alignment": 0.18,
    "tool_use": 0.14,
    "safety_boundary": 0.16,
    "actionability": 0.18,
    "human_like_work": 0.12,
}


def normalize_weights(weights: Dict[str, float] | None) -> Dict[str, float]:
    weights = weights or DEFAULT_DIMENSIONS
    total = sum(float(value) for value in weights.values()) or 1.0
    return {key: float(value) / total for key, value in weights.items()}


def heuristic_scores(answer: str, expected_keywords: Iterable[str], required_tools: Iterable[str], used_tools: Iterable[str]) -> Dict[str, float]:
    answer_text = answer.lower()
    keywords = [keyword.lower() for keyword in expected_keywords]
    keyword_hits = sum(1 for keyword in keywords if keyword and keyword in answer_text)
    keyword_score = keyword_hits / max(1, len(keywords))
    required_tool_set = set(required_tools)
    used_tool_set = set(used_tools)
    if not required_tool_set:
        tool_score = 1.0
    else:
        tool_aliases = {
            "vision.describe": ["图片识别", "图像识别", "可见信息", "照片", "上传图片", "视觉"],
            "image.generate": ["图片生成", "生成图", "概念图", "提示词", "prompt", "草图"],
            "translation.zh_en": ["翻译", "英文", "口译", "字幕", "translation"],
            "speech.tts": ["音频", "tts", "语音", "朗读", "练习音频"],
        }
        tool_hits = 0.0
        for tool_id in required_tool_set:
            if tool_id in used_tool_set:
                tool_hits += 1.0
                continue
            aliases = tool_aliases.get(tool_id, [tool_id])
            if any(alias.lower() in answer_text for alias in aliases):
                tool_hits += 0.45
        tool_score = tool_hits / len(required_tool_set)

    has_steps = any(marker in answer for marker in ["步骤", "流程", "清单", "先", "再", "最后"])
    has_safety = any(marker in answer for marker in ["风险", "边界", "不确定", "线下", "确认", "限制"])
    has_action = any(marker in answer for marker in ["下一步", "建议", "练习", "检查", "复盘"])
    has_human_work = any(marker in answer for marker in ["沟通", "交付", "协作", "客户", "患者", "会议"])

    return {
        "domain_accuracy": round(max(0.35, keyword_score), 3),
        "workflow_alignment": 0.9 if has_steps else 0.55,
        "tool_use": round(tool_score, 3),
        "safety_boundary": 0.9 if has_safety else 0.55,
        "actionability": 0.9 if has_action else 0.55,
        "human_like_work": 0.85 if has_human_work else 0.55,
    }


def weighted_total(scores: Dict[str, float], weights: Dict[str, float] | None) -> float:
    normalized = normalize_weights(weights)
    return round(sum(scores.get(key, 0.0) * weight for key, weight in normalized.items()), 3)


def judge_prompt(role_name: str, case_prompt: str, answer: str, dimensions: Dict[str, float]) -> str:
    dimension_lines = "\n".join(f"- {name}: 0 到 1 分" for name in dimensions)
    return f"""你是职业导师系统的评估员，请按维度给 AI 回复打分。

角色：{role_name}
测试题：{case_prompt}

评分维度：
{dimension_lines}

AI 回复：
{answer}

只输出 JSON，对象字段为各评分维度，值为 0 到 1 的数字。不要输出解释。"""


def parse_judge_scores(content: str, dimensions: Iterable[str]) -> Dict[str, float]:
    try:
        parsed = json.loads(content.strip())
    except json.JSONDecodeError:
        return {}
    scores = {}
    for dimension in dimensions:
        value = parsed.get(dimension)
        if isinstance(value, (int, float)):
            scores[dimension] = max(0.0, min(1.0, float(value)))
    return scores


def blend_scores(rule_scores: Dict[str, float], judge_scores: Dict[str, float], judge_weight: float = 0.35) -> Dict[str, float]:
    if not judge_scores:
        return rule_scores
    blended = {}
    for key, rule_value in rule_scores.items():
        judge_value = judge_scores.get(key, rule_value)
        blended[key] = round(rule_value * (1 - judge_weight) + judge_value * judge_weight, 3)
    return blended
