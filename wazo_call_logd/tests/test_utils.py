from wazo_call_logd.utils import find, defaultdict
from unittest import TestCase


class TestFind(TestCase):
    def test_empty_input(self):
        collection = []
        pred = lambda x: x  # noqa: E731
        self.assertIsNone(find(collection, pred))

    def test_no_match(self):
        collection = [True] * 10
        pred = lambda x: not x  # noqa: E731
        self.assertIsNone(find(collection, pred))

    def test_one_match(self):
        collection = range(10)
        pred = lambda x: x == 5  # noqa: E731
        self.assertEqual(find(collection, pred), 5)

    def test_multiple_match(self):
        collection = range(10)
        pred = lambda x: x > 5  # noqa: E731
        self.assertEqual(find(collection, pred), 6)


class TestDefaultdict(TestCase):
    def test_default_list(self):
        """
        Simple multidict/accumulator use case example
        """
        s = [('yellow', 1), ('blue', 2), ('yellow', 3), ('blue', 4), ('red', 1)]
        d = defaultdict(default=list)
        for k, v in s:
            d[k].append(v)

        # because of the ordered dict backing, we expect items to appear according to insertion order of keys
        self.assertEqual(
            list(d.items()), [('yellow', [1, 3]), ('blue', [2, 4]), ('red', [1])]
        )

    def test_counter(self):
        """
        Simple counter use case example
        """
        s = 'mississippi'
        d = defaultdict(default=int)
        for k in s:
            d[k] += 1

        self.assertEqual(list(d.items()), [('m', 1), ('i', 4), ('s', 4), ('p', 2)])

    def test_set_ordering(self):
        """
        Insertion order is maintained on iteration over keys and items
        """
        d = defaultdict()
        for i in range(10):
            d[i] = i

        self.assertEqual(list(d.keys()), list(range(10)))
        self.assertEqual(list(d.items()), list(zip(range(10), range(10))))
