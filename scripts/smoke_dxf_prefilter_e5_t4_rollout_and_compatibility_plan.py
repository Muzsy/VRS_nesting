#!/usr/bin/env python3
"""DXF Prefilter E5-T4 structural smoke.

Deterministic checks only (no backend/frontend runtime execution).
Validates that the rollout+compatibility doc:
1. exists and references current-code canonical flags,
2. states explicit ON/OFF behavior truth,
3. contains ON/OFF matrix + support checklist + metrics plan,
4. does not claim new project-level rollout flag or runtime frontend config endpoint.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "web_platform" / "architecture" / "dxf_prefilter_rollout_and_compatibility_plan.md"

REQUIRED_TOKENS = [
    "API_DXF_PREFLIGHT_REQUIRED",
    "DXF_PREFLIGHT_REQUIRED",
    "VITE_DXF_PREFLIGHT_ENABLED",
    "rollout OFF eseten a `complete_upload` legacy direct geometry import helperre esik vissza",
    "rollout OFF eseten a `replace_file` gate-elve van",
    "rollout OFF eseten a DXF Intake route/CTA nem latszik",
]

REQUIRED_SECTIONS = [
    "## 4. ON/OFF viselkedesi matrix",
    "## 8. Support/debug checklist",
    "## 9. Rollout metrika terv",
    "## 10. Legacy sunset kriteriumok",
]

REQUIRED_METRIC_TOKENS = [
    "accepted_for_import",
    "preflight_review_required",
    "preflight_rejected",
]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(f"FAIL: {message}")


def _assert_contains_all(content: str, tokens: list[str], *, label: str) -> None:
    haystack = content.lower()
    for token in tokens:
        _assert(token.lower() in haystack, f"missing {label} token: {token!r}")


def _assert_no_positive_claim(lines: list[str], *, keywords: tuple[str, ...], label: str) -> None:
    negations = ("nem", "nincs", "tilos", "out-of-scope", "anti-scope", "korlatozas")
    for idx, line in enumerate(lines, start=1):
        lowered = line.lower()
        if all(keyword in lowered for keyword in keywords):
            if not any(neg in lowered for neg in negations):
                raise AssertionError(
                    f"FAIL: suspicious positive {label} claim at line {idx}: {line.strip()!r}"
                )


def main() -> None:
    print("=== smoke_dxf_prefilter_e5_t4_rollout_and_compatibility_plan ===")

    _assert(DOC.is_file(), f"missing rollout document: {DOC}")
    content = DOC.read_text(encoding="utf-8")
    lines = content.splitlines()

    _assert_contains_all(content, REQUIRED_TOKENS, label="required")
    print("  [OK] Canonical flags + explicit ON/OFF truths are present")

    _assert_contains_all(content, REQUIRED_SECTIONS, label="required-section")
    print("  [OK] Required sections are present (matrix/checklist/metrics/sunset)")

    _assert_contains_all(content, REQUIRED_METRIC_TOKENS, label="required-metric")
    print("  [OK] Required acceptance outcome metrics are present")

    _assert_no_positive_claim(
        lines,
        keywords=("project-level", "rollout", "flag"),
        label="project-level rollout flag",
    )
    print("  [OK] No positive claim about new project-level rollout flag")

    _assert_no_positive_claim(
        lines,
        keywords=("runtime", "frontend", "config", "endpoint"),
        label="runtime frontend config endpoint",
    )
    print("  [OK] No positive claim about runtime frontend config endpoint")

    print("All checks passed.")


if __name__ == "__main__":
    main()
