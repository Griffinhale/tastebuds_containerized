"""Validate ingestion mapping manifests."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.ingestion.mapping_schema import validate_mapping_paths


def _collect_mapping_files(target: Path) -> list[Path]:
    if target.is_dir():
        return sorted(target.glob("*.yaml")) + sorted(target.glob("*.yml"))
    if target.is_file():
        return [target]
    raise FileNotFoundError(f"Path not found: {target}")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    default_path = repo_root / "mappings"

    parser = argparse.ArgumentParser(description="Validate mapping manifests")
    parser.add_argument(
        "--path",
        default=str(default_path),
        help="Path to a mapping file or directory (default: mappings/)",
    )
    args = parser.parse_args()
    target = Path(args.path).resolve()

    paths = _collect_mapping_files(target)
    errors = validate_mapping_paths(paths)
    if errors:
        for error in errors:
            print(error)
        return 1

    print(f"Validated {len(paths)} mapping file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
