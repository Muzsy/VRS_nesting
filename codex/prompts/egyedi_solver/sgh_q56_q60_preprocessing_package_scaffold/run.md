# Runner — Q56–Q60 preprocessing package scaffold

Hajtsd végre a canvas + goal YAML alapján a `sgh_q56_q60_preprocessing_package_scaffold` taskot. Ez a
task **csak task package-eket** készít; nem implementál solver-logikát.

## Kötelező olvasnivaló

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
codex/prompts/task_runner_prompt_template.md
tmp/plans/q56_q60_preprocessing_tasks/00_README_TASK_SEQUENCE.md
canvases/egyedi_solver/sgh_q56_q60_preprocessing_package_scaffold.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56_q60_preprocessing_package_scaffold.yaml
```

## Canvas / YAML

- Canvas: `canvases/egyedi_solver/sgh_q56_q60_preprocessing_package_scaffold.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56_q60_preprocessing_package_scaffold.yaml`

## Kemény szabályok

- Csak `outputs`-ban szereplő fájlt hozhatsz létre / módosíthatsz.
- nincs Rust solver / worker runtime / API / quality profile módosítás
- nincs fixture átírás vagy benchmark hamisítás
- nincs PASS package-ready taskra
- nincs kitalált fájl/API (hiány esetén `DISCOVERED_MISMATCH: <path>`)
- a forrás markdown tasktervek (`tmp/plans/q56_q60_preprocessing_tasks/`) nem módosulnak

## Célzott ellenőrzés (sanity)

```bash
python3 - <<'PY'
from pathlib import Path
import yaml
slugs = [
 "sgh_q56a_orientation_catalog_alap",
 "sgh_q56b_part_analysis_shape_profile_v2",
 "sgh_q56b2_cavity_prepack_bridge_hints",
 "sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates",
 "sgh_q57a_pair_compatibility_index_critical_only",
 "sgh_q57b_pair_candidates_to_interlock_role",
 "sgh_q58a_sheet_feasibility_hints",
 "sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder",
 "sgh_q59_band_insert_true_extreme_slot_edge_placement",
 "sgh_q60_critical_triple_simultaneous_admission",
]
for slug in slugs:
    for p in [
        Path(f"canvases/egyedi_solver/{slug}.md"),
        Path(f"codex/goals/canvases/egyedi_solver/fill_canvas_{slug}.yaml"),
        Path(f"codex/prompts/egyedi_solver/{slug}/run.md"),
        Path(f"codex/codex_checklist/egyedi_solver/{slug}.md"),
        Path(f"codex/reports/egyedi_solver/{slug}.md"),
    ]:
        assert p.exists(), f"missing: {p}"
    data = yaml.safe_load(Path(f"codex/goals/canvases/egyedi_solver/fill_canvas_{slug}.yaml").read_text())
    assert isinstance(data, dict) and isinstance(data.get("steps"), list) and data["steps"]
    for step in data["steps"]:
        assert "name" in step and "description" in step and isinstance(step.get("outputs"), list)
    assert "verify.sh" in data["steps"][-1]["description"]
print("Q56-Q60 package sanity: OK")
PY
```

## Végső verify

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q56_q60_preprocessing_package_scaffold.md
```

## Checklist / report elvárás

Frissítsd a checklistet, a reportot (Standard v2, DoD→Evidence path+line) és a verify.log-ot. Ha a
verify piros, a self-report státusza nem lehet PASS — a failure-t őszintén dokumentáld.
