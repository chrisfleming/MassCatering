"""Validation utilities for Mass Catering recipes and menus."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import combinations
import re
from typing import Any

from rapidfuzz.fuzz import ratio

from mass_catering.units import QuantityError, parse_quantity


# ----------------------------------------------------------------------
# Validation models
# ----------------------------------------------------------------------


class Severity(str, Enum):
    """Severity assigned to a validation issue."""

    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"


@dataclass(frozen=True)
class ValidationIssue:
    """A validation issue associated with a location."""

    severity: Severity
    location: str
    message: str


@dataclass(frozen=True)
class IngredientNameMatch:
    """A possible duplicate ingredient-name match."""

    first: str
    second: str
    score: float
    reason: str


# ----------------------------------------------------------------------
# General validation helpers
# ----------------------------------------------------------------------


def is_positive_integer(value: Any) -> bool:
    """Return whether a value is a positive integer."""

    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0
    )


def is_positive_number(value: Any) -> bool:
    """Return whether a value is a positive integer or float."""

    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value > 0
    )


def validate_optional_text(
    value: Any,
    location: str,
    field_name: str,
) -> list:
    """Validate an optional text field."""

    if value is None:
        return []

    if not isinstance(value, str):
        return [
            ValidationIssue(
                Severity.ERROR,
                location,
                f"{field_name} must be text.",
            )
        ]

    if not value.strip():
        return [
            ValidationIssue(
                Severity.INFORMATION,
                location,
                f"{field_name} is empty.",
            )
        ]

    return []


# ----------------------------------------------------------------------
# Ingredient-name normalisation
# ----------------------------------------------------------------------


def singularise_word(word: str) -> str:
    """
    Apply conservative English singularisation.

    This is intended only for possible duplicate detection. It is
    deliberately conservative and is not a complete inflection engine.
    """

    if len(word) <= 3:
        return word

    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"

    if word.endswith(
        (
            "sses",
            "shes",
            "ches",
            "xes",
            "zes",
        )
    ):
        return word[:-2]

    if (
        word.endswith("s")
        and not word.endswith(
            (
                "ss",
                "us",
                "is",
            )
        )
    ):
        return word[:-1]

    return word


def normalise_ingredient_name(name: str) -> str:
    """
    Normalise an ingredient name for comparison.

    Normalisation includes:

    - case folding;
    - replacing underscores and hyphens with spaces;
    - removing punctuation;
    - collapsing repeated whitespace;
    - conservative singularisation.
    """

    normalised = str(name).casefold()
    normalised = normalised.replace("_", " ")
    normalised = normalised.replace("-", " ")

    normalised = re.sub(
        r"[^a-z0-9\s]",
        "",
        normalised,
    )

    normalised = re.sub(
        r"\s+",
        " ",
        normalised,
    ).strip()

    words = [
        singularise_word(word)
        for word in normalised.split()
    ]

    return " ".join(words)


def is_likely_distinct_compound(
    first: str,
    second: str,
) -> bool:
    """
    Return whether one name appears to be a distinct compound.

    This suppresses warnings for pairs such as:

    - milk and coconut milk;
    - cream and sour cream;
    - onion and spring onion;
    - oil and olive oil.
    """

    first_words = set(first.split())
    second_words = set(second.split())

    return (
        first_words < second_words
        or second_words < first_words
    )


# ----------------------------------------------------------------------
# Similar ingredient detection
# ----------------------------------------------------------------------


def find_similar_ingredient_names(
    ingredient_names: set[str],
    fuzzy_threshold: float = 92.0,
) -> list:
    """
    Find likely duplicate ingredient names.

    Exact matches after normalisation are always returned. Fuzzy matches
    are returned when they meet the supplied similarity threshold.

    No ingredients are merged automatically.
    """

    matches: list[IngredientNameMatch] = []

    cleaned_names = {
        str(name).strip()
        for name in ingredient_names
        if str(name).strip()
    }

    for first, second in combinations(
        sorted(cleaned_names, key=str.casefold),
        2,
    ):
        first_normalised = normalise_ingredient_name(first)
        second_normalised = normalise_ingredient_name(second)

        if not first_normalised or not second_normalised:
            continue

        if first_normalised == second_normalised:
            matches.append(
                IngredientNameMatch(
                    first=first,
                    second=second,
                    score=100.0,
                    reason=(
                        "Names become identical after normalisation "
                        "and singularisation."
                    ),
                )
            )
            continue

        if is_likely_distinct_compound(
            first_normalised,
            second_normalised,
        ):
            continue

        similarity = float(
            ratio(
                first_normalised,
                second_normalised,
            )
        )

        if similarity >= fuzzy_threshold:
            matches.append(
                IngredientNameMatch(
                    first=first,
                    second=second,
                    score=similarity,
                    reason=(
                        "Names have a high text-similarity score."
                    ),
                )
            )

    return matches


def collect_menu_ingredient_names(
    menu: dict,
    recipes: dict[str, dict],
) -> set:
    """Collect ingredient names used by recipes and additional items."""

    ingredient_names: set[str] = set()

    for recipe in recipes.values():
        if not isinstance(recipe, dict):
            continue

        ingredients = recipe.get("ingredients", {})

        if not isinstance(ingredients, dict):
            continue

        ingredient_names.update(
            str(name)
            for name in ingredients
            if str(name).strip()
        )

    additional_items = menu.get(
        "additional_items",
        [],
    )

    if isinstance(additional_items, list):
        for item in additional_items:
            if not isinstance(item, dict):
                continue

            ingredient_name = item.get("ingredient")

            if (
                isinstance(ingredient_name, str)
                and ingredient_name.strip()
            ):
                ingredient_names.add(ingredient_name)

    return ingredient_names


def validate_ingredient_names(
    menu: dict,
    recipes: dict[str, dict],
    fuzzy_threshold: float = 92.0,
) -> list:
    """Warn about possible duplicate ingredient identifiers."""

    ingredient_names = collect_menu_ingredient_names(
        menu,
        recipes,
    )

    matches = find_similar_ingredient_names(
        ingredient_names,
        fuzzy_threshold=fuzzy_threshold,
    )

    issues: list[ValidationIssue] = []

    for match in matches:
        issues.append(
            ValidationIssue(
                Severity.WARNING,
                "ingredients",
                (
                    f"Possible duplicate ingredients: "
                    f"{match.first!r} and {match.second!r}. "
                    f"{match.reason} Similarity: "
                    f"{match.score:.0f}%. Review the names before "
                    "generating the final shopping list. The "
                    "quantities have not been merged automatically."
                ),
            )
        )

    return issues


# ----------------------------------------------------------------------
# Recipe validation
# ----------------------------------------------------------------------


def validate_recipe(
    recipe_name: str,
    recipe: object,
) -> list:
    """Validate a recipe mapping."""

    issues: list[ValidationIssue] = []

    if not isinstance(recipe, dict):
        return [
            ValidationIssue(
                Severity.ERROR,
                recipe_name,
                "Recipe must be a YAML mapping.",
            )
        ]

    display_name = recipe.get("name")

    if (
        not isinstance(display_name, str)
        or not display_name.strip()
    ):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{recipe_name}.name",
                "Recipe name is required.",
            )
        )

    if "serves" in recipe:
        serves = recipe["serves"]

        if not is_positive_number(serves):
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    f"{recipe_name}.serves",
                    "'serves' must be a positive number.",
                )
            )

    ingredients = recipe.get("ingredients")

    if not isinstance(ingredients, dict) or not ingredients:
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{recipe_name}.ingredients",
                "At least one ingredient is required.",
            )
        )

        return issues

    for ingredient_name, raw_quantity in ingredients.items():
        ingredient_location = (
            f"{recipe_name}.ingredients.{ingredient_name}"
        )

        if (
            not isinstance(ingredient_name, str)
            or not ingredient_name.strip()
        ):
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    f"{recipe_name}.ingredients",
                    "Ingredient names must be non-empty text.",
                )
            )

            continue

        try:
            quantity = parse_quantity(
                raw_quantity,
                ingredient_name,
            )

            if quantity.magnitude <= 0:
                issues.append(
                    ValidationIssue(
                        Severity.ERROR,
                        ingredient_location,
                        "Quantity must be greater than zero.",
                    )
                )

        except QuantityError as exc:
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    ingredient_location,
                    str(exc),
                )
            )

    method = recipe.get("method")

    if method is None:
        issues.append(
            ValidationIssue(
                Severity.INFORMATION,
                f"{recipe_name}.method",
                "Recipe does not include a method.",
            )
        )

    elif not isinstance(method, str):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{recipe_name}.method",
                "Method must be text.",
            )
        )

    issues.extend(
        validate_optional_text(
            recipe.get("notes"),
            f"{recipe_name}.notes",
            "Recipe notes",
        )
    )

    issues.extend(
        validate_optional_text(
            recipe.get("source"),
            f"{recipe_name}.source",
            "Recipe source",
        )
    )

    return issues


# ----------------------------------------------------------------------
# Menu component validation
# ----------------------------------------------------------------------


def validate_dish(
    dish: object,
    location: str,
    available_recipes: set[str],
) -> list:
    """Validate one dish in a scheduled event."""

    issues: list[ValidationIssue] = []

    if not isinstance(dish, dict):
        return [
            ValidationIssue(
                Severity.ERROR,
                location,
                "Dish must be a mapping.",
            )
        ]

    recipe_name = dish.get("recipe")

    if (
        not isinstance(recipe_name, str)
        or not recipe_name.strip()
    ):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{location}.recipe",
                "Recipe must be non-empty text.",
            )
        )

    elif recipe_name not in available_recipes:
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{location}.recipe",
                f"Recipe {recipe_name!r} was not found.",
            )
        )

    if "people" in dish:
        dish_people = dish["people"]

        if not is_positive_integer(dish_people):
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    f"{location}.people",
                    "Dish people must be a positive integer.",
                )
            )

    issues.extend(
        validate_optional_text(
            dish.get("notes"),
            f"{location}.notes",
            "Dish preparation notes",
        )
    )

    return issues


def validate_event(
    event: object,
    location: str,
    available_recipes: set[str],
) -> list:
    """Validate one scheduled catering event."""

    issues: list[ValidationIssue] = []

    if not isinstance(event, dict):
        return [
            ValidationIssue(
                Severity.ERROR,
                location,
                "Event must be a mapping.",
            )
        ]

    day = event.get("day")

    if (
        not isinstance(day, str)
        or not day.strip()
    ):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{location}.day",
                "Day must be non-empty text.",
            )
        )

    meal = event.get("meal")

    if (
        not isinstance(meal, str)
        or not meal.strip()
    ):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{location}.meal",
                "Meal must be non-empty text.",
            )
        )

    elif meal.strip().casefold() == "unspecified":
        issues.append(
            ValidationIssue(
                Severity.WARNING,
                f"{location}.meal",
                (
                    "Meal type is unspecified. Review whether this "
                    "event is breakfast, lunch, dinner or another "
                    "meal type."
                ),
            )
        )

    people = event.get("people")

    if not is_positive_integer(people):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{location}.people",
                "People must be a positive integer.",
            )
        )

    issues.extend(
        validate_optional_text(
            event.get("name"),
            f"{location}.name",
            "Event name",
        )
    )

    issues.extend(
        validate_optional_text(
            event.get("notes"),
            f"{location}.notes",
            "Event notes",
        )
    )

    dishes = event.get("dishes")

    if not isinstance(dishes, list):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{location}.dishes",
                "Dishes must be a list.",
            )
        )

        return issues

    for dish_index, dish in enumerate(dishes):
        issues.extend(
            validate_dish(
                dish=dish,
                location=(
                    f"{location}.dishes[{dish_index}]"
                ),
                available_recipes=available_recipes,
            )
        )

    return issues


def validate_general_provision(
    provision: object,
    location: str,
    available_recipes: set[str],
) -> list:
    """Validate one general-provision entry."""

    issues: list[ValidationIssue] = []

    if not isinstance(provision, dict):
        return [
            ValidationIssue(
                Severity.ERROR,
                location,
                "General provision must be a mapping.",
            )
        ]

    recipe_name = provision.get("recipe")

    if (
        not isinstance(recipe_name, str)
        or not recipe_name.strip()
    ):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{location}.recipe",
                "Recipe must be non-empty text.",
            )
        )

    elif recipe_name not in available_recipes:
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{location}.recipe",
                f"Recipe {recipe_name!r} was not found.",
            )
        )

    has_people = "people" in provision
    has_multiplier = "multiplier" in provision

    if has_people == has_multiplier:
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                location,
                (
                    "General provision must define exactly one of "
                    "'people' or 'multiplier'."
                ),
            )
        )

    if has_people and not is_positive_integer(
        provision["people"]
    ):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{location}.people",
                "People must be a positive integer.",
            )
        )

    if has_multiplier and not is_positive_number(
        provision["multiplier"]
    ):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{location}.multiplier",
                "Multiplier must be a positive number.",
            )
        )

    applies_to = provision.get("applies_to")

    if applies_to is not None:
        if not isinstance(applies_to, list):
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    f"{location}.applies_to",
                    "'applies_to' must be a list of text values.",
                )
            )

        else:
            for day_index, value in enumerate(applies_to):
                if (
                    not isinstance(value, str)
                    or not value.strip()
                ):
                    issues.append(
                        ValidationIssue(
                            Severity.ERROR,
                            (
                                f"{location}.applies_to"
                                f"[{day_index}]"
                            ),
                            (
                                "Each 'applies_to' value must be "
                                "non-empty text."
                            ),
                        )
                    )

    issues.extend(
        validate_optional_text(
            provision.get("notes"),
            f"{location}.notes",
            "General-provision notes",
        )
    )

    return issues


def validate_additional_item(
    item: object,
    location: str,
) -> list:
    """Validate one standalone shopping-list item."""

    issues: list[ValidationIssue] = []

    if not isinstance(item, dict):
        return [
            ValidationIssue(
                Severity.ERROR,
                location,
                "Additional item must be a mapping.",
            )
        ]

    ingredient_name = item.get("ingredient")

    ingredient_is_valid = (
        isinstance(ingredient_name, str)
        and bool(ingredient_name.strip())
    )

    if not ingredient_is_valid:
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{location}.ingredient",
                "Ingredient must be non-empty text.",
            )
        )

    if "quantity" not in item:
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                f"{location}.quantity",
                "Additional item quantity is required.",
            )
        )

    elif ingredient_is_valid:
        try:
            quantity = parse_quantity(
                item["quantity"],
                ingredient_name,
            )

            if quantity.magnitude <= 0:
                issues.append(
                    ValidationIssue(
                        Severity.ERROR,
                        f"{location}.quantity",
                        "Quantity must be greater than zero.",
                    )
                )

        except QuantityError as exc:
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    f"{location}.quantity",
                    str(exc),
                )
            )

    issues.extend(
        validate_optional_text(
            item.get("notes"),
            f"{location}.notes",
            "Additional-item notes",
        )
    )

    return issues


# ----------------------------------------------------------------------
# Complete menu validation
# ----------------------------------------------------------------------


def validate_menu(
    menu: object,
    available_recipes: set[str],
) -> list:
    """Validate a complete version 2 menu."""

    issues: list[ValidationIssue] = []

    if not isinstance(menu, dict):
        return [
            ValidationIssue(
                Severity.ERROR,
                "menu",
                "Menu must be a YAML mapping.",
            )
        ]

    schema_version = menu.get("schema_version")

    if schema_version != 2:
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                "schema_version",
                "Expected schema_version: 2.",
            )
        )

    name = menu.get("name")

    if (
        not isinstance(name, str)
        or not name.strip()
    ):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                "name",
                "Menu name must be non-empty text.",
            )
        )

    issues.extend(
        validate_optional_text(
            menu.get("description"),
            "description",
            "Menu description",
        )
    )

    issues.extend(
        validate_optional_text(
            menu.get("notes"),
            "notes",
            "Menu notes",
        )
    )

    attendance = menu.get("attendance")

    if attendance is not None:
        if not isinstance(attendance, dict):
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    "attendance",
                    "Attendance must be a mapping.",
                )
            )

        else:
            for attendance_key, attendance_value in (
                attendance.items()
            ):
                if not isinstance(attendance_key, str):
                    issues.append(
                        ValidationIssue(
                            Severity.ERROR,
                            "attendance",
                            "Attendance group names must be text.",
                        )
                    )

                if not is_positive_integer(attendance_value):
                    issues.append(
                        ValidationIssue(
                            Severity.ERROR,
                            f"attendance.{attendance_key}",
                            (
                                "Attendance values must be "
                                "positive integers."
                            ),
                        )
                    )

    events = menu.get("events")

    if not isinstance(events, list):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                "events",
                "Events must be a list.",
            )
        )

    else:
        occupied_slots: set[tuple[str, str]] = set()

        for event_index, event in enumerate(events):
            event_location = f"events[{event_index}]"

            issues.extend(
                validate_event(
                    event=event,
                    location=event_location,
                    available_recipes=available_recipes,
                )
            )

            if not isinstance(event, dict):
                continue

            day = event.get("day")
            meal = event.get("meal")

            if (
                isinstance(day, str)
                and day.strip()
                and isinstance(meal, str)
                and meal.strip()
            ):
                slot = (
                    day.strip().casefold(),
                    meal.strip().casefold(),
                )

                if slot in occupied_slots:
                    issues.append(
                        ValidationIssue(
                            Severity.WARNING,
                            event_location,
                            (
                                f"Duplicate event slot: "
                                f"{day.strip()} {meal.strip()}."
                            ),
                        )
                    )

                occupied_slots.add(slot)

    general_provisions = menu.get(
        "general_provisions",
        [],
    )

    if not isinstance(general_provisions, list):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                "general_provisions",
                "General provisions must be a list.",
            )
        )

    else:
        for provision_index, provision in enumerate(
            general_provisions
        ):
            issues.extend(
                validate_general_provision(
                    provision=provision,
                    location=(
                        "general_provisions"
                        f"[{provision_index}]"
                    ),
                    available_recipes=available_recipes,
                )
            )

    additional_items = menu.get(
        "additional_items",
        [],
    )

    if not isinstance(additional_items, list):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                "additional_items",
                "Additional items must be a list.",
            )
        )

    else:
        for item_index, item in enumerate(
            additional_items
        ):
            issues.extend(
                validate_additional_item(
                    item=item,
                    location=(
                        f"additional_items[{item_index}]"
                    ),
                )
            )

    return issues