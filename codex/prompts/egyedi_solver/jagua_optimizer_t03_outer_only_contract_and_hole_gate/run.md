# Runner — JG-03 jagua_optimizer_t03_outer_only_contract_and_hole_gate

## Feladat

A VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-03 contract/gate taskot:

```text
JG-03 — jagua_optimizer_t03_outer_only_contract_and_hole_gate
```

Ez **nem optimizer implementáció**. A feladat célja: Phase 1 outer-only contract + hole gate, hogy hole-os part soha ne fusson át csendben rectangular itemként.

## Kötelező bemenetek

Először olvasd el teljes egészében:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
canvases/jagua_rs_sajat_optimizer/plan/deep-research-report.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md
canvases/egyedi_solver/jagua_optimizer_task_index.md
codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md
codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md
canvases/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t03_outer_only_contract_and_hole_gate.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md
```

Ha bármelyik hiányzik, állj meg `STATUS: BLOCKED` státusszal.

## Globális hard rules

```text
REAL_CODE_ONLY:
- Work only from actual repository files.
- Do not invent files, modules, APIs, functions, schemas, or test commands.
- If the expected element does not exist, report it as mismatch/blocker.
```

```text
NO_SILENT_GEOMETRY_LOSS:
- Do not drop holes, contours, item identities, quantities, transforms, or validation data silently.
```

```text
EXACT_VALIDATION_REQUIRED:
- Any task that produces or modifies nesting layout behavior must require exact final validation.
- Invalid layout cannot be accepted as success.
```

```text
CHECKLIST_REQUIRED:
- Update the task-specific checklist entries in jagua_optimizer_task_progress_checklist.md.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

## Scope

Benne van: Phase 1 outer-only capability policy, `docs/solver_io_contract.md`, opcionális `solver_profile` / capability / unsupported reason contract, Rust hole detection/gate, Python runner/validator unsupported státuszkezelés, `scripts/smoke_jagua_optimizer_outer_only_contract.py`, pozitív és negatív fixture, exact validation, legacy/default rectangle smoke regressziómentesség, checklist és report.

Tilos: hole-os part nesting, part-in-hole/cavity-prepack, irregular/remnant nesting, JaguaAdapter PoC, új optimizer algoritmus, IO contract kompatibilitást törő módosítás, default `scripts/check.sh` smoke törése, invalid layout PASS-ként elfogadása.

## Fontos valós kódhelyzet JG-02 után

A task bontás eredeti Rust output listája részben elavult. A valós kódban:

- `rust/vrs_solver/src/io.rs` tartalmazza a `SolverInput` / `SolverOutput` / `Metrics` DTO-kat.
- `rust/vrs_solver/src/item.rs` tartalmazza a `Part` DTO-t és az instance expansiont.
- `rust/vrs_solver/src/adapter.rs` tartalmazza a `solve(input)` orchestrationt.
- `rust/vrs_solver/src/sheet.rs` tartalmazza a `Stock` DTO-t és a sheet hole-aware checket.
- `vrs_nesting/runner/vrs_solver_runner.py` minden successful solver output után `_validate_contract_fields()` hívást futtat.
- `vrs_nesting/nesting/instances.py` Python oldalon már ismeri a part `outer_points`, `prepared_outer_points`, `holes_points`, `prepared_holes_points` mezőket.
- `docs/solver_io_contract.md` már létezik, de még nem írja le a JG-03 Phase 1 unsupported policyt.

Ezért a JG-03 implementációnak érintenie kell az `item.rs` és valószínűleg az `adapter.rs` fájlt is. Ez nem scope-bővítés, hanem a JG-02 utáni valós modulhatár.

## Végrehajtási lépések

### 1. Task és dependency ellenőrzés

Keresd meg a JG-03 definíciót itt:

```text
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
canvases/egyedi_solver/jagua_optimizer_task_index.md
```

Ellenőrizd: `JG-03`, slug `jagua_optimizer_t03_outer_only_contract_and_hole_gate`, Phase 1 / rectangular preflight, dependency JG-02, JG-02 report első sora `PASS`, és JG-02 report tartalmazza: `JG-03_STATUS = READY`. Ha bármelyik nem igazolható, `BLOCKED`.

### 2. Goal YAML sanity

Validáld a goal YAML-t, ellenőrizd a nem üres `steps` listát és hogy nincs sandbox-specifikus útvonal.

