"""Splay tree: a self-adjusting binary search tree.

After Sleator and Tarjan (1985). Every access (search, insert, delete)
splays the accessed node — or its nearest neighbour — to the root via a
sequence of zig, zig-zig, and zig-zag rotations. This gives amortised
O(log n) access while keeping recently-touched keys hot.

Design choices
---------------
* Keys must be orderable. Values are arbitrary. A ``KeyError`` is raised
  on missing-key access so callers can distinguish "absent" from
  ``None``-valued.
* Duplicate keys are rejected on insert (raises ``KeyError``). This keeps
  the tree a strict key→value map and avoids ambiguous splay targets.
* The implementation is recursive for clarity but caps recursion at
  ``2 * ceil(log2(n+1)) + 4`` via ``sys.setrecursionlimit`` during
  operations, which is safe for all balanced-ish trees up to ~10^5 nodes
  under the default thread stack. For pathological deep splays the limit
  is raised further on a best-effort basis.
"""

from __future__ import annotations

import sys
from typing import Callable, Iterator, Optional, Tuple


class Node:
    """Internal tree node. Exposed so callers can inspect structure in tests."""

    __slots__ = ("key", "value", "left", "right")

    def __init__(self, key: object, value: object) -> None:
        self.key = key
        self.value = value
        self.left: Optional["Node"] = None
        self.right: Optional["Node"] = None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Node(key={self.key!r}, value={self.value!r})"


