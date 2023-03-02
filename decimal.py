from decimal import Decimal, ROUND_UP, ROUND_DOWN, localcontext


def dec_round(value: Decimal, decimal_places: int, rounding: str | None = None) -> Decimal:
    if decimal_places < 0:
        raise ValueError(f'incorrect rounding {decimal_places}, must be non negative')
    return value.quantize(Decimal(f'0.{"0"*decimal_places}'), rounding=rounding)


def dec_round_up(value: Decimal, decimal_places: int) -> Decimal:
    return dec_round(value, decimal_places, rounding=ROUND_UP)


def dec_round_down(value: Decimal, decimal_places: int) -> Decimal:
    return dec_round(value, decimal_places, rounding=ROUND_DOWN)


def dec_div_round(a: Decimal, b: Decimal, decimal_places: int, rounding: str | None) -> Decimal:
    with localcontext() as ctx:
        ctx.rounding = rounding
        value = a / b
        return dec_round(value, decimal_places, rounding)


def dec_div_round_up(a: Decimal, b: Decimal, decimal_places: int) -> Decimal:
    with localcontext() as ctx:
        ctx.rounding = ROUND_UP
        value = a / b
        return dec_round_up(value, decimal_places)


def dec_div_round_down(a: Decimal, b: Decimal, decimal_places: int) -> Decimal:
    with localcontext() as ctx:
        ctx.rounding = ROUND_DOWN
        value = a / b
        return dec_round_down(value, decimal_places)


def dec_mul_round_up(a: Decimal, b: Decimal, decimal_places: int) -> Decimal:
    with localcontext() as ctx:
        ctx.rounding = ROUND_UP
        value = a * b
        return dec_round_up(value, decimal_places)


def dec_mul_round_down(a: Decimal, b: Decimal, decimal_places: int) -> Decimal:
    with localcontext() as ctx:
        ctx.rounding = ROUND_DOWN
        value = a * b
        return dec_round_down(value, decimal_places)
