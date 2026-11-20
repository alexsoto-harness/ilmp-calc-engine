"""Index methodology config loader."""

import yaml


def load_methodology(text: str) -> dict:
    return yaml.load(text, Loader=yaml.FullLoader)
