"""Expose the chat backend lazily so independent APIs can import without it."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lwe.backends.api.backend import ApiBackend as ApiBackend

__all__ = ["ApiBackend"]


def __getattr__(name: str) -> object:
    """Load the historical public backend only when requested."""
    if name == "ApiBackend":
        from lwe.backends.api.backend import ApiBackend

        globals()[name] = ApiBackend
        return ApiBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
