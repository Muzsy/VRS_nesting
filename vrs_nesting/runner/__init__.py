"""Runner utilities for Sparrow orchestration."""

__all__ = ["resolve_sparrow_bin", "run_sparrow"]


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
