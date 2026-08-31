"""Compile validated Mass Catering menus into scaled recipes and shopping lists."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mass_catering.units import QuantityError, parse_quantity


# ----------------------------------------------------------------------
# Exceptions
# ----------------------------------------------------------------------


class CompilationError(ValueError):
    """Raised when a menu cannot be compiled safely."""


# ----------------------------------------------------------------------
# Compilation result models
# ----------------------------------------------------------------------


@dataclass
class ScaledRecipe:
    """A recipe scaled for one scheduled catering event."""

    key: str
    name: str
    day: str
    meal: str
    event_name: str
    people: int
    ingredients: dict[str, Any]
    method: str | None = None
    recipe_notes: str | None = None
    preparation_notes: str | None = None
    event_notes: str | None = None

    @property
    def label(self) -> str:
        """Return a human-readable event label."""

        components = [
            component
            for component in (
                self.day,
                self.meal,
                self.event_name,
            )
            if component
        ]

        return " - ".join(components)


@dataclass
class CompilationResult:
    """Structured output produced by compiling a menu."""

    scaled_recipes: list[ScaledRecipe] = field(
        default_factory=list
    )

    shopping_list: dict[str, Any] = field(
        default_factory=dict
    )

    warnings: list[str] = field(
        default_factory=list
    )


# ----------------------------------------------------------------------
# Error-message helpers
# ----------------------------------------------------------------------


def recipe_file_label(recipe_key: str) -> str:
    """Return the expected repository filepath for a recipe."""

    return f"recipe/{recipe_key}.yaml"


def event_label(event: dict[str, Any]) -> str:
    """Return a human-readable description of an event."""

    components = [
        str(event.get("day", "")).strip(),
        str(event.get("meal", "")).strip(),
        str(event.get("name", "")).strip(),
    ]

    return " - ".join(
        component
        for component in components
        if component
    )


def ingredient_error_message(
    *,
    recipe_key: str,
    ingredient_name: str,
    raw_amount: Any,
    reason: Exception,
    context: str | None = None,
) -> str:
    """Create a detailed ingredient compilation error."""

    lines = [
        f"Could not compile recipe {recipe_key!r}.",
        f"File: {recipe_file_label(recipe_key)}",
    ]

    if context:
        lines.append(f"Context: {context}")

    lines.extend(
        [
            f"Ingredient: {ingredient_name}",
            f"Value: {raw_amount!r}",
            f"Reason: {reason}",
        ]
    )

    return "\n".join(lines)


# ----------------------------------------------------------------------
# Shopping-list aggregation
# ----------------------------------------------------------------------


def add_quantity(
    quantities: dict[str, Any],
    ingredient_name: str,
    quantity: Any,
    source: str | None = None,
) -> None:
    """
    Add one quantity to an ingredient total.

    Compatible Pint quantities are converted and aggregated
    automatically. Incompatible quantities produce a detailed error.
    """

    if ingredient_name not in quantities:
        quantities[ingredient_name] = quantity
        return

    existing_quantity = quantities[ingredient_name]

    try:
        quantities[ingredient_name] = (
            existing_quantity + quantity
        )

    except Exception as exc:
        lines = [
            (
                "Could not combine quantities for "
                f"{ingredient_name!r}."
            )
        ]

        if source:
            lines.append(
                f"While processing: {source}"
            )

        lines.extend(
            [
                (
                    "Existing quantity: "
                    f"{existing_quantity!s}"
                ),
                f"New quantity: {quantity!s}",
                (
                    "The ingredient may be represented using "
                    "incompatible units in different recipe files."
                ),
            ]
        )

        raise CompilationError(
            "\n".join(lines)
        ) from exc


def add_ingredients_to_shopping_list(
    result: CompilationResult,
    ingredients: dict[str, Any],
    source: str | None = None,
) -> None:
    """Add a collection of ingredients to the shopping list."""

    for ingredient_name, quantity in ingredients.items():
        add_quantity(
            quantities=result.shopping_list,
            ingredient_name=ingredient_name,
            quantity=quantity,
            source=source,
        )


# ----------------------------------------------------------------------
# Recipe validation during compilation
# ----------------------------------------------------------------------


def get_recipe(
    recipes: dict[str, dict],
    recipe_key: str,
    context: str | None = None,
) -> dict[str, Any]:
    """Retrieve a recipe or raise a detailed compilation error."""

    if recipe_key not in recipes:
        lines = [
            f"Recipe {recipe_key!r} was not loaded.",
            f"Expected file: {recipe_file_label(recipe_key)}",
        ]

        if context:
            lines.append(f"Context: {context}")

        raise CompilationError(
            "\n".join(lines)
        )

    recipe = recipes[recipe_key]

    if not isinstance(recipe, dict):
        raise CompilationError(
            "\n".join(
                [
                    (
                        f"Could not compile recipe "
                        f"{recipe_key!r}."
                    ),
                    (
                        f"File: "
                        f"{recipe_file_label(recipe_key)}"
                    ),
                    (
                        "The recipe must contain a YAML "
                        "mapping."
                    ),
                ]
            )
        )

    return recipe


def get_recipe_serves(
    recipe: dict[str, Any],
    recipe_key: str,
    context: str | None = None,
) -> float:
    """Return and validate a recipe's serves value."""

    raw_serves = recipe.get("serves", 1)

    try:
        serves = float(raw_serves)

    except (TypeError, ValueError) as exc:
        lines = [
            f"Could not compile recipe {recipe_key!r}.",
            f"File: {recipe_file_label(recipe_key)}",
        ]

        if context:
            lines.append(f"Context: {context}")

        lines.extend(
            [
                f"Invalid serves value: {raw_serves!r}",
                (
                    "The serves value must be a positive "
                    "number."
                ),
            ]
        )

        raise CompilationError(
            "\n".join(lines)
        ) from exc

    if serves <= 0:
        lines = [
            f"Could not compile recipe {recipe_key!r}.",
            f"File: {recipe_file_label(recipe_key)}",
        ]

        if context:
            lines.append(f"Context: {context}")

        lines.extend(
            [
                f"Invalid serves value: {raw_serves!r}",
                (
                    "The serves value must be greater "
                    "than zero."
                ),
            ]
        )

        raise CompilationError(
            "\n".join(lines)
        )

    return serves


