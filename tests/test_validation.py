import pytest

from mass_catering.validation import (
    IngredientNameMatch,
    Severity,
    ValidationIssue,
    collect_menu_ingredient_names,
    find_similar_ingredient_names,
    is_likely_distinct_compound,
    normalise_ingredient_name,
    singularise_word,
    validate_ingredient_names,
    validate_menu,
)


# ----------------------------------------------------------------------
# Test fixtures and helpers
# ----------------------------------------------------------------------


@pytest.fixture
def valid_menu():
    """Return a minimal valid version 2 menu."""

    return {
        "schema_version": 2,
        "name": "Test Weekend",
        "events": [
            {
                "day": "Saturday",
                "meal": "dinner",
                "name": "Soup night",
                "people": 20,
                "dishes": [
                    {
                        "recipe": "vegetable_soup",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def available_recipes():
    """Return recipe identifiers available to menu validation."""

    return {
        "vegetable_soup",
        "fruit_salad",
        "coconut_curry",
    }


def errors_from(issues):
    """Return only validation errors."""

    return [
        issue
        for issue in issues
        if issue.severity == Severity.ERROR
    ]


def warnings_from(issues):
    """Return only validation warnings."""

    return [
        issue
        for issue in issues
        if issue.severity == Severity.WARNING
    ]


# ----------------------------------------------------------------------
# Validation model tests
# ----------------------------------------------------------------------


def test_validation_issue_is_created():
    issue = ValidationIssue(
        severity=Severity.WARNING,
        location="events[0].meal",
        message="Meal type is unspecified.",
    )

    assert issue.severity == Severity.WARNING
    assert issue.location == "events[0].meal"
    assert issue.message == "Meal type is unspecified."


def test_ingredient_name_match_is_created():
    match = IngredientNameMatch(
        first="banana",
        second="bananas",
        score=100.0,
        reason="Names match after normalisation.",
    )

    assert match.first == "banana"
    assert match.second == "bananas"
    assert match.score == 100.0
    assert match.reason == "Names match after normalisation."


# ----------------------------------------------------------------------
# Singularisation tests
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("banana", "banana"),
        ("bananas", "banana"),
        ("berries", "berry"),
        ("boxes", "box"),
        ("dishes", "dish"),
        ("peaches", "peach"),
        ("classes", "class"),
        ("glass", "glass"),
        ("couscous", "couscous"),
        ("oil", "oil"),
    ],
)
def test_singularise_word(original, expected):
    assert singularise_word(original) == expected


# ----------------------------------------------------------------------
# Ingredient normalisation tests
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("banana", "banana"),
        ("Banana", "banana"),
        ("BANANAS", "banana"),
        ("olive_oil", "olive oil"),
        ("olive-oil", "olive oil"),
        ("  olive   oil  ", "olive oil"),
        ("Red_Onions", "red onion"),
        ("red-onions", "red onion"),
        ("Apple's", "apple"),
    ],
)
def test_normalise_ingredient_name(original, expected):
    assert normalise_ingredient_name(original) == expected


def test_plural_and_singular_normalise_identically():
    assert (
        normalise_ingredient_name("bananas")
        == normalise_ingredient_name("banana")
    )


def test_underscore_and_spaces_normalise_identically():
    assert (
        normalise_ingredient_name("olive_oil")
        == normalise_ingredient_name("olive oil")
    )


def test_hyphens_and_spaces_normalise_identically():
    assert (
        normalise_ingredient_name("sweet-potato")
        == normalise_ingredient_name("sweet potato")
    )


def test_normalisation_is_case_insensitive():
    assert (
        normalise_ingredient_name("Red Onion")
        == normalise_ingredient_name("red onion")
    )


# ----------------------------------------------------------------------
# Compound ingredient tests
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("milk", "coconut milk"),
        ("cream", "sour cream"),
        ("onion", "spring onion"),
        ("oil", "olive oil"),
        ("rice", "brown rice"),
    ],
)
def test_distinct_compound_ingredient_is_detected(
    first,
    second,
):
    assert is_likely_distinct_compound(
        first,
        second,
    )


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("banana", "bananas"),
        ("coriander", "corriander"),
        ("olive oil", "olive oils"),
        ("red onion", "red onions"),
    ],
)
def test_similar_names_are_not_treated_as_compounds(
    first,
    second,
):
    first_normalised = normalise_ingredient_name(first)
    second_normalised = normalise_ingredient_name(second)

    assert not is_likely_distinct_compound(
        first_normalised,
        second_normalised,
    )


