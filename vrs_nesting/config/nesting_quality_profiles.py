#!/usr/bin/env python3
"""Canonical nesting quality profile registry for nesting_engine_v2 runtime policy."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

DEFAULT_QUALITY_PROFILE = "quality_default"

VALID_PLACERS = ("blf", "nfp")
VALID_SEARCH_MODES = ("none", "sa")
VALID_PART_IN_PART_MODES = ("off", "auto", "prepack")
VALID_COMPACTION_MODES = ("off", "slide")

_RUNTIME_POLICY_KEYS = (
    "placer",
    "search",
    "part_in_part",
    "compaction",
    "sa_iters",
    "sa_temp_start",
    "sa_temp_end",
    "sa_seed",
    "sa_eval_budget_sec",
    "nfp_kernel",
)

VALID_NFP_KERNELS = ("old_concave", "cgal_reference")

_QUALITY_PROFILE_REGISTRY: dict[str, dict[str, Any]] = {
    "fast_preview": {
        "placer": "blf",
        "search": "none",
        "part_in_part": "off",
        "compaction": "off",
    },
    "quality_default": {
        "placer": "nfp",
        "search": "sa",
        "part_in_part": "auto",
        "compaction": "slide",
    },
    "quality_aggressive": {
        "placer": "nfp",
        "search": "sa",
        "part_in_part": "auto",
        "compaction": "slide",
        "sa_iters": 768,
        "sa_eval_budget_sec": 1,
    },
    "quality_cavity_prepack": {
        "placer": "nfp",
        "search": "sa",
        "part_in_part": "prepack",
        "compaction": "slide",
    },
    # T06g: explicit dev/reference profile — cavity_prepack with CGAL reference NFP kernel.
    # cgal_reference is NOT production. It is used for developmental correctness
    # benchmarking when the OldConcave kernel times out on LV8-scale concave geometry.
    # Do NOT promote cgal_reference to production default.
    "quality_cavity_prepack_cgal_reference": {
        "placer": "nfp",
        "search": "sa",
        "part_in_part": "prepack",
        "compaction": "slide",
        "nfp_kernel": "cgal_reference",
    },
}

VALID_QUALITY_PROFILE_NAMES = tuple(sorted(_QUALITY_PROFILE_REGISTRY.keys()))


def _parse_optional_int(value: Any, *, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"invalid {field}")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field}") from exc
    if parsed <= 0:
        raise ValueError(f"invalid {field}")
    return parsed


def normalize_quality_profile_name(raw: str | None, *, default: str = DEFAULT_QUALITY_PROFILE) -> str:
    candidate = str(raw or "").strip() or default
    if candidate not in _QUALITY_PROFILE_REGISTRY:
        valid = ", ".join(VALID_QUALITY_PROFILE_NAMES)
        raise ValueError(f"unsupported quality profile: {candidate} (valid: {valid})")
    return candidate


def validate_runtime_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, Mapping):
        raise ValueError("invalid runtime policy")

    placer = str(policy.get("placer") or "").strip().lower()
    if placer not in VALID_PLACERS:
        raise ValueError("invalid runtime policy placer")

    search = str(policy.get("search") or "").strip().lower()
    if search not in VALID_SEARCH_MODES:
        raise ValueError("invalid runtime policy search")

    part_in_part = str(policy.get("part_in_part") or policy.get("part-in-part") or "").strip().lower()
    if part_in_part not in VALID_PART_IN_PART_MODES:
        raise ValueError("invalid runtime policy part_in_part")

    compaction = str(policy.get("compaction") or "").strip().lower()
    if compaction not in VALID_COMPACTION_MODES:
        raise ValueError("invalid runtime policy compaction")

    normalized: dict[str, Any] = {
        "placer": placer,
        "search": search,
        "part_in_part": part_in_part,
        "compaction": compaction,
    }

    sa_fields = (
        "sa_iters",
        "sa_temp_start",
        "sa_temp_end",
        "sa_seed",
        "sa_eval_budget_sec",
    )
    for field in sa_fields:
        parsed = _parse_optional_int(policy.get(field), field=field)
        if parsed is not None:
            normalized[field] = parsed

    has_sa_overrides = any(field in normalized for field in sa_fields)
    if search != "sa" and has_sa_overrides:
        raise ValueError("SA runtime flags require search='sa'")

    nfp_kernel_raw = policy.get("nfp_kernel")
    if nfp_kernel_raw is not None:
        nfp_kernel_str = str(nfp_kernel_raw or "").strip().lower()
        if nfp_kernel_str not in VALID_NFP_KERNELS:
            raise ValueError(f"invalid nfp_kernel: {nfp_kernel_raw!r} (valid: {', '.join(VALID_NFP_KERNELS)})")
        normalized["nfp_kernel"] = nfp_kernel_str

    return normalized


def runtime_policy_for_quality_profile(name: str | None) -> dict[str, Any]:
    resolved = normalize_quality_profile_name(name)
    policy = validate_runtime_policy(_QUALITY_PROFILE_REGISTRY[resolved])
    policy["quality_profile"] = resolved
    return policy


def get_quality_profile_registry() -> dict[str, dict[str, Any]]:
    return deepcopy(_QUALITY_PROFILE_REGISTRY)


def get_quality_profile_policy(name: str | None) -> dict[str, Any]:
    resolved = normalize_quality_profile_name(name)
    return runtime_policy_for_quality_profile(resolved)


def build_nesting_engine_cli_args_from_runtime_policy(policy: Mapping[str, Any]) -> list[str]:
    normalized = validate_runtime_policy(policy)
    requested_part_in_part = str(normalized["part_in_part"])
    effective_engine_part_in_part = "off" if requested_part_in_part == "prepack" else requested_part_in_part

    args: list[str] = [
        "--placer",
        str(normalized["placer"]),
        "--search",
        str(normalized["search"]),
        "--part-in-part",
        effective_engine_part_in_part,
        "--compaction",
        str(normalized["compaction"]),
    ]

    if str(normalized["search"]) == "sa":
        if "sa_iters" in normalized:
            args.extend(["--sa-iters", str(normalized["sa_iters"])])
        if "sa_temp_start" in normalized:
            args.extend(["--sa-temp-start", str(normalized["sa_temp_start"])])
        if "sa_temp_end" in normalized:
            args.extend(["--sa-temp-end", str(normalized["sa_temp_end"])])
        if "sa_seed" in normalized:
            args.extend(["--sa-seed", str(normalized["sa_seed"])])
        if "sa_eval_budget_sec" in normalized:
            args.extend(["--sa-eval-budget-sec", str(normalized["sa_eval_budget_sec"])])

    # T06g: --nfp-kernel for explicit NFP kernel selection (dev/reference profiles only).
    if "nfp_kernel" in normalized:
        args.extend(["--nfp-kernel", str(normalized["nfp_kernel"])])

    return args


def build_nesting_engine_cli_args_for_quality_profile(name: str | None) -> list[str]:
    policy = runtime_policy_for_quality_profile(name)
    return build_nesting_engine_cli_args_from_runtime_policy(policy)


def compact_runtime_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_runtime_policy(policy)
    out = {
        "placer": normalized["placer"],
        "search": normalized["search"],
        "part_in_part": normalized["part_in_part"],
        "compaction": normalized["compaction"],
    }
    for field in _RUNTIME_POLICY_KEYS:
        if field in out:
            continue
        if field in normalized:
            out[field] = normalized[field]
    return out


__all__ = [
    "DEFAULT_QUALITY_PROFILE",
    "VALID_QUALITY_PROFILE_NAMES",
    "VALID_NFP_KERNELS",
    "build_nesting_engine_cli_args_for_quality_profile",
    "build_nesting_engine_cli_args_from_runtime_policy",
    "compact_runtime_policy",
    "get_quality_profile_policy",
    "get_quality_profile_registry",
    "normalize_quality_profile_name",
    "runtime_policy_for_quality_profile",
    "validate_runtime_policy",
]
