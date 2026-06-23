# Runner — Q60 Critical triple / simultaneous admission

Hajtsd végre a canvas + goal YAML alapján a `sgh_q60_critical_triple_simultaneous_admission` taskot.

## Kötelező olvasnivaló

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
tmp/plans/q56_q60_preprocessing_tasks/Q60_Critical_triple_simultaneous_admission.md
canvases/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q60_critical_triple_simultaneous_admission.yaml
```

Előfeltétel: Q56C, Q57A/B, Q58A/B, Q59 preprocessing rétegek elérhetők.

## Canvas / YAML

- Canvas: `canvases/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q60_critical_triple_simultaneous_admission.yaml`

## Kemény szabályok

- Csak `outputs`-ban szereplő fájlt módosíts.
- nincs ál-simultaneous (szekvenciális berakás a korábbi kritikus partok mozgatása nélkül)
- valid best partial nem dobható el
- nincs spacing/margin csökkentés; nincs LV8 part-name / koordináta hardcode
- nincs bbox-only collision check; nem válhat unbounded all-part global optimizerré
- timeout/failure nem rejthető el sikerként (spacing=0 siker önmagában nem siker)
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
- VRS_SIMULTANEOUS_CRITICAL gate default off → no-regression

## Célzott tesztek / runnerek

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml critical_simultaneous
VRS_SIMULTANEOUS_CRITICAL=1 cargo test --manifest-path rust/vrs_solver/Cargo.toml critical_simultaneous
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
```

> cargo PATH: exportáld a `RUSTUP_HOME`/`CARGO_HOME`/toolchain-bin változókat futtatás előtt.

## Végső verify

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.md
```

## Checklist / report elvárás

Frissítsd a checklistet, a reportot (Standard v2, DoD→Evidence path+line) és a verify.log-ot. A
reportban jelentsd a fókuszált 3-kritikus eredményt valós spacingnél, hogy a full 3 sikerült-e vagy a
best partial maradt meg, és a fennmaradó blockereket. PASS csak zöld verify + teljesült DoD esetén.
