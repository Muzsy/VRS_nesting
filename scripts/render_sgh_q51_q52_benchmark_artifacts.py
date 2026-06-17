#!/usr/bin/env python3
"""Render SGH-Q51-Q52 benchmark solver outputs as SVG and PNG sheet plans."""
from __future__ import annotations

from render_sgh_q47_q50_benchmark_artifacts import render_run

RUNS = {
    51: [
        ("6big_sp0_builderon", "inputs/q51_6big_sp0.json", "outputs/6big_sp0_builderon_output.json"),
        ("6big_sp8_builderon", "inputs/q51_6big_sp8.json", "outputs/6big_sp8_builderon_output.json"),
        ("full276_builderon", "inputs/q51_full276_sp8.json", "outputs/full276_builderon_output.json"),
        ("full276_builderoff", "inputs/q51_full276_sp8.json", "outputs/full276_builderoff_output.json"),
    ],
    52: [
        ("6big_sp0_builderon", "inputs/q52_6big_sp0.json", "outputs/6big_sp0_builderon_output.json"),
        ("6big_sp5_bias", "inputs/q52_6big_sp5.json", "outputs/6big_sp5_bias_output.json"),
        ("6big_sp5_builderonly", "inputs/q52_6big_sp5.json", "outputs/6big_sp5_builderonly_output.json"),
        ("6big_sp8_bias", "inputs/q52_6big_sp8.json", "outputs/6big_sp8_bias_output.json"),
        ("6big_sp8_builderonly", "inputs/q52_6big_sp8.json", "outputs/6big_sp8_builderonly_output.json"),
        ("full276_bias", "inputs/q52_full276_sp8.json", "outputs/full276_bias_output.json"),
        ("full276_builderonly", "inputs/q52_full276_sp8.json", "outputs/full276_builderonly_output.json"),
        ("full276_off", "inputs/q52_full276_sp8.json", "outputs/full276_off_output.json"),
    ],
}


def main() -> int:
    manifests = []
    for task_no, runs in RUNS.items():
        for run_id, input_rel, output_rel in runs:
            manifest = render_run(task_no, run_id, input_rel, output_rel)
            manifests.append(manifest)
            print(
                f"[render] q{task_no} {run_id}: sheets={manifest['used_sheet_count']} "
                f"svg={manifest['svg_count']} png={manifest['png_count']}"
            )
    if not all(m["png_count"] == m["svg_count"] for m in manifests):
        raise SystemExit("not all SVG renders have matching PNG outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