# ----------------------------------------------------------------------
# Similar ingredient detection tests
# ----------------------------------------------------------------------


def test_plural_duplicate_is_detected():
    matches = find_similar_ingredient_names(
        {
            "banana",
            "bananas",
        }
    )

    assert len(matches) == 1

    match = matches[0]

    assert {match.first, match.second} == {
        "banana",
        "bananas",
    }

    assert match.score == 100.0
    assert "identical" in match.reason.casefold()


def test_underscore_duplicate_is_detected():
    matches = find_similar_ingredient_names(
        {
            "olive_oil",
            "olive oil",
        }
    )

    assert len(matches) == 1
    assert matches[0].score == 100.0


def test_hyphen_duplicate_is_detected():
    matches = find_similar_ingredient_names(
        {
            "sweet-potato",
            "sweet potato",
        }
    )

    assert len(matches) == 1
    assert matches[0].score == 100.0


def test_case_duplicate_is_detected():
    matches = find_similar_ingredient_names(
        {
            "Banana",
            "banana",
        }
    )

    assert len(matches) == 1
    assert matches[0].score == 100.0


def test_likely_typo_is_detected():
    matches = find_similar_ingredient_names(
        {
            "coriander",
            "corriander",
        },
        fuzzy_threshold=90.0,
    )

    assert len(matches) == 1
    assert matches[0].score >= 90.0
    assert "similarity" in matches[0].reason.casefold()


def test_similarity_below_threshold_is_not_detected():
    matches = find_similar_ingredient_names(
        {
            "coriander",
            "cinnamon",
        },
        fuzzy_threshold=92.0,
    )

    assert matches == []


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("milk", "coconut_milk"),
        ("cream", "sour_cream"),
        ("onion", "spring_onion"),
        ("oil", "olive_oil"),
    ],
)
def test_compound_ingredients_are_not_flagged(
    first,
    second,
):
    matches = find_similar_ingredient_names(
        {
            first,
            second,
        }
    )

    assert matches == []


def test_empty_ingredient_names_are_ignored():
    matches = find_similar_ingredient_names(
        {
            "",
            "   ",
            "banana",
        }
    )

    assert matches == []


def test_each_pair_is_reported_only_once():
    matches = find_similar_ingredient_names(
        {
            "banana",
            "bananas",
        }
    )

    assert len(matches) == 1


def test_multiple_duplicate_pairs_are_detected():
    matches = find_similar_ingredient_names(
        {
            "banana",
            "bananas",
            "olive_oil",
            "olive oil",
        }
    )

    matched_pairs = {
        frozenset(
            {
                match.first,
                match.second,
            }
        )
        for match in matches
    }

    assert frozenset(
        {
            "banana",
            "bananas",
        }
    ) in matched_pairs

    assert frozenset(
        {
            "olive_oil",
            "olive oil",
        }
    ) in matched_pairs


# ----------------------------------------------------------------------
# Menu ingredient collection tests
# ----------------------------------------------------------------------


def test_collects_ingredients_from_recipes():
    menu = {
        "schema_version": 2,
        "name": "Test",
        "events": [],
    }

    recipes = {
        "fruit_salad": {
            "name": "Fruit salad",
            "ingredients": {
                "banana": 4,
                "apple": 6,
            },
        },
        "soup": {
            "name": "Soup",
            "ingredients": {
                "potato": "1 kg",
            },
        },
    }

    names = collect_menu_ingredient_names(
        menu,
        recipes,
    )

    assert names == {
        "banana",
        "apple",
        "potato",
    }


def test_collects_additional_item_ingredients():
    menu = {
        "schema_version": 2,
        "name": "Test",
        "events": [],
        "additional_items": [
            {
                "ingredient": "coffee",
                "quantity": "500 g",
            },
            {
                "ingredient": "milk",
                "quantity": "2 l",
            },
        ],
    }

    names = collect_menu_ingredient_names(
        menu,
        recipes={},
    )

    assert names == {
        "coffee",
        "milk",
    }


def test_collects_recipe_and_additional_item_ingredients():
    menu = {
        "schema_version": 2,
        "name": "Test",
        "events": [],
        "additional_items": [
            {
                "ingredient": "bananas",
                "quantity": 2,
            }
        ],
    }

    recipes = {
        "fruit_salad": {
            "name": "Fruit salad",
            "ingredients": {
                "banana": 4,
                "apple": 6,
            },
        }
    }

    names = collect_menu_ingredient_names(
        menu,
        recipes,
    )

    assert names == {
        "banana",
        "bananas",
        "apple",
    }


