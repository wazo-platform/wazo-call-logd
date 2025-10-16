from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

T = TypeVar("T")


def find(col: Iterable[T], pred: Callable[[T], bool]) -> T | None:
    """
    find first element of an iterable matching a predicate
    """
    for x in col:
        if pred(x):
            return x
