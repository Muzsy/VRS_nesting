PASS

# Report — SGH-Q22R1 Sparrow CDE Diagnostics and Acceptance Hardening

SGH-Q22R1_STATUS: READY_FOR_AUDIT
SGH-Q22_STATUS: READY_FOR_AUDIT
SPARROW_EXPERIMENTAL_STATUS: TESTABLE_WITH_CDE_MICRO
SGH-Q23_STATUS: HOLD
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: REQUIRED_FOR_CDE_SCALE

---

## 1) Meta

* **Task slug:** `sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix`
* **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.md`
* **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.yaml`
* **Futás dátuma:** 2026-05-30
* **Branch / commit:** main / a308494 (uncommitted changes on top)
* **Fókusz terület:** Solver mode | Diagnostics

---

## 2) Pre-audit findings

A Q22 PASS-en felül a következő gyengeségeket dokumentáltuk:

| # | Probléma | Hely (Q22 állapot) |
|---|---|---|
| A | `SPARROW_NO_FEASIBLE_LAYOUT` unsupported output dropolja az `optimizer_diagnostics`-ot | `adapter.rs` `_unsupported_output` és `_unsupported_output_with_backend_diag` (mindkettő `optimizer_diagnostics: None`) |
| B | `SPARROW_COMMIT_VIOLATION_BACKEND` ugyanaz | uo. |
| C | Smoke `fixture_cde_no_bbox_fallback` `SKIP`-el ha unsupported → ez nem PASS evidence | `scripts/smoke_sgh_q22_sparrow_kernel.py` |
| D | Smoke `boundary_recovery` fixture nem valódi boundary violation-ből indul (a seed (0,0)-ra rakja az 1 itemet, ami már feasible) | smoke |
| E | Smoke `continuous_rotation_rescue` nem require convergence-t | smoke |
| F | Bench `sparrow_total` ki**zárja** az unsupported sparrow run-okat → félrevezető convergence summary | `scripts/bench_sgh_q22_sparrow_kernel.py` |
| G | Bench `0.0`, `0`, `False` mezők `'-'`-ként renderelődnek (`v or '-'` antipattern) | uo. |
| H | Bench nincs per-backend summary (bbox vs cde) | uo. |
| I | Q22 report `Q18B_RECOMMENDATION: NOT_REQUIRED_NOW`-ot tett, miközben a measurements szerint CDE Sparrow 20s/30s után fail-el a medium fixture-eken | Q22 report |

---

## 3) Mit valósít meg Q22R1

### 3.1 `adapter.rs` — diagnostics preservation 2 új helperrel

**Új helper:** `_unsupported_output_with_full_diag(reason, input, optimizer_diag, backend_diag)` — `optimizer_diagnostics` és `collision_backend_diagnostics` opcionálisan átmegy.

**Új builder:** `sparrow_optimizer_diag_from(sd: &SparrowDiagnostics, backend_name, final_commit_ms) -> OptimizerDiagnosticsOutput` — egy helyen állítja össze a teljes `OptimizerDiagnosticsOutput`-ot a `SparrowDiagnostics`-ből. Mind a sikeres, mind az unsupported path ezt használja → konzisztens.

**Path frissítések:**

```text
SPARROW_NO_FEASIBLE_LAYOUT (Sparrow loop didn't converge):
  - bbox: _unsupported_output_with_full_diag(reason, input, Some(opt_diag), None)
  - cde:  _unsupported_output_with_full_diag(reason, input, Some(opt_diag), Some(cde_diag))

SPARROW_COMMIT_VIOLATION_BACKEND (Sparrow converged but backend final-commit failed):
  - bbox: _unsupported_output_with_full_diag(reason, input, Some(opt_diag), None)
  - cde:  _unsupported_output_with_full_diag(reason, input, Some(opt_diag), Some(cde_diag))
```

### 3.2 Smoke hardening

**Renamed `fixture2_boundary_recovery` → `fixture2_already_feasible_single_item`** — pontos elnevezés, mert az adapter-szintű seed (0,0)-ra rak egy 40×30 itemet egy 100×100 sheet-re → már feasible. A *valódi* boundary recovery az `optimizer::sparrow::tests::sparrow_kernel_boundary_recovery` unit teszt fedi le (ami manuálisan injektál egy boundary-violating placementet a SparrowState-be).

