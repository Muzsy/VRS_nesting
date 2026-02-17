#!/usr/bin/env python3

from __future__ import annotations

import json
import stat
from pathlib import Path

from vrs_nesting.runner.sparrow_runner import run_sparrow


def _write_fake_sparrow(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]
if "-i" not in args:
    raise SystemExit(2)
input_path = Path(args[args.index("-i") + 1])
payload = json.loads(input_path.read_text(encoding="utf-8"))
name = str(payload.get("name", input_path.stem)).strip() or input_path.stem

final_payload = {
    "solution": {
        "strip_width": 1000.0,
        "density": 0.5,
        "layout": {"placed_items": []},
    }
}
out_dir = Path.cwd() / "output"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / f"final_{name}.json").write_text(json.dumps(final_payload), encoding="utf-8")
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def test_run_sparrow_uses_shared_run_dir_allocator_contract(tmp_path: Path):
    fake_sparrow = tmp_path / "fake_sparrow.py"
    _write_fake_sparrow(fake_sparrow)

    input_json = tmp_path / "instance.json"
    input_json.write_text(
        json.dumps(
            {
                "name": "allocator_contract",
                "strip_height": 1000.0,
                "items": [],
            }
        ),
        encoding="utf-8",
    )

    run_root = tmp_path / "runs"
    run_dir, meta = run_sparrow(
        str(input_json),
        seed=0,
        time_limit=5,
        run_root=str(run_root),
        sparrow_bin=str(fake_sparrow),
    )

    assert run_dir.is_dir()
    assert run_dir.parent == run_root.resolve()
    assert (run_dir / "out").is_dir()
    assert (run_dir / "run.log").is_file()
    assert (run_dir / "instance.json").is_file()
    assert (run_dir / "runner_meta.json").is_file()
    assert Path(str(meta.get("run_dir", ""))).resolve() == run_dir.resolve()
