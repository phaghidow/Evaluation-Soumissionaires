from decimal import Decimal, InvalidOperation
import math


def is_digit_string(value):
    text = str(value)
    return bool(text) and text.isdigit()


def parse_integer(value, minimum=None, maximum=None):
    if not is_digit_string(value):
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    if minimum is not None and parsed < minimum:
        return None
    if maximum is not None and parsed > maximum:
        return None
    return parsed


def parse_integer_tokens(value):
    parsed_values = []
    for token in str(value).split():
        parsed = parse_integer(token)
        if parsed is not None:
            parsed_values.append(parsed)
    return parsed_values


def get_lot_delay_requirements(lot_number):
    lot = int(lot_number)
    if lot in {1, 2, 4, 5, 7, 9, 10}:
        return {
            "execution_min": 60,
            "execution_max": 120,
            "garantie_min": 12,
        }
    if lot in {3, 6, 8, 11}:
        return {
            "execution_min": 45,
            "execution_max": 90,
            "garantie_min": 12,
        }
    raise ValueError("Le numéro de lot doit être compris entre 1 et 11.")


def validate_lot_delay_inputs(lot_number, delai_execution, delai_garantie):
    requirements = get_lot_delay_requirements(lot_number)
    execution = parse_integer(
        str(delai_execution),
        minimum=requirements["execution_min"],
        maximum=requirements["execution_max"],
    )
    garantie = parse_integer(
        str(delai_garantie),
        minimum=requirements["garantie_min"],
    )
    if execution is None or garantie is None:
        return None
    return execution, garantie


def parse_amount(value, maximum_decimal_places=None):
    normalized = str(value).strip().replace(" ", "").replace(",", ".")
    if not normalized:
        return None
    try:
        decimal_value = Decimal(normalized)
        if not decimal_value.is_finite() or decimal_value < 0:
            return None
        if maximum_decimal_places is not None:
            quantum = Decimal(1).scaleb(-maximum_decimal_places)
            if decimal_value.quantize(quantum) != decimal_value:
                return None
        parsed = float(decimal_value)
    except (InvalidOperation, OverflowError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None