"""Schema validation for ingestion mapping manifests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

_ALLOWED_CANONICAL_TABLES = {
    "media_items",
    "book_items",
    "movie_items",
    "game_items",
    "music_items",
}
_METADATA_PREFIX = "media_items.metadata."


class MetadataMapping(BaseModel):
    """Mapping entry for metadata fields."""

    upstream: str
    stored_as: str

    @field_validator("stored_as")
    @classmethod
    def _validate_stored_as(cls, value: str) -> str:
        if not value.startswith(_METADATA_PREFIX):
            msg = f"metadata stored_as must start with '{_METADATA_PREFIX}'"
            raise ValueError(msg)
        return value


class RawOnlyMapping(BaseModel):
    """Mapping entry for raw-only fields."""

    upstream: str
    reason: str


class MappingManifest(BaseModel):
    """Top-level mapping manifest."""

    source: str
    canonical: dict[str, dict[str, str]]
    metadata: list[MetadataMapping] = Field(default_factory=list)
    raw_only: list[RawOnlyMapping] = Field(default_factory=list)
    data_notes: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @field_validator("source")
    @classmethod
    def _validate_source(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source must be non-empty")
        return value

    @field_validator("canonical")
    @classmethod
    def _validate_canonical(cls, value: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
        if "media_items" not in value:
            raise ValueError("canonical.media_items is required")
        for table_name, fields in value.items():
            if table_name not in _ALLOWED_CANONICAL_TABLES:
                raise ValueError(f"canonical table '{table_name}' is not allowed")
            if not isinstance(fields, dict) or not fields:
                raise ValueError(f"canonical.{table_name} must map fields to source paths")
            for field_name, source_path in fields.items():
                if not isinstance(field_name, str) or not field_name.strip():
                    raise ValueError(f"canonical.{table_name} has an invalid field name")
                if not isinstance(source_path, str) or not source_path.strip():
                    raise ValueError(f"canonical.{table_name}.{field_name} must be a string path")
        return value


def load_mapping_manifest(path: Path) -> MappingManifest:
    """Load and validate a mapping manifest from YAML."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("mapping manifest must be a YAML mapping")
    return MappingManifest.model_validate(data)


def validate_mapping_file(path: Path) -> list[str]:
    """Validate a single mapping file and return any errors."""
    errors: list[str] = []
    try:
        manifest = load_mapping_manifest(path)
    except (ValidationError, ValueError) as exc:
        errors.append(f"{path}: {exc}")
        return errors
    if manifest.source != path.stem:
        errors.append(
            f"{path}: source '{manifest.source}' does not match file name '{path.stem}'"
        )
    return errors


def validate_mapping_paths(paths: Iterable[Path]) -> list[str]:
    """Validate mapping manifests and collect error messages."""
    errors: list[str] = []
    for path in paths:
        errors.extend(validate_mapping_file(path))
    return errors
