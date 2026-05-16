import argparse
import getpass
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llms.openai_compatible import OpenAICompatibleChatModel, OpenAICompatibleVisionModel
from llms.providers import get_provider


def load_dotenv(path):
    if not path.exists():
        return

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    parser = argparse.ArgumentParser(description="Test an OpenAI-compatible LLM provider.")
    parser.add_argument("--provider", default="sjtu")
    parser.add_argument("--api-key")
    parser.add_argument("--text-model")
    parser.add_argument("--vision-model")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--prompt", default="请用一句话介绍上海交通大学。")
    parser.add_argument("--skip-text", action="store_true")
    parser.add_argument("--image", help="Local image path for vision model test.")
    parser.add_argument("--image-prompt", default="请描述这张图片的主要内容。")
    args = parser.parse_args()

    provider = get_provider(args.provider)
    api_key = args.api_key or os.environ.get(provider.api_key_env)
    api_key = api_key or getpass.getpass(f"{provider.name} API Key: ")

    if not args.skip_text:
        text_model = OpenAICompatibleChatModel(
            provider=provider,
            api_key=api_key,
            model=args.text_model,
            timeout=args.timeout,
        )
        text_response = text_model.invoke(args.prompt)
        print("[Text]")
        print(text_response)

    if args.image:
        vision_model = OpenAICompatibleVisionModel(
            provider=provider,
            api_key=api_key,
            model=args.vision_model,
            timeout=args.timeout,
        )
        vision_response = vision_model.describe_image(args.image, args.image_prompt)
        print("\n[Vision]")
        print(vision_response.content)


if __name__ == "__main__":
    main()