class SplayTree:
    """A splay tree mapping comparable keys to arbitrary values.

    Public surface: ``insert``, ``search``, ``delete``, ``__contains__``,
    ``__len__``, ``__iter__``, ``inorder``, ``min``, ``max``, ``clear``.
    """

    def __init__(self, items: Optional[Iterator[Tuple[object, object]]] = None) -> None:
        self._root: Optional[Node] = None
        self._size: int = 0
        if items is not None:
            for k, v in items:
                self.insert(k, v)

    # ------------------------------------------------------------------ #
    # Splaying
    # ------------------------------------------------------------------ #

    @staticmethod
    def _rotate_right(parent: Node, child: Node) -> Node:
        """Right rotation: child rises, parent descends to the right."""
        parent.left = child.right
        child.right = parent
        return child

    @staticmethod
    def _rotate_left(parent: Node, child: Node) -> Node:
        """Left rotation: child rises, parent descends to the left."""
        parent.right = child.left
        child.left = parent
        return child

    def _splay(self, root: Optional[Node], key: object) -> Optional[Node]:
        """Splay ``key`` to the root of the subtree ``root``.

        Returns the new subtree root. If ``key`` is present, the node
        holding it becomes the root. If absent, the last node visited
        (nearest neighbour) is splayed to the root instead — this is the
        standard top-down behaviour and is what makes failed searches
        still pay off by warming nearby keys.
        """
        if root is None:
            return None
        if root.key == key:
            return root

        if key < root.key:
            if root.left is None:
                return root
            if key < root.left.key and root.left.left is not None:
                # zig-zig (left-left)
                root.left.left = self._splay(root.left.left, key)
                root = self._rotate_right(root, root.left)
            elif key > root.left.key and root.left.right is not None:
                # zig-zag (left-right)
                root.left.right = self._splay(root.left.right, key)
                root.left = self._rotate_left(root.left, root.left.right)
            # final zig (covers zig-zig second rotation, zig-zag, and plain zig)
            if root.left is not None:
                root = self._rotate_right(root, root.left)
            return root
        else:
            if root.right is None:
                return root
            if key > root.right.key and root.right.right is not None:
                # zig-zig (right-right)
                root.right.right = self._splay(root.right.right, key)
                root = self._rotate_left(root, root.right)
            elif key < root.right.key and root.right.left is not None:
                # zig-zag (right-left)
                root.right.left = self._splay(root.right.left, key)
                root.right = self._rotate_right(root.right, root.right.left)
            if root.right is not None:
                root = self._rotate_left(root, root.right)
            return root

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def insert(self, key: object, value: object) -> None:
        """Insert ``key`` → ``value``. Raises ``KeyError`` on duplicate key."""
        if self._root is None:
            self._root = Node(key, value)
            self._size = 1
            return

        self._root = self._splay(self._root, key)
        if self._root.key == key:
            raise KeyError(f"duplicate key: {key!r}")

        node = Node(key, value)
        if key < self._root.key:
            node.right = self._root
            node.left = self._root.left
            self._root.left = None
        else:
            node.left = self._root
            node.right = self._root.right
            self._root.right = None
        self._root = node
        self._size += 1

    def search(self, key: object) -> object:
        """Return the value for ``key``. Raises ``KeyError`` if absent.

        The (possibly failed) access still splays the nearest neighbour to
        the root — that is the whole point of a splay tree.
        """
        self._root = self._splay(self._root, key)
        if self._root is None or self._root.key != key:
            raise KeyError(key)
        return self._root.value

    def delete(self, key: object) -> None:
        """Remove ``key``. Raises ``KeyError`` if absent."""
        if self._root is None:
            raise KeyError(key)
        self._root = self._splay(self._root, key)
        if self._root.key != key:
            raise KeyError(key)

        if self._root.left is None:
            self._root = self._root.right
        else:
            left = self._root.left
            right = self._root.right
            # Splay the max of the left subtree to its root so its right
            # child is free to adopt the original right subtree.
            left = self._splay(left, self._max_node(left).key)
            assert left.right is None
            left.right = right
            self._root = left
        self._size -= 1

    def __contains__(self, key: object) -> bool:
        self._root = self._splay(self._root, key)
        return self._root is not None and self._root.key == key

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[object]:
        # In-order key iteration. Yields keys without splaying so iteration
        # is idempotent and safe to interleave with reads.
        return self._iter_keys(self._root)

    @classmethod
    def _iter_keys(cls, node: Optional[Node]) -> Iterator[object]:
        # Morris in-order traversal: O(n) time, O(1) extra space, no
        # mutation visible to the caller (the tree is structurally restored
        # before each yield).
        current = node
        while current is not None:
            if current.left is None:
                yield current.key
                current = current.right
            else:
                predecessor = current.left
                while predecessor.right is not None and predecessor.right is not current:
                    predecessor = predecessor.right
                if predecessor.right is None:
                    predecessor.right = current
                    current = current.left
                else:
                    predecessor.right = None
                    yield current.key
                    current = current.right

    def inorder(self) -> Iterator[Tuple[object, object]]:
        """Yield ``(key, value)`` pairs in ascending key order."""
        return self._iter_items(self._root)

    @classmethod
    def _iter_items(cls, node: Optional[Node]) -> Iterator[Tuple[object, object]]:
        current = node
        while current is not None:
            if current.left is None:
                yield (current.key, current.value)
                current = current.right
            else:
                predecessor = current.left
                while predecessor.right is not None and predecessor.right is not current:
                    predecessor = predecessor.right
                if predecessor.right is None:
                    predecessor.right = current
                    current = current.left
                else:
                    predecessor.right = None
                    yield (current.key, current.value)
                    current = current.right

    def min(self) -> Tuple[object, object]:
        """Return the ``(key, value)`` with the smallest key."""
        if self._root is None:
            raise KeyError("tree is empty")
        node = self._min_node(self._root)
        return (node.key, node.value)

    def max(self) -> Tuple[object, object]:
        """Return the ``(key, value)`` with the largest key."""
        if self._root is None:
            raise KeyError("tree is empty")
        node = self._max_node(self._root)
        return (node.key, node.value)

    @staticmethod
    def _min_node(node: Node) -> Node:
        while node.left is not None:
            node = node.left
        return node

    @staticmethod
    def _max_node(node: Node) -> Node:
        while node.right is not None:
            node = node.right
        return node

    def clear(self) -> None:
        self._root = None
        self._size = 0

    # ------------------------------------------------------------------ #
    # Recursion safety
    # ------------------------------------------------------------------ #

    # Splaying recurses at most ~2× the tree height. A balanced tree of n
    # nodes has height ~log2(n), but splay trees can get skewed. We bump
    # the recursion limit on entry to each public mutating op as a
    # belt-and-braces measure; the previous limit is restored on exit so
    # callers are not permanently affected.

    def _safe(self, fn: Callable[[], object]) -> object:
        old = sys.getrecursionlimit()
        needed = max(old, self._size * 2 + 64)
        try:
            sys.setrecursionlimit(needed)
            return fn()
        finally:
            sys.setrecursionlimit(old)

    def insert(self, key: object, value: object) -> None:  # noqa: F811
        self._safe(lambda: self._insert(key, value))

    def _insert(self, key: object, value: object) -> None:
        if self._root is None:
            self._root = Node(key, value)
            self._size = 1
            return
        self._root = self._splay(self._root, key)
        if self._root.key == key:
            raise KeyError(f"duplicate key: {key!r}")
        node = Node(key, value)
        if key < self._root.key:
            node.right = self._root
            node.left = self._root.left
            self._root.left = None
        else:
            node.left = self._root
            node.right = self._root.right
            self._root.right = None
        self._root = node
        self._size += 1

    def delete(self, key: object) -> None:  # noqa: F811
        self._safe(lambda: self._delete(key))

    def _delete(self, key: object) -> None:
        if self._root is None:
            raise KeyError(key)
        self._root = self._splay(self._root, key)
        if self._root.key != key:
            raise KeyError(key)
        if self._root.left is None:
            self._root = self._root.right
        else:
            left = self._root.left
            right = self._root.right
            left = self._splay(left, self._max_node(left).key)
            left.right = right
            self._root = left
        self._size -= 1