def test_invalid_recipe_ingredients_are_ignored():
    menu = {
        "schema_version": 2,
        "name": "Test",
        "events": [],
    }

    recipes = {
        "invalid_recipe": {
            "name": "Invalid recipe",
            "ingredients": None,
        }
    }

    names = collect_menu_ingredient_names(
        menu,
        recipes,
    )

    assert names == set()


def test_invalid_additional_items_are_ignored():
    menu = {
        "schema_version": 2,
        "name": "Test",
        "events": [],
        "additional_items": [
            None,
            "coffee",
            {},
        ],
    }

    names = collect_menu_ingredient_names(
        menu,
        recipes={},
    )

    assert names == set()


# ----------------------------------------------------------------------
# Ingredient validation tests
# ----------------------------------------------------------------------


def test_similar_recipe_ingredients_produce_warning():
    menu = {
        "schema_version": 2,
        "name": "Duplicate ingredient test",
        "events": [],
    }

    recipes = {
        "recipe_one": {
            "name": "Recipe one",
            "ingredients": {
                "banana": 2,
            },
        },
        "recipe_two": {
            "name": "Recipe two",
            "ingredients": {
                "bananas": 4,
            },
        },
    }

    issues = validate_ingredient_names(
        menu=menu,
        recipes=recipes,
    )

    assert len(issues) == 1

    issue = issues[0]

    assert issue.severity == Severity.WARNING
    assert issue.location == "ingredients"
    assert "'banana'" in issue.message
    assert "'bananas'" in issue.message
    assert "100%" in issue.message


def test_recipe_and_additional_item_duplicate_produces_warning():
    menu = {
        "schema_version": 2,
        "name": "Duplicate ingredient test",
        "events": [],
        "additional_items": [
            {
                "ingredient": "bananas",
                "quantity": 4,
            }
        ],
    }

    recipes = {
        "fruit_salad": {
            "name": "Fruit salad",
            "ingredients": {
                "banana": 2,
            },
        }
    }

    issues = validate_ingredient_names(
        menu=menu,
        recipes=recipes,
    )

    assert any(
        issue.severity == Severity.WARNING
        and "banana" in issue.message
        and "bananas" in issue.message
        for issue in issues
    )


def test_no_duplicate_ingredients_produces_no_issues():
    menu = {
        "schema_version": 2,
        "name": "Clean menu",
        "events": [],
    }

    recipes = {
        "fruit_salad": {
            "name": "Fruit salad",
            "ingredients": {
                "banana": 2,
                "apple": 4,
            },
        }
    }

    issues = validate_ingredient_names(
        menu=menu,
        recipes=recipes,
    )

    assert issues == []


def test_compound_ingredients_do_not_produce_warning():
    menu = {
        "schema_version": 2,
        "name": "Compound ingredients",
        "events": [],
    }

    recipes = {
        "curry": {
            "name": "Curry",
            "ingredients": {
                "milk": "1 l",
                "coconut_milk": "1 l",
            },
        }
    }

    issues = validate_ingredient_names(
        menu=menu,
        recipes=recipes,
    )

    assert issues == []


def test_custom_fuzzy_threshold_is_respected():
    menu = {
        "schema_version": 2,
        "name": "Threshold test",
        "events": [],
    }

    recipes = {
        "recipe": {
            "name": "Recipe",
            "ingredients": {
                "coriander": "10 g",
                "corriander": "10 g",
            },
        }
    }

    strict_issues = validate_ingredient_names(
        menu=menu,
        recipes=recipes,
        fuzzy_threshold=100.0,
    )

    relaxed_issues = validate_ingredient_names(
        menu=menu,
        recipes=recipes,
        fuzzy_threshold=90.0,
    )

    assert strict_issues == []
    assert len(relaxed_issues) == 1


# ----------------------------------------------------------------------
# Valid menu tests
# ----------------------------------------------------------------------


def test_valid_menu_has_no_issues(
    valid_menu,
    available_recipes,
):
    issues = validate_menu(
        valid_menu,
        available_recipes,
    )

    assert issues == []


def test_empty_events_list_is_accepted():
    menu = {
        "schema_version": 2,
        "name": "Shopping-only menu",
        "events": [],
    }

    issues = validate_menu(
        menu,
        available_recipes=set(),
    )

    assert issues == []


def test_optional_event_name_is_not_required(
    available_recipes,
):
    menu = {
        "schema_version": 2,
        "name": "Test",
        "events": [
            {
                "day": "Saturday",
                "meal": "dinner",
                "people": 10,
                "dishes": [
                    {
                        "recipe": "vegetable_soup",
                    }
                ],
            }
        ],
    }

    issues = validate_menu(
        menu,
        available_recipes,
    )

    assert issues == []