### 3. Valós code-boundary audit

Olvasd el és dokumentáld a reportban:

```text
docs/solver_io_contract.md
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/main.rs
vrs_nesting/runner/vrs_solver_runner.py
vrs_nesting/nesting/instances.py
scripts/check.sh
```

Különösen keresd meg, hol lehet `solver_profile`-t bevezetni visszafelé kompatibilisen, hol lehet a part `holes_points` / `prepared_holes_points` mezőket explicit észlelni, milyen output/runner contract mellett nem sérül a `validate_multi_sheet_output()`, és a default `scripts/check.sh` stock-hole smoke hogyan maradhat zöld.

### 4. Contract döntés

Válassz egy implementálható unsupported policyt:

A) Output-alapú unsupported: `status: unsupported`, `unsupported_reason: UNSUPPORTED_PART_HOLES_PHASE1`, `placements: []`, és a runner ezt non-layout állapotként kezeli.

B) Controlled non-zero unsupported error: a Rust solver kontrollált non-zero exitet ad, stderr tartalmazza `UNSUPPORTED_PART_HOLES_PHASE1`, és a smoke script ellenőrzi a stderr/log reason stringet.

A reportban indokold, melyiket választottad. Ha egyik sem kivitelezhető kompatibilisen, állj meg `REQUIRES_DECISION` státusszal.

### 5. `docs/solver_io_contract.md` frissítése

Dokumentáld a `solver_profile` opcionális input mezőt, Phase 1 outer-only capability policyt, part hole unsupported szabályt, `unsupported_reason` vagy controlled error formátumot, exact validation és unsupported viszonyát, backward compatibility policyt.

### 6. Rust implementáció

Implementáld a gate-et a valós modulhatárok mentén. Minimum: a Rust boundary ne ignorálja csendben a part `holes_points` vagy `prepared_holes_points` mezőket; hole-os part Phase 1 jagua profile alatt determinisztikus unsupported/error legyen; a gate solver placement előtt fusson; a default legacy input és standard check smoke ne törjön; stock holes/remnant policyt csak profilhoz kötötten érints; ne változtasd meg a row/cursor baseline optimizer viselkedését normál rectangle-only inputokon.

### 7. Python runner / validator frissítés

Output-alapú unsupported státusz esetén `vrs_solver_runner.py` olvassa ki az outputot, unsupported esetén mentse a metaadatokat, ne hívja rá a layout-only exact validátort, és ne kezelje successful layoutként. Controlled non-zero error esetén a meglévő non-zero útvonal lehet elég, de a smoke scriptnek ellenőriznie kell a reason stringet.

### 8. Smoke script

Hozd létre:

```text
scripts/smoke_jagua_optimizer_outer_only_contract.py
```

A script hozzon létre pozitív outer-only fixture-t és negatív hole-os part fixture-t, futtassa a solver runner útvonalat, pozitív esetben exact validation PASS-t követeljen, negatív esetben deterministic unsupported/error állapotot és a reason stringet ellenőrizze. Ne hagyjon hátra nem szükséges repo-szennyezést.

### 9. Kötelező parancsok

```bash
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_optimizer_outer_only_contract.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md
```

Ha környezeti dependency miatt valami nem fut, dokumentáld pontosan, és ne adj tiszta PASS-t.

### 10. Checklist és report

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md
```

A report első sora csak akkor legyen `PASS`, ha az implementation kész, az unsupported/hole gate bizonyított, a positive exact validation PASS, a legacy rectangle smoke nem törik, repo verify PASS, checklist frissítve.

Ha minden rendben, a report végén szerepeljen:

```text
JG-04_STATUS: READY
```

## Végső válasz formátuma

```text
JG03_RESULT
STATUS: PASS | REVISE | BLOCKED
CREATED_OR_UPDATED:
- ...
VERIFY:
- cargo build ...: PASS/FAIL
- cargo test ...: PASS/FAIL
- python3 scripts/smoke_jagua_optimizer_outer_only_contract.py: PASS/FAIL
- ./scripts/verify.sh --report ...: PASS/FAIL
CONTRACT_DECISION:
- output unsupported | controlled non-zero error | requires decision
UNSUPPORTED_REASON:
- ...
NEXT:
- JG-04_STATUS: READY | NOT_READY
BLOCKERS:
- ...
```
