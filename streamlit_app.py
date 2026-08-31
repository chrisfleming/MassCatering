from pathlib import Path
import re

import streamlit as st
import yaml

from mass_catering.compiler import compile_menu
from mass_catering.pdf import generate_menu_pdf
from mass_catering.rendering import (
    format_quantity,
    render_shopping_list_markdown,
)
from mass_catering.repository import (
    RepositoryError,
    list_menu_names,
    list_recipe_names,
    load_food_catalogue,
    load_menu,
    load_recipe,
)
from mass_catering.validation import (
    Severity,
    ValidationIssue,
    validate_ingredient_names,
    validate_menu,
)

st.set_page_config(
    page_title="Mass Catering",
    page_icon="🍲",
    layout="wide",
)


# ----------------------------------------------------------------------
# Menu loading and parsing
# ----------------------------------------------------------------------


def make_safe_identifier(value: str) -> str:
    """Create a safe filename stem from a menu name."""

    identifier = value.strip().casefold()
    identifier = re.sub(r"[^a-z0-9]+", "_", identifier)
    identifier = identifier.strip("_")

    return identifier or "uploaded_menu"


def parse_menu_yaml(
    yaml_text: str,
    source_name: str,
) -> dict:
    """Parse menu YAML and check that it contains a mapping."""

    if not yaml_text.strip():
        raise ValueError(
            f"No YAML content was provided for {source_name}."
        )

    try:
        menu = yaml.safe_load(yaml_text)

    except yaml.YAMLError as exc:
        raise ValueError(
            f"Invalid YAML in {source_name}: {exc}"
        ) from exc

    if not isinstance(menu, dict):
        raise ValueError(
            f"{source_name} must contain a YAML mapping."
        )

    return menu


def store_selected_menu(
    menu: dict,
    identifier: str,
    source: str,
) -> None:
    """Store a selected menu in the current Streamlit session."""

    st.session_state["selected_menu_input"] = {
        "menu": menu,
        "identifier": identifier,
        "source": source,
    }

    # Clear outputs from a previously selected menu.
    st.session_state.pop("compilation", None)
    st.session_state.pop("validation_issues", None)


def get_referenced_recipe_names(
    menu: dict,
) -> set:
    """Return every recipe identifier referenced by a menu."""

    recipe_names: set[str] = set()

    for event in menu.get("events", []):
        if not isinstance(event, dict):
            continue

        for dish in event.get("dishes", []):
            if not isinstance(dish, dict):
                continue

            recipe_name = dish.get("recipe")

            if isinstance(recipe_name, str) and recipe_name:
                recipe_names.add(recipe_name)

    for provision in menu.get(
        "general_provisions",
        [],
    ):
        if not isinstance(provision, dict):
            continue

        recipe_name = provision.get("recipe")

        if isinstance(recipe_name, str) and recipe_name:
            recipe_names.add(recipe_name)

    return recipe_names


def load_referenced_recipes(
    menu: dict,
) -> dict[str, dict]:
    """Load all recipes referenced by a version 2 menu."""

    recipes: dict[str, dict] = {}

    for recipe_name in sorted(
        get_referenced_recipe_names(menu)
    ):
        recipes[recipe_name] = load_recipe(recipe_name)

    return recipes


# ----------------------------------------------------------------------
# Validation display
# ----------------------------------------------------------------------


def display_validation_issues(
    issues: list[ValidationIssue],
) -> None:
    """Display validation issues grouped by severity."""

    errors = [
        issue
        for issue in issues
        if issue.severity == Severity.ERROR
    ]

    warnings = [
        issue
        for issue in issues
        if issue.severity == Severity.WARNING
    ]

    information = [
        issue
        for issue in issues
        if issue.severity == Severity.INFORMATION
    ]

    if errors:
        st.error(
            f"{len(errors)} validation error(s) must be fixed "
            "before the menu can be compiled."
        )

        for issue in errors:
            st.markdown(
                f"**Error** · `{issue.location}`  \n"
                f"{issue.message}"
            )

    if warnings:
        st.warning(
            f"{len(warnings)} validation warning(s) found. "
            "Compilation can continue, but the menu should "
            "be reviewed."
        )

        for issue in warnings:
            st.markdown(
                f"**Warning** · `{issue.location}`  \n"
                f"{issue.message}"
            )

    if information:
        with st.expander(
            f"{len(information)} additional validation note(s)"
        ):
            for issue in information:
                st.markdown(
                    f"**Information** · `{issue.location}`  \n"
                    f"{issue.message}"
                )

    if not issues:
        st.success("Menu validation passed with no issues.")


