# Runner — Q57A PairCompatibilityIndex critical-only

Hajtsd végre a canvas + goal YAML alapján a `sgh_q57a_pair_compatibility_index_critical_only` taskot.

## Kötelező olvasnivaló

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
tmp/plans/q56_q60_preprocessing_tasks/Q57A_PairCompatibilityIndex_critical_only.md
canvases/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q57a_pair_compatibility_index_critical_only.yaml
```

## Canvas / YAML

- Canvas: `canvases/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q57a_pair_compatibility_index_critical_only.yaml`

## Kemény szabályok

- Csak `outputs`-ban szereplő fájlt módosíts.
- nincs vak all-pairs számítás bounds nélkül; bounded + critical-only default
- nincs part-ID / LV8-specifikus hack (same-part pár OrientationCatalog + criticality alapján)
- nincs CDE/spacing nélküli pair suggestion tárolás production top-listában
- pair candidate nem kötelező superpart; Interlock viselkedés nem változik Q57B előtt
- pair_matrix.rs stub nem maradhat magyarázat nélkül (replace/extend/supersede)
- nincs NFP, nincs bbox collision shortcut, nincs spacing/margin gyengítés
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
- env-gate (VRS_PAIR_INDEX) default off → no-regression

## Célzott tesztek / runnerek

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml pair_compatibility_index
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
```

> cargo PATH: exportáld a `RUSTUP_HOME`/`CARGO_HOME`/toolchain-bin változókat futtatás előtt.

## Végső verify

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.md
```

## Checklist / report elvárás

Frissítsd a checklistet, a reportot (Standard v2, DoD→Evidence path+line) és a verify.log-ot. PASS csak
zöld verify + teljesült DoD esetén.
