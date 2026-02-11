"""Utilities for working with PyYAML Node trees (no monkey-patching).

`yaml.compose(...)` returns a tree of *Node* objects (MappingNode/SequenceNode/ScalarNode).
Upstream dolang historically monkey-patched these classes to behave like dict/list.

In this repo we avoid monkey-patching and instead use these explicit helpers.
"""

from __future__ import annotations

from typing import Any, Iterable, Iterator, Tuple, TypeGuard

from yaml.nodes import MappingNode, ScalarNode, SequenceNode


def is_scalar_node(x: Any) -> TypeGuard[ScalarNode]:
    return isinstance(x, ScalarNode)


def is_mapping_node(x: Any) -> TypeGuard[MappingNode]:
    return isinstance(x, MappingNode)


def is_sequence_node(x: Any) -> TypeGuard[SequenceNode]:
    return isinstance(x, SequenceNode)


def scalar_value(x: Any) -> Any:
    """Return `.value` for ScalarNodes; passthrough otherwise."""

    if isinstance(x, ScalarNode):
        return x.value
    return x


def mapping_items(m: Any) -> Iterator[Tuple[str, Any]]:
    """Iterate (key, value) over a YAML MappingNode (or dict)."""

    if isinstance(m, dict):
        yield from m.items()
        return

    if not isinstance(m, MappingNode):
        raise TypeError(f"Expected MappingNode or dict, got {type(m)}")

    for k_node, v_node in m.value:
        if not isinstance(k_node, ScalarNode):
            raise TypeError(f"Expected ScalarNode key, got {type(k_node)}")
        yield k_node.value, v_node


def mapping_keys(m: Any) -> list[str]:
    return [k for k, _ in mapping_items(m)]


def mapping_has(m: Any, key: str) -> bool:
    if isinstance(m, dict):
        return key in m
    if not isinstance(m, MappingNode):
        raise TypeError(f"Expected MappingNode or dict, got {type(m)}")
    for k, _ in mapping_items(m):
        if k == key:
            return True
    return False


def mapping_get(m: Any, key: str, default: Any = None) -> Any:
    if isinstance(m, dict):
        return m.get(key, default)
    if not isinstance(m, MappingNode):
        raise TypeError(f"Expected MappingNode or dict, got {type(m)}")
    for k, v in mapping_items(m):
        if k == key:
            return v
    return default


def mapping_get_required(m: Any, key: str) -> Any:
    v = mapping_get(m, key, default=None)
    if v is None:
        raise KeyError(key)
    return v


def mapping_set(m: Any, key: str, value_node: Any) -> None:
    """Set or update a key in a YAML MappingNode (or dict).

    For MappingNode: if key exists, replaces the value node; otherwise appends.
    For dict: simple assignment.
    """
    if isinstance(m, dict):
        m[key] = value_node
        return

    if not isinstance(m, MappingNode):
        raise TypeError(f"Expected MappingNode or dict, got {type(m)}")

    for i, (k_node, _v_node) in enumerate(m.value):
        if isinstance(k_node, ScalarNode) and k_node.value == key:
            m.value[i] = (k_node, value_node)
            return

    # Key not found — append
    new_key = ScalarNode(tag="tag:yaml.org,2002:str", value=key)
    m.value.append((new_key, value_node))


def sequence_values(s: Any) -> list[Any]:
    """Return children of a YAML SequenceNode (or list)."""

    if isinstance(s, list):
        return s
    if not isinstance(s, SequenceNode):
        raise TypeError(f"Expected SequenceNode or list, got {type(s)}")
    return list(s.value)


def sequence_iter(s: Any) -> Iterator[Any]:
    yield from sequence_values(s)


def to_str_keyed_dict(m: Any) -> dict[str, Any]:
    """Convert a MappingNode to a plain dict[str, Any] of *nodes* (shallow)."""

    return {k: v for k, v in mapping_items(m)}


