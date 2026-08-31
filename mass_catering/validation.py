from dataclasses import dataclass
from enum import Enum

class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"


@dataclass
class ValidationIssue:
    severity: Severity
    location: str
    message: str




from typing import Any


def validate_optional_notes(
    value: Any,
    location: str,
) -> list:
    """Validate an optional notes field."""

    if value is None:
        return []

    if not isinstance(value, str):
        return [
            ValidationIssue(
                Severity.ERROR,
                location,
                "Notes must be text.",
            )
        ]

    if not value.strip():
        return [
            ValidationIssue(
                Severity.INFORMATION,
                location,
                "Notes field is empty.",
            )
        ]

    return []


def validate_menu(
    menu: object,
    available_recipes: set[str],
) -> list:
    """Validate a version 2 event-based menu."""

    issues: list[ValidationIssue] = []

    if not isinstance(menu, dict):
        return [
            ValidationIssue(
                Severity.ERROR,
                "menu",
                "Menu must be a YAML mapping.",
            )
        ]

    if menu.get("schema_version") != 2:
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                "schema_version",
                "Menu must use schema version 2.",
            )
        )

    name = menu.get("name")

    if not isinstance(name, str) or not name.strip():
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                "name",
                "Menu name is required.",
            )
        )

    issues.extend(
        validate_optional_notes(
            menu.get("notes"),
            "notes",
        )
    )

    description = menu.get("description")

    if (
        description is not None
        and not isinstance(description, str)
    ):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                "description",
                "Description must be text.",
            )
        )

    events = menu.get("events")

    if not isinstance(events, list) or not events:
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                "events",
                "Menu must contain at least one event.",
            )
        )

        return issues

    occupied_slots: set[tuple[str, str]] = set()

    for event_index, event in enumerate(events):
        event_location = f"events[{event_index}]"

        if not isinstance(event, dict):
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    event_location,
                    "Event must be a YAML mapping.",
                )
            )
            continue

        day = event.get("day")
        meal = event.get("meal")
        people = event.get("people")
        dishes = event.get("dishes")

        if not isinstance(day, str) or not day.strip():
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    f"{event_location}.day",
                    "Day must be non-empty text.",
                )
            )

        if not isinstance(meal, str) or not meal.strip():
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    f"{event_location}.meal",
                    "Meal must be non-empty text.",
                )
            )

        elif meal.strip().casefold() == "unspecified":
            issues.append(
                ValidationIssue(
                    Severity.WARNING,
                    f"{event_location}.meal",
                    (
                        "Meal type is unspecified. Review whether this "
                        "event is breakfast, lunch, dinner or another "
                        "meal type."
                    ),
                )
            )

        if (
            not isinstance(people, int)
            or isinstance(people, bool)
            or people <= 0
        ):
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    f"{event_location}.people",
                    "People must be a positive integer.",
                )
            )

        issues.extend(
            validate_optional_notes(
                event.get("notes"),
                f"{event_location}.notes",
            )
        )

        if isinstance(day, str) and isinstance(meal, str):
            slot = (
                day.strip().casefold(),
                meal.strip().casefold(),
            )

            if slot in occupied_slots:
                issues.append(
                    ValidationIssue(
                        Severity.WARNING,
                        event_location,
                        f"Duplicate event slot: {day} {meal}.",
                    )
                )

            occupied_slots.add(slot)

        if not isinstance(dishes, list) or not dishes:
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    f"{event_location}.dishes",
                    "Event must contain at least one dish.",
                )
            )
            continue

        for dish_index, dish in enumerate(dishes):
            dish_location = (
                f"{event_location}.dishes[{dish_index}]"
            )

            if not isinstance(dish, dict):
                issues.append(
                    ValidationIssue(
                        Severity.ERROR,
                        dish_location,
                        "Dish must be a YAML mapping.",
                    )
                )
                continue

            recipe_key = dish.get("recipe")

            if (
                not isinstance(recipe_key, str)
                or not recipe_key.strip()
            ):
                issues.append(
                    ValidationIssue(
                        Severity.ERROR,
                        f"{dish_location}.recipe",
                        "Recipe identifier is required.",
                    )
                )
            elif recipe_key not in available_recipes:
                issues.append(
                    ValidationIssue(
                        Severity.ERROR,
                        f"{dish_location}.recipe",
                        f"Recipe {recipe_key!r} was not found.",
                    )
                )

            if "people" in dish:
                dish_people = dish["people"]

                if (
                    not isinstance(dish_people, int)
                    or isinstance(dish_people, bool)
                    or dish_people <= 0
                ):
                    issues.append(
                        ValidationIssue(
                            Severity.ERROR,
                            f"{dish_location}.people",
                            "Dish people must be a positive integer.",
                        )
                    )

            issues.extend(
                validate_optional_notes(
                    dish.get("notes"),
                    f"{dish_location}.notes",
                )
            )

    return issues