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
    Convert a recipe value into a Pint quantity.

    Numeric values follow the original application's behaviour:
    try the ingredient name as a custom unit, then fall back to
    the custom dimensionless 'quantity' unit.
    """

    try:
        if isinstance(value, (int, float)):
            if ingredient_name:
                try:
                    return ureg(
                        f"{value} {ingredient_name}"
                    )
                except (PintError, TypeError, ValueError):
                    pass

            return ureg(f"{value} quantity")

        return ureg(str(value))

    except (PintError, TypeError, ValueError) as exc:
        message = f"Could not parse quantity {value!r}"

        if ingredient_name:
            message += (
                f" for ingredient {ingredient_name!r}"
            )

        raise QuantityError(message) from exc