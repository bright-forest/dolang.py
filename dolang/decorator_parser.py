"""
Decorator Application Parser

Parses decorator strings like "@in (0,1)" or "@def R+" into Lark ASTs.
Returns Lark parse trees directly - no custom classes needed.

Usage:
    from dolang.decorator_parser import parse_decorator

    tree = parse_decorator("@in (0,1)")
    # tree is a Lark Tree object
"""

from typing import Optional
from lark import Lark
from lark.tree import Tree

__all__ = [
    "parse_decorator",
    "get_decorator_parser",
    "DECORATOR_GRAMMAR",
]

# Minimal grammar for decorator applications
# Handles: @in (0,1), @in R+, @def ClOp(a,b), @dist Normal(μ, σ)
DECORATOR_GRAMMAR = r'''
start: decorator_app

decorator_app: DECORATOR domain_expr

// Order matters: primitive_domain must be tried before symbol_ref
// to ensure R+ is not parsed as R (symbol_ref) + garbage
domain_expr: interval
           | primitive_domain
           | constructor_call
           | symbol_ref

interval: "(" number "," number ")"    -> open_interval
        | "[" number "," number "]"    -> closed_interval
        | "(" number "," number "]"    -> left_open_interval
        | "[" number "," number ")"    -> right_open_interval

constructor_call: CNAME "(" arg_list ")"
arg_list: arg ("," arg)*
arg: symbol_ref | number

// Primitive domains: R, R+, R++, Z, Z+
// Higher priority (2) ensures these are matched before CNAME
primitive_domain: PRIMITIVE_DOMAIN
PRIMITIVE_DOMAIN.2: /R\+\+/ | /R\+/ | /Z\+/ | /R/ | /Z/

symbol_ref: CNAME
number: SIGNED_NUMBER

DECORATOR: /@[a-z]+/
CNAME: /[A-Za-z_][A-Za-z0-9_]*/

%import common.SIGNED_NUMBER
%import common.WS
%ignore WS
'''

_parser: Optional[Lark] = None


def get_decorator_parser() -> Lark:
    """Get or create the decorator parser (singleton)."""
    global _parser
    if _parser is None:
        _parser = Lark(DECORATOR_GRAMMAR, start='start', parser='lalr')
    return _parser


def reset_parser():
    """Reset the parser singleton (for testing after grammar changes)."""
    global _parser
    _parser = None


def parse_decorator(raw: str) -> Optional[Tree]:
    """
    Parse a decorator application string into a Lark Tree.

    Args:
        raw: e.g., "@in (0,1)" or "@def R+" or "@dist Normal(μ, σ)"

    Returns:
        Lark Tree object, or None if parse fails.

    Example:
        >>> tree = parse_decorator("@in (0,1)")
        >>> tree.data
        'start'
        >>> tree.children[0].data
        'decorator_app'
    """
    try:
        return get_decorator_parser().parse(raw.strip())
    except Exception:
        return None


def get_decorator_name(tree: Tree) -> Optional[str]:
    """
    Extract the decorator name (e.g., '@in') from a parsed tree.

    Args:
        tree: Lark Tree from parse_decorator()

    Returns:
        Decorator name string, or None if not found.
    """
    if tree is None:
        return None
    try:
        # tree.data == 'start', tree.children[0].data == 'decorator_app'
        decorator_app = tree.children[0]
        # First child of decorator_app is the DECORATOR token
        decorator_token = decorator_app.children[0]
        return str(decorator_token)
    except (IndexError, AttributeError):
        return None


def get_domain_expr(tree: Tree) -> Optional[Tree]:
    """
    Extract the domain expression subtree from a parsed decorator.

    Args:
        tree: Lark Tree from parse_decorator()

    Returns:
        The inner domain expression subtree (e.g., open_interval, primitive_domain),
        or None if not found.
    """
    if tree is None:
        return None
    try:
        # tree.data == 'start', tree.children[0].data == 'decorator_app'
        decorator_app = tree.children[0]
        # Second child of decorator_app is the domain_expr wrapper
        domain_expr = decorator_app.children[1]
        # Return the first child of domain_expr (the actual rule like open_interval)
        if hasattr(domain_expr, 'children') and domain_expr.children:
            return domain_expr.children[0]
        return domain_expr
    except (IndexError, AttributeError):
        return None
