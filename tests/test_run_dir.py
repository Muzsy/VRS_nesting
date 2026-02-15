#!/usr/bin/env python3

from pathlib import Path

from vrs_nesting.run_artifacts.run_dir import append_run_log, create_run_dir, write_project_snapshot


def test_create_run_dir_and_helpers(tmp_path):
    run_root = tmp_path / "runs"

    ctx = create_run_dir(run_root=str(run_root))

    assert ctx.run_dir.is_dir()
    assert ctx.out_dir.is_dir()
    assert ctx.run_log_path.is_file()

    snapshot_path = write_project_snapshot(ctx.run_dir, {"name": "demo", "version": "v1"})
    assert snapshot_path == ctx.run_dir / "project.json"
    assert snapshot_path.is_file()

    append_run_log(ctx.run_log_path, "EVENT_A", "first")
    append_run_log(ctx.run_log_path, "EVENT_B", "second")

    lines = ctx.run_log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 2
    assert "EVENT_A first" in lines[-2]
    assert "EVENT_B second" in lines[-1]
    assert Path(snapshot_path).read_text(encoding="utf-8").strip().startswith("{")
