#!/usr/bin/env python3
"""Common solver adapter boundary for runner backends."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol


class SolverAdapterError(RuntimeError):
    """Unified adapter error for backend runner failures."""

    def __init__(self, adapter_name: str, message: str) -> None:
        super().__init__(message)
        self.adapter_name = adapter_name


class SolverAdapter(Protocol):
    """Unified solver execution contract for in-dir runs."""

    @property
    def name(self) -> str:
        ...

    def run_in_dir(
        self,
        *,
        input_path: str,
        run_dir: str | Path,
        seed: int,
        time_limit_s: int,
        solver_bin: str | None = None,
    ) -> tuple[Path, dict[str, Any]]:
        ...


RunnerFn = Callable[[str, str | Path, int, int, str | None], tuple[Path, dict[str, Any]]]


@dataclass(frozen=True)
class FunctionSolverAdapter:
    """Adapter backed by a concrete runner function."""

    name: str
    runner_fn: RunnerFn
    handled_error_types: tuple[type[BaseException], ...]

    def run_in_dir(
        self,
        *,
        input_path: str,
        run_dir: str | Path,
        seed: int,
        time_limit_s: int,
        solver_bin: str | None = None,
    ) -> tuple[Path, dict[str, Any]]:
        try:
            return self.runner_fn(input_path, run_dir, seed, time_limit_s, solver_bin)
        except self.handled_error_types as exc:
            raise SolverAdapterError(self.name, str(exc)) from exc


def _run_vrs_solver_in_dir(
    input_path: str,
    run_dir: str | Path,
    seed: int,
    time_limit_s: int,
    solver_bin: str | None,
) -> tuple[Path, dict[str, Any]]:
    from vrs_nesting.runner.vrs_solver_runner import run_solver_in_dir

    return run_solver_in_dir(
        input_path,
        run_dir=run_dir,
        seed=seed,
        time_limit_s=time_limit_s,
        solver_bin=solver_bin,
    )


def _run_sparrow_in_dir(
    input_path: str,
    run_dir: str | Path,
    seed: int,
    time_limit_s: int,
    solver_bin: str | None,
) -> tuple[Path, dict[str, Any]]:
    from vrs_nesting.runner.sparrow_runner import run_sparrow_in_dir

    return run_sparrow_in_dir(
        input_path,
        run_dir=run_dir,
        seed=seed,
        time_limit=time_limit_s,
        sparrow_bin=solver_bin,
    )


def build_vrs_solver_adapter() -> SolverAdapter:
    from vrs_nesting.runner.vrs_solver_runner import VrsSolverRunnerError

    return FunctionSolverAdapter(
        name="vrs_solver",
        runner_fn=_run_vrs_solver_in_dir,
        handled_error_types=(VrsSolverRunnerError,),
    )


def build_sparrow_solver_adapter() -> SolverAdapter:
    from vrs_nesting.runner.sparrow_runner import SparrowRunnerError

    return FunctionSolverAdapter(
        name="sparrow",
        runner_fn=_run_sparrow_in_dir,
        handled_error_types=(SparrowRunnerError,),
    )
