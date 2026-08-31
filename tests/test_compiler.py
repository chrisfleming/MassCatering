from mass_catering.compiler import compile_menu


def test_recipe_is_scaled_to_people():
    menu = {
        "soup": {
            "Monday lunch": 20,
        }
    }

    recipes = {
        "soup": {
            "name": "Soup",
            "serves": 10,
            "ingredients": {
                "potato": "1 kg",
                "water": "2 litre",
            },
        }
    }

    result = compile_menu(
        menu=menu,
        recipes=recipes,
    )

    assert len(result.scaled_recipes) == 1

    scaled_recipe = result.scaled_recipes[0]

    assert scaled_recipe.people == 20
    assert (
        scaled_recipe.ingredients["potato"]
        .to("kg")
        .magnitude
        == 2
    )
    assert (
        scaled_recipe.ingredients["water"]
        .to("litre")
        .magnitude
        == 4
    )


def test_repeated_ingredient_is_aggregated():
    menu = {
        "soup": {
            "Monday": 10,
            "Tuesday": 20,
        }
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

    result = compile_menu(
        menu=menu,
        recipes=recipes,
    )

    total = result.shopping_list["potato"].to("kg")

    assert total.magnitude == 3