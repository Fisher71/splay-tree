import unittest

from splay_tree import SplayTree, Node


class TestBasics(unittest.TestCase):
    def test_empty_tree(self):
        t = SplayTree()
        self.assertEqual(len(t), 0)
        self.assertFalse(5 in t)
        self.assertEqual(list(t), [])
        self.assertEqual(list(t.inorder()), [])
        with self.assertRaises(KeyError):
            t.search(1)
        with self.assertRaises(KeyError):
            t.delete(1)
        with self.assertRaises(KeyError):
            t.min()
        with self.assertRaises(KeyError):
            t.max()

    def test_single_insert_and_search(self):
        t = SplayTree()
        t.insert("a", 1)
        self.assertEqual(len(t), 1)
        self.assertIn("a", t)
        self.assertEqual(t.search("a"), 1)
        self.assertEqual(t.min(), ("a", 1))
        self.assertEqual(t.max(), ("a", 1))

    def test_duplicate_insert_raises(self):
        t = SplayTree()
        t.insert(5, "first")
        with self.assertRaises(KeyError):
            t.insert(5, "second")
        self.assertEqual(len(t), 1)
        self.assertEqual(t.search(5), "first")

    def test_search_missing_splays_nearest(self):
        # Searching for a missing key splays the nearest neighbour to root.
        t = SplayTree()
        for k in [10, 20, 30, 40, 50]:
            t.insert(k, k)
        with self.assertRaises(KeyError):
            t.search(22)
        # Nearest to 22 among {10,20,30,40,50} is 20 or 30; both are leaves
        # after insertion order. The root should hold one of the nearest keys.
        self.assertIn(t._root.key, (20, 30))

    def test_delete_missing_raises(self):
        t = SplayTree()
        t.insert(1, 1)
        with self.assertRaises(KeyError):
            t.delete(99)
        self.assertEqual(len(t), 1)

    def test_insert_many_inorder(self):
        t = SplayTree()
        for i in range(100):
            t.insert(i, i * 2)
        self.assertEqual(len(t), 100)
        for i in range(100):
            self.assertEqual(t.search(i), i * 2)
        # After searching the max, it should be at the root.
        t.search(99)
        self.assertEqual(t._root.key, 99)

    def test_insert_many_reverse(self):
        t = SplayTree()
        for i in range(99, -1, -1):
            t.insert(i, str(i))
        self.assertEqual(len(t), 100)
        self.assertEqual(list(t), list(range(100)))

    def test_delete_all_variants(self):
        for order in [
            list(range(50)),
            list(range(49, -1, -1)),
            [25, 0, 49, 13, 37, 5, 45, 20, 30, 10]
            + [k for k in range(50) if k not in {25, 0, 49, 13, 37, 5, 45, 20, 30, 10}],
        ]:
            t = SplayTree()
            for k in range(50):
                t.insert(k, k)
            for k in order:
                t.delete(k)
                self.assertNotIn(k, t)
            self.assertEqual(len(t), 0)
            self.assertIsNone(t._root)

    def test_delete_root_with_two_children(self):
        t = SplayTree()
        t.insert(10, 10)
        t.insert(5, 5)
        t.insert(20, 20)
        # After inserting 20, 20 is root. Splay 10 back to root then delete.
        t.search(10)
        t.delete(10)
        self.assertEqual(len(t), 2)
        self.assertNotIn(10, t)
        self.assertIn(5, t)
        self.assertIn(20, t)

    def test_iteration_is_sorted(self):
        import random
        rng = random.Random(42)
        keys = rng.sample(range(1000), 200)
        t = SplayTree()
        for k in keys:
            t.insert(k, k)
        self.assertEqual(list(t), sorted(keys))
        self.assertEqual([k for k, _ in t.inorder()], sorted(keys))

    def test_iteration_does_not_splay(self):
        t = SplayTree()
        for k in [3, 1, 2]:
            t.insert(k, k)
        # After inserting 2, root.key == 2.
        self.assertEqual(t._root.key, 2)
        list(t)
        # Iteration must not have moved the root.
        self.assertEqual(t._root.key, 2)

    def test_min_max_with_duplicates_rejected(self):
        t = SplayTree()
        t.insert(5, None)
        t.insert(1, None)
        t.insert(9, None)
        self.assertEqual(t.min(), (1, None))
        self.assertEqual(t.max(), (9, None))

    def test_none_value_roundtrip(self):
        t = SplayTree()
        t.insert("k", None)
        self.assertIn("k", t)
        self.assertIsNone(t.search("k"))

    def test_float_keys(self):
        t = SplayTree()
        t.insert(1.5, "a")
        t.insert(1.25, "b")
        t.insert(1.75, "c")
        self.assertEqual(t.search(1.25), "b")
        self.assertEqual(t.min()[0], 1.25)
        self.assertEqual(t.max()[0], 1.75)

    def test_constructor_from_items(self):
        t = SplayTree([(3, "c"), (1, "a"), (2, "b")])
        self.assertEqual(len(t), 3)
        self.assertEqual(list(t), [1, 2, 3])
        self.assertEqual(t.search(2), "b")

    def test_clear(self):
        t = SplayTree([(i, i) for i in range(10)])
        t.clear()
        self.assertEqual(len(t), 0)
        self.assertIsNone(t._root)
        self.assertEqual(list(t), [])
        # Usable again after clear.
        t.insert(7, 7)
        self.assertEqual(t.search(7), 7)

    def test_contains_does_not_raise_on_missing(self):
        t = SplayTree()
        t.insert(1, 1)
        self.assertNotIn(2, t)
        self.assertIn(1, t)

    def test_splay_bring_accessed_to_root(self):
        t = SplayTree()
        for k in range(1, 8):
            t.insert(k, k)
        # Access key 1 (deepest left). After splay it must be root.
        t.search(1)
        self.assertEqual(t._root.key, 1)
        # Access key 7 (deepest right).
        t.search(7)
        self.assertEqual(t._root.key, 7)

    def test_zig_zig_case(self):
        # Insert 3, 2, 1 to force a left-left chain, then access 1.
        t = SplayTree()
        t.insert(3, 3)
        t.insert(2, 2)
        t.insert(1, 1)
        t.search(1)
        self.assertEqual(t._root.key, 1)
        self.assertEqual(t._root.right.key, 2)
        self.assertEqual(t._root.right.right.key, 3)

    def test_zig_zag_case(self):
        t = SplayTree()
        t.insert(3, 3)
        t.insert(1, 1)
        t.insert(2, 2)  # right child of 1 → zig-zag on access
        t.search(2)
        self.assertEqual(t._root.key, 2)
        self.assertEqual(t._root.left.key, 1)
        self.assertEqual(t._root.right.key, 3)

    def test_node_class_exposed(self):
        n = Node("k", "v")
        self.assertEqual(n.key, "k")
        self.assertEqual(n.value, "v")
        self.assertIsNone(n.left)
        self.assertIsNone(n.right)

    def test_update_via_delete_insert(self):
        # No update method is provided; documented pattern is delete+insert.
        t = SplayTree()
        t.insert(5, "old")
        t.delete(5)
        t.insert(5, "new")
        self.assertEqual(t.search(5), "new")
        self.assertEqual(len(t), 1)

    def test_large_sequential_insert_no_recursion_error(self):
        # Splay trees fed sorted keys can get deep; verify the recursion
        # guard keeps things working for a moderately large n.
        t = SplayTree()
        for i in range(2000):
            t.insert(i, i)
        self.assertEqual(len(t), 2000)
        self.assertEqual(t.search(1999), 1999)
        self.assertEqual(t._root.key, 1999)

    def test_string_keys(self):
        t = SplayTree()
        for w in ["banana", "apple", "cherry", "date"]:
            t.insert(w, len(w))
        self.assertEqual(list(t), ["apple", "banana", "cherry", "date"])
        self.assertEqual(t.search("cherry"), 6)
        self.assertEqual(t.min(), ("apple", 5))
        self.assertEqual(t.max(), ("date", 4))


if __name__ == "__main__":
    unittest.main()
