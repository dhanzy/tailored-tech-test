from collections.abc import Callable

Transformer = Callable[[str], str]


def upper_transformer(value: str) -> str:
    """Stand-in for the external service the task asks us to simulate.

    Treat every call as expensive: the rest of the code exists to avoid it.
    """
    return value.upper()
