#!/usr/bin/env python3
"""Validate VRS nesting solver output invariants for table-solver flow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from vrs_nesting.nesting.instances import validate_multi_sheet_output


class ValidationError(RuntimeError):
    """Raised when the nesting output is invalid."""


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise ValidationError(f"missing file: {path}")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid json {path}: line={exc.lineno} col={exc.colno}") from exc
    if not isinstance(loaded, dict):
        raise ValidationError(f"top-level json object required: {path}")
    return loaded


def resolve_paths(run_dir: Path | None, input_path: Path | None, output_path: Path | None) -> tuple[Path, Path]:
    if run_dir is not None:
        return run_dir / "solver_input.json", run_dir / "solver_output.json"
    if input_path is None or output_path is None:
        raise ValidationError("provide either --run-dir OR both --input and --output")
    return input_path, output_path


def validate_nesting_solution(input_path: Path, output_path: Path) -> None:
    input_payload = _read_json(input_path)
    output_payload = _read_json(output_path)
    validate_multi_sheet_output(input_payload, output_payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate table-solver nesting output invariants")
    parser.add_argument("--run-dir", default=None, help="Run directory containing solver_input.json and solver_output.json")
    parser.add_argument("--input", default=None, help="Path to solver_input.json")
    parser.add_argument("--output", default=None, help="Path to solver_output.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir).resolve() if args.run_dir else None
    input_path = Path(args.input).resolve() if args.input else None
    output_path = Path(args.output).resolve() if args.output else None

    try:
        resolved_input, resolved_output = resolve_paths(run_dir, input_path, output_path)
        validate_nesting_solution(resolved_input, resolved_output)
    except ValidationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: unexpected validator error: {exc}", file=sys.stderr)
        return 2

    print("PASS: nesting solution is valid")
    print(f" input={resolved_input}")
    print(f" output={resolved_output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
