from decimal import Decimal, ROUND_UP, ROUND_DOWN, localcontext
from collections.abc import Callable


def dec_round(func: Callable[[], Decimal], decimal_places: int = None, rounding: str = None) -> Decimal:
    if decimal_places and decimal_places < 0:
        raise ValueError(f'incorrect rounding "{decimal_places}", must be non negative integer or None')
    with localcontext() as ctx:
        if rounding:
            ctx.rounding = rounding
        value = func()
        if decimal_places:
            value = value.quantize(Decimal(f'0.{"0"*decimal_places}'), rounding=rounding)
    return value


def dec_round_up(func: Callable[[], Decimal], decimal_places: int = None) -> Decimal:
    return dec_round(func, decimal_places, rounding=ROUND_UP)


def dec_round_down(func: Callable[[], Decimal], decimal_places: int = None) -> Decimal:
    return dec_round(func, decimal_places, rounding=ROUND_DOWN)
