# Runner — Q57B Pair candidate-ek → Interlock role

Hajtsd végre a canvas + goal YAML alapján a `sgh_q57b_pair_candidates_to_interlock_role` taskot.

## Kötelező olvasnivaló

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
tmp/plans/q56_q60_preprocessing_tasks/Q57B_Pair_candidates_to_Interlock_role.md
canvases/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q57b_pair_candidates_to_interlock_role.yaml
```

Előfeltétel: Q57A `PairCompatibilityIndex` elérhető.

## Canvas / YAML

- Canvas: `canvases/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q57b_pair_candidates_to_interlock_role.yaml`

## Kemény szabályok

- Csak `outputs`-ban szereplő fájlt módosíts.
- pair candidate nem kötelező superpart
- a neighbour feature candidate fallback nem távolítható el (megőrizve + logolva)
- pair transzform CDE validáció nélkül nem fogadható el
- a placement origin szemantika bizonyítva, nem feltételezve (transzform matek logolva)
- bbox overlap nem clearance truth; nincs part-ID / LV8 hardcode
- nincs NFP, nincs spacing/margin gyengítés
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
- env-gate default off → no-regression

## Célzott tesztek / runnerek

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml interlock_pair
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_sheet_skeleton
```

> cargo PATH: exportáld a `RUSTUP_HOME`/`CARGO_HOME`/toolchain-bin változókat futtatás előtt.

## Végső verify

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.md
```

## Checklist / report elvárás

Frissítsd a checklistet, a reportot (Standard v2, DoD→Evidence path+line) és a verify.log-ot. PASS csak
zöld verify + teljesült DoD esetén.