# ----------------------------------------------------------------------
# Recipe preview
# ----------------------------------------------------------------------


def render_scaled_recipe_preview(
    recipe,
    rounding_places: int,
) -> None:
    """Display one compiled recipe in Streamlit."""

    if recipe.people:
        heading = (
            f"{recipe.label}: {recipe.name} "
            f"for {recipe.people} people"
        )
    else:
        heading = f"{recipe.label}: {recipe.name}"

    with st.expander(heading):
        if recipe.event_notes:
            st.markdown("#### Notes for this meal")
            st.info(recipe.event_notes)

        if recipe.preparation_notes:
            st.markdown(
                "#### Preparation notes for the chef"
            )
            st.warning(recipe.preparation_notes)

        st.markdown("#### Ingredients")

        for ingredient_name, quantity in sorted(
            recipe.ingredients.items()
        ):
            formatted_quantity = format_quantity(
                quantity,
                rounding_places,
            )

            display_name = ingredient_name.replace(
                "_",
                " ",
            )

            st.markdown(
                f"- **{display_name}:** "
                f"{formatted_quantity}"
            )

        if recipe.method:
            st.markdown("#### Method")
            st.write(recipe.method)

        if recipe.recipe_notes:
            st.markdown("#### Recipe notes")
            st.info(recipe.recipe_notes)


# ----------------------------------------------------------------------
# Compilation
# ----------------------------------------------------------------------


def count_scheduled_dishes(result) -> int:
    """Count scheduled dishes, excluding general provisions."""

    return sum(
        recipe.meal != "provisions"
        for recipe in result.scaled_recipes
    )


def count_validation_warnings(
    issues: list[ValidationIssue],
) -> int:
    """Count validation warnings."""

    return sum(
        issue.severity == Severity.WARNING
        for issue in issues
    )


def compile_selected_menu(
    menu: dict,
    menu_identifier: str,
    menu_source: str,
    rounding_places: int,
) -> None:
    """Validate and compile a supplied version 2 menu."""

    st.session_state.pop("compilation", None)
    st.session_state.pop("validation_issues", None)

    validation_issues = validate_menu(
        menu=menu,
        available_recipes=set(list_recipe_names()),
    )

    validation_errors = [
        issue
        for issue in validation_issues
        if issue.severity == Severity.ERROR
    ]

    if validation_errors:
        st.session_state["validation_issues"] = (
            validation_issues
        )
        return

    structural_issues = validate_menu(
        menu=menu,
        available_recipes=set(list_recipe_names()),
    )

    recipes = load_referenced_recipes(menu)

    ingredient_issues = validate_ingredient_names(
        menu=menu,
        recipes=recipes,
    )

    validation_issues = (
        structural_issues
        + ingredient_issues
    )
    result = compile_menu(
        menu=menu,
        recipes=recipes,
    )

    food_catalogue = load_food_catalogue()

    markdown = render_shopping_list_markdown(
        result=result,
        food_catalogue=food_catalogue,
        rounding_places=rounding_places,
    )

    pdf = generate_menu_pdf(
        menu=menu,
        result=result,
        food_catalogue=food_catalogue,
        rounding_places=rounding_places,
    )

    st.session_state["compilation"] = {
        "menu_name": menu_identifier,
        "menu_source": menu_source,
        "menu": menu,
        "result": result,
        "markdown": markdown,
        "pdf": pdf,
        "validation_issues": validation_issues,
        "rounding_places": rounding_places,
    }


# ----------------------------------------------------------------------
# Application heading
# ----------------------------------------------------------------------


st.title("🍲 Mass Catering")
st.caption(
    "Plan, scale and shop for meals for large groups."
)


# ----------------------------------------------------------------------
# Load repository menu names
# ----------------------------------------------------------------------


try:
    menu_names = list_menu_names()

except RepositoryError as exc:
    st.error(str(exc))
    menu_names = []


# ----------------------------------------------------------------------
# Menu source
# ----------------------------------------------------------------------


st.markdown("### Choose a menu")

(
    repository_tab,
    upload_tab,
    paste_tab,
) = st.tabs(
    [
        "Existing menu",
        "Upload YAML",
        "Paste YAML",
    ]
)


# ----------------------------------------------------------------------
# Existing repository menu
# ----------------------------------------------------------------------


