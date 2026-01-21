"""
Operation Registry Loader (spec_0.1d)

Loads the operation registry for scheme validation.
Schemes are registered; methods are NOT (they are opaque/downstream-interpreted).

Usage:
    from dolang.operation_registry import load_operation_registry, get_registered_schemes

    registry = load_operation_registry()
    schemes = get_registered_schemes(registry)
    # {'expectation', 'maximization', 'interpolation', ...}
"""

from pathlib import Path
from typing import Set, Dict, Any, Optional
import yaml


__all__ = [
    "load_operation_registry",
    "get_registered_schemes",
    "is_registered_scheme",
]


_REGISTRY_PATH = Path(__file__).parent / "operation_registry.yaml"
_CACHED_REGISTRY: Optional[Dict] = None


def load_operation_registry(path: Optional[Path] = None) -> dict:
    """
    Load the operation registry.

    Args:
        path: Optional custom path. Defaults to bundled registry.

    Returns:
        Registry dict with 'version' and 'schemes' keys.
    """
    global _CACHED_REGISTRY

    if path is None:
        path = _REGISTRY_PATH
        if _CACHED_REGISTRY is not None:
            return _CACHED_REGISTRY

    with open(path, 'r', encoding='utf-8') as f:
        registry = yaml.safe_load(f)

    if path == _REGISTRY_PATH:
        _CACHED_REGISTRY = registry

    return registry


def get_registered_schemes(registry: Optional[dict] = None) -> Set[str]:
    """
    Get set of registered scheme names.

    Args:
        registry: Operation registry dict. Loads default if None.

    Returns:
        Set of scheme names, e.g. {'expectation', 'interpolation', ...}
    """
    if registry is None:
        registry = load_operation_registry()

    return set(registry.get('schemes', {}).keys())


def is_registered_scheme(scheme_name: str, registry: Optional[dict] = None) -> bool:
    """
    Check if a scheme name is registered.

    Args:
        scheme_name: Name to check
        registry: Operation registry dict. Loads default if None.

    Returns:
        True if scheme is registered
    """
    return scheme_name in get_registered_schemes(registry)


def get_scheme_info(scheme_name: str, registry: Optional[dict] = None) -> Optional[dict]:
    """
    Get information about a registered scheme.

    Args:
        scheme_name: Name of scheme
        registry: Operation registry dict. Loads default if None.

    Returns:
        Scheme info dict with 'description', 'expected_settings', 'common_methods'
        or None if not found.
    """
    if registry is None:
        registry = load_operation_registry()

    return registry.get('schemes', {}).get(scheme_name)
