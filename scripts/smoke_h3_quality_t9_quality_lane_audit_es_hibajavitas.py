#!/usr/bin/env python3
"""Smoke for T9 closure-fix task.

Validates:
- nesting_engine_runner parser accepts --compaction slide
- main() forwards --compaction into nesting_engine_cli_args
- T1 smoke passes in the current repo state
- T1/T6 historical YAML outputs and report changed-files sections are consistent
"""

from __future__ import annotations

import re
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import vrs_nesting.runner.nesting_engine_runner as runner_mod  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _run_parser_command_check() -> None:
    cmd = [
        sys.executable,
        "-m",
        "vrs_nesting.runner.nesting_engine_runner",
        "--input",
        "/tmp/missing.json",
        "--seed",
        "1",
        "--time-limit",
        "1",
        "--compaction",
        "slide",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    _assert(proc.returncode == 2, f"unexpected return code for parser command check: {proc.returncode}")
    _assert(
        "unrecognized arguments: --compaction slide" not in (proc.stderr or ""),
        f"parser still rejects --compaction flag:\n{proc.stderr}",
    )


def _assert_parser_and_forwarding() -> None:
    parser = runner_mod.build_arg_parser()
    parsed = parser.parse_args(
        [
            "--input",
            "/tmp/fake.json",
            "--seed",
            "7",
            "--time-limit",
            "3",
            "--search",
            "sa",
            "--compaction",
            "slide",
        ]
    )
    _assert(parsed.compaction == "slide", f"parser compaction mismatch: {parsed.compaction}")

    try:
        with redirect_stderr(StringIO()):
            parser.parse_args(["--input", "/tmp/fake.json", "--seed", "1", "--time-limit", "1", "--compaction", "bad"])
    except SystemExit as exc:
        _assert(int(getattr(exc, "code", 1)) != 0, "invalid --compaction value should fail-fast")
    else:
        raise RuntimeError("invalid --compaction value unexpectedly accepted")

    captured: dict[str, Any] = {}
    original_runner: Callable[..., tuple[Path, dict[str, Any]]] = runner_mod.run_nesting_engine

    def _fake_run_nesting_engine(
        input_path: str,
        *,
        seed: int,
        time_limit_sec: int,
        run_root: str = "runs",
        nesting_engine_bin: str | None = None,
        nesting_engine_cli_args: list[str] | None = None,
    ) -> tuple[Path, dict[str, Any]]:
        captured["input_path"] = input_path
        captured["seed"] = seed
        captured["time_limit_sec"] = time_limit_sec
        captured["run_root"] = run_root
        captured["nesting_engine_bin"] = nesting_engine_bin
        captured["nesting_engine_cli_args"] = list(nesting_engine_cli_args or [])
        return Path("/tmp/t9_fake_run_dir"), {"ok": True}

    try:
        runner_mod.run_nesting_engine = _fake_run_nesting_engine  # type: ignore[assignment]
        with redirect_stdout(StringIO()):
            rc = runner_mod.main(
                [
                    "--input",
                    "/tmp/fake.json",
                    "--seed",
                    "9",
                    "--time-limit",
                    "5",
                    "--search",
                    "sa",
                    "--compaction",
                    "slide",
                ]
            )
    finally:
        runner_mod.run_nesting_engine = original_runner  # type: ignore[assignment]

    _assert(rc == 0, f"runner main returned non-zero in forwarding check: {rc}")
    cli_args = captured.get("nesting_engine_cli_args", [])
    _assert(isinstance(cli_args, list), f"captured cli args type mismatch: {type(cli_args)}")
    _assert("--compaction" in cli_args, f"--compaction missing from forwarded args: {cli_args}")
    compaction_index = cli_args.index("--compaction")
    _assert(compaction_index + 1 < len(cli_args), f"--compaction value missing in forwarded args: {cli_args}")
    _assert(cli_args[compaction_index + 1] == "slide", f"--compaction value mismatch: {cli_args}")


def _run_t1_smoke() -> None:
    cmd = [sys.executable, str(ROOT / "scripts" / "smoke_h3_quality_t1_engine_observability_and_artifact_truth.py")]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            "T1 smoke failed from T9 closure smoke\n"
            f"exit={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )


def _extract_yaml_outputs(yaml_path: Path) -> set[str]:
    outputs: set[str] = set()
    for line in yaml_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r'^\s*-\s+"([^"]+)"\s*$', line)
        if not match:
            continue
        candidate = match.group(1).strip()
        if "/" not in candidate:
            continue
        outputs.add(candidate)
    return outputs


def _extract_report_changed_files(report_path: Path) -> set[str]:
    text = report_path.read_text(encoding="utf-8")
    section_match = re.search(
        r"### 3\.1 Erintett fajlok(?P<section>.*?)(?:\n### 3\.2 |\n## 4\))",
        text,
        flags=re.DOTALL,
    )
    if not section_match:
        raise RuntimeError(f"report missing 3.1 Erintett fajlok section: {report_path}")
    section = section_match.group("section")
    paths: set[str] = set()
    for candidate in re.findall(r"`([^`]+)`", section):
        normalized = candidate.strip()
        if "/" not in normalized:
            continue
        paths.add(normalized)
    return paths


def _assert_historical_outputs_report_consistency() -> None:
    checks = (
        (
            ROOT / "codex" / "goals" / "canvases" / "web_platform" / "fill_canvas_h3_quality_t1_engine_observability_and_artifact_truth.yaml",
            ROOT / "codex" / "reports" / "web_platform" / "h3_quality_t1_engine_observability_and_artifact_truth.md",
            "T1",
        ),
        (
            ROOT / "codex" / "goals" / "canvases" / "web_platform" / "fill_canvas_h3_quality_t6_local_tool_backend_selector_and_ab_compare.yaml",
            ROOT / "codex" / "reports" / "web_platform" / "h3_quality_t6_local_tool_backend_selector_and_ab_compare.md",
            "T6",
        ),
    )

    for yaml_path, report_path, label in checks:
        outputs = _extract_yaml_outputs(yaml_path)
        changed_files = _extract_report_changed_files(report_path)
        missing = sorted(path for path in changed_files if path not in outputs)
        if missing:
            raise RuntimeError(
                f"{label} outputs/report drift: files listed in report 3.1 but missing from YAML outputs: {missing}"
            )


def main() -> int:
    _run_parser_command_check()
    _assert_parser_and_forwarding()
    _run_t1_smoke()
    _assert_historical_outputs_report_consistency()
    print("PASS smoke_h3_quality_t9_quality_lane_audit_es_hibajavitas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
