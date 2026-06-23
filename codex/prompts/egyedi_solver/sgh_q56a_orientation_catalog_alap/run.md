# Runner — Q56A OrientationCatalog alap

Hajtsd végre a canvas + goal YAML alapján a `sgh_q56a_orientation_catalog_alap` taskot.

## Kötelező olvasnivaló

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
tmp/plans/q56_q60_preprocessing_tasks/Q56A_OrientationCatalog_alap.md
canvases/egyedi_solver/sgh_q56a_orientation_catalog_alap.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56a_orientation_catalog_alap.yaml
```

## Canvas / YAML

- Canvas: `canvases/egyedi_solver/sgh_q56a_orientation_catalog_alap.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56a_orientation_catalog_alap.yaml`

Hajtsd végre a YAML `steps` lépéseit sorrendben.

## Kemény szabályok

- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.
- Valós repo alapján dolgozz; ne találj ki nem létező API-t. Ha valami hiányzik, jelöld
  `DISCOVERED_MISMATCH: <path>` / `BLOCKED` / `DEVIATION` státusszal.
- nincs NFP-visszahozás
- nincs bbox collision shortcut (part.width/height nem lehet final extrema)
- nincs part-id hack
- nincs spacing/margin gyengítés
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság

## Célzott tesztek / runnerek

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml orientation_catalog
cargo test --manifest-path rust/vrs_solver/Cargo.toml shape_profile
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
```

> Megjegyzés: cargo a default PATH-on nem feltétlenül elérhető — exportáld a
> `RUSTUP_HOME`/`CARGO_HOME`/toolchain-bin változókat futtatás előtt.

## Végső verify

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q56a_orientation_catalog_alap.md
```

## Checklist / report elvárás

A végén frissítsd:

```text
codex/codex_checklist/egyedi_solver/sgh_q56a_orientation_catalog_alap.md
codex/reports/egyedi_solver/sgh_q56a_orientation_catalog_alap.md
codex/reports/egyedi_solver/sgh_q56a_orientation_catalog_alap.verify.log
```

A report Standard v2 szerint legyen kitöltve, a DoD→Evidence Matrix path+line bizonyítékkal.
PASS csak zöld verify + teljesült DoD esetén. A végén add meg a módosított fájlok listáját, a gate
eredményét, és ha van, a BLOCKED/DEVIATION okát.
