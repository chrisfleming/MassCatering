"""Tests for Mass Catering quantity and Markdown rendering."""

from dataclasses import dataclass

import pytest

from mass_catering.compiler import CompilationResult
from mass_catering.rendering import (
    compact_physical_quantity,
    display_ingredient_name,
    format_count_unit_name,
    format_measurement_number,
    format_number,
    format_quantity,
    format_shopping_quantity,
    is_continuous_shopping_unit,
    normalise_unit_name,
    render_all_recipes_markdown,
    render_scaled_recipe_markdown,
    render_shopping_list_markdown,
    round_half_up,
    round_purchasable_count,
)
from mass_catering.units import parse_quantity


# ----------------------------------------------------------------------
# Test helper
# ----------------------------------------------------------------------


@dataclass
class ExampleScaledRecipe:
    """Minimal recipe object for Markdown rendering tests."""

    name: str = "Example Stew"
    day: str = "Saturday"
    meal: str = "Dinner"
    event_name: str = "Stew night"
    people: int = 10
    ingredients: dict | None = None
    method: str | None = "Cook until tender."
    recipe_notes: str | None = "May be prepared in advance."
    preparation_notes: str | None = "Keep one portion separate."
    event_notes: str | None = "Serve at 18:00."

    def __post_init__(self):
        if self.ingredients is None:
            self.ingredients = {
                "potato": parse_quantity(
                    "1500 g",
                    "potato",
                ),
                "milk": parse_quantity(
                    "500 ml",
                    "milk",
                ),
            }


# ----------------------------------------------------------------------
# Unit-name normalisation
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("g", "g"),
        ("gram", "g"),
        ("grams", "g"),
        ("kg", "kg"),
        ("kilograms", "kg"),
        ("ml", "ml"),
        ("millilitres", "ml"),
        ("l", "l"),
        ("litres", "l"),
        ("teaspoons", "tsp"),
        ("tablespoons", "tbsp"),
        ("egg_large", "egg_large"),
    ],
)
def test_normalise_unit_name(original, expected):
    assert normalise_unit_name(original) == expected


# ----------------------------------------------------------------------
# Conventional half-up rounding
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "decimal_places", "expected"),
    [
        (418.5, 0, "419"),
        (418.4, 0, "418"),
        (2.25, 1, "2.3"),
        (2.24, 1, "2.2"),
        (13.97, 0, "14"),
        (7.39, 0, "7"),
    ],
)
def test_round_half_up(
    value,
    decimal_places,
    expected,
):
    result = round_half_up(
        value,
        decimal_places,
    )

    assert str(result) == expected


# ----------------------------------------------------------------------
# General number formatting
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "rounding_places", "expected"),
    [
        (18, 2, "18"),
        (18.0, 2, "18"),
        (18.5, 2, "18.5"),
        (18.567, 2, "18.57"),
        (2.25, 1, "2.3"),
        (0.5, 2, "0.5"),
    ],
)
def test_format_number(
    value,
    rounding_places,
    expected,
):
    assert format_number(
        value,
        rounding_places,
    ) == expected


# ----------------------------------------------------------------------
# Unit-aware measurement formatting
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (418.5, "g", "419"),
        (26.25, "g", "26"),
        (13.97, "ml", "14"),
        (7.39, "ml", "7"),
        (8.12, "kg", "8.1"),
        (2.25, "kg", "2.3"),
        (11.33, "l", "11.3"),
        (1.9, "l", "1.9"),
        (2.345, "tbsp", "2.35"),
    ],
)
def test_format_measurement_number(
    value,
    unit,
    expected,
):
    assert format_measurement_number(
        value=value,
        unit_name=unit,
        rounding_places=2,
    ) == expected


# ----------------------------------------------------------------------
# Physical quantity compaction
# ----------------------------------------------------------------------


def test_large_mass_is_compacted_to_kilograms():
    quantity = parse_quantity(
        "8120 g",
        "potato",
    )

    compacted = compact_physical_quantity(
        quantity
    )

    assert compacted.units == quantity._REGISTRY.kg
    assert compacted.magnitude == pytest.approx(
        8.12
    )


def test_small_mass_remains_in_grams():
    quantity = parse_quantity(
        "425 g",
        "prawns",
    )

    compacted = compact_physical_quantity(
        quantity
    )

    assert compacted.units == quantity._REGISTRY.g
    assert compacted.magnitude == pytest.approx(
        425
    )


