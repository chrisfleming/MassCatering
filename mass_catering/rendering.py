"""Rendering and quantity formatting for Mass Catering."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
import math
from typing import Any

from pint.errors import DimensionalityError, UndefinedUnitError

from mass_catering.compiler import CompilationResult


# ----------------------------------------------------------------------
# Unit configuration
# ----------------------------------------------------------------------


MASS_UNITS = {
    "g",
    "gram",
    "grams",
    "kg",
    "kilogram",
    "kilograms",
}

VOLUME_UNITS = {
    "ml",
    "millilitre",
    "millilitres",
    "milliliter",
    "milliliters",
    "l",
    "litre",
    "litres",
    "liter",
    "liters",
}

CULINARY_VOLUME_UNITS = {
    "tsp",
    "teaspoon",
    "teaspoons",
    "tbsp",
    "tablespoon",
    "tablespoons",
    "cup",
    "cups",
}

COUNT_UNITS = {
    "quantity",
    "count",
    "each",
}

UNIT_ALIASES = {
    "gram": "g",
    "grams": "g",
    "kilogram": "kg",
    "kilograms": "kg",
    "millilitre": "ml",
    "millilitres": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "litre": "l",
    "litres": "l",
    "liter": "l",
    "liters": "l",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
}


# ----------------------------------------------------------------------
# Number formatting
# ----------------------------------------------------------------------


def normalise_unit_name(unit_name: str) -> str:
    """Return a normalised unit name."""

    normalised = str(unit_name).strip().casefold()

    return UNIT_ALIASES.get(
        normalised,
        normalised,
    )


def round_half_up(
    value: Any,
    decimal_places: int = 0,
) -> Decimal:
    """
    Round using conventional half-up rounding.

    Unlike Python's built-in round(), values ending in .5 always
    round away from zero. For example, 418.5 becomes 419.
    """

    decimal_value = Decimal(str(value))

    quantum = Decimal("1").scaleb(
        -decimal_places
    )

    return decimal_value.quantize(
        quantum,
        rounding=ROUND_HALF_UP,
    )


def format_number(
    value: Any,
    rounding_places: int = 2,
) -> str:
    """Format a number without unnecessary trailing zeros."""

    rounded_value = round_half_up(
        value,
        decimal_places=rounding_places,
    )

    if rounded_value == rounded_value.to_integral_value():
        return str(int(rounded_value))

    return (
        f"{rounded_value:.{rounding_places}f}"
        .rstrip("0")
        .rstrip(".")
    )


def format_measurement_number(
    value: Any,
    unit_name: str,
    rounding_places: int = 2,
) -> str:
    """
    Format a measurement according to its displayed unit.

    Shopping-friendly rules:

    - grams and millilitres are rounded to whole units;
    - kilograms and litres use one decimal place;
    - other units use the requested decimal precision.
    """

    normalised_unit = normalise_unit_name(
        unit_name
    )

    if normalised_unit in {"g", "ml"}:
        rounded = round_half_up(
            value,
            decimal_places=0,
        )

        return str(int(rounded))

    if normalised_unit in {"kg", "l"}:
        rounded = round_half_up(
            value,
            decimal_places=1,
        )

        return (
            f"{rounded:.1f}"
            .rstrip("0")
            .rstrip(".")
        )

    return format_number(
        value,
        rounding_places=rounding_places,
    )


# ----------------------------------------------------------------------
# Pint quantity helpers
# ----------------------------------------------------------------------


def format_unit(quantity) -> str:
    """Return the abbreviated display form of a Pint unit."""

    return f"{quantity.units:~P}"


def is_plain_count_quantity(quantity) -> bool:
    """
    Return whether a quantity represents an unqualified item count.

    Mass Catering uses the custom ``quantity`` unit for items that
    cannot be converted to mass, volume or another purchasing unit.
    """

    return str(quantity.units) == "quantity"


def is_mass_quantity(quantity) -> bool:
    """Return whether a Pint quantity represents mass."""

    try:
        registry = quantity._REGISTRY

        return (
            quantity.dimensionality
            == registry.gram.dimensionality
        )

    except (AttributeError, UndefinedUnitError):
        return False


def is_volume_quantity(quantity) -> bool:
    """Return whether a Pint quantity represents volume."""

    try:
        registry = quantity._REGISTRY

        return (
            quantity.dimensionality
            == registry.litre.dimensionality
        )

    except (AttributeError, UndefinedUnitError):
        return False


def compact_physical_quantity(quantity):
    """
    Convert physical quantities to practical display units.

    Mass quantities below 1,000 g remain in grams. Larger quantities
    are displayed in kilograms.

    Volume quantities below 1,000 ml remain in millilitres. Larger
    quantities are displayed in litres.
    """

    try:
        if is_mass_quantity(quantity):
            grams = quantity.to("g")

            if abs(float(grams.magnitude)) >= 1000:
                return grams.to("kg")

            return grams

        if is_volume_quantity(quantity):

            original_unit = f"{quantity.units:~P}"

            # Preserve culinary units
            if original_unit in {
                "tsp",
                "tbsp",
                "cup",
            }:
                return quantity

            millilitres = quantity.to("ml")

            if abs(float(millilitres.magnitude)) >= 1000:
                return millilitres.to("l")

            return millilitres

    except (
        DimensionalityError,
        UndefinedUnitError,
        ValueError,
    ):
        pass

    return quantity


def format_quantity(
    quantity,
    rounding_places: int = 2,
) -> str:
    """
    Format a quantity for recipe and general display.

    Large masses and volumes are compacted into kilograms and litres.
    Grams and millilitres are rounded to whole units, while kilograms
    and litres use one decimal place.
    """

    if is_plain_count_quantity(quantity):
        return format_number(
            quantity.magnitude,
            rounding_places,
        )

    if quantity.dimensionless:
        return format_number(
            quantity.magnitude,
            rounding_places,
        )

    display_quantity = compact_physical_quantity(
        quantity
    )

    unit = format_unit(
        display_quantity
    )

    magnitude = format_measurement_number(
        value=display_quantity.magnitude,
        unit_name=unit,
        rounding_places=rounding_places,
    )

    if not unit:
        return magnitude

    return f"{magnitude} {unit}"


# ----------------------------------------------------------------------
# Shopping-unit formatting
# ----------------------------------------------------------------------


def is_continuous_shopping_unit(
    unit_name: str,
) -> bool:
    """
    Return whether a preferred unit may retain fractional values.

    Mass, volume and culinary-volume units are continuous. Other
    custom units, such as eggs, leaves, loaves and cans, are treated
    as whole purchasable items.
    """

    normalised = normalise_unit_name(
        unit_name
    )

    return normalised in (
        MASS_UNITS
        | VOLUME_UNITS
        | CULINARY_VOLUME_UNITS
        | COUNT_UNITS
    )


def format_count_unit_name(
    preferred_unit: str,
) -> str:
    """Return a readable custom count-unit name."""

    return preferred_unit.replace(
        "_",
        " ",
    )


def round_purchasable_count(
    value: Any,
) -> int:
    """
    Round a purchasing quantity upwards without floating-point noise.

    Exact values such as 18.000000000000004 remain 18. Genuine
    fractional values such as 18.2 become 19.
    """

    raw_count = float(value)
    nearest_integer = round(raw_count)

    if math.isclose(
        raw_count,
        nearest_integer,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        return int(nearest_integer)

    return math.ceil(raw_count)


def format_shopping_quantity(
    quantity,
    food_details: dict | None = None,
    rounding_places: int = 2,
) -> str:
    """
    Format a quantity for a shopping list.

    If ``food.yaml`` defines a preferred ``unit``, the calculated
    quantity is converted into that purchasing unit.

    Examples:

    - egg mass with ``unit: egg_large`` becomes a count of eggs;
    - bay-leaf mass with ``unit: bay_leaf`` becomes a leaf count;
    - potato mass with ``unit: g`` displays in grams or kilograms;
    - milk volume with ``unit: ml`` displays in millilitres or litres.

    Custom purchasable count units are rounded upwards. Quantities
    are never silently rounded down.
    """

    if not isinstance(food_details, dict):
        food_details = {}

    preferred_unit = food_details.get(
        "unit"
    )

    if not preferred_unit:
        return format_quantity(
            quantity,
            rounding_places,
        )

    preferred_unit = normalise_unit_name(
        str(preferred_unit)
    )

    try:
        converted = quantity.to(
            preferred_unit
        )

    except (
        DimensionalityError,
        UndefinedUnitError,
        ValueError,
    ):
        # Invalid or incompatible catalogue units should not prevent
        # the shopping list from being produced.
        return format_quantity(
            quantity,
            rounding_places,
        )

    if preferred_unit in COUNT_UNITS:
        return format_number(
            converted.magnitude,
            rounding_places,
        )

    if is_continuous_shopping_unit(
        preferred_unit
    ):
        return format_quantity(
            converted,
            rounding_places,
        )

    count = round_purchasable_count(
        converted.magnitude
    )

    count_unit = format_count_unit_name(
        preferred_unit
    )

    return f"{count} {count_unit}"


# ----------------------------------------------------------------------
# Ingredient-name formatting
# ----------------------------------------------------------------------


def display_ingredient_name(
    ingredient_name: str,
    food_details: dict | None = None,
) -> str:
    """
    Return a human-readable ingredient name.

    A ``display_name`` from ``food.yaml`` takes precedence. Otherwise,
    underscores are replaced with spaces.
    """

    if isinstance(food_details, dict):
        display_name = food_details.get(
            "display_name"
        )

        if (
            isinstance(display_name, str)
            and display_name.strip()
        ):
            return display_name.strip()

    return ingredient_name.replace(
        "_",
        " ",
    )


# ----------------------------------------------------------------------
# Recipe Markdown rendering
# ----------------------------------------------------------------------


def render_scaled_recipe_markdown(
    recipe,
    rounding_places: int = 2,
) -> str:
    """Render one scaled recipe for a chef."""

    output = [
        f"# {recipe.name}",
        "",
        f"**Event:** {recipe.day} {recipe.meal}",
    ]

    if recipe.event_name:
        output.append(
            f"**Menu:** {recipe.event_name}"
        )

    if recipe.people:
        output.extend(
            [
                (
                    f"**Prepare for:** "
                    f"{recipe.people} people"
                ),
                "",
            ]
        )

    else:
        output.extend(
            [
                "**Purpose:** General provision",
                "",
            ]
        )

    if recipe.event_notes:
        output.extend(
            [
                "## Event notes",
                "",
                str(recipe.event_notes),
                "",
            ]
        )

    if recipe.preparation_notes:
        output.extend(
            [
                "## Preparation notes for this menu",
                "",
                str(recipe.preparation_notes),
                "",
            ]
        )

    output.extend(
        [
            "## Ingredients",
            "",
        ]
    )

    for ingredient_name, quantity in sorted(
        recipe.ingredients.items(),
        key=lambda item: item[0].casefold(),
    ):
        formatted_quantity = format_quantity(
            quantity,
            rounding_places,
        )

        output.append(
            (
                f"- "
                f"{display_ingredient_name(ingredient_name)}: "
                f"{formatted_quantity}"
            )
        )

    if recipe.method:
        output.extend(
            [
                "",
                "## Method",
                "",
                str(recipe.method),
            ]
        )

    if recipe.recipe_notes:
        output.extend(
            [
                "",
                "## Recipe notes",
                "",
                str(recipe.recipe_notes),
            ]
        )

    output.append("")

    return "\n".join(output)


# ----------------------------------------------------------------------
# Shopping-list Markdown rendering
# ----------------------------------------------------------------------


def render_shopping_list_markdown(
    result: CompilationResult,
    food_catalogue: dict,
    rounding_places: int = 2,
    default_shop: str = "Supermarket",
) -> str:
    """Render a shopper-friendly list grouped by shop."""

    shops: dict[str, list[str]] = defaultdict(
        list
    )

    for ingredient_name in sorted(
        result.shopping_list,
        key=str.casefold,
    ):
        quantity = result.shopping_list[
            ingredient_name
        ]

        food_details = food_catalogue.get(
            ingredient_name,
            {},
        )

        if not isinstance(food_details, dict):
            food_details = {}

        shop = str(
            food_details.get(
                "shop",
                default_shop,
            )
        )

        formatted_quantity = (
            format_shopping_quantity(
                quantity=quantity,
                food_details=food_details,
                rounding_places=rounding_places,
            )
        )

        ingredient_display_name = (
            display_ingredient_name(
                ingredient_name,
                food_details,
            )
        )

        shops[shop].append(
            (
                f"- [ ] "
                f"{formatted_quantity} "
                f"{ingredient_display_name}"
            )
        )

    output = [
        "# Shopping List",
        "",
    ]

    for shop in sorted(
        shops,
        key=str.casefold,
    ):
        output.append(
            f"## {shop}"
        )

        output.extend(
            shops[shop]
        )

        output.append("")

    return "\n".join(output)


# ----------------------------------------------------------------------
# Complete recipe-pack Markdown rendering
# ----------------------------------------------------------------------


def render_all_recipes_markdown(
    result: CompilationResult,
    rounding_places: int = 2,
) -> str:
    """Render all scaled recipes in menu order."""

    rendered_recipes = [
        render_scaled_recipe_markdown(
            recipe,
            rounding_places,
        )
        for recipe in result.scaled_recipes
    ]

    return "\n\n\\pagebreak\n\n".join(
        rendered_recipes
    )