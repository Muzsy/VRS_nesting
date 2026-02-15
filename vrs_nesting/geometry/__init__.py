"""Geometry preprocessing helpers for polygon clean + offset pipeline."""

from vrs_nesting.geometry.clean import GeometryCleanError

__all__ = ["GeometryCleanError", "GeometryOffsetError"]


def __getattr__(name: str) -> object:
    if name == "GeometryOffsetError":
        # Keep package-level API without forcing shapely import at module load time.
        from vrs_nesting.geometry.offset import GeometryOffsetError

        return GeometryOffsetError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
