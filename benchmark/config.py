from pathlib import Path

import yaml


# Load configuration from YAML
_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

with open(_CONFIG_PATH, encoding="utf-8") as f:
    _config = yaml.safe_load(f)


BENCHMARK_PROVIDERS = _config["providers"]
DEFAULT_BENCHMARK_PROVIDER = _config["default_provider"]
DEFAULT_BENCHMARK_MODELS = _config["default_models"]


def get_model_display_names() -> dict:
    """Build display name mapping from provider configs."""
    names = {}
    for provider_id, provider_config in BENCHMARK_PROVIDERS.items():
        for model in provider_config["models"]:
            names[model["id"]] = f"{model['display_name']} ({provider_config['display_name'].split()[0]})"
    return names


MODEL_DISPLAY_NAMES = get_model_display_names()