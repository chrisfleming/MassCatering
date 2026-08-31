"""Functions for migrating legacy Mass Catering menus to schema version 2."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any


class MenuMigrationError(ValueError):
    """Raised when a legacy menu cannot be migrated safely."""


def normalise_people(
    value: Any,
    *,
    menu_name: str,
    recipe_name: str,
    label: str,
) -> int:
    """Convert a legacy people count to a positive integer."""

    if isinstance(value, bool):
        raise MenuMigrationError(
            f"Cannot migrate menu {menu_name!r}: "
            f"recipe {recipe_name!r}, label {label!r} "
            "contains a Boolean value instead of a people count."
        )

    try:
        people = int(value)
    except (TypeError, ValueError) as exc:
        raise MenuMigrationError(
            f"Cannot migrate menu {menu_name!r}: "
            f"recipe {recipe_name!r}, label {label!r} "
            f"contains {value!r}, which is not a people count."
        ) from exc

    if people <= 0:
        raise MenuMigrationError(
            f"Cannot migrate menu {menu_name!r}: "
            f"recipe {recipe_name!r}, label {label!r} "
            f"has a non-positive people count: {people}."
        )

    return people


def is_general_provision_label(label: str) -> bool:
    """
    Return True for legacy artificial provisioning labels.

    Examples include:
        z_people
        z_sunday
        z_monday
    """

    return label.strip().casefold().startswith("z_")


def provision_applies_to(label: str) -> list:
    """
    Extract an optional day from a legacy provisioning label.

    For example, ``z_sunday`` becomes ``["Sunday"]``.
    ``z_people`` has no specific day and therefore returns an
    empty list.
    """

    normalised = label.strip()

    if not is_general_provision_label(normalised):
        return []

    suffix = normalised[2:].strip()

    if not suffix or suffix.casefold() == "people":
        return []

    return [suffix.replace("_", " ").title()]


def migrate_general_provision(
    *,
    recipe_name: str,
    label: str,
    value: Any,
    menu_name: str,
) -> dict[str, Any]:
    """Convert a legacy z_* entry to a general provision."""

    amount = normalise_people(
        value,
        menu_name=menu_name,
        recipe_name=recipe_name,
        label=label,
    )

    applies_to = provision_applies_to(label)

    if label.strip().casefold() == "z_people":
        provision: dict[str, Any] = {
            "recipe": recipe_name,
            "multiplier": amount,
        }
    else:
        provision = {
            "recipe": recipe_name,
            "people": amount,
        }

    if applies_to:
        provision["applies_to"] = applies_to

    provision["notes"] = (
        f"Automatically migrated from legacy label {label!r}. "
        "Review how this provision should be scaled."
    )

    return provision


def migrate_menu(
    old_menu: dict[str, Any],
    menu_name: str,
) -> dict[str, Any]:
    """
    Convert a legacy Mass Catering menu to schema version 2.

    Legacy recipe entries are grouped by their schedule label.
    Since labels commonly contain only a day, the generated meal
    type is set to ``unspecified`` for manual review.

    Scalar entries are migrated to ``additional_items``.

    Legacy z_* entries are migrated to ``general_provisions``.
    """

    if not isinstance(old_menu, dict):
        raise MenuMigrationError(
            f"Cannot migrate menu {menu_name!r}: "
            "the YAML document must contain a mapping."
        )

    # Ordered by first occurrence in the legacy file.
    event_dishes: OrderedDict[
        str,
        list[dict[str, Any]],
    ] = OrderedDict()

    general_provisions: list[dict[str, Any]] = []
    additional_items: list[dict[str, Any]] = []

    for item_name, schedule in old_menu.items():
        if not isinstance(item_name, str) or not item_name.strip():
            raise MenuMigrationError(
                f"Cannot migrate menu {menu_name!r}: "
                f"item name {item_name!r} is not valid."
            )

        if isinstance(schedule, dict):
            if not schedule:
                raise MenuMigrationError(
                    f"Cannot migrate menu {menu_name!r}: "
                    f"recipe {item_name!r} has an empty schedule."
                )

            for raw_label, raw_people in schedule.items():
                label = str(raw_label).strip()

                if not label:
                    raise MenuMigrationError(
                        f"Cannot migrate menu {menu_name!r}: "
                        f"recipe {item_name!r} has an empty "
                        "schedule label."
                    )

                if is_general_provision_label(label):
                    general_provisions.append(
                        migrate_general_provision(
                            recipe_name=item_name,
                            label=label,
                            value=raw_people,
                            menu_name=menu_name,
                        )
                    )
                    continue

                people = normalise_people(
                    raw_people,
                    menu_name=menu_name,
                    recipe_name=item_name,
                    label=label,
                )

                dish = {
                    "recipe": item_name,
                    "people": people,
                }

                event_dishes.setdefault(label, []).append(dish)

        else:
            additional_items.append(
                {
                    "ingredient": item_name,
                    "quantity": schedule,
                }
            )

    events: list[dict[str, Any]] = []

    for label, dishes in event_dishes.items():
        people_counts = [
            int(dish["people"])
            for dish in dishes
        ]

        # The largest dish count is the safest event-level default.
        # Dish-level overrides retain every original value exactly.
        event_people = max(people_counts)

        migrated_dishes = []

        for dish in dishes:
            migrated_dish = {
                "recipe": dish["recipe"],
            }

            if dish["people"] != event_people:
                migrated_dish["people"] = dish["people"]

            migrated_dishes.append(migrated_dish)

        event = {
            "day": label,
            "meal": "unspecified",
            "people": event_people,
            "notes": (
                "Automatically migrated from a legacy menu. "
                "Review the meal type, event grouping and "
                "dish-specific preparation notes."
            ),
            "dishes": migrated_dishes,
        }

        events.append(event)

    new_menu: dict[str, Any] = {
        "schema_version": 2,
        "name": menu_name.replace("_", " ").replace("-", " ").title(),
        "description": (
            "Automatically migrated from the legacy menu format. "
            "Review this menu before using it for catering."
        ),
        "events": events,
    }

    if general_provisions:
        new_menu["general_provisions"] = general_provisions

    if additional_items:
        new_menu["additional_items"] = additional_items

    return new_menu