# ----------------------------------------------------------------------
# Top-level menu validation tests
# ----------------------------------------------------------------------


def test_non_mapping_menu_is_rejected():
    issues = validate_menu(
        ["not", "a", "mapping"],
        available_recipes=set(),
    )

    assert len(issues) == 1
    assert issues[0].severity == Severity.ERROR
    assert issues[0].location == "menu"


@pytest.mark.parametrize(
    "schema_version",
    [
        None,
        1,
        "2",
        3,
    ],
)
def test_invalid_schema_version_is_rejected(
    schema_version,
):
    menu = {
        "schema_version": schema_version,
        "name": "Test",
        "events": [],
    }

    issues = validate_menu(
        menu,
        available_recipes=set(),
    )

    assert any(
        issue.severity == Severity.ERROR
        and issue.location == "schema_version"
        for issue in issues
    )


@pytest.mark.parametrize(
    "name",
    [
        None,
        "",
        "   ",
        42,
        [],
    ],
)
def test_invalid_menu_name_is_rejected(name):
    menu = {
        "schema_version": 2,
        "name": name,
        "events": [],
    }

    issues = validate_menu(
        menu,
        available_recipes=set(),
    )

    assert any(
        issue.severity == Severity.ERROR
        and issue.location == "name"
        for issue in issues
    )


@pytest.mark.parametrize(
    "events",
    [
        None,
        {},
        "events",
        42,
    ],
)
def test_non_list_events_are_rejected(events):
    menu = {
        "schema_version": 2,
        "name": "Test",
        "events": events,
    }

    issues = validate_menu(
        menu,
        available_recipes=set(),
    )

    assert any(
        issue.severity == Severity.ERROR
        and issue.location == "events"
        for issue in issues
    )


# ----------------------------------------------------------------------
# Event validation tests
# ----------------------------------------------------------------------


def test_non_mapping_event_is_rejected():
    menu = {
        "schema_version": 2,
        "name": "Test",
        "events": [
            "Saturday dinner",
        ],
    }

    issues = validate_menu(
        menu,
        available_recipes=set(),
    )

    assert any(
        issue.severity == Severity.ERROR
        and issue.location == "events[0]"
        for issue in issues
    )


@pytest.mark.parametrize(
    "day",
    [
        None,
        "",
        "   ",
        42,
        [],
    ],
)
def test_invalid_event_day_is_rejected(
    valid_menu,
    available_recipes,
    day,
):
    valid_menu["events"][0]["day"] = day

    issues = validate_menu(
        valid_menu,
        available_recipes,
    )

    assert any(
        issue.severity == Severity.ERROR
        and issue.location == "events[0].day"
        for issue in issues
    )


@pytest.mark.parametrize(
    "meal",
    [
        None,
        "",
        "   ",
        42,
        [],
    ],
)
def test_invalid_meal_is_rejected(
    valid_menu,
    available_recipes,
    meal,
):
    valid_menu["events"][0]["meal"] = meal

    issues = validate_menu(
        valid_menu,
        available_recipes,
    )

    assert any(
        issue.severity == Severity.ERROR
        and issue.location == "events[0].meal"
        for issue in issues
    )


def test_unspecified_meal_produces_warning(
    valid_menu,
    available_recipes,
):
    valid_menu["events"][0]["meal"] = "unspecified"

    issues = validate_menu(
        valid_menu,
        available_recipes,
    )

    assert any(
        issue.severity == Severity.WARNING
        and issue.location == "events[0].meal"
        and "unspecified" in issue.message.casefold()
        for issue in issues
    )

    assert errors_from(issues) == []


def test_unspecified_meal_check_is_case_insensitive(
    valid_menu,
    available_recipes,
):
    valid_menu["events"][0]["meal"] = "Unspecified"

    issues = validate_menu(
        valid_menu,
        available_recipes,
    )

    assert any(
        issue.severity == Severity.WARNING
        and issue.location == "events[0].meal"
        for issue in issues
    )


@pytest.mark.parametrize(
    "people",
    [
        None,
        0,
        -1,
        1.5,
        "20",
        [],
    ],
)
def test_invalid_event_people_is_rejected(
    valid_menu,
    available_recipes,
    people,
):
    valid_menu["events"][0]["people"] = people

    issues = validate_menu(
        valid_menu,
        available_recipes,
    )

    assert any(
        issue.severity == Severity.ERROR
        and issue.location == "events[0].people"
        for issue in issues
    )


