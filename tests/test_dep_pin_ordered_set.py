#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Learning test for the external dependency `ordered_set`.

Purpose
-------
Pin the OrderedSet surface used by bin/feed_maker.py's window deduplication.
A future ordered_set upgrade that drops `add()`, breaks `in` membership, or
loses insertion-order iteration would silently break feed deduplication.

Reference call sites (production code):
    bin/feed_maker.py:16    from ordered_set import OrderedSet
    bin/feed_maker.py:364   feed_item_existence_set: OrderedSet[str] = OrderedSet([])
    bin/feed_maker.py:383   if link not in feed_item_existence_set:
    bin/feed_maker.py:386   feed_item_existence_set.add(link)
"""

import unittest

from ordered_set import OrderedSet


class OrderedSetImportSurfaceTest(unittest.TestCase):
    def test_ordered_set_is_a_class(self) -> None:
        self.assertTrue(isinstance(OrderedSet, type))

    def test_ordered_set_is_generic_subscriptable(self) -> None:
        # feed_maker.py:364 -- OrderedSet[str] type annotation
        _ = OrderedSet[str]


class OrderedSetConstructorTest(unittest.TestCase):
    def test_constructor_accepts_empty_list(self) -> None:
        # feed_maker.py:364 -- OrderedSet([])
        s: OrderedSet[str] = OrderedSet([])
        self.assertEqual(len(s), 0)

    def test_constructor_accepts_iterable_with_dedup(self) -> None:
        s: OrderedSet[str] = OrderedSet(["a", "b", "a", "c", "b"])
        self.assertEqual(list(s), ["a", "b", "c"])


class OrderedSetMembershipAndAddTest(unittest.TestCase):
    """Pin the two operations production performs: `in` and `.add()`."""

    def test_in_returns_false_then_true_after_add(self) -> None:
        # feed_maker.py:383-386
        #   if link not in feed_item_existence_set:
        #       feed_item_existence_set.add(link)
        s: OrderedSet[str] = OrderedSet([])
        self.assertNotIn("https://example.com/1", s)
        s.add("https://example.com/1")
        self.assertIn("https://example.com/1", s)

    def test_add_preserves_insertion_order(self) -> None:
        # The whole reason production picks OrderedSet over `set`: insertion
        # order must round-trip through iteration so the resulting feed list
        # stays stable.
        s: OrderedSet[str] = OrderedSet([])
        for link in ["c", "a", "b", "a", "d"]:
            if link not in s:
                s.add(link)
        self.assertEqual(list(s), ["c", "a", "b", "d"])

    def test_add_of_existing_item_is_idempotent(self) -> None:
        s: OrderedSet[str] = OrderedSet([])
        s.add("x")
        s.add("x")
        self.assertEqual(len(s), 1)


if __name__ == "__main__":
    unittest.main()
