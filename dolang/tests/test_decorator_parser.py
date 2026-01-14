"""
Tests for decorator application parser.
"""

import pytest
from dolang.decorator_parser import (
    parse_decorator,
    get_decorator_name,
    get_domain_expr,
)


class TestParseDecorator:
    def test_parse_in_open_interval(self):
        tree = parse_decorator("@in (0,1)")
        assert tree is not None
        assert tree.data == "start"

    def test_parse_in_closed_interval(self):
        tree = parse_decorator("@in [0,1]")
        assert tree is not None

    def test_parse_in_primitive_r(self):
        tree = parse_decorator("@in R")
        assert tree is not None

    def test_parse_in_primitive_r_plus(self):
        tree = parse_decorator("@in R+")
        assert tree is not None

    def test_parse_in_primitive_r_plusplus(self):
        tree = parse_decorator("@in R++")
        assert tree is not None

    def test_parse_in_primitive_z(self):
        tree = parse_decorator("@in Z")
        assert tree is not None

    def test_parse_in_primitive_z_plus(self):
        tree = parse_decorator("@in Z+")
        assert tree is not None

    def test_parse_in_symbol_ref(self):
        tree = parse_decorator("@in X")
        assert tree is not None

    def test_parse_def_constructor(self):
        tree = parse_decorator("@def ClOp(a,b)")
        assert tree is not None

    def test_parse_def_primitive(self):
        tree = parse_decorator("@def R+")
        assert tree is not None

    def test_parse_dist_normal(self):
        tree = parse_decorator("@dist Normal(mu, sigma)")
        assert tree is not None

    def test_parse_dist_with_numbers(self):
        tree = parse_decorator("@dist Normal(0, 1)")
        assert tree is not None

    def test_parse_invalid_returns_none(self):
        tree = parse_decorator("not a decorator")
        assert tree is None

    def test_parse_empty_returns_none(self):
        tree = parse_decorator("")
        assert tree is None


class TestGetDecoratorName:
    def test_get_in(self):
        tree = parse_decorator("@in (0,1)")
        assert get_decorator_name(tree) == "@in"

    def test_get_def(self):
        tree = parse_decorator("@def R+")
        assert get_decorator_name(tree) == "@def"

    def test_get_dist(self):
        tree = parse_decorator("@dist Normal(0,1)")
        assert get_decorator_name(tree) == "@dist"

    def test_none_tree(self):
        assert get_decorator_name(None) is None


class TestGetDomainExpr:
    def test_get_interval(self):
        tree = parse_decorator("@in (0,1)")
        domain = get_domain_expr(tree)
        assert domain is not None
        assert domain.data == "open_interval"

    def test_get_closed_interval(self):
        tree = parse_decorator("@in [0,1]")
        domain = get_domain_expr(tree)
        assert domain is not None
        assert domain.data == "closed_interval"

    def test_get_primitive(self):
        tree = parse_decorator("@in R+")
        domain = get_domain_expr(tree)
        assert domain is not None
        assert domain.data == "primitive_domain"

    def test_get_symbol_ref(self):
        tree = parse_decorator("@in X")
        domain = get_domain_expr(tree)
        assert domain is not None
        assert domain.data == "symbol_ref"

    def test_get_constructor(self):
        tree = parse_decorator("@def ClOp(a,b)")
        domain = get_domain_expr(tree)
        assert domain is not None
        assert domain.data == "constructor_call"

    def test_none_tree(self):
        assert get_domain_expr(None) is None


class TestIntervalVariants:
    def test_left_open(self):
        tree = parse_decorator("@in (0,1]")
        domain = get_domain_expr(tree)
        assert domain.data == "left_open_interval"

    def test_right_open(self):
        tree = parse_decorator("@in [0,1)")
        domain = get_domain_expr(tree)
        assert domain.data == "right_open_interval"

    def test_negative_numbers(self):
        tree = parse_decorator("@in (-1,1)")
        assert tree is not None
        domain = get_domain_expr(tree)
        assert domain.data == "open_interval"

    def test_float_numbers(self):
        tree = parse_decorator("@in (0.0, 1.5)")
        assert tree is not None
