"""Runner utilities for Sparrow orchestration."""

from .solver_adapter import SolverAdapterError

__all__ = [
    "resolve_sparrow_bin",
    "run_sparrow",
    "build_sparrow_solver_adapter",
    "build_vrs_solver_adapter",
    "SolverAdapterError",
]


def resolve_sparrow_bin(explicit_bin=None):
    from .sparrow_runner import resolve_sparrow_bin as _resolve_sparrow_bin

    return _resolve_sparrow_bin(explicit_bin)


def run_sparrow(input_path, *, seed, time_limit, run_root="runs", sparrow_bin=None):
    from .sparrow_runner import run_sparrow as _run_sparrow

    return _run_sparrow(
        input_path,
        seed=seed,
        time_limit=time_limit,
        run_root=run_root,
        sparrow_bin=sparrow_bin,
    )


def build_sparrow_solver_adapter():
    from .solver_adapter import build_sparrow_solver_adapter as _build_sparrow_solver_adapter

    return _build_sparrow_solver_adapter()


def build_vrs_solver_adapter():
    from .solver_adapter import build_vrs_solver_adapter as _build_vrs_solver_adapter

    return _build_vrs_solver_adapter()
