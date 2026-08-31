from tokenize import TokenError

from pint import UnitRegistry
from pint.errors import PintError

from mass_catering.repository import UNIT_REGISTRY_FILE


ureg = UnitRegistry()
ureg.load_definitions(str(UNIT_REGISTRY_FILE))


class QuantityError(ValueError):
    """Raised when a quantity cannot be interpreted."""


def parse_quantity(
    value: str | int | float,
    ingredient_name: str | None = None,
):
    """
    Convert an ingredient amount into a Pint quantity.

    String values such as ``500 g`` are parsed normally.

    Bare numeric values use an ingredient-specific conversion when
    one is defined in the unit registry. The result is converted to
    base units so that individual items become an explicit mass for
    shopping-list aggregation.

    If no ingredient-specific conversion exists, the value is
    retained as a dimensionless item count.
    """

    if isinstance(value, bool):
        raise QuantityError(
            f"Invalid Boolean quantity for "
            f"{ingredient_name or 'item'}."
        )

    if isinstance(value, (int, float)):
        if ingredient_name:
            try:
                ingredient_unit = ureg.Unit(ingredient_name)
                ingredient_quantity = value * ingredient_unit

                return ingredient_quantity.to_base_units()

            except Exception:
                # The ingredient has no registered conversion.
                pass

        return value * ureg.quantity

    if not isinstance(value, str):
        raise QuantityError(
            f"Quantity for {ingredient_name or 'item'} must be "
            f"text or a number, not {type(value).__name__}."
        )

    value = value.strip()

    if not value:
        raise QuantityError(
            f"Quantity for {ingredient_name or 'item'} is empty."
        )

    try:
        return ureg(value)

    except (
        PintError,
        TokenError,
        TypeError,
        ValueError,
        SyntaxError,
    ) as exc:
        message = f"Could not parse quantity {value!r}"

        if ingredient_name:
            message += f" for ingredient {ingredient_name!r}"

        raise QuantityError(message) from exc