from __future__ import annotations
from typing import Callable, TypeVar
from collections.abc import Iterable
from collections import OrderedDict


T = TypeVar("T")


def find(col: Iterable[T], pred: Callable[[T], bool]) -> T | None:
    """
    find first element of an iterable matching a predicate
    """
    for x in col:
        if pred(x):
            return x


class defaultdict(OrderedDict):
    """
    https://gist.github.com/ohe/1605376
    Default Dict Implementation built upon OrderedDict(because collections.defaultdict and collections.OrderedDict are not composable)
    Representation of a default dict:
    >>> defaultdict([('foo', 'bar'), ('bar', 'baz'])
    defaultdict(None, OrderedDict([('foo', 'bar'), ('bar', 'baz')]))
    """

    def __init__(self, *args, **kwargs):
        self.default = kwargs.pop('default', None)
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return 'defaultdict(%s, %s)' % (self.default, super().__repr__())

    def __missing__(self, key):
        if self.default:
            self[key] = value = self.default()
            return value
        else:
            raise KeyError(key)

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            return self.__missing__(key)