with repository_tab:
    st.write(
        "Choose one of the version 2 menus already available "
        "in the project."
    )

    if not menu_names:
        st.warning(
            "No version 2 menu files were found in the repository."
        )

    else:
        selected_repository_menu = st.selectbox(
            "Existing menu",
            options=menu_names,
            index=(
                menu_names.index("hostel_feb26")
                if "hostel_feb26" in menu_names
                else 0
            ),
            key="repository_menu_selector",
        )

        if st.button(
            "Use existing menu",
            key="use_repository_menu",
            use_container_width=True,
        ):
            try:
                repository_menu = load_menu(
                    selected_repository_menu
                )

                store_selected_menu(
                    menu=repository_menu,
                    identifier=selected_repository_menu,
                    source="Repository",
                )

            except RepositoryError as exc:
                st.error(str(exc))


# ----------------------------------------------------------------------
# Uploaded YAML menu
# ----------------------------------------------------------------------


with upload_tab:
    st.write(
        "Upload a version 2 menu as a YAML file. "
        "The file is used only for this browser session "
        "and is not written to GitHub."
    )

    uploaded_menu = st.file_uploader(
        "Upload a menu",
        type=["yaml", "yml"],
        accept_multiple_files=False,
        key="menu_file_uploader",
        help=(
            "Upload a menu using the Mass Catering "
            "version 2 YAML schema."
        ),
    )

    if uploaded_menu is not None:
        st.caption(
            f"Selected file: {uploaded_menu.name}"
        )

        if st.button(
            "Use uploaded menu",
            key="use_uploaded_menu",
            use_container_width=True,
        ):
            try:
                uploaded_text = (
                    uploaded_menu
                    .getvalue()
                    .decode("utf-8-sig")
                )

                uploaded_menu_data = parse_menu_yaml(
                    uploaded_text,
                    uploaded_menu.name,
                )

                identifier = make_safe_identifier(
                    uploaded_menu_data.get(
                        "name",
                        Path(uploaded_menu.name).stem,
                    )
                )

                store_selected_menu(
                    menu=uploaded_menu_data,
                    identifier=identifier,
                    source=f"Uploaded file: {uploaded_menu.name}",
                )

            except UnicodeDecodeError:
                st.error(
                    "The uploaded file is not valid UTF-8 text."
                )

            except ValueError as exc:
                st.error(str(exc))


# ----------------------------------------------------------------------
# Pasted YAML menu
# ----------------------------------------------------------------------


with paste_tab:
    st.write(
        "Paste a complete version 2 menu below. "
        "The menu is used only for this browser session "
        "and is not written to GitHub."
    )

    pasted_yaml = st.text_area(
        "Paste menu YAML",
        height=400,
        key="pasted_menu_yaml",
        placeholder=(
            "schema_version: 2\n"
            "name: Example Weekend\n"
            "description: Example catering menu\n"
            "\n"
            "events:\n"
            "  - day: Saturday\n"
            "    meal: dinner\n"
            "    name: Soup night\n"
            "    people: 20\n"
            "    dishes:\n"
            "      - recipe: soup\n"
            "        notes: Serve promptly.\n"
            "\n"
            "additional_items:\n"
            "  - ingredient: coffee\n"
            "    quantity: 500 g\n"
        ),
        help=(
            "Paste the complete YAML document, including "
            "schema_version, name and events."
        ),
    )

    if st.button(
        "Use pasted menu",
        key="use_pasted_menu",
        use_container_width=True,
        disabled=not pasted_yaml.strip(),
    ):
        try:
            pasted_menu_data = parse_menu_yaml(
                pasted_yaml,
                "pasted menu",
            )

            identifier = make_safe_identifier(
                pasted_menu_data.get(
                    "name",
                    "pasted menu",
                )
            )

            store_selected_menu(
                menu=pasted_menu_data,
                identifier=identifier,
                source="Pasted YAML",
            )

        except ValueError as exc:
            st.error(str(exc))


# ----------------------------------------------------------------------
# Selected menu summary
# ----------------------------------------------------------------------


selected_menu_input = st.session_state.get(
    "selected_menu_input"
)

if selected_menu_input:
    selected_menu_data = selected_menu_input["menu"]

    selected_display_name = selected_menu_data.get(
        "name",
        selected_menu_input["identifier"],
    )

    st.success(
        f"Selected menu: **{selected_display_name}**"
    )

    st.caption(
        f"Source: {selected_menu_input['source']}"
    )

    with st.expander("Preview selected menu YAML"):
        preview_yaml = yaml.safe_dump(
            selected_menu_data,
            sort_keys=False,
            allow_unicode=True,
        )

        st.code(
            preview_yaml,
            language="yaml",
        )


# ----------------------------------------------------------------------
# Compilation controls
# ----------------------------------------------------------------------


st.markdown("### Generate menu outputs")