def get_recipe_ingredients(
    recipe: dict[str, Any],
    recipe_key: str,
    context: str | None = None,
) -> dict[str, Any]:
    """Return and validate a recipe's ingredient mapping."""

    ingredients = recipe.get("ingredients")

    if not isinstance(ingredients, dict):
        lines = [
            f"Could not compile recipe {recipe_key!r}.",
            f"File: {recipe_file_label(recipe_key)}",
        ]

        if context:
            lines.append(f"Context: {context}")

        lines.append(
            "The ingredients field must be a YAML mapping."
        )

        raise CompilationError(
            "\n".join(lines)
        )

    if not ingredients:
        lines = [
            f"Could not compile recipe {recipe_key!r}.",
            f"File: {recipe_file_label(recipe_key)}",
        ]

        if context:
            lines.append(f"Context: {context}")

        lines.append(
            "The recipe contains no ingredients."
        )

        raise CompilationError(
            "\n".join(lines)
        )

    return ingredients


# ----------------------------------------------------------------------
# Recipe scaling
# ----------------------------------------------------------------------


def scale_recipe_ingredients(
    recipe: dict[str, Any],
    people: int,
    recipe_key: str,
    context: str | None = None,
) -> dict[str, Any]:
    """Scale a recipe's ingredients to a number of people."""

    if (
        not isinstance(people, int)
        or isinstance(people, bool)
        or people <= 0
    ):
        lines = [
            f"Could not compile recipe {recipe_key!r}.",
            f"File: {recipe_file_label(recipe_key)}",
        ]

        if context:
            lines.append(f"Context: {context}")

        lines.append(
            f"People must be a positive integer, not {people!r}."
        )

        raise CompilationError(
            "\n".join(lines)
        )

    serves = get_recipe_serves(
        recipe=recipe,
        recipe_key=recipe_key,
        context=context,
    )

    ingredients = get_recipe_ingredients(
        recipe=recipe,
        recipe_key=recipe_key,
        context=context,
    )

    scaled_ingredients: dict[str, Any] = {}

    for ingredient_name, raw_amount in ingredients.items():
        try:
            base_amount = parse_quantity(
                raw_amount,
                ingredient_name,
            )

        except (QuantityError, ValueError) as exc:
            raise CompilationError(
                ingredient_error_message(
                    recipe_key=recipe_key,
                    ingredient_name=ingredient_name,
                    raw_amount=raw_amount,
                    reason=exc,
                    context=context,
                )
            ) from exc

        try:
            scaled_amount = (
                base_amount / serves * people
            )

        except Exception as exc:
            raise CompilationError(
                ingredient_error_message(
                    recipe_key=recipe_key,
                    ingredient_name=ingredient_name,
                    raw_amount=raw_amount,
                    reason=exc,
                    context=context,
                )
            ) from exc

        scaled_ingredients[
            ingredient_name
        ] = scaled_amount

    return scaled_ingredients


