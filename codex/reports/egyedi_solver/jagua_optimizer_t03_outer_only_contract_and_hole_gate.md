PASS

## 1) Meta

- **Task slug:** `jagua_optimizer_t03_outer_only_contract_and_hole_gate`
- **Task ID:** `JG-03`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t03_outer_only_contract_and_hole_gate.yaml`
- **Runner prompt:** `codex/prompts/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate/run.md`
- **Futás dátuma:** `2026-05-23`
- **Fókusz terület:** `Solver IO Contract | Rust DTO/Gate | Python Runner | Phase 1 outer-only preflight`

---

## 2) Dependency ellenőrzés

| Ellenőrzés | Eredmény |
|---|---|
| JG-02 report első sora | `PASS` (`codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md`) |
| `JG-03_STATUS = READY` | IGAZOLT (report 9. szekció) |
| Goal YAML sanity | `YAML_OK, steps: 9`, nincs sandbox path |

---

## 3) Code-boundary audit (JG-02 utáni állapot)

| Fájl | JG-03-ban érintett terület |
|---|---|
| `rust/vrs_solver/src/io.rs` | `SolverInput.solver_profile`, `SolverOutput.unsupported_reason` |
| `rust/vrs_solver/src/item.rs` | `Part.holes_points`, `Part.prepared_holes_points`, `Part.outer_points`, `Part.prepared_outer_points`, `part_has_holes()` |
| `rust/vrs_solver/src/adapter.rs` | Phase 1 hole gate a `solve()` elején |
| `rust/vrs_solver/src/sheet.rs` | Nem érintett (stock hole az eredeti legacy path, default smoke-ban marad) |
| `vrs_nesting/runner/vrs_solver_runner.py` | `status == "unsupported"` kezelés `_run_solver_with_paths()` végén |
| `docs/solver_io_contract.md` | `solver_profile`, `unsupported_reason`, Phase 1 capability policy |
| `vrs_nesting/nesting/instances.py` | Nem módosult — a meglévő `status not in {"ok", "partial"}` check már visszautasítja az `"unsupported"` státuszt; a runner réteg védi a validátort |

---

## 4) Contract döntés

**Választott policy: Output-alapú unsupported (Option A)**

Indoklás:
- Audit-barát: a `solver_output.json` tartalmaz olvasható `unsupported_reason` stringet.
- Runner-szintű elválasztás: a runner ellenőrzi a status-t MIELŐTT `_validate_contract_fields()` hívna.
- A `validate_multi_sheet_output()` (instances.py) változatlan marad és csak `ok`/`partial` layoutokra fut.
- A `runner_meta.json` tartalmaz `solver_status: "unsupported"` és `unsupported_reason` mezőket — auditálható.

---

## 5) Implementált változások

### 5.1 `rust/vrs_solver/src/io.rs`

```rust
// SolverInput: opcionális profil mező
#[serde(default)]
pub solver_profile: Option<String>,

// SolverOutput: opcionális unsupported reason (skip_serializing_if = None)
#[serde(skip_serializing_if = "Option::is_none")]
pub unsupported_reason: Option<String>,
```

### 5.2 `rust/vrs_solver/src/item.rs`

```rust
// Part: hole detection mezők (serde default = None ha hiányzik)
#[serde(default)]
pub holes_points: Option<JsonValue>,
#[serde(default)]
pub prepared_holes_points: Option<JsonValue>,
#[serde(default)]
#[allow(dead_code)]  // fenntartva jövőbeli cavity-prepack számára
pub outer_points: Option<JsonValue>,
#[serde(default)]
#[allow(dead_code)]
pub prepared_outer_points: Option<JsonValue>,

// Hole detection függvény:
pub fn part_has_holes(part: &Part) -> bool { ... }
// null és [] → false; non-empty array → true
```

### 5.3 `rust/vrs_solver/src/adapter.rs`

```rust
const PROFILE_PHASE1: &str = "jagua_optimizer_phase1_outer_only";

pub fn solve(input: SolverInput) -> Result<SolverOutput, String> {
    if input.solver_profile.as_deref() == Some(PROFILE_PHASE1) {
        for part in &input.parts {
            if part_has_holes(part) {
                return Ok(SolverOutput {
                    status: "unsupported".to_string(),
                    unsupported_reason: Some("UNSUPPORTED_PART_HOLES_PHASE1".to_string()),
                    placements: vec![],
                    ...
                });
            }
        }
    }
    // normal solve path unchanged
}
```

### 5.4 `vrs_nesting/runner/vrs_solver_runner.py`

```python
output_data = _read_json(output_path)
if output_data.get("status") == "unsupported":
    meta["solver_status"] = "unsupported"
    meta["unsupported_reason"] = output_data.get("unsupported_reason")
    meta["output_sha256"] = _sha256_file(output_path)
    _write_run_log(...)
    _write_json(meta_path, meta)
    return run_dir, meta
