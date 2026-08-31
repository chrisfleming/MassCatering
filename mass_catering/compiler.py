from dataclasses import dataclass, field
from typing import Any

from pint import Quantity
from mass_catering.units import parse_quantity


@dataclass
class ScaledRecipe:
    """A recipe scaled for one scheduled catering event."""

    key: str
    name: str
    day: str
    meal: str
    event_name: str
    people: int
    ingredients: dict
    method: str | None = None
    recipe_notes: str | None = None
    preparation_notes: str | None = None
    event_notes: str | None = None

    @property
    def label(self) -> str:
        """Return a human-readable event label."""

        components = [self.day, self.meal]

        if self.event_name:
            components.append(self.event_name)

        return " - ".join(components)


@dataclass
class CompilationResult:
    """Structured output from compiling a menu."""

    scaled_recipes: list[ScaledRecipe] = field(
        default_factory=list
    )
    shopping_list: dict[str, Any] = field(
        default_factory=dict
    )
    warnings: list[str] = field(default_factory=list)


def add_quantity(
    quantities: dict[str, Any],
    ingredient_name: str,
    quantity: Any,
) -> None:
    """Add a quantity to an ingredient total."""

    if ingredient_name in quantities:
        quantities[ingredient_name] += quantity
    else:
        quantities[ingredient_name] = quantity


def compile_menu(
    menu: dict[str, Any],
    recipes: dict[str, dict],
) -> CompilationResult:
    """Compile a validated version 2 menu."""

    result = CompilationResult()

    for event in menu["events"]:
        event_people = int(event["people"])
        event_name = str(event.get("name", ""))
        event_notes = event.get("notes")

        for dish in event["dishes"]:
            recipe_key = dish["recipe"]
            recipe = recipes[recipe_key]

            people = int(
                dish.get("people", event_people)
            )

            serves = float(
                recipe.get("serves", 1)
            )

            scaled_ingredients: dict[str, Any] = {}

            for ingredient_name, raw_amount in (
                recipe["ingredients"].items()
            ):
                base_amount = parse_quantity(
                    raw_amount,
                    ingredient_name,
                )

                scaled_amount = (
                    base_amount / serves * people
                )

                scaled_ingredients[
                    ingredient_name
                ] = scaled_amount

                add_quantity(
                    result.shopping_list,
                    ingredient_name,
                    scaled_amount,
                )

            result.scaled_recipes.append(
                ScaledRecipe(
                    key=recipe_key,
                    name=recipe["name"],
                    day=str(event["day"]),
                    meal=str(event["meal"]),
                    event_name=event_name,
                    people=people,
                    ingredients=scaled_ingredients,
                    method=recipe.get("method"),
                    recipe_notes=recipe.get("notes"),
                    preparation_notes=dish.get("notes"),
                    event_notes=event_notes,
                )
            )

    for item in menu.get("additional_items", []):
        ingredient_name = item["ingredient"]

        amount = parse_quantity(
            item["quantity"],
            ingredient_name,
        )

        add_quantity(
            result.shopping_list,
            ingredient_name,
            amount,
        )

    return result