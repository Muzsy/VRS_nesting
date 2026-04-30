#!/usr/bin/env python3
"""Smoke for cavity T7 UI observability wiring."""

from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_contains(rel: str, needle: str) -> None:
    text = _read(rel)
    _assert(needle in text, f"missing marker in {rel}: {needle}")


def _assert_no_new_run_wizard_diff() -> None:
    out = subprocess.check_output(
        ["git", "diff", "--name-only"],
        cwd=ROOT,
        text=True,
    )
    changed = [line.strip() for line in out.splitlines() if line.strip()]
    touched_wizard = [
        path
        for path in changed
        if "new_run_wizard" in path.lower() or "wizard" in path.lower() and "run_detail" not in path.lower()
    ]
    _assert(
        not touched_wizard,
        f"unexpected New Run Wizard related changes in T7 scope: {touched_wizard}",
    )


def main() -> int:
    _assert_contains("api/routes/files.py", '"cavity_observability": _build_cavity_observability_from_acceptance_summary')
    _assert_contains("api/routes/runs.py", "cavity_prepack_summary")
    _assert_contains("frontend/src/lib/types.ts", "PreflightCavityObservability")
    _assert_contains("frontend/src/lib/types.ts", "cavity_prepack_summary")
    _assert_contains("frontend/src/lib/api.ts", "normalizePreflightCavityObservability")
    _assert_contains("frontend/src/lib/dxfIntakePresentation.ts", "section_cavity")
    _assert_contains("frontend/src/pages/DxfIntakePage.tsx", "INTAKE_COPY.diagnostics.section_cavity")
    _assert_contains("frontend/src/pages/RunDetailPage.tsx", "Cavity prepack summary")
    _assert_contains("frontend/e2e/cavity_prepack_observability.spec.ts", "DXF Intake diagnostics drawer shows cavity observability")

    _assert_no_new_run_wizard_diff()
    print("[smoke_cavity_t7_ui_observability] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
