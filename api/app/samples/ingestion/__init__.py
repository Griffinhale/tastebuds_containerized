from __future__ import annotations

import json
from importlib import resources
from typing import Any


def load_ingestion_sample(name: str) -> dict[str, Any]:
    """Return a deep copy of the stored ingestion payload sample."""
    resource = resources.files(__name__).joinpath(f"{name}.json")
    if not resource.is_file():
        raise FileNotFoundError(f"No ingestion sample named {name}")
    text = resource.read_text(encoding="utf-8")
    return json.loads(text)