# normal layout path: _validate_contract_fields(snapshot_path, output_path)
```

### 5.5 `docs/solver_io_contract.md`

- `solver_profile` opcionális input mező dokumentálva.
- `status: "unsupported"` és `unsupported_reason` output mező dokumentálva.
- Phase 1 capability policy dokumentálva: támogatott/nem támogatott lista.
- Backward compat policy: `solver_profile` hiánya = legacy rectangular mode.
- Runner viselkedés unsupported esetén dokumentálva.

### 5.6 `scripts/smoke_jagua_optimizer_outer_only_contract.py`

Új smoke script, 3 teszteset:
1. **Positive outer-only fixture**: Phase 1 profil + rectangular parts → `ok` + exact validator PASS
2. **Negative holed-part fixture**: Phase 1 profil + `holes_points` → `unsupported` + reason string + `placements=[]`
3. **Legacy regression**: nincs `solver_profile` + stock holes → `partial` + exact validator PASS

---

## 6) Viselkedésváltozás táblázat

| Elem | Változott? | Megjegyzés |
|---|---|---|
| Legacy rectangular solver path | NO | default profile, nincs solver_profile |
| `validate_multi_sheet_output()` logika | NO | változatlan, csak ok/partial-t fogad el |
| `_validate_contract_fields()` hívás | NO | csak layout outputs-ra hívódik (unsupported előtte tér vissza) |
| Part `holes_points` silent drop | FIX | most serde-szinten rögzítve, `part_has_holes()` detektál |
| check.sh default smoke | NO | nem törik (nincs solver_profile, parts nem holedek) |
| Hole-os part Phase 1 alatt | NEW | deterministic `unsupported` + reason |
| runner_meta.json | EXTENDED | new fields: solver_status, unsupported_reason (only for unsupported) |
| IO contract | EXTENDED | solver_profile input, unsupported_reason output, Phase 1 policy |

---

## 7) Verifikáció

### 7.1 Cargo build

```bash
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
# PASS (2.19s)
```

### 7.2 Cargo test

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml
# test item::tests::placement_anchor_from_rect_min... ok
# test item::tests::rotated_bbox_min_offset... ok
# test result: ok. 2 passed
```

### 7.3 Outer-only contract smoke

```bash
python3 scripts/smoke_jagua_optimizer_outer_only_contract.py
```

| Teszteset | Eredmény |
|---|---|
| Positive outer-only: status=ok | PASS |
| Positive outer-only: unsupported_reason absent | PASS |
| Positive outer-only: exact validator | PASS |
| Negative holed-part: status=unsupported | PASS |
| Negative holed-part: reason=UNSUPPORTED_PART_HOLES_PHASE1 | PASS |
| Negative holed-part: placements=[] | PASS |
| Negative holed-part: runner_meta.json reason | PASS |
| Negative holed-part: runner_meta.json solver_status | PASS |
| Legacy regression: status=partial | PASS |
| Legacy regression: placements=2 | PASS |
| Legacy regression: exact validator | PASS |

### 7.4 Repo gate

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md
```

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-23
- parancs: `./scripts/check.sh`
- log: `codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.verify.log`

<!-- AUTO_VERIFY_END -->

---

## 8) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték |
|---|---|---|
| JG-02 dependency PASS | PASS | report 1. sor |
| JG-03_STATUS = READY | PASS | JG-02 report 9. szekció |
| Goal YAML parse OK | PASS | YAML_OK, steps: 9 |
| Code boundary audit dokumentálva | PASS | 3. szekció |
| Contract döntés dokumentálva | PASS | 4. szekció (Option A) |
| `solver_profile` visszafelé kompatibilis | PASS | legacy smoke nem törött |
| Part `holes_points` detektálva (nem silent drop) | PASS | serde + part_has_holes() |
| Phase 1 hole gate Rust oldalon | PASS | adapter.rs, UNSUPPORTED_PART_HOLES_PHASE1 |
| `docs/solver_io_contract.md` frissítve | PASS | Phase 1 policy, unsupported format |
| Python runner unsupported path | PASS | vrs_solver_runner.py, meta.solver_status |
| `validate_multi_sheet_output()` nem hívódik unsupported-ra | PASS | runner path, smoke bizonyítja |
| Negatív hole-os fixture | PASS | smoke teszt 2/3 |
| Pozitív outer-only fixture | PASS | smoke teszt 1/3 |
| Legacy regression nem törött | PASS | smoke teszt 3/3 |
| Exact validation csak layout-on | PASS | positive + legacy PASS, negative nem fut rá |
| `cargo build` PASS | PASS | 2.19s |
| `cargo test` 2/2 | PASS | item::tests |
| `scripts/smoke_...py` ALL PASS | PASS | 11/11 ok |
| `./scripts/verify.sh` PASS | PASS | EXIT_CODE=0 |
| Nincs új optimizer algoritmus | PASS | scope guard |
| Nincs cavity-prepack / irregular | PASS | scope guard |

---

## 9) JG03_RESULT

```text
JG03_RESULT
STATUS: PASS
CREATED_OR_UPDATED:
- rust/vrs_solver/src/io.rs (solver_profile input, unsupported_reason output)
- rust/vrs_solver/src/item.rs (Part hole fields, part_has_holes())
- rust/vrs_solver/src/adapter.rs (Phase 1 hole gate)
- vrs_nesting/runner/vrs_solver_runner.py (unsupported status path)
- docs/solver_io_contract.md (Phase 1 policy, solver_profile, unsupported_reason)
- scripts/smoke_jagua_optimizer_outer_only_contract.py (new)
- canvases/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md
- codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t03_outer_only_contract_and_hole_gate.yaml
- codex/prompts/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate/run.md
- codex/codex_checklist/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md
- codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md
- codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.verify.log
CONTRACT_DECISION: output-based unsupported (Option A)
UNSUPPORTED_REASON: UNSUPPORTED_PART_HOLES_PHASE1
VERIFY:
- cargo build: PASS
- cargo test: PASS (2/2)
- smoke script: ALL PASS (11/11)
- repo verify: PASS (EXIT_CODE=0)
NEXT:
- JG-04_STATUS: READY
- Nincs showstopper, nincs blokkoló
- JG-04: jagua-rs adapter PoC — az io.rs solver_profile és az item.rs hole fields most már rendelkezésre állnak
```
