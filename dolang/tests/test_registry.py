"""
Tests for DDSL registry loader.
"""

import pytest
from dolang.registry import (
    REGISTRY,
    get_decorator,
    is_decorator,
    is_primitive_domain,
    get_primitive_domain,
    get_constructor,
    is_constructor,
    get_distribution,
    is_distribution,
    canonicalize,
    to_identifier_safe,
    from_identifier_safe,
)


class TestRegistryLoad:
    def test_registry_loads(self):
        assert REGISTRY is not None
        assert "version" in REGISTRY
        assert REGISTRY["version"] == "0.1"

    def test_decorators_exist(self):
        assert "decorators" in REGISTRY
        assert "@in" in REGISTRY["decorators"]
        assert "@def" in REGISTRY["decorators"]
        assert "@dist" in REGISTRY["decorators"]


class TestDecoratorLookup:
    def test_get_decorator_in(self):
        dec = get_decorator("@in")
        assert dec is not None
        assert dec["kind"] == "membership"
        assert dec["arity"] == 1

    def test_get_decorator_def(self):
        dec = get_decorator("@def")
        assert dec is not None
        assert dec["kind"] == "definition"

    def test_get_decorator_dist(self):
        dec = get_decorator("@dist")
        assert dec is not None
        assert dec["kind"] == "distribution"

    def test_get_decorator_unknown(self):
        assert get_decorator("@unknown") is None

    def test_is_decorator(self):
        assert is_decorator("@in") is True
        assert is_decorator("@def") is True
        assert is_decorator("@dist") is True
        assert is_decorator("@foo") is False


class TestPrimitiveDomains:
    def test_is_primitive_domain(self):
        assert is_primitive_domain("R") is True
        assert is_primitive_domain("R+") is True
        assert is_primitive_domain("R++") is True
        assert is_primitive_domain("Z") is True
        assert is_primitive_domain("Z+") is True
        assert is_primitive_domain("Foo") is False

    def test_is_primitive_via_alias(self):
        # R_plus is an alias for R+
        assert is_primitive_domain("R_plus") is True

    def test_get_primitive_domain(self):
        dom = get_primitive_domain("R+")
        assert dom is not None
        assert "description" in dom


class TestConstructors:
    def test_get_constructor_clop(self):
        con = get_constructor("ClOp")
        assert con is not None
        assert con["arity"] == 2
        assert con["kind"] == "domain_constructor"

    def test_is_constructor(self):
        assert is_constructor("ClOp") is True
        assert is_constructor("OpCl") is True
        assert is_constructor("Unknown") is False

    def test_get_constructor_unknown(self):
        assert get_constructor("Unknown") is None


class TestDistributions:
    def test_get_distribution_normal(self):
        dist = get_distribution("Normal")
        assert dist is not None
        assert dist["arity"] == 2

    def test_get_distribution_unormal(self):
        dist = get_distribution("UNormal")
        assert dist is not None
        assert dist["arity"] == 1

    def test_is_distribution(self):
        assert is_distribution("Normal") is True
        assert is_distribution("LogNormal") is True
        assert is_distribution("Unknown") is False


class TestAliases:
    def test_canonicalize_alias(self):
        assert canonicalize("R_plus") == "R+"
        assert canonicalize("R_plusplus") == "R++"
        assert canonicalize("Z_plus") == "Z+"

    def test_canonicalize_already_canonical(self):
        assert canonicalize("R+") == "R+"
        assert canonicalize("R") == "R"

    def test_canonicalize_unknown(self):
        assert canonicalize("Foo") == "Foo"


class TestIdentifierSafe:
    def test_to_identifier_safe(self):
        assert to_identifier_safe("R+") == "R_plus"
        assert to_identifier_safe("R++") == "R_plusplus"
        assert to_identifier_safe("Z+") == "Z_plus"

    def test_to_identifier_safe_already_safe(self):
        assert to_identifier_safe("R") == "R"

    def test_from_identifier_safe(self):
        assert from_identifier_safe("R_plus") == "R+"
        assert from_identifier_safe("R_plusplus") == "R++"

    def test_roundtrip(self):
        for canonical in ["R+", "R++", "Z+"]:
            safe = to_identifier_safe(canonical)
            assert from_identifier_safe(safe) == canonical
