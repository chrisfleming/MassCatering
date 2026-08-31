#!/usr/bin/env python3

"""Migrate legacy Mass Catering menus to schema version 2."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))

from migrate_menus_v1_to_v2 import migrate_menu


DEFAULT_SOURCE_DIR = PROJECT_ROOT / "menu" / "legacy"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "menu_v2"
DEFAULT_REPORT_FILE = DEFAULT_OUTPUT_DIR / "migration_report.yaml"


def get_args() -> argparse.Namespace:
    """Read command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Migrate legacy Mass Catering menu YAML files "
            "to schema version 2."
        )
    )

    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help=(
            "Directory containing legacy menu files "
            f"(default: {DEFAULT_SOURCE_DIR})"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=(
            "Directory for migrated menu files "
            f"(default: {DEFAULT_OUTPUT_DIR})"
        ),
    )

    parser.add_argument(
        "--menu",
        help=(
            "Migrate only one menu. Supply either its filename "
            "or filename stem."
        ),
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help=(
            "Delete existing YAML files from the output directory "
            "before migration."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Perform migration checks without writing migrated files."
        ),
    )

    return parser.parse_args()


def load_legacy_menu(menu_file: Path) -> dict[str, Any]:
    """Load and check one legacy menu."""

    try:
        with menu_file.open("r", encoding="utf-8") as stream:
            menu = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Invalid YAML: {exc}"
        ) from exc

    if not isinstance(menu, dict):
        raise ValueError(
            "The YAML document must contain a mapping."
        )

    return menu


def select_menu_files(
    source_dir: Path,
    requested_menu: str | None,
) -> list:
    """Return the legacy menu files selected for migration."""

    if requested_menu:
        requested_path = Path(requested_menu)

        filename = requested_path.name

        if not filename.endswith((".yaml", ".yml")):
            filename += ".yaml"

        menu_file = source_dir / filename

        if not menu_file.exists():
            raise FileNotFoundError(
                f"Legacy menu not found: {menu_file}"
            )

        return [menu_file]

    return sorted(
        [
            *source_dir.glob("*.yaml"),
            *source_dir.glob("*.yml"),
        ],
        key=lambda path: path.name.casefold(),
    )


def clean_output_directory(output_dir: Path) -> None:
    """Remove previously generated YAML files."""

    if not output_dir.exists():
        return

    for pattern in ("*.yaml", "*.yml"):
        for output_file in output_dir.glob(pattern):
            output_file.unlink()


def write_yaml(
    output_file: Path,
    content: Any,
) -> None:
    """Write content as readable YAML."""

    with output_file.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(
            content,
            stream,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=88,
        )


def count_review_items(menu: dict[str, Any]) -> int:
    """Count migrated fields that require manual review."""

    review_count = 0

    for event in menu.get("events", []):
        if event.get("meal") == "unspecified":
            review_count += 1

    review_count += len(
        menu.get("general_provisions", [])
    )

    return review_count


def main() -> int:
    """Run the menu migration."""

    args = get_args()

    source_dir = args.source.resolve()
    output_dir = args.output.resolve()

    if not source_dir.exists():
        print(
            f"ERROR: Source directory does not exist: "
            f"{source_dir}"
        )
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    if args.clean and not args.dry_run:
        clean_output_directory(output_dir)

    try:
        menu_files = select_menu_files(
            source_dir,
            args.menu,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 1

    if not menu_files:
        print(
            f"No YAML menu files found in {source_dir}"
        )
        return 1

    migrated: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []

    for menu_file in menu_files:
        print(f"Processing {menu_file.name}...")

        try:
            old_menu = load_legacy_menu(menu_file)

            new_menu = migrate_menu(
                old_menu=old_menu,
                menu_name=menu_file.stem,
            )

            review_items = count_review_items(
                new_menu
            )

            output_file = (
                output_dir / menu_file.name
            )

            if not args.dry_run:
                write_yaml(
                    output_file,
                    new_menu,
                )

            migrated.append(
                {
                    "source": str(menu_file),
                    "output": str(output_file),
                    "events": len(
                        new_menu.get("events", [])
                    ),
                    "general_provisions": len(
                        new_menu.get(
                            "general_provisions",
                            [],
                        )
                    ),
                    "additional_items": len(
                        new_menu.get(
                            "additional_items",
                            [],
                        )
                    ),
                    "review_items": review_items,
                }
            )

            action = (
                "Checked"
                if args.dry_run
                else "Migrated"
            )

            print(
                f"  {action}: "
                f"{len(new_menu.get('events', []))} event(s), "
                f"{review_items} review item(s)"
            )

        except Exception as exc:
            failed.append(
                {
                    "source": str(menu_file),
                    "error": str(exc),
                }
            )

            print(f"  FAILED: {exc}")

    report = {
        "schema_version": 2,
        "source_directory": str(source_dir),
        "output_directory": str(output_dir),
        "dry_run": args.dry_run,
        "summary": {
            "source_menus": len(menu_files),
            "migrated": len(migrated),
            "failed": len(failed),
            "review_items": sum(
                item["review_items"]
                for item in migrated
            ),
        },
        "migrated": migrated,
        "failed": failed,
    }

    if not args.dry_run:
        report_file = (
            output_dir / "migration_report.yaml"
        )

        write_yaml(
            report_file,
            report,
        )

    print()
    print("Migration summary")
    print("=================")
    print(f"Source menus: {len(menu_files)}")
    print(f"Migrated:    {len(migrated)}")
    print(f"Failed:      {len(failed)}")
    print(
        "Review items:",
        report["summary"]["review_items"],
    )

    if failed:
        print()
        print("Menus requiring manual review")
        print("-----------------------------")

        for failure in failed:
            print(f"- {failure['source']}")
            print(f"  {failure['error']}")

    if args.dry_run:
        print()
        print("Dry run only. No files were written.")
    else:
        print()
        print(
            "Migration report:",
            output_dir / "migration_report.yaml",
        )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())