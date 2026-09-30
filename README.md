# splay_tree

A small, dependency-free Python implementation of the splay tree: a
self-adjusting binary search tree that moves every accessed node to the
root via zig / zig-zig / zig-zag rotations, giving amortised O(log n)
access and keeping recently-touched keys hot.

## Usage

```python
from splay_tree import SplayTree

t = SplayTree()
t.insert(10, "ten")
t.insert(5, "five")
t.insert(20, "twenty")

assert t.search(5) == "five"    # 5 is now at the root
assert 20 in t
t.delete(10)
assert len(t) == 2

# In-order iteration yields keys in sorted order.
assert list(t) == [5, 20]
assert list(t.inorder()) == [(5, "five"), (20, "twenty")]

assert t.min() == (5, "five")
assert t.max() == (20, "twenty")

t.clear()
```

The constructor also accepts an iterable of `(key, value)` pairs:
`SplayTree([(3, "c"), (1, "a")])`.

## Exported names

- `SplayTree` — the tree class. Methods: `insert`, `search`, `delete`,
  `min`, `max`, `clear`, `inorder`, `__contains__`, `__len__`, `__iter__`.
- `Node` — internal node type (`key`, `value`, `left`, `right`). Exposed
  for structural inspection in tests; not part of the stable API contract.

## Why this exists

Splay trees are useful when access is non-uniform: a small working set of
hot keys should stay near the root without explicit re-balancing. The
trade-off versus an AVL or red-black tree is that individual operations
are *amortised* O(log n), not worst-case — a single access can be O(n),
and there is no height bound after pathological input.

This library picks one interpretation of the brief and sticks to it: the
tree is a strict key→value map. Duplicate keys are rejected on insert
(`KeyError`), and `search` raises `KeyError` for missing keys rather than
returning a sentinel. There is no `update` method — replace a value by
deleting and re-inserting.

## Awkward edges

- **Failed searches still mutate the tree.** A missing-key `search` or
  `contains` splays the nearest neighbour to the root. This is the
  defining behaviour of a splay tree, but it means read-looking calls are
  not side-effect free. If you need a snapshot, iterate `inorder()` which
  uses Morris traversal and does not splay.
- **Duplicate keys raise.** This is a map, not a multiset.
- **No worst-case height bound.** Feeding sorted keys produces a deep
  tree; the recursion limit is raised during operations as a safety
  measure, but very large ordered inserts (≥10^5) may still hit CPython's
  thread stack limit. Shuffle input if that matters.

## Running the tests

```
PYTHONPATH=src python -m unittest discover -s tests
```