@pytest.mark.parametrize(
    "dishes",
    [
        None,
        {},
        "vegetable_soup",
        42,
    ],
)
def test_non_list_dishes_are_rejected(
    valid_menu,
    available_recipes,
    dishes,
):
    valid_menu["events"][0]["dishes"] = dishes

    issues = validate_menu(
        valid_menu,
        available_recipes,
    )

    assert any(
        issue.severity == Severity.ERROR
        and issue.location == "events[0].dishes"
        for issue in issues
    )


def test_empty_dishes_list_is_accepted(
    valid_menu,
    available_recipes,
):
    valid_menu["events"][0]["dishes"] = []

    issues = validate_menu(
        valid_menu,
        available_recipes,
    )

    assert issues == []


# ----------------------------------------------------------------------
# Dish validation tests
# ----------------------------------------------------------------------


def test_non_mapping_dish_is_rejected(
    valid_menu,
    available_recipes,
):
    valid_menu["events"][0]["dishes"] = [
        "vegetable_soup"
    ]

    issues = validate_menu(
        valid_menu,
        available_recipes,
    )

    assert any(
        issue.severity == Severity.ERROR
        and issue.location == "events[0].dishes[0]"
        for issue in issues
    )


@pytest.mark.parametrize(
    "recipe_name",
    [
        None,
        "",
        "   ",
        42,
        [],
    ],
)
def test_invalid_recipe_identifier_is_rejected(
    valid_menu,
    available_recipes,
    recipe_name,
):
    valid_menu["events"][0]["dishes"][0][
        "recipe"
    ] = recipe_name

    issues = validate_menu(
        valid_menu,
        available_recipes,
    )

    assert any(
        issue.severity == Severity.ERROR
        and (
            issue.location
            == "events[0].dishes[0].recipe"
        )
        for issue in issues
    )


def test_missing_recipe_is_rejected(
    valid_menu,
    available_recipes,
):
    valid_menu["events"][0]["dishes"][0][
        "recipe"
    ] = "missing_recipe"

    issues = validate_menu(
        valid_menu,
        available_recipes,
    )

    matching_issues = [
        issue
        for issue in issues
        if (
            issue.severity == Severity.ERROR
            and issue.location
            == "events[0].dishes[0].recipe"
        )
    ]

    assert len(matching_issues) == 1
    assert "missing_recipe" in matching_issues[0].message


def test_nested_recipe_identifier_is_accepted():
    menu = {
        "schema_version": 2,
        "name": "Nested recipe test",
        "events": [
            {
                "day": "Sunday",
                "meal": "dinner",
                "people": 20,
                "dishes": [
                    {
                        "recipe": (
                            "carribean_curry/"
                            "rice_and_peas"
                        ),
                    }
                ],
            }
        ],
    }

    issues = validate_menu(
        menu,
        available_recipes={
            "carribean_curry/rice_and_peas"
        },
    )

    assert issues == []


def test_all_dishes_are_checked():
    menu = {
        "schema_version": 2,
        "name": "Multiple dishes",
        "events": [
            {
                "day": "Sunday",
                "meal": "dinner",
                "people": 20,
                "dishes": [
                    {
                        "recipe": "vegetable_soup",
                    },
                    {
                        "recipe": "missing_recipe_one",
                    },
                    {
                        "recipe": "missing_recipe_two",
                    },
                ],
            }
        ],
    }

    issues = validate_menu(
        menu,
        available_recipes={
            "vegetable_soup",
        },
    )

    missing_recipe_errors = [
        issue
        for issue in issues
        if (
            issue.severity == Severity.ERROR
            and issue.location.endswith(".recipe")
        )
    ]

    assert len(missing_recipe_errors) == 2


# ----------------------------------------------------------------------
# Multiple validation issue tests
# ----------------------------------------------------------------------


def test_menu_can_report_multiple_errors():
    menu = {
        "schema_version": 1,
        "name": "",
        "events": [
            {
                "day": "",
                "meal": "",
                "people": 0,
                "dishes": [
                    {
                        "recipe": "missing_recipe",
                    }
                ],
            }
        ],
    }

    issues = validate_menu(
        menu,
        available_recipes=set(),
    )

    assert len(errors_from(issues)) >= 6


def test_warning_does_not_create_validation_error(
    valid_menu,
    available_recipes,
):
    valid_menu["events"][0]["meal"] = "unspecified"

    issues = validate_menu(
        valid_menu,
        available_recipes,
    )

    assert len(warnings_from(issues)) == 1
    assert errors_from(issues) == []