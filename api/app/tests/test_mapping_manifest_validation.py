"""Tests for mapping manifest schema validation."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.mapping_schema import validate_mapping_paths


def test_mapping_manifests_are_valid():
    repo_root = Path(__file__).resolve().parents[3]
    mapping_dir = repo_root / "mappings"
    mapping_files = sorted(mapping_dir.glob("*.yaml"))
    errors = validate_mapping_paths(mapping_files)
    assert errors == []