def multiply_recipe_ingredients(
    recipe: dict[str, Any],
    multiplier: int | float,
    recipe_key: str,
    context: str | None = None,
) -> dict[str, Any]:
    """Multiply all base recipe quantities by a multiplier."""

    if (
        not isinstance(multiplier, (int, float))
        or isinstance(multiplier, bool)
        or multiplier <= 0
    ):
        lines = [
            f"Could not compile recipe {recipe_key!r}.",
            f"File: {recipe_file_label(recipe_key)}",
        ]

        if context:
            lines.append(f"Context: {context}")

        lines.append(
            (
                "The general-provision multiplier must be "
                f"a positive number, not {multiplier!r}."
            )
        )

        raise CompilationError(
            "\n".join(lines)
        )

    ingredients = get_recipe_ingredients(
        recipe=recipe,
        recipe_key=recipe_key,
        context=context,
    )

    multiplied_ingredients: dict[str, Any] = {}

    for ingredient_name, raw_amount in ingredients.items():
        try:
            base_amount = parse_quantity(
                raw_amount,
                ingredient_name,
            )

        except (QuantityError, ValueError) as exc:
            raise CompilationError(
                ingredient_error_message(
                    recipe_key=recipe_key,
                    ingredient_name=ingredient_name,
                    raw_amount=raw_amount,
                    reason=exc,
                    context=context,
                )
            ) from exc

        try:
            multiplied_amount = (
                base_amount * multiplier
            )

        except Exception as exc:
            raise CompilationError(
                ingredient_error_message(
                    recipe_key=recipe_key,
                    ingredient_name=ingredient_name,
                    raw_amount=raw_amount,
                    reason=exc,
                    context=context,
                )
            ) from exc

        multiplied_ingredients[
            ingredient_name
        ] = multiplied_amount

    return multiplied_ingredients


# ----------------------------------------------------------------------
# Scheduled event compilation
# ----------------------------------------------------------------------


def compile_event_dishes(
    menu: dict[str, Any],
    recipes: dict[str, dict],
    result: CompilationResult,
) -> None:
    """Compile all scheduled dishes in a menu."""

    events = menu.get("events", [])

    for event_index, event in enumerate(events):
        if not isinstance(event, dict):
            raise CompilationError(
                "\n".join(
                    [
                        (
                            f"Could not compile event "
                            f"events[{event_index}]."
                        ),
                        "The event must be a YAML mapping.",
                    ]
                )
            )

        context = event_label(event)

        try:
            event_people = int(event["people"])

        except (KeyError, TypeError, ValueError) as exc:
            raise CompilationError(
                "\n".join(
                    [
                        (
                            f"Could not compile event "
                            f"events[{event_index}]."
                        ),
                        f"Event: {context or '<unnamed event>'}",
                        (
                            "The event must define a valid "
                            "people count."
                        ),
                    ]
                )
            ) from exc

        event_name = str(
            event.get("name", "")
        ).strip()

        event_notes = event.get("notes")

        dishes = event.get("dishes", [])

        if not isinstance(dishes, list):
            raise CompilationError(
                "\n".join(
                    [
                        (
                            f"Could not compile event "
                            f"events[{event_index}]."
                        ),
                        f"Event: {context or '<unnamed event>'}",
                        "The dishes field must be a list.",
                    ]
                )
            )

        for dish_index, dish in enumerate(dishes):
            dish_location = (
                f"events[{event_index}]"
                f".dishes[{dish_index}]"
            )

            if not isinstance(dish, dict):
                raise CompilationError(
                    "\n".join(
                        [
                            (
                                f"Could not compile "
                                f"{dish_location}."
                            ),
                            (
                                f"Event: "
                                f"{context or '<unnamed event>'}"
                            ),
                            "The dish must be a YAML mapping.",
                        ]
                    )
                )

            try:
                recipe_key = dish["recipe"]

            except KeyError as exc:
                raise CompilationError(
                    "\n".join(
                        [
                            (
                                f"Could not compile "
                                f"{dish_location}."
                            ),
                            (
                                f"Event: "
                                f"{context or '<unnamed event>'}"
                            ),
                            (
                                "The dish does not define a "
                                "recipe."
                            ),
                        ]
                    )
                ) from exc

            recipe = get_recipe(
                recipes=recipes,
                recipe_key=recipe_key,
                context=context,
            )

            try:
                people = int(
                    dish.get(
                        "people",
                        event_people,
                    )
                )

            except (TypeError, ValueError) as exc:
                raise CompilationError(
                    "\n".join(
                        [
                            (
                                f"Could not compile recipe "
                                f"{recipe_key!r}."
                            ),
                            (
                                f"File: "
                                f"{recipe_file_label(recipe_key)}"
                            ),
                            (
                                f"Event: "
                                f"{context or '<unnamed event>'}"
                            ),
                            (
                                f"Location: {dish_location}"
                            ),
                            (
                                "The dish people count must "
                                "be a positive integer."
                            ),
                        ]
                    )
                ) from exc

            scaled_ingredients = (
                scale_recipe_ingredients(
                    recipe=recipe,
                    people=people,
                    recipe_key=recipe_key,
                    context=context,
                )
            )

            add_ingredients_to_shopping_list(
                result=result,
                ingredients=scaled_ingredients,
                source=(
                    f"{recipe_file_label(recipe_key)} "
                    f"for {context}"
                ),
            )

            result.scaled_recipes.append(
                ScaledRecipe(
                    key=recipe_key,
                    name=str(
                        recipe.get(
                            "name",
                            recipe_key,
                        )
                    ),
                    day=str(
                        event.get("day", "")
                    ),
                    meal=str(
                        event.get("meal", "")
                    ),
                    event_name=event_name,
                    people=people,
                    ingredients=scaled_ingredients,
                    method=recipe.get("method"),
                    recipe_notes=recipe.get(
                        "notes"
                    ),
                    preparation_notes=dish.get(
                        "notes"
                    ),
                    event_notes=event_notes,
                )
            )


