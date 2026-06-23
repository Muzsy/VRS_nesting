# Runner — Q56B PartAnalysis / ShapeProfileV2

Hajtsd végre a canvas + goal YAML alapján a `sgh_q56b_part_analysis_shape_profile_v2` taskot.

## Kötelező olvasnivaló

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
tmp/plans/q56_q60_preprocessing_tasks/Q56B_PartAnalysis_ShapeProfileV2.md
canvases/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56b_part_analysis_shape_profile_v2.yaml
```

## Canvas / YAML

- Canvas: `canvases/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56b_part_analysis_shape_profile_v2.yaml`

Hajtsd végre a YAML `steps` lépéseit sorrendben.

## Kemény szabályok

- Csak `outputs`-ban szereplő fájlt módosíts.
- Valós repo alapján dolgozz; ne találj ki API-t. Hiány esetén `DISCOVERED_MISMATCH`/`BLOCKED`/`DEVIATION`.
- nincs párhuzamos konfliktusos profilrendszer; a régit nem hagyod aktívan ütköző döntésekkel
- nincs part-ID alapú osztályozás
- shape tag nem exact collision/fit proof; nincs bbox collision shortcut
- nincs NFP-visszahozás
- nincs spacing/margin gyengítés
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe (worker prepack tisztelete)
- CDE/final exact validation marad az igazság

## Célzott tesztek / runnerek

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml part_analysis
cargo test --manifest-path rust/vrs_solver/Cargo.toml shape_profile
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
```

> cargo PATH: exportáld a `RUSTUP_HOME`/`CARGO_HOME`/toolchain-bin változókat futtatás előtt.

## Végső verify

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.md
```

## Checklist / report elvárás

Frissítsd a checklistet, a reportot (Standard v2, DoD→Evidence path+line) és a verify.log-ot. PASS csak
zöld verify + teljesült DoD esetén. A végén add meg a módosított fájlok listáját és a gate eredményét.
