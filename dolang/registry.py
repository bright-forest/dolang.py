"""
DDSL Registry Loader

Provides access to DDSL primitives (decorators, domains, constructors, aliases).
This module loads ddsl_registry.yaml once at import time and exposes lookup functions.

Usage:
    from dolang.registry import (
        get_decorator,
        is_primitive_domain,
        get_constructor,
        canonicalize,
        to_identifier_safe,
    )
"""

from pathlib import Path
from typing import Any, Dict, Optional
import yaml

__all__ = [
    "REGISTRY",
    "get_decorator",
    "is_decorator",
    "is_primitive_domain",
    "get_primitive_domain",
    "get_constructor",
    "get_distribution",
    "canonicalize",
    "to_identifier_safe",
    "from_identifier_safe",
]

# ---------------------------------------------------------------------------
# Load registry once at import time
# ---------------------------------------------------------------------------

_REGISTRY_PATH = Path(__file__).parent / "ddsl_registry.yaml"


def _load_registry() -> Dict[str, Any]:
    """Load the DDSL registry from YAML."""
    if not _REGISTRY_PATH.exists():
        raise FileNotFoundError(f"DDSL registry not found: {_REGISTRY_PATH}")
    with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


REGISTRY: Dict[str, Any] = _load_registry()

# ---------------------------------------------------------------------------
# Decorator lookups
# ---------------------------------------------------------------------------


def get_decorator(name: str) -> Optional[Dict[str, Any]]:
    """Get decorator spec by name (e.g., '@in'). Returns None if not found."""
    return REGISTRY.get("decorators", {}).get(name)


def is_decorator(name: str) -> bool:
    """Check if name is a registered decorator."""
    return name in REGISTRY.get("decorators", {})


# ---------------------------------------------------------------------------
# Primitive domain lookups
# ---------------------------------------------------------------------------


def is_primitive_domain(name: str) -> bool:
    """Check if name is a primitive domain (e.g., 'R+')."""
    canonical = canonicalize(name)
    return canonical in REGISTRY.get("primitive_objects", {}).get("domains", {})


def get_primitive_domain(name: str) -> Optional[Dict[str, Any]]:
    """Get primitive domain spec by name. Returns None if not found."""
    canonical = canonicalize(name)
    return REGISTRY.get("primitive_objects", {}).get("domains", {}).get(canonical)


# ---------------------------------------------------------------------------
# Constructor lookups
# ---------------------------------------------------------------------------


def get_constructor(name: str) -> Optional[Dict[str, Any]]:
    """Get constructor spec by name (e.g., 'ClOp'). Returns None if not found."""
    return REGISTRY.get("constructors", {}).get(name)


def is_constructor(name: str) -> bool:
    """Check if name is a registered constructor."""
    return name in REGISTRY.get("constructors", {})


# ---------------------------------------------------------------------------
# Distribution lookups
# ---------------------------------------------------------------------------


def get_distribution(name: str) -> Optional[Dict[str, Any]]:
    """Get distribution spec by name (e.g., 'Normal'). Returns None if not found."""
    return REGISTRY.get("primitive_objects", {}).get("distributions", {}).get(name)


def is_distribution(name: str) -> bool:
    """Check if name is a registered distribution."""
    return name in REGISTRY.get("primitive_objects", {}).get("distributions", {})


# ---------------------------------------------------------------------------
# Alias resolution
# ---------------------------------------------------------------------------


def canonicalize(name: str) -> str:
    """Resolve alias to canonical form. Returns name unchanged if not an alias."""
    aliases = REGISTRY.get("aliases", {})
    return aliases.get(name, name)


def to_identifier_safe(name: str) -> str:
    """Convert canonical form to identifier-safe token (e.g., 'R+' -> 'R_plus')."""
    id_safe = REGISTRY.get("identifier_safe", {})
    return id_safe.get(name, name)


def from_identifier_safe(name: str) -> str:
    """Convert identifier-safe token back to canonical form."""
    # Reverse lookup
    id_safe = REGISTRY.get("identifier_safe", {})
    reverse = {v: k for k, v in id_safe.items()}
    return reverse.get(name, name)