rounding_places = st.number_input(
    "Decimal places",
    min_value=0,
    max_value=4,
    value=2,
    step=1,
    help=(
        "Controls the number of decimal places shown in "
        "shopping lists and scaled recipe quantities."
    ),
)

compile_clicked = st.button(
    "Validate and compile",
    type="primary",
    use_container_width=True,
    disabled=selected_menu_input is None,
)

if compile_clicked and selected_menu_input:
    try:
        with st.spinner(
            "Validating menu and generating outputs..."
        ):
            compile_selected_menu(
                menu=selected_menu_input["menu"],
                menu_identifier=selected_menu_input[
                    "identifier"
                ],
                menu_source=selected_menu_input[
                    "source"
                ],
                rounding_places=int(rounding_places),
            )

    except (
        RepositoryError,
        ValueError,
        KeyError,
    ) as exc:
        st.error(str(exc))

    except Exception as exc:
        st.error(
            "An unexpected error occurred while compiling "
            "the menu."
        )

        with st.expander("Technical details"):
            st.exception(exc)


# ----------------------------------------------------------------------
# Standalone validation failure
# ----------------------------------------------------------------------


standalone_validation = st.session_state.get(
    "validation_issues"
)

if standalone_validation:
    st.divider()
    st.subheader("Validation")
    display_validation_issues(
        standalone_validation
    )


# ----------------------------------------------------------------------
# Compilation results
# ----------------------------------------------------------------------


compilation = st.session_state.get("compilation")

if compilation:
    result = compilation["result"]
    markdown = compilation["markdown"]
    pdf = compilation["pdf"]
    menu = compilation["menu"]

    compiled_rounding = compilation[
        "rounding_places"
    ]

    validation_issues = compilation[
        "validation_issues"
    ]

    st.divider()

    st.subheader(
        menu.get(
            "name",
            compilation["menu_name"],
        )
    )

    st.caption(
        f"Menu source: {compilation['menu_source']}"
    )

    if menu.get("description"):
        st.write(menu["description"])

    if menu.get("notes"):
        st.info(menu["notes"])

    metric_1, metric_2, metric_3 = st.columns(3)

    metric_1.metric(
        "Scheduled dishes",
        count_scheduled_dishes(result),
    )

    metric_2.metric(
        "Shopping items",
        len(result.shopping_list),
    )

    metric_3.metric(
        "Validation warnings",
        count_validation_warnings(
            validation_issues
        ),
    )

    (
        shopping_tab,
        recipes_tab,
        validation_tab,
    ) = st.tabs(
        [
            "Shopping list",
            "Scaled recipes",
            "Validation",
        ]
    )


    # ------------------------------------------------------------------
    # Shopping list
    # ------------------------------------------------------------------

    with shopping_tab:
        st.markdown(markdown)

        st.divider()

        st.markdown("### Downloads")

        download_column_1, download_column_2 = (
            st.columns(2)
        )

        with download_column_1:
            st.download_button(
                label="Download shopping list",
                data=markdown,
                file_name=(
                    f"{compilation['menu_name']}"
                    "_shopping_list.md"
                ),
                mime="text/markdown",
                use_container_width=True,
            )

        with download_column_2:
            st.download_button(
                label="Download complete weekend PDF",
                data=pdf,
                file_name=(
                    f"{compilation['menu_name']}"
                    "_menu_pack.pdf"
                ),
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )


    # ------------------------------------------------------------------
    # Scaled recipes
    # ------------------------------------------------------------------

    with recipes_tab:
        general_provisions = [
            recipe
            for recipe in result.scaled_recipes
            if recipe.meal == "provisions"
        ]

        scheduled_recipes = [
            recipe
            for recipe in result.scaled_recipes
            if recipe.meal != "provisions"
        ]

        if general_provisions:
            st.markdown("### General provisions")

            st.caption(
                "These recipes support the wider catering "
                "arrangements rather than one scheduled meal."
            )

            for recipe in general_provisions:
                render_scaled_recipe_preview(
                    recipe,
                    compiled_rounding,
                )

            st.divider()

        st.markdown("### Scheduled dishes")

        if not scheduled_recipes:
            st.info(
                "This menu contains no scheduled dishes."
            )

        for recipe in scheduled_recipes:
            render_scaled_recipe_preview(
                recipe,
                compiled_rounding,
            )


    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    with validation_tab:
        display_validation_issues(
            validation_issues
        )

        if not any(
            issue.severity == Severity.ERROR
            for issue in validation_issues
        ):
            st.markdown(
                "The menu was compiled successfully. "
                "Warnings should be reviewed before using "
                "the generated catering documents."
            )