from mass_catering.compiler import compile_menu


def test_event_default_people_are_used():
    menu = {
        "schema_version": 2,
        "name": "Test menu",
        "events": [
            {
                "day": "Saturday",
                "meal": "dinner",
                "people": 20,
                "dishes": [
                    {
                        "recipe": "soup",
                    }
                ],
            }
        ],
    }

    recipes = {
        "soup": {
            "name": "Soup",
            "serves": 10,
            "ingredients": {
                "potato": "1 kg",
            },
        }
    }

    result = compile_menu(menu, recipes)

    quantity = result.shopping_list[
        "potato"
    ].to("kg")

    assert quantity.magnitude == 2
    assert result.scaled_recipes[0].people == 20


def test_dish_people_override_event_default():
    menu = {
        "schema_version": 2,
        "name": "Test menu",
        "events": [
            {
                "day": "Saturday",
                "meal": "dinner",
                "people": 20,
                "dishes": [
                    {
                        "recipe": "vegan_soup",
                        "people": 4,
                    }
                ],
            }
        ],
    }

    recipes = {
        "vegan_soup": {
            "name": "Vegan soup",
            "serves": 2,
            "ingredients": {
                "potato": "500 g",
            },
        }
    }

    result = compile_menu(menu, recipes)

    quantity = result.shopping_list[
        "potato"
    ].to("kg")

    assert quantity.magnitude == 1
    assert result.scaled_recipes[0].people == 4


def test_dish_preparation_notes_are_preserved():
    menu = {
        "schema_version": 2,
        "name": "Test menu",
        "events": [
            {
                "day": "Monday",
                "meal": "dinner",
                "people": 10,
                "dishes": [
                    {
                        "recipe": "wellington",
                        "notes": (
                            "Prepare separately from the meat."
                        ),
                    }
                ],
            }
        ],
    }

    recipes = {
        "wellington": {
            "name": "Wellington",
            "serves": 10,
            "ingredients": {
                "mushroom": "1 kg",
            },
        }
    }

    result = compile_menu(menu, recipes)

    assert (
        result.scaled_recipes[0].preparation_notes
        == "Prepare separately from the meat."
    )


def test_additional_item_is_included():
    menu = {
        "schema_version": 2,
        "name": "Test menu",
        "events": [],
        "additional_items": [
            {
                "ingredient": "coffee",
                "quantity": "2 kg",
            }
        ],
    }

    result = compile_menu(menu, recipes={})

    quantity = result.shopping_list[
        "coffee"
    ].to("kg")

    assert quantity.magnitude == 2