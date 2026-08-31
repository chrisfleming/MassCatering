from dataclasses import dataclass, field
from typing import Any

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
    """Structured output from compiling a menu."""

    scaled_recipes: list[ScaledRecipe] = field(
        default_factory=list
    )

    shopping_list: dict[str, Any] = field(
        default_factory=dict
    )

    warnings: list[str] = field(
        default_factory=list
    )


def add_quantity(
    quantities: dict[str, Any],
    ingredient_name: str,
    quantity: Any,
) -> None:
    """Add a quantity to an ingredient total."""

    if ingredient_name in quantities:
        try:
            quantities[ingredient_name] += quantity
        except Exception as exc:
            existing = quantities[ingredient_name]

            raise ValueError(
                f"Could not combine quantities for "
                f"{ingredient_name!r}: {existing!s} and "
                f"{quantity!s}. Check that their units are "
                "compatible."
            ) from exc
    else:
        quantities[ingredient_name] = quantity


def scale_recipe_ingredients(
    recipe: dict[str, Any],
    people: int,
) -> dict[str, Any]:
    """
    Scale a recipe's ingredients to a number of people.

    Recipes without a serves value are treated as serving one.
    """

    serves = float(recipe.get("serves", 1))

    if serves <= 0:
        raise ValueError(
            f"Recipe {recipe.get('name', '<unnamed>')!r} "
            "has a non-positive serves value."
        )

    scaled_ingredients: dict[str, Any] = {}

    for ingredient_name, raw_amount in (
        recipe["ingredients"].items()
    ):
        base_amount = parse_quantity(
            raw_amount,
            ingredient_name,
        )

        scaled_ingredients[ingredient_name] = (
            base_amount / serves * people
        )

    return scaled_ingredients


def multiply_recipe_ingredients(
    recipe: dict[str, Any],
    multiplier: int | float,
) -> dict[str, Any]:
    """Multiply all base recipe quantities by a multiplier."""

    if multiplier <= 0:
        raise ValueError(
            "General-provision multiplier must be positive."
        )

    multiplied_ingredients: dict[str, Any] = {}

    for ingredient_name, raw_amount in (
        recipe["ingredients"].items()
    ):
        base_amount = parse_quantity(
            raw_amount,
            ingredient_name,
        )

        multiplied_ingredients[ingredient_name] = (
            base_amount * multiplier
        )

    return multiplied_ingredients


def add_ingredients_to_shopping_list(
    result: CompilationResult,
    ingredients: dict[str, Any],
) -> None:
    """Add a collection of ingredients to the shopping list."""

    for ingredient_name, quantity in ingredients.items():
        add_quantity(
            result.shopping_list,
            ingredient_name,
            quantity,
        )


def compile_event_dishes(
    menu: dict[str, Any],
    recipes: dict[str, dict],
    result: CompilationResult,
) -> None:
    """Compile all scheduled dishes in a menu."""

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

            scaled_ingredients = scale_recipe_ingredients(
                recipe,
                people,
            )

            add_ingredients_to_shopping_list(
                result,
                scaled_ingredients,
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


def compile_general_provisions(
    menu: dict[str, Any],
    recipes: dict[str, dict],
    result: CompilationResult,
) -> None:
    """Compile recipes used for general catering provisions."""

    for index, provision in enumerate(
        menu.get("general_provisions", [])
    ):
        recipe_key = provision["recipe"]
        recipe = recipes[recipe_key]

        if "people" in provision:
            people = int(provision["people"])

            scaled_ingredients = scale_recipe_ingredients(
                recipe,
                people,
            )

        elif "multiplier" in provision:
            multiplier = float(
                provision["multiplier"]
            )

            scaled_ingredients = (
                multiply_recipe_ingredients(
                    recipe,
                    multiplier,
                )
            )

            people = 0

        else:
            raise ValueError(
                f"General provision {index} for "
                f"{recipe_key!r} must define either "
                "'people' or 'multiplier'."
            )

        add_ingredients_to_shopping_list(
            result,
            scaled_ingredients,
        )

        applies_to = provision.get(
            "applies_to",
            [],
        )

        applies_to_text = ", ".join(
            str(value)
            for value in applies_to
        )

        result.scaled_recipes.append(
            ScaledRecipe(
                key=recipe_key,
                name=recipe["name"],
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
            )
        )


def compile_additional_items(
    menu: dict[str, Any],
    result: CompilationResult,
) -> None:
    """Add standalone shopping items from a menu."""

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


def compile_menu(
    menu: dict[str, Any],
    recipes: dict[str, dict],
) -> CompilationResult:
    """Compile a validated version 2 menu."""

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