# ----------------------------------------------------------------------
# General provision compilation
# ----------------------------------------------------------------------


def compile_general_provisions(
    menu: dict[str, Any],
    recipes: dict[str, dict],
    result: CompilationResult,
) -> None:
    """Compile recipes used for general catering provisions."""

    provisions = menu.get(
        "general_provisions",
        [],
    )

    for provision_index, provision in enumerate(
        provisions
    ):
        provision_location = (
            f"general_provisions[{provision_index}]"
        )

        if not isinstance(provision, dict):
            raise CompilationError(
                "\n".join(
                    [
                        (
                            f"Could not compile "
                            f"{provision_location}."
                        ),
                        (
                            "The general provision must be "
                            "a YAML mapping."
                        ),
                    ]
                )
            )

        try:
            recipe_key = provision["recipe"]

        except KeyError as exc:
            raise CompilationError(
                "\n".join(
                    [
                        (
                            f"Could not compile "
                            f"{provision_location}."
                        ),
                        (
                            "The general provision does not "
                            "define a recipe."
                        ),
                    ]
                )
            ) from exc

        context = f"General provisions, entry {provision_index + 1}"

        recipe = get_recipe(
            recipes=recipes,
            recipe_key=recipe_key,
            context=context,
        )

        has_people = "people" in provision
        has_multiplier = "multiplier" in provision

        if has_people and has_multiplier:
            raise CompilationError(
                "\n".join(
                    [
                        (
                            f"Could not compile recipe "
                            f"{recipe_key!r}."
                        ),
                        (
                            f"File: "
                            f"{recipe_file_label(recipe_key)}"
                        ),
                        f"Location: {provision_location}",
                        (
                            "A general provision may define "
                            "'people' or 'multiplier', but "
                            "not both."
                        ),
                    ]
                )
            )

        if has_people:
            try:
                people = int(
                    provision["people"]
                )

            except (TypeError, ValueError) as exc:
                raise CompilationError(
                    "\n".join(
                        [
                            (
                                f"Could not compile recipe "
                                f"{recipe_key!r}."
                            ),
                            (
                                f"File: "
                                f"{recipe_file_label(recipe_key)}"
                            ),
                            (
                                f"Location: "
                                f"{provision_location}"
                            ),
                            (
                                "The people count must be a "
                                "positive integer."
                            ),
                        ]
                    )
                ) from exc

            scaled_ingredients = (
                scale_recipe_ingredients(
                    recipe=recipe,
                    people=people,
                    recipe_key=recipe_key,
                    context=context,
                )
            )

        else:
            # A provision without explicit scaling is included once.
            raw_multiplier = provision.get(
                "multiplier",
                1,
            )

            try:
                multiplier = float(
                    raw_multiplier
                )

            except (TypeError, ValueError) as exc:
                raise CompilationError(
                    "\n".join(
                        [
                            (
                                f"Could not compile recipe "
                                f"{recipe_key!r}."
                            ),
                            (
                                f"File: "
                                f"{recipe_file_label(recipe_key)}"
                            ),
                            (
                                f"Location: "
                                f"{provision_location}"
                            ),
                            (
                                "The multiplier must be a "
                                "positive number."
                            ),
                        ]
                    )
                ) from exc

            scaled_ingredients = (
                multiply_recipe_ingredients(
                    recipe=recipe,
                    multiplier=multiplier,
                    recipe_key=recipe_key,
                    context=context,
                )
            )

            people = 0

        add_ingredients_to_shopping_list(
            result=result,
            ingredients=scaled_ingredients,
            source=(
                f"{recipe_file_label(recipe_key)} "
                f"as {provision_location}"
            ),
        )

        applies_to = provision.get(
            "applies_to",
            [],
        )

        if isinstance(applies_to, list):
            applies_to_text = ", ".join(
                str(value)
                for value in applies_to
            )
        else:
            applies_to_text = str(applies_to)

        result.scaled_recipes.append(
            ScaledRecipe(
                key=recipe_key,
                name=str(
                    recipe.get(
                        "name",
                        recipe_key,
                    )
                ),
                day=applies_to_text or "General",
                meal="provisions",
                event_name="General provisions",
                people=people,
                ingredients=scaled_ingredients,
                method=recipe.get("method"),
                recipe_notes=recipe.get("notes"),
                preparation_notes=provision.get(
                    "notes"
                ),
                event_notes=None,
            )
        )