def test_large_volume_is_compacted_to_litres():
    quantity = parse_quantity(
        "11326 ml",
        "milk",
    )

    compacted = compact_physical_quantity(
        quantity
    )

    assert compacted.units == quantity._REGISTRY.l
    assert compacted.magnitude == pytest.approx(
        11.326
    )


def test_small_volume_remains_in_millilitres():
    quantity = parse_quantity(
        "250 ml",
        "oat_cream",
    )

    compacted = compact_physical_quantity(
        quantity
    )

    assert compacted.units == quantity._REGISTRY.ml
    assert compacted.magnitude == pytest.approx(
        250
    )


# ----------------------------------------------------------------------
# General quantity display
# ----------------------------------------------------------------------


def test_plain_count_is_formatted_without_unit_symbol():
    quantity = parse_quantity(
        2,
        "marshmallow",
    )

    assert format_quantity(quantity) == "2"


def test_registered_item_count_is_displayed_as_mass():
    """
    Fourteen potatoes are converted to mass using the registry.

    One potato is configured as 150 g, giving 2.1 kg.
    """

    quantity = parse_quantity(
        14,
        "potato",
    )

    assert format_quantity(quantity) == "2.1 kg"


def test_grams_are_rounded_to_whole_numbers():
    quantity = parse_quantity(
        "418.5 g",
        "cucumber",
    )

    assert format_quantity(
        quantity,
        rounding_places=2,
    ) == "419 g"


def test_small_gram_quantity_is_rounded_to_whole_number():
    quantity = parse_quantity(
        "26.25 g",
        "custard_powder",
    )

    assert format_quantity(
        quantity,
        rounding_places=2,
    ) == "26 g"


def test_millilitres_are_rounded_to_whole_numbers():
    quantity = parse_quantity(
        "13.97 ml",
        "dijon_mustard",
    )

    assert format_quantity(
        quantity,
        rounding_places=2,
    ) == "14 ml"


def test_small_millilitre_quantity_is_rounded():
    quantity = parse_quantity(
        "7.39 ml",
        "dill",
    )

    assert format_quantity(
        quantity,
        rounding_places=2,
    ) == "7 ml"


def test_large_mass_uses_one_decimal_place():
    quantity = parse_quantity(
        "8120 g",
        "potato",
    )

    assert format_quantity(
        quantity,
        rounding_places=2,
    ) == "8.1 kg"


def test_half_kilogram_decimal_uses_half_up_rounding():
    quantity = parse_quantity(
        "2250 g",
        "salmon",
    )

    assert format_quantity(
        quantity,
        rounding_places=2,
    ) == "2.3 kg"


def test_large_volume_uses_one_decimal_place():
    quantity = parse_quantity(
        "11326 ml",
        "milk",
    )

    assert format_quantity(
        quantity,
        rounding_places=2,
    ) == "11.3 l"


def test_small_volume_remains_in_millilitres():
    quantity = parse_quantity(
        "250 ml",
        "oat_cream",
    )

    assert format_quantity(
        quantity,
        rounding_places=2,
    ) == "250 ml"


def test_culinary_unit_retains_requested_precision():
    quantity = parse_quantity(
        "2.345 tbsp",
        "parsley",
    )

    assert format_quantity(
        quantity,
        rounding_places=2,
    ) == "2.35 tbsp"


# ----------------------------------------------------------------------
# Shopping-unit classification
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "unit_name",
    [
        "g",
        "kg",
        "ml",
        "l",
        "tsp",
        "tbsp",
        "quantity",
    ],
)
def test_continuous_shopping_units(
    unit_name,
):
    assert is_continuous_shopping_unit(
        unit_name
    )


@pytest.mark.parametrize(
    "unit_name",
    [
        "egg_large",
        "bay_leaf",
        "loaf",
        "can",
        "nori_sheet",
    ],
)
def test_custom_units_are_purchasable_counts(
    unit_name,
):
    assert not is_continuous_shopping_unit(
        unit_name
    )


def test_count_unit_name_is_human_readable():
    assert (
        format_count_unit_name("egg_large")
        == "egg large"
    )

    assert (
        format_count_unit_name("bay_leaf")
        == "bay leaf"
    )