**`fixture4_continuous_rotation_rescue`** — most kötelező a convergence (2×80×30 a 100×100 sheet-en continuous rotation-rel MUST converge).

**`fixture_cde_no_bbox_fallback` lecserélve 2 explicit fixture-re:**

* `fixture_tiny_cde_must_converge` — 2 small parts on 200×200 sheet, CDE, **MUST** converge, **MUST** have `bbox_fallback_queries == 0`. Nincs skip.
* `fixture_cde_medium_diagnostics_preserved` — 12 parts on 200×200 sheets, CDE; ha `unsupported`, az `optimizer_diagnostics`-nak jelen kell lennie, és tartalmaznia kell a `sparrow_invoked=true`, `sparrow_converged=false`, `sparrow_iterations>0`, `sparrow_initial_raw_loss`, `sparrow_best_infeasible_raw_loss` mezőket.

### 3.3 Bench hardening

**`render_value(v)`** — csak `None` → `-`. `0`, `0.0`, `False`, `""` → tényleges érték.

**Denominator fix:** `sparrow_total += 1` MINDEN sparrow_experimental run-ra, akkor is ha `unsupported` vagy `timeout`. A `sparrow_converged_count` csak akkor növekszik ha `sparrow_converged == True`.

**Per-backend summary:** új tábla per backend (bbox, cde) — `total`, `converged`, `unsupported`, `timeout`. Erre alapozzuk a Q18B döntést.

### 3.4 Q18B döntés a measurements alapján

Q22 bench measurements (`sgh_q22_sparrow_state_separation_kernel_measurements.json`) megmutatja, hogy:

* Sparrow + bbox: 6/6 convergent (medium + synthetic fixtures)
* Sparrow + cde: 0/6 convergent (medium: 3× `unsupported` ~20s, synthetic: 3× `timeout` 30s)

A Q22R1 smoke `tiny_cde_must_converge` (2 parts, 200×200) PASS — tehát CDE Sparrow technikailag működik **micro** méretben, de medium méretre **nem skálázódik** a multi-direction probe + CDE backend query költsége miatt.

**Döntés:** `Q18B_RECOMMENDATION: REQUIRED_FOR_CDE_SCALE`.

Ez a `REQUIRED` egy precízebb formája — a Q22R1 nem mondja hogy a CDE használhatatlan (micro-on PASS-ed), de a sheet/part count növelésével a Q18B CDE session/cache rewrite szükséges.

---

## 4) Érintett fájlok

**Új:**
* `codex/reports/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.md` — ez a report
* `codex/reports/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.verify.log` — verify.sh log

**Módosított:**
* `rust/vrs_solver/src/adapter.rs` — `_unsupported_output_with_full_diag` helper, `sparrow_optimizer_diag_from` builder, 4 unsupported path frissítve, 2 új Q22R1 adapter teszt
* `scripts/smoke_sgh_q22_sparrow_kernel.py` — F2 rename, F4 kötelező convergence, `fixture_tiny_cde_must_converge` új (replaces skip-on-unsupported), `fixture_cde_medium_diagnostics_preserved` új
* `scripts/bench_sgh_q22_sparrow_kernel.py` — `render_value`, denominator fix, per-backend summary
* `codex/codex_checklist/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.md` — checklist

**Regenerated:**
* `codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.{json,md}` — Q22R1 honest accounting

---

## 5) Tests

### 5.1 Új Q22R1 adapter integration tesztek (2 db)

| Teszt | Verifikál |
|---|---|
| `sparrow_unsupported_preserves_optimizer_diagnostics_bbox` | 5×50×50 → 100×100 (impossible) → `unsupported` `SPARROW_NO_FEASIBLE_LAYOUT` + `optimizer_diagnostics` jelen + `pipeline_used=="sparrow_experimental"` + `sparrow_iterations>0` + `sparrow_initial_raw_loss>0` |
| `sparrow_pipeline_cde_tiny_converges_with_no_bbox_fallback` | 2 small parts × 200×200 sheet × CDE → `ok` + `sparrow_converged==true` + `bbox_fallback_queries==0` |

### 5.2 Cargo eredmények

```text
cargo test optimizer::sparrow                          → 9 passed (unchanged from Q22)
cargo test adapter -- sparrow                          → 6 passed (4 Q22 + 2 Q22R1)
cargo test --lib                                       → 419 passed, 0 failed (+2 Q22R1)
```

