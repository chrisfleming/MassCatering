from mass_catering.compiler import compile_menu
from mass_catering.pdf import generate_menu_pdf


def test_complete_menu_pdf_is_generated():
    menu = {
        "schema_version": 2,
        "name": "Test Weekend",
        "description": "A test catering weekend.",
        "events": [
            {
                "day": "Saturday",
                "meal": "dinner",
                "name": "Soup night",
                "people": 10,
                "notes": "Serve at 18:00.",
                "dishes": [
                    {
                        "recipe": "soup",
                        "notes": "Keep one portion separate.",
                    }
                ],
            }
        ],
        "additional_items": [
            {
                "ingredient": "coffee",
                "quantity": "500 g",
            }
        ],
    }

    recipes = {
        "soup": {
            "name": "Vegetable soup",
            "serves": 5,
            "ingredients": {
                "potato": "1 kg",
                "water": "2 l",
            },
            "method": "Cook until the vegetables are tender.",
            "notes": "Can be made one day in advance.",
        }
    }

    result = compile_menu(
        menu=menu,
        recipes=recipes,
    )

    pdf = generate_menu_pdf(
        menu=menu,
        result=result,
        food_catalogue={},
        rounding_places=2,
    )

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_pdf_preserves_dish_preparation_notes():
    menu = {
        "schema_version": 2,
        "name": "Chef Notes Test",
        "events": [
            {
                "day": "Monday",
                "meal": "dinner",
                "people": 4,
                "dishes": [
                    {
                        "recipe": "wellington",
                        "notes": "Prepare separately from the meat.",
                    }
                ],
            }
        ],
    }

    recipes = {
        "wellington": {
            "name": "Vegan Wellington",
            "serves": 4,
            "ingredients": {
                "mushroom": "500 g",
            },
            "method": "Bake until golden.",
        }
    }

    result = compile_menu(
        menu=menu,
        recipes=recipes,
    )

    assert (
        result.scaled_recipes[0].preparation_notes
        == "Prepare separately from the meat."
    )

    pdf = generate_menu_pdf(
        menu=menu,
        result=result,
        food_catalogue={},
    )

    assert pdf.startswith(b"%PDF")