"""
Bare Symbol Resolution (Native Perch Inference) — spec_0.1g

This module walks a parsed AST and resolves bare symbols to indexed variables
using native perch mappings from symbol declarations.

Example:
    Given symbols: prestate=[m], states=[m_d]
    Input:  m_d = m
    Output: m_d[_dcsn] = m[_arvl]
"""

from __future__ import annotations

import copy
from typing import Dict, List, Optional, Set

from lark import Tree, Token


# Symbol group → canonical perch tag mapping
GROUP_TO_PERCH: Dict[str, str] = {
    'prestate': '_arvl',
    'states': '_dcsn',
    'poststates': '_cntn',
    'controls': '_dcsn',
    'rewards': '_dcsn',
    'exogenous': '_dcsn',
}

# Groups that require explicit perch indices (perch value objects)
REQUIRES_EXPLICIT_INDEX: Set[str] = {'values', 'values_marginal', 'shadow_value'}


def build_native_perch_map(symbol_groups: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Build a mapping from symbol name to its native perch tag.

    Args:
        symbol_groups: {group_name: [symbol_names], ...}

    Returns:
        {symbol_name: perch_tag, ...}
    """
    native_perch = {}

    for group, names in symbol_groups.items():
        if group in GROUP_TO_PERCH:
            perch = GROUP_TO_PERCH[group]
            for name in names:
                # Strip any existing index from symbol name (e.g., "V[_arvl]" -> "V")
                bare_name = name.split('[')[0] if '[' in name else name
                native_perch[bare_name] = perch

    return native_perch


def build_requires_explicit_set(symbol_groups: Dict[str, List[str]]) -> Set[str]:
    """
    Build a set of symbol names that require explicit perch indices.

    Args:
        symbol_groups: {group_name: [symbol_names], ...}

    Returns:
        Set of symbol names that require explicit indices
    """
    requires_explicit = set()

    for group, names in symbol_groups.items():
        if group in REQUIRES_EXPLICIT_INDEX:
            for name in names:
                # Extract base name (e.g., "V[_arvl]" -> "V")
                bare_name = name.split('[')[0] if '[' in name else name
                requires_explicit.add(bare_name)

    return requires_explicit


def _make_variable_node(name: str, perch_tag: str) -> Tree:
    """
    Create a variable Tree node with the given name and perch tag.

    Args:
        name: Variable name (e.g., "m")
        perch_tag: Perch tag (e.g., "_arvl")

    Returns:
        Tree node: variable(name(Token), date(Token))
    """
    name_token = Token('NAME', name)
    name_tree = Tree('name', [name_token])
    perch_token = Token('PERCH_TAG', perch_tag)
    date_tree = Tree('date', [perch_token])
    return Tree('variable', [name_tree, date_tree])


def _resolve_symbol_in_tree(tree: Tree, native_perch: Dict[str, str],
                            requires_explicit: Set[str],
                            errors: List[str]) -> Tree:
    """
    Recursively walk the tree and resolve bare symbols to indexed variables.

    Args:
        tree: Lark parse tree
        native_perch: {symbol_name: perch_tag}
        requires_explicit: Set of symbols requiring explicit indices
        errors: List to accumulate error messages

    Returns:
        Modified tree (deep copy)
    """
    if not isinstance(tree, Tree):
        return tree

    # Process children first (bottom-up)
    new_children = []
    for child in tree.children:
        if isinstance(child, Tree):
            new_children.append(_resolve_symbol_in_tree(
                child, native_perch, requires_explicit, errors))
        else:
            new_children.append(child)

    # Check if this is a symbol node that needs resolution
    if tree.data == 'symbol':
        # Get the symbol name
        if new_children and isinstance(new_children[0], Token):
            sym_name = new_children[0].value

            # Check if this symbol requires explicit index
            if sym_name in requires_explicit:
                errors.append(
                    f"Symbol '{sym_name}' requires explicit perch index "
                    f"(e.g., {sym_name}[_dcsn]). "
                    f"Perch value objects cannot be used bare."
                )
                # Return unchanged to continue processing
                return Tree(tree.data, new_children)

            # Check if we have a native perch for this symbol
            if sym_name in native_perch:
                perch_tag = native_perch[sym_name]
                return _make_variable_node(sym_name, perch_tag)

            # Symbol not in native_perch map - could be a parameter or unknown
            # Parameters remain as bare symbols (no perch)
            # Let it pass through unchanged

    return Tree(tree.data, new_children)


def resolve_native_perches(tree: Tree, symbol_groups: Dict[str, List[str]],
                           strict: bool = True) -> Tree:
    """
    Walk AST and replace bare symbols with indexed variables
    using native perch from symbol declarations.

    Args:
        tree: Lark parse tree
        symbol_groups: {group_name: [symbol_names], ...}
        strict: If True, raise exception on errors; if False, return errors list

    Returns:
        Modified tree with bare symbols resolved to indexed variables

    Raises:
        ValueError: If strict=True and symbols requiring explicit indices are found bare
    """
    # Build mappings
    native_perch = build_native_perch_map(symbol_groups)
    requires_explicit = build_requires_explicit_set(symbol_groups)

    # Collect errors
    errors: List[str] = []

    # Deep copy and resolve
    resolved_tree = _resolve_symbol_in_tree(
        copy.deepcopy(tree), native_perch, requires_explicit, errors)

    # Handle errors
    if errors and strict:
        raise ValueError("\n".join(errors))

    return resolved_tree


def resolve_native_perches_lenient(tree: Tree, symbol_groups: Dict[str, List[str]]) -> tuple:
    """
    Same as resolve_native_perches but returns errors instead of raising.

    Args:
        tree: Lark parse tree
        symbol_groups: {group_name: [symbol_names], ...}

    Returns:
        Tuple of (resolved_tree, errors_list)
    """
    native_perch = build_native_perch_map(symbol_groups)
    requires_explicit = build_requires_explicit_set(symbol_groups)

    errors: List[str] = []
    resolved_tree = _resolve_symbol_in_tree(
        copy.deepcopy(tree), native_perch, requires_explicit, errors)

    return resolved_tree, errors
