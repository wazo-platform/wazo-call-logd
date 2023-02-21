from __future__ import annotations
from typing import Callable, TypeVar
from collections.abc import Iterable

T = TypeVar("T")


def find(col: Iterable[T], pred: Callable[[T], bool]) -> T | None:
    """
    find first element of an iterable matching a predicate
    """
    for x in col:
        if pred(x):
            return x
