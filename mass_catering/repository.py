from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_DIR = PROJECT_ROOT / "config"
RECIPE_DIR = PROJECT_ROOT / "recipe"
MENU_DIR = PROJECT_ROOT / "menu"

FOOD_FILE = CONFIG_DIR / "food.yaml"
UNIT_REGISTRY_FILE = CONFIG_DIR / "unit_registry.txt"


class RepositoryError(Exception):
    """Raised when Mass Catering data cannot be loaded."""


def load_yaml(path: Path) -> Any:
    """Load a YAML document."""

    try:
        with path.open("r", encoding="utf-8") as stream:
            return yaml.safe_load(stream)

    except FileNotFoundError as exc:
        raise RepositoryError(
            f"File not found: {path}"
        ) from exc

    except yaml.YAMLError as exc:
        raise RepositoryError(
            f"Invalid YAML in {path}: {exc}"
        ) from exc


def list_recipe_names() -> list:
    """
    Return recipe identifiers relative to the recipe directory.

    Nested recipes retain their relative path, for example:
    ``carribean_curry/apple_coleslaw``.
    """

    recipe_names = []

    for path in RECIPE_DIR.rglob("*.yaml"):
        relative_path = path.relative_to(RECIPE_DIR)
        recipe_name = relative_path.with_suffix("").as_posix()
        recipe_names.append(recipe_name)

    return sorted(recipe_names)


def list_menu_names() -> list:
    """Return available version 2 menu identifiers."""

    return sorted(
        path.stem
        for path in MENU_DIR.glob("*.yaml")
        if path.name != "migration_report.yaml"
    )


def load_recipe(recipe_name: str) -> dict:
    """Load a recipe by filename stem."""

    path = RECIPE_DIR / f"{recipe_name}.yaml"
    data = load_yaml(path)

    if not isinstance(data, dict):
        raise RepositoryError(
            f"Recipe must contain a YAML mapping: {path}"
        )

    return data


def load_menu(menu_name: str) -> dict:
    """Load a menu by filename stem."""

    path = MENU_DIR / f"{menu_name}.yaml"
    data = load_yaml(path)

    if not isinstance(data, dict):
        raise RepositoryError(
            f"Menu must contain a YAML mapping: {path}"
        )

    return data


def load_food_catalogue() -> dict:
    """Load ingredient and shop configuration."""

    data = load_yaml(FOOD_FILE)

    if not isinstance(data, dict):
        raise RepositoryError(
            "config/food.yaml must contain a YAML mapping."
            )

    return data