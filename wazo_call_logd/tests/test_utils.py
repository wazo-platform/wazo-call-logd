from wazo_call_logd.utils import find
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