# ----------------------------------------------------------------------
# Additional shopping-item compilation
# ----------------------------------------------------------------------


def compile_additional_items(
    menu: dict[str, Any],
    result: CompilationResult,
) -> None:
    """Add standalone shopping items from a menu."""

    additional_items = menu.get(
        "additional_items",
        [],
    )

    for item_index, item in enumerate(
        additional_items
    ):
        item_location = (
            f"additional_items[{item_index}]"
        )

        if not isinstance(item, dict):
            raise CompilationError(
                "\n".join(
                    [
                        (
                            "Could not compile an additional "
                            "shopping item."
                        ),
                        f"Location: {item_location}",
                        (
                            "The additional item must be a "
                            "YAML mapping."
                        ),
                    ]
                )
            )

        ingredient_name = item.get(
            "ingredient"
        )

        if (
            not isinstance(ingredient_name, str)
            or not ingredient_name.strip()
        ):
            raise CompilationError(
                "\n".join(
                    [
                        (
                            "Could not compile an additional "
                            "shopping item."
                        ),
                        f"Location: {item_location}",
                        (
                            "The ingredient name must be "
                            "non-empty text."
                        ),
                    ]
                )
            )

        raw_quantity = item.get("quantity")

        try:
            amount = parse_quantity(
                raw_quantity,
                ingredient_name,
            )

        except (QuantityError, ValueError) as exc:
            raise CompilationError(
                "\n".join(
                    [
                        (
                            "Could not compile an additional "
                            "shopping item."
                        ),
                        f"Location: {item_location}",
                        f"Ingredient: {ingredient_name}",
                        f"Value: {raw_quantity!r}",
                        f"Reason: {exc}",
                    ]
                )
            ) from exc

        add_quantity(
            quantities=result.shopping_list,
            ingredient_name=ingredient_name,
            quantity=amount,
            source=item_location,
        )


# ----------------------------------------------------------------------
# Complete menu compilation
# ----------------------------------------------------------------------


def compile_menu(
    menu: dict[str, Any],
    recipes: dict[str, dict],
) -> CompilationResult:
    """
    Compile a validated version 2 menu.

    Compilation includes:

    - scheduled event dishes;
    - general-provision recipes;
    - standalone additional shopping items.

    Menu and recipe validation should normally be completed before
    calling this function. Defensive checks remain here so failures
    contain enough context to diagnose the responsible source file.
    """

    if not isinstance(menu, dict):
        raise CompilationError(
            "The menu must be a YAML mapping."
        )

    result = CompilationResult()

    compile_event_dishes(
        menu=menu,
        recipes=recipes,
        result=result,
    )

    compile_general_provisions(
        menu=menu,
        recipes=recipes,
        result=result,
    )

    compile_additional_items(
        menu=menu,
        result=result,
    )

    return result