from mass_catering.repository import (
    list_menu_names,
    list_recipe_names,
    load_menu,
    load_recipe,
)


def test_repository_contains_recipes():
    assert list_recipe_names()


def test_repository_contains_menus():
    assert list_menu_names()


def test_all_recipe_files_load():
    for recipe_name in list_recipe_names():
        recipe = load_recipe(recipe_name)
        assert isinstance(recipe, dict)


def test_all_menu_files_load():
    for menu_name in list_menu_names():
        menu = load_menu(menu_name)
        assert isinstance(menu, dict)