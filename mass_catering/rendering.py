from collections import defaultdict

from mass_catering.compiler import CompilationResult


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

    output.extend(
        [
            f"**Prepare for:** {recipe.people} people",
            "",
        ]
    )

    if recipe.event_notes:
        output.extend(
            [
                "## Event notes",
                "",
                recipe.event_notes,
                "",
            ]
        )

    if recipe.preparation_notes:
        output.extend(
            [
                "## Preparation notes for this menu",
                "",
                recipe.preparation_notes,
                "",
            ]
        )

    output.extend(
        [
            "## Ingredients",
            "",
        ]
    )

    for ingredient_name, quantity in (
        recipe.ingredients.items()
    ):
        rounded_quantity = round(
            quantity,
            rounding_places,
        )

        output.append(
            f"- {ingredient_name}: "
            f"{rounded_quantity:~P}"
        )

    if recipe.method:
        output.extend(
            [
                "",
                "## Method",
                "",
                recipe.method,
            ]
        )

    if recipe.recipe_notes:
        output.extend(
            [
                "",
                "## Recipe notes",
                "",
                recipe.recipe_notes,
            ]
        )

    output.append("")

    return "\n".join(output)



def render_shopping_list_markdown(
    result: CompilationResult,
    food_catalogue: dict,
    rounding_places: int = 2,
    default_shop: str = "Supermarket",
) -> str:
    """Render a shopping list grouped by shop."""

    shops: dict[str, list[str]] = defaultdict(list)

    for ingredient_name in sorted(result.shopping_list):
        quantity = result.shopping_list[ingredient_name]

        food_details = food_catalogue.get(
            ingredient_name,
            {},
        )

        if not isinstance(food_details, dict):
            food_details = {}

        shop = food_details.get(
            "shop",
            default_shop,
        )

        rounded_quantity = round(
            quantity,
            rounding_places,
        )

        shops[shop].append(
            f"- [ ] {rounded_quantity:~P} "
            f"{ingredient_name}"
        )

    output = [
        "# Shopping List",
        "",
    ]

    for shop in sorted(shops):
        output.append(f"## {shop}")
        output.extend(shops[shop])
        output.append("")

    return "\n".join(output)



def render_all_recipes_markdown(
    result: CompilationResult,
    rounding_places: int = 2,
) -> str:
    """Render all scaled recipes in menu order."""

    recipes = []

    for recipe in result.scaled_recipes:
        recipes.append(
            render_scaled_recipe_markdown(
                recipe,
                rounding_places,
            )
        )

    return "\n\n\\pagebreak\n\n".join(recipes)