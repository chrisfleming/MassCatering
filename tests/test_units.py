import pytest

from mass_catering.units import parse_quantity


def test_potato_count_is_converted_to_mass():
    quantity = parse_quantity(
        14,
        "potato",
    )

    assert quantity.to("kg").magnitude == pytest.approx(
        2.1
    )


def test_banana_count_is_converted_to_mass():
    quantity = parse_quantity(
        6,
        "banana",
    )

    assert quantity.to("kg").magnitude == pytest.approx(
        1.098
    )


def test_unknown_item_remains_a_count():
    quantity = parse_quantity(
        2,
        "marshmallow",
    )

    assert quantity.magnitude == 2
    assert str(quantity.units) == "quantity"


def test_item_name_beginning_with_number_remains_a_count():
    quantity = parse_quantity(
        1,
        "50_50_bread",
    )

    assert quantity.magnitude == 1
    assert str(quantity.units) == "quantity"

def test_potato_count_combines_with_explicit_mass():
    total = (
        parse_quantity(14, "potato")
        + parse_quantity("6400 g", "potato")
    )

    assert total.to("kg").magnitude == pytest.approx(
        8.5
    )