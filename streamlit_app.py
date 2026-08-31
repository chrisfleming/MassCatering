import streamlit as st

from mass_catering.compiler import compile_menu
from mass_catering.rendering import (
    render_shopping_list_markdown,
)
from mass_catering.repository import (
    RepositoryError,
    list_menu_names,
    load_food_catalogue,
    load_menu,
    load_recipe,
)


st.set_page_config(
    page_title="Mass Catering",
    page_icon="🍲",
    layout="wide",
)


def load_referenced_recipes(
    menu: dict,
) -> tuple[dict[str, dict], list[str]]:
    """
    Load recipes referenced by a menu.

    Unmatched names are retained as possible standalone
    shopping-list entries.
    """

    recipes = {}
    standalone_items = []

    for item_name in menu:
        try:
            recipes[item_name] = load_recipe(item_name)
        except RepositoryError:
            standalone_items.append(item_name)

    return recipes, standalone_items


st.title("🍲 Mass Catering")
st.caption(
    "Plan, scale and shop for meals for large groups."
)

menu_names = list_menu_names()

if not menu_names:
    st.warning("No menu files were found.")
    st.stop()

left_column, right_column = st.columns([2, 1])

with left_column:
    selected_menu = st.selectbox(
        "Choose a menu",
        options=menu_names,
        index=(
            menu_names.index("hostel_feb26")
            if "hostel_feb26" in menu_names
            else 0
        ),
    )

with right_column:
    rounding_places = st.number_input(
        "Decimal places",
        min_value=0,
        max_value=4,
        value=2,
        step=1,
    )

compile_clicked = st.button(
    "Validate and compile",
    type="primary",
    use_container_width=True,
)

if compile_clicked:
    try:
        menu = load_menu(selected_menu)

        recipes, standalone_items = (
            load_referenced_recipes(menu)
        )

        result = compile_menu(
            menu=menu,
            recipes=recipes,
        )

        food_catalogue = load_food_catalogue()

        markdown = render_shopping_list_markdown(
            result=result,
            food_catalogue=food_catalogue,
            rounding_places=int(rounding_places),
        )

        st.session_state["compilation"] = {
            "menu_name": selected_menu,
            "result": result,
            "markdown": markdown,
            "standalone_items": standalone_items,
        }

    except (RepositoryError, ValueError) as exc:
        st.error(str(exc))

compilation = st.session_state.get("compilation")

if compilation:
    result = compilation["result"]
    markdown = compilation["markdown"]

    if compilation["standalone_items"]:
        st.info(
            "The following menu entries were treated as "
            "standalone shopping items: "
            + ", ".join(
                compilation["standalone_items"]
            )
        )

    metric_1, metric_2, metric_3 = st.columns(3)

    metric_1.metric(
        "Meal entries",
        len(result.scaled_recipes),
    )

    metric_2.metric(
        "Shopping items",
        len(result.shopping_list),
    )

    metric_3.metric(
        "Warnings",
        len(result.warnings),
    )

    preview_tab, recipes_tab = st.tabs(
        [
            "Shopping list",
            "Scaled recipes",
        ]
    )

    with preview_tab:
        st.markdown(markdown)

    with recipes_tab:
        for recipe in result.scaled_recipes:
            with st.expander(
                f"{recipe.label}: {recipe.name} "
                f"for {recipe.people} people"
            ):
                for ingredient_name, quantity in (
                    recipe.ingredients.items()
                ):
                    rounded_quantity = round(
                        quantity,
                        int(rounding_places),
                    )

                    st.write(
                        f"- {ingredient_name}: "
                        f"{rounded_quantity:~P}"
                    )

                if recipe.method:
                    st.markdown("#### Method")
                    st.write(recipe.method)

    st.download_button(
        label="Download shopping list",
        data=markdown,
        file_name=(
            f"{compilation['menu_name']}"
            "_shopping_list.md"
        ),
        mime="text/markdown",
        type="primary",
    )