# ----------------------------------------------------------------------
# Purchasable count rounding
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (18.0, 18),
        (18.000000000000004, 18),
        (14.000000000000002, 14),
        (18.2, 19),
        (0.5, 1),
        (1.01, 2),
    ],
)
def test_round_purchasable_count(
    value,
    expected,
):
    assert round_purchasable_count(
        value
    ) == expected


# ----------------------------------------------------------------------
# Shopping quantity formatting
# ----------------------------------------------------------------------


def test_egg_quantity_is_displayed_as_count():
    quantity = parse_quantity(
        "18 egg_large",
        "egg_large",
    )

    formatted = format_shopping_quantity(
        quantity=quantity,
        food_details={
            "unit": "egg_large",
        },
        rounding_places=2,
    )

    assert formatted == "18 egg large"


def test_fractional_egg_count_is_rounded_up():
    """
    One large egg is 68 g, so 34 g represents half an egg.

    A shopping list must request one whole egg.
    """

    quantity = parse_quantity(
        "34 g",
        "egg_large",
    )

    formatted = format_shopping_quantity(
        quantity=quantity,
        food_details={
            "unit": "egg_large",
        },
        rounding_places=2,
    )

    assert formatted == "1 egg large"


def test_floating_point_noise_does_not_add_an_egg():
    quantity = parse_quantity(
        "18 egg_large",
        "egg_large",
    )

    formatted = format_shopping_quantity(
        quantity=quantity,
        food_details={
            "unit": "egg_large",
        },
        rounding_places=2,
    )

    assert formatted == "18 egg large"


def test_bay_leaf_quantity_is_displayed_as_count():
    quantity = parse_quantity(
        "14 bay_leaf",
        "bay_leaf",
    )

    formatted = format_shopping_quantity(
        quantity=quantity,
        food_details={
            "unit": "bay_leaf",
        },
        rounding_places=2,
    )

    assert formatted == "14 bay leaf"


def test_fractional_bay_leaf_count_is_rounded_up():
    quantity = parse_quantity(
        "7.5 g",
        "bay_leaf",
    )

    formatted = format_shopping_quantity(
        quantity=quantity,
        food_details={
            "unit": "bay_leaf",
        },
        rounding_places=2,
    )

    assert formatted == "2 bay leaf"


def test_potato_remains_mass_for_shopping():
    quantity = parse_quantity(
        14,
        "potato",
    )

    formatted = format_shopping_quantity(
        quantity=quantity,
        food_details={
            "unit": "g",
        },
        rounding_places=2,
    )

    assert formatted == "2.1 kg"


def test_milk_is_displayed_in_litres_for_shopping():
    quantity = parse_quantity(
        "11326 ml",
        "milk",
    )

    formatted = format_shopping_quantity(
        quantity=quantity,
        food_details={
            "unit": "ml",
        },
        rounding_places=2,
    )

    assert formatted == "11.3 l"


def test_count_without_preferred_unit_remains_count():
    quantity = parse_quantity(
        2,
        "marshmallow",
    )

    formatted = format_shopping_quantity(
        quantity=quantity,
        food_details={},
        rounding_places=2,
    )

    assert formatted == "2"


def test_invalid_preferred_unit_falls_back_safely():
    quantity = parse_quantity(
        "500 g",
        "plain_flour",
    )

    formatted = format_shopping_quantity(
        quantity=quantity,
        food_details={
            "unit": "not_a_real_unit",
        },
        rounding_places=2,
    )

    assert formatted == "500 g"


def test_incompatible_preferred_unit_falls_back_safely():
    quantity = parse_quantity(
        "500 ml",
        "milk",
    )

    formatted = format_shopping_quantity(
        quantity=quantity,
        food_details={
            "unit": "kg",
        },
        rounding_places=2,
    )

    assert formatted == "500 ml"


# ----------------------------------------------------------------------
# Ingredient display names
# ----------------------------------------------------------------------


def test_ingredient_underscores_are_replaced():
    assert (
        display_ingredient_name(
            "dijon_mustard"
        )
        == "dijon mustard"
    )


def test_catalogue_display_name_takes_precedence():
    assert (
        display_ingredient_name(
            "egg_large",
            {
                "display_name": "large eggs",
            },
        )
        == "large eggs"
    )


