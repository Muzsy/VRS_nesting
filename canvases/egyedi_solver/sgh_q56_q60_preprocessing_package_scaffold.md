# Q56–Q60 preprocessing package scaffold

## Goal / Funkció

Repo-kompatibilis `canvas + goal YAML + runner + checklist + report skeleton` csomagok előállítása a
már elkészített Q56–Q60 preprocessing markdown taskokból. Ez a task **nem implementál solver-logikát**;
csak task package-eket készít a repo meglévő szabályai, mintái és a valós kód alapján, hogy a következő
fejlesztési taskok egyesével, Codex/Hermes agenttel futtathatóak legyenek.

## Context / Háttér

A forrás tasktervek: `tmp/plans/q56_q60_preprocessing_tasks/`. A package-generálás nem mozgatja, nem
írja át és nem törli ezeket a forrásterveket. A 10 fejlesztési task (Q56A → Q60) mindegyikéhez teljes
package készül; plusz egy task-index és master runner, valamint ez a self-package.

## Source of truth

- `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
  `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`,
  `codex/prompts/task_runner_prompt_template.md`
- Forrástervek: `tmp/plans/q56_q60_preprocessing_tasks/*.md`
- Repo-minták: `sgh_q55f_*`, `sgh_q53a_*`, `sgh_q15_*`, `jagua_optimizer_t00_*` package-ek.

## Existing code anchors

A csomagok valós kódhorgonyokra hivatkoznak (auditálva, léteznek):

- `rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs`, `contour_features.rs`, `model.rs`,
  `feature_candidate_generator.rs`, `sheet_skeleton.rs`, `bpp_reduction.rs`, `fixed_sheet.rs`,
  `quantify/pair_matrix.rs`, `mod.rs`; `rust/vrs_solver/src/io.rs`.
- `worker/cavity_prepack.py`, `worker/cavity_validation.py`, `worker/result_normalizer.py`,
  `worker/engine_adapter_input.py`, `worker/main.py`.
- `scripts/verify.sh`, `scripts/render_sgh_q56_one_part_edge.py`, és a Q47/Q52/Q53/Q54 bench scriptek.

## Valós repo anchorok

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
codex/prompts/task_runner_prompt_template.md
scripts/verify.sh
tmp/plans/q56_q60_preprocessing_tasks/
canvases/egyedi_solver/sgh_q55f_runner_primary_acceptance.md
canvases/egyedi_solver/sgh_q53a_contour_feature_extraction.md
canvases/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
```

## Scope

- 10 Q56–Q60 task package (canvas + YAML + runner + checklist + report skeleton).
- Task-index (`sgh_q56_q60_preprocessing_task_index.md`) + master runner
  (`sgh_q56_q60_preprocessing_master_runner.md`).
- Ez a self-package (canvas + YAML + runner + checklist + report).
- Sanity ellenőrzés (Python) + `verify.sh` repo gate.

## Out of scope

```text
- Rust solver implementáció írása
- worker runtime logika módosítása
- API / quality profile módosítás
- fixture átírás vagy benchmark hamisítás
- PASS írása package-ready taskra
- hiányzó fájl/API kitalálása
- a forrás markdown tasktervek átírása
```

## Required implementation

- Minden canvas a repo-standard szekciókat tartalmazza, plusz egy `## Valós repo anchorok` blokkot
  valós, megtalált fájlokkal.
- Minden goal YAML kizárólag a `steps` sémát használja; az utolsó step a "Repo gate (automatikus
  verify)", `verify.sh` paranccsal, és a report + verify.log outputtal. A YAML outputs listák minden
  fájlt tartalmaznak, amit az adott implementációs task később módosíthat.
- Minden runner önállóan használható: kötelező olvasnivaló, canvas/YAML path, kemény szabályok,
  célzott test/runner parancsok, végső verify, checklist/report frissítési elvárás, task-specifikus
  tilalmak.
- Minden checklist tartalmazza a generikus DoD-ot és a task-specifikus kapukat.
- Minden report skeleton a Report Standard v2-t követi, `STATUS: PACKAGE_READY_IMPLEMENTATION_NOT_RUN`
  alapállással és AUTO_VERIFY placeholderrel. Nincs előre írt PASS.
- Q56B2 helyesen kezeli: a cavity prepack v2 már meglévő worker/pre-solver réteg.

## Required diagnostics

A self-package nem termel solver artifactot. A "diagnosztika" itt a sanity ellenőrzés kimenete
(`Q56-Q60 package sanity: OK`) és a `verify.sh` által generált AUTO_VERIFY blokk + verify.log.

## Required tests / runners

Sanity (Python) — minden slug 5 fájlja létezik, és a YAML steps séma + utolsó verify step teljesül:

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

Repo gate:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q56_q60_preprocessing_package_scaffold.md
```

## Acceptance criteria

```text
- mind a 10 Q56–Q60 task package létrejött;
- minden package canvas + YAML + runner + checklist + report skeleton fájlt tartalmaz;
- minden YAML megfelel a docs/codex/yaml_schema.md steps sémának;
- minden runner önállóan használható;
- minden canvas valós repo anchorokra hivatkozik;
- Q56B2 helyesen kezeli, hogy a cavity prepack v2 már meglévő worker/pre-solver réteg;
- nincs solver/runtime implementáció ebben a taskban;
- a self-report kitölti a DoD→Evidence mátrixot;
- a standard verify wrapper lefutott, vagy a failure őszintén dokumentált.
```

## Hard restrictions

```text
- nincs Rust solver / worker runtime / API / quality profile módosítás
- nincs fixture átírás vagy benchmark hamisítás
- nincs PASS package-ready taskra
- nincs kitalált fájl/API
- a forrás markdown tasktervek nem módosulnak
```

## Rollback

- A csomagok újonnan létrehozott dokumentációs/Codex artefaktok; ha valamelyik hibás, töröld/írd
  felül az adott fájlt — production kód nem érintett, így rollback-kockázat nincs.

## Deliverables

A 10 task package (lásd lent a YAML outputs listáját), a task-index, a master runner, és ez a
self-package (canvas + YAML + runner + checklist + report + verify.log).
