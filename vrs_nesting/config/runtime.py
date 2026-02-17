#!/usr/bin/env python3
"""Centralized runtime configuration and defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


class RuntimeConfigError(ValueError):
    """Raised when runtime environment configuration is invalid."""


def _parse_int_env(
    env: Mapping[str, str],
    key: str,
    *,
    default: int,
    min_value: int | None = None,
) -> int:
    raw = env.get(key, "").strip()
    if not raw:
        value = default
    else:
        try:
            value = int(raw)
        except ValueError as exc:
            raise RuntimeConfigError(f"{key} must be integer (got: {raw!r})") from exc

    if min_value is not None and value < min_value:
        raise RuntimeConfigError(f"{key} must be >= {min_value} (got: {value})")
    return value


@dataclass(frozen=True)
class RuntimeDefaults:
    seed: int
    time_limit_s: int


@dataclass(frozen=True)
class SolverRuntimeConfig:
    seed: int
    time_limit_s: int
    solver_bin: str


@dataclass(frozen=True)
class SparrowRuntimeConfig:
    seed: int
    time_limit_s: int
    sparrow_bin: str


def runtime_defaults_from_env(env: Mapping[str, str] | None = None) -> RuntimeDefaults:
    source = os.environ if env is None else env
    seed = _parse_int_env(source, "VRS_RUNTIME_SEED", default=0, min_value=0)
    time_limit_s = _parse_int_env(source, "VRS_RUNTIME_TIME_LIMIT_S", default=60, min_value=1)
    return RuntimeDefaults(seed=seed, time_limit_s=time_limit_s)


def solver_runtime_from_env(env: Mapping[str, str] | None = None) -> SolverRuntimeConfig:
    source = os.environ if env is None else env
    defaults = runtime_defaults_from_env(source)
    seed = _parse_int_env(source, "VRS_SOLVER_SEED", default=defaults.seed, min_value=0)
    time_limit_s = _parse_int_env(source, "VRS_SOLVER_TIME_LIMIT_S", default=defaults.time_limit_s, min_value=1)
    solver_bin = source.get("VRS_SOLVER_BIN", "").strip() or "vrs_solver"
    return SolverRuntimeConfig(seed=seed, time_limit_s=time_limit_s, solver_bin=solver_bin)


def sparrow_runtime_from_env(env: Mapping[str, str] | None = None) -> SparrowRuntimeConfig:
    source = os.environ if env is None else env
    defaults = runtime_defaults_from_env(source)
    seed = _parse_int_env(source, "SPARROW_SEED", default=defaults.seed, min_value=0)
    time_limit_s = _parse_int_env(source, "SPARROW_TIME_LIMIT_S", default=defaults.time_limit_s, min_value=1)
    sparrow_bin = source.get("SPARROW_BIN", "").strip() or "sparrow"
    return SparrowRuntimeConfig(seed=seed, time_limit_s=time_limit_s, sparrow_bin=sparrow_bin)


def resolve_solver_bin_name(
    *,
    explicit_bin: str | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    """Resolve solver binary name/path from explicit override or runtime config."""
    if explicit_bin and explicit_bin.strip():
        return explicit_bin.strip()
    return solver_runtime_from_env(env).solver_bin


def resolve_sparrow_bin_name(
    *,
    explicit_bin: str | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    """Resolve Sparrow binary name/path from explicit override or runtime config."""
    if explicit_bin and explicit_bin.strip():
        return explicit_bin.strip()
    return sparrow_runtime_from_env(env).sparrow_bin
