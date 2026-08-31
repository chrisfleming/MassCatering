from mass_catering.rendering import format_quantity
from mass_catering.units import parse_quantity


def test_count_is_formatted_without_unit_symbol():
    quantity = parse_quantity(
        2,
        "marshmallow",
    )

    assert format_quantity(quantity) == "2"


def test_mass_is_formatted_with_unit():
    quantity = parse_quantity(
        14,
        "potato",
    )

    assert format_quantity(quantity) == "2.1 kg"