### 5.3 Smoke eredmények (`scripts/smoke_sgh_q22_sparrow_kernel.py`)

**26 / 26 PASS** — mind 5 eredeti fixture + tiny CDE + medium CDE diagnostics.

| Fixture | Outcome | Evidence |
|---|---|---|
| overlap_two_rects | converged, 1→0 pairs | bbox |
| **already_feasible_single_item** (Q22R1 rename) | already feasible, `initial_raw_loss==0` | bbox |
| three_item_collision_chain | converged, 3→0 pairs | bbox |
| **continuous_rotation_rescue** (Q22R1 hard requirement) | **converged** (`2×80×30 on 100×100`) | continuous |
| medium_10_to_20_items | converged, 66→0 pairs, 11 moves | bbox |
| same_seed_determinism | identical placements | bbox |
| **tiny_cde_must_converge** (Q22R1 new — no skip) | **converged, `bbox_fallback_queries==0`** | **CDE** |
| **cde_medium_diagnostics** (Q22R1 new) | `unsupported`, BUT all sparrow fields present: 66→36 pairs, 1320→720 raw loss, 4 iters, 3 moves, `bbox_fb==0` | **CDE** |

### 5.4 Bench eredmények (`scripts/bench_sgh_q22_sparrow_kernel.py --quick`)

Lásd: `sgh_q22_sparrow_state_separation_kernel_measurements.md`.

A Q22R1 accounting után a per-backend summary egyértelműen mutatja:

* **bbox**: minden Sparrow run convergent
* **cde**: medium fixture-eken `unsupported`, synthetic fixture-eken `timeout` → Q18B `REQUIRED_FOR_CDE_SCALE`

---

## 6) Known limitations (PASS-mellett megengedett)

* **Sparrow + CDE medium/synthetic fixture-eken jelenleg nem konvergál a 30s hard timeout-on belül.** A `tiny_cde_must_converge` smoke micro-on PASS-ed, ezért tudjuk hogy a CDE/Sparrow integration működik elvileg. A skálázódás Q18B (CDE session/cache rewrite) scope. A Q22R1 nem ad fake convergence-t — a measurement őszintén `unsupported`/`timeout`, és minden diagnostics megmarad → analyzable.
* **Nincs LV8 acceptance gate** — Q19 scope.
* **Nincs strip-shrink Algorithm 12/13 parity** — Q23 scope.

### 6.1 Nem megengedett ismert hibák (mind ellenőrizve, nincs ilyen)

- ❌ unsupported Sparrow dropolja a diagnostics-ot → ✅ minden unsupported path megőrzi
- ❌ smoke skip-eli a CDE unsupported-et pass-ként → ✅ `tiny_cde_must_converge` skip nélkül converged-ot követel
- ❌ bench `sparrow_total` kihagyja az unsupported-et → ✅ minden run beleszámít
- ❌ zero-value rendering `-`-ként → ✅ `render_value` csak `None`-ra ad `-`-ot
- ❌ Q18B `NOT_REQUIRED_NOW` CDE medium failure mellett → ✅ `REQUIRED_FOR_CDE_SCALE`

---

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-30T05:58:42+02:00 → 2026-05-30T06:01:53+02:00 (191s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.verify.log`
- git: `main@7cdd4e7`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 ...arrow_state_separation_kernel_measurements.json | 146 +++++-----
 ...sparrow_state_separation_kernel_measurements.md |  57 ++--
 rust/vrs_solver/src/adapter.rs                     | 295 +++++++++++++++------
 scripts/bench_sgh_q22_sparrow_kernel.py            |  63 ++++-
 scripts/smoke_sgh_q22_sparrow_kernel.py            |  97 +++++--
 5 files changed, 459 insertions(+), 199 deletions(-)
```

**git status --porcelain (preview)**

```text
 M codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.json
 M codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.md
 M rust/vrs_solver/src/adapter.rs
 M scripts/bench_sgh_q22_sparrow_kernel.py
 M scripts/smoke_sgh_q22_sparrow_kernel.py
?? README_SGH_Q22R1_PACKAGE.md
?? canvases/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.md
?? codex/codex_checklist/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.yaml
?? codex/prompts/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix/
?? codex/reports/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.md
?? codex/reports/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.verify.log
```

<!-- AUTO_VERIFY_END -->