def test_blank_catalogue_display_name_is_ignored():
    assert (
        display_ingredient_name(
            "egg_large",
            {
                "display_name": "   ",
            },
        )
        == "egg large"
    )


# ----------------------------------------------------------------------
# Shopping-list Markdown rendering
# ----------------------------------------------------------------------


def test_shopping_list_is_grouped_by_shop():
    result = CompilationResult(
        shopping_list={
            "egg_large": parse_quantity(
                "18 egg_large",
                "egg_large",
            ),
            "potato": parse_quantity(
                "8120 g",
                "potato",
            ),
        }
    )

    food_catalogue = {
        "egg_large": {
            "shop": "Butchers",
            "unit": "egg_large",
            "display_name": "large eggs",
        },
        "potato": {
            "shop": "Supermarket",
            "unit": "g",
            "display_name": "potatoes",
        },
    }

    rendered = render_shopping_list_markdown(
        result=result,
        food_catalogue=food_catalogue,
        rounding_places=2,
    )

    assert "# Shopping List" in rendered
    assert "## Butchers" in rendered
    assert "## Supermarket" in rendered

    assert (
        "- [ ] 18 egg large large eggs"
        in rendered
    )

    assert (
        "- [ ] 8.1 kg potatoes"
        in rendered
    )


def test_unknown_shop_uses_default_shop():
    result = CompilationResult(
        shopping_list={
            "marshmallow": parse_quantity(
                2,
                "marshmallow",
            )
        }
    )

    rendered = render_shopping_list_markdown(
        result=result,
        food_catalogue={},
        default_shop="Supermarket",
    )

    assert "## Supermarket" in rendered
    assert "- [ ] 2 marshmallow" in rendered


def test_shopping_list_uses_half_up_rounding():
    result = CompilationResult(
        shopping_list={
            "cucumber": parse_quantity(
                "418.5 g",
                "cucumber",
            ),
            "dijon_mustard": parse_quantity(
                "13.97 ml",
                "dijon_mustard",
            ),
        }
    )

    food_catalogue = {
        "cucumber": {
            "shop": "Supermarket",
            "unit": "g",
        },
        "dijon_mustard": {
            "shop": "Supermarket",
            "unit": "ml",
        },
    }

    rendered = render_shopping_list_markdown(
        result=result,
        food_catalogue=food_catalogue,
        rounding_places=2,
    )

    assert "- [ ] 419 g cucumber" in rendered

    assert (
        "- [ ] 14 ml dijon mustard"
        in rendered
    )


# ----------------------------------------------------------------------
# Scaled recipe Markdown rendering
# ----------------------------------------------------------------------


def test_scaled_recipe_markdown_includes_context_and_notes():
    recipe = ExampleScaledRecipe()

    rendered = render_scaled_recipe_markdown(
        recipe,
        rounding_places=2,
    )

    assert "# Example Stew" in rendered
    assert "**Event:** Saturday Dinner" in rendered
    assert "**Menu:** Stew night" in rendered
    assert "**Prepare for:** 10 people" in rendered

    assert "## Event notes" in rendered
    assert "Serve at 18:00." in rendered

    assert (
        "## Preparation notes for this menu"
        in rendered
    )

    assert "Keep one portion separate." in rendered

    assert "## Ingredients" in rendered
    assert "- potato: 1.5 kg" in rendered
    assert "- milk: 500 ml" in rendered

    assert "## Method" in rendered
    assert "Cook until tender." in rendered

    assert "## Recipe notes" in rendered
    assert "May be prepared in advance." in rendered


def test_general_provision_does_not_show_zero_people():
    recipe = ExampleScaledRecipe(
        day="General",
        meal="provisions",
        event_name="General provisions",
        people=0,
        event_notes=None,
        preparation_notes=None,
    )

    rendered = render_scaled_recipe_markdown(
        recipe
    )

    assert "**Purpose:** General provision" in rendered
    assert "Prepare for" not in rendered


def test_all_recipes_are_separated_by_page_break():
    first = ExampleScaledRecipe(
        name="First recipe"
    )

    second = ExampleScaledRecipe(
        name="Second recipe"
    )

    result = CompilationResult(
        scaled_recipes=[
            first,
            second,
        ]
    )

    rendered = render_all_recipes_markdown(
        result
    )

    assert "# First recipe" in rendered
    assert "# Second recipe" in rendered
    assert "\\pagebreak" in rendered