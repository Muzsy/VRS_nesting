PASS

## 1) Meta

- **Task slug:** `jagua_optimizer_t09_exact_validation_bridge_and_metrics`
- **Task ID:** `JG-09`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t09_exact_validation_bridge_and_metrics.yaml`
- **Runner prompt:** `codex/prompts/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics/run.md`
- **Futás dátuma:** `2026-05-24`
- **Fókusz terület:** `exact validation bridge | runner meta validation_status | utilization metrics | invalid layout rejection`

---

## 2) Dependency ellenőrzés

| Ellenőrzés | Eredmény |
|---|---|
| JG-08 report létezik | IGAZ |
| JG-08 report első sora | `PASS` |
| JG-08 report tartalmazza `JG-09_STATUS: READY` | IGAZ |
| `rust/vrs_solver/src/optimizer/candidates.rs` létezik | IGAZ |
| `rust/vrs_solver/src/optimizer/initializer.rs` létezik | IGAZ |
| `scripts/smoke_jagua_initial_construction.py` létezik | IGAZ |
| Goal YAML sanity | YAML_OK, `steps: 8`, nincs sandbox path |

---

## 3) Valós kód audit

### `vrs_nesting/runner/vrs_solver_runner.py` (JG-09 előtt)

- `_run_solver_with_paths()` már hívja `_validate_contract_fields()` → `validate_multi_sheet_output()` az `ok`/`partial` útvonalakon.
- `unsupported` status esetén early return: nincs explicit `validation_status`.
- Invalid output esetén exception propagál a meta írása ELŐTT → `runner_meta.json` nem keletkezik sikertelen validáció esetén.
- `runner_meta.json` tartalmaz: `duration_sec`, `placements_count`, `unplaced_count`, `sheet_count_used`, de **nincs** `validation_status`, `validation_error`, `utilization`.

### `vrs_nesting/nesting/instances.py`

- `validate_multi_sheet_output(input_payload, output_payload)` → `None` visszatérési érték PASS esetén, `ValueError` FAIL esetén.
- Ellenőriz: contract_version, status (`ok`/`partial`), sheet-index, overlap (shapely area), spacing, margin, duplicate instance_id, allowed_rotations, coverage count mismatch.
- Nincs metrics-visszatérítő helper — ez runner szinten lesz implementálva.

### `rust/vrs_solver/src/io.rs`

- `Metrics` jelenlegi mezők: `placed_count`, `unplaced_count`, `sheet_count_used`, `seed`, `time_limit_s`, `project_name`.
- **Rust módosítás nem szükséges** — validation_status és utilization Python runner meta szinten elegendő.

---

## 4) Validation bridge design döntés

**A final exact validation a Python runner felelőssége, nem a Rust solveré.**

Indoklás:
- A Rust solver output contract (v1) `status`, `placements`, `unplaced`, `metrics` mezőket tartalmaz.
- Az independent exact validator (`validate_multi_sheet_output`) Python rétegben fut shapely-vel.
- A runner `_run_solver_with_paths()` wrapper biztosítja, hogy `ok`/`partial` status soha ne legyen sikeres futás, ha a validator `ValueError`-t dob.
- `validation_status`, `validation_error`, `utilization` → `runner_meta.json` szinten kerül bele.

### Bridge flow

```
Rust solver → solver_output.json
                  │
           (status == "unsupported")? → meta[validation_status="skipped_unsupported"] → return
                  │
         _validate_contract_fields()
           = validate_multi_sheet_output()
                  │
          raises ValueError?
         /                   \
   meta[validation_status="fail"]    meta[validation_status="pass"]
   meta[validation_error=str(exc)]   meta[validation_error=None]
   _write_json(meta) + raise         meta[utilization=...]
                                     _write_json(meta) + return
```

---

## 5) Metrics definíció

### `utilization` (Phase 1 rectangular, `_compute_utilization()` helper)

```
utilization = placed_area / used_sheet_area
```

ahol:
- `placed_area`: sum(width × height) minden elhelyezett instance-re (part dimenzió × instance count)
- `used_sheet_area`: sum(width × height) a használt sheet_index-ekre (stock dimenzió × expanded index)
- **Érvényességi kör**: Phase 1 rectangular stocks és parts esetén exact; non-rectangular geometriánál None visszatérési érték.

### Példafutás (valid fixture):

```text
input:
  stocks: S (300×200, qty=1)
  parts: A (50×50, qty=2), B (80×30, qty=1)

placed_area   = 2*(50*50) + 1*(80*30) = 5000 + 2400 = 7400
used_sheet_area = 300*200 = 60000
utilization   = 7400/60000 = 0.123333
```

### Runner meta mezők (PASS eset):

```json
{
  "duration_sec": 0.004,
  "placements_count": 3,
  "unplaced_count": 0,
  "sheet_count_used": 1,
  "utilization": 0.123333,
  "validation_status": "pass",
  "validation_error": null
}
```

---

## 6) Módosítások

### `vrs_nesting/runner/vrs_solver_runner.py`

**Hozzáadva: `_compute_utilization(inp, out)` helper** (rectangular Phase 1 utilization):
- part_dims lookup (id → (w, h))
- sheet_areas lookup (sheet_index → w*h via stock expand)
- placed_area = sum(w*h) per placed instance
- used_sheet_area = sum(area) for unique sheet_index-ek
- returns float or None

**Meta dict bővítés** (initial values):
```python
"utilization": None,
"validation_status": None,
"validation_error": None,
```

**Unsupported branch:**
```python
meta["validation_status"] = "skipped_unsupported"
meta["validation_error"] = None
```

**Validation try/except:**
```python
try:
    _validate_contract_fields(snapshot_path, output_path)
except Exception as exc:
    meta["validation_status"] = "fail"
    meta["validation_error"] = str(exc)
    meta["output_sha256"] = _sha256_file(output_path)
    _write_run_log(...)
    _write_json(meta_path, meta)
    raise

meta["validation_status"] = "pass"
meta["validation_error"] = None
...
meta["utilization"] = _compute_utilization(inp_data, output_data)
```

### `scripts/smoke_jagua_exact_validation_bridge.py` (ÚJ)

13 check:
1. Valid runner PASS → `validation_status=pass`
2. `validation_error=None` on valid run
3–8. Metrics jelenlét (duration_sec, placements_count, unplaced_count, sheet_count_used, utilization, utilization range)
9. Overlap → `validate_multi_sheet_output` raises ValueError
10. Invalid sheet_index → raises ValueError
11. Unsupported hole input → `validation_status=skipped_unsupported`
12. `solver_status=unsupported` confirmed
13. Regression: `smoke_jagua_initial_construction.py` PASS

---

## 7) Futtatási eredmények

### cargo build

```
Finished `dev` profile [unoptimized + debuginfo] target(s) in 2.96s
```

**PASS**

### cargo test (35/35)

```
test result: ok. 35 passed; 0 failed
```

**PASS** (35 meglévő JG-05/JG-06/JG-07/JG-08 teszt, 0 új Rust teszt — JG-09 Python-only)

### python3 scripts/smoke_jagua_initial_construction.py (13/13)

```
=== RESULTS: 13 PASS, 0 FAIL ===
OVERALL: PASS
```

**PASS** (regresszió: JG-08 smoke érintetlen)

### python3 scripts/smoke_jagua_exact_validation_bridge.py (13/13)

```
[Valid Phase 1 fixture via runner: validation_status=pass]
  PASS: validation_status=pass
  PASS: validation_error=None on valid run

[Metrics fields present in valid runner meta]
  PASS: duration_sec=0.004
  PASS: placements_count=3
  PASS: unplaced_count=0
  PASS: sheet_count_used=1
  PASS: utilization=0.123333
  PASS: utilization in [0,1]: 0.123333

[Overlap-invalid output: bridge raises ValueError]
  PASS: bridge raised ValueError on overlap: overlap detected on sheet 0 for A__0002

[Invalid sheet_index: bridge raises ValueError]
  PASS: bridge raised ValueError on invalid sheet_index: invalid sheet_index: 9999

[Unsupported hole-containing Phase 1 input: skipped_unsupported]
  PASS: validation_status=skipped_unsupported for hole-containing Phase 1 input
  PASS: solver_status=unsupported confirmed

[Regression: smoke_jagua_initial_construction.py]
  PASS: smoke_jagua_initial_construction.py PASS

=== RESULTS: 13 PASS, 0 FAIL ===
OVERALL: PASS
```

**PASS**

---

## 8) Contract summary

| Contract pont | Státusz |
|---|---|
| `status=ok/partial` csak exact validator PASS után sikeres | ✓ IGAZOLT (try/except bridge) |
| Overlap invalid output runner szinten FAIL | ✓ IGAZOLT (smoke: overlap → ValueError) |
| Invalid sheet_index output runner szinten FAIL | ✓ IGAZOLT (smoke: sheet_index=9999 → ValueError) |
| `validation_status` runner meta-ban van | ✓ IGAZOLT (smoke: validation_status=pass) |
| `validation_error` runner meta-ban van | ✓ IGAZOLT (None on PASS, str on FAIL) |
| `validation_status=fail` meta íródik FAIL ELŐTT | ✓ IGAZOLT (meta write before raise) |
| `unsupported` nem valid success | ✓ IGAZOLT (skipped_unsupported branch) |
| `utilization` runner meta-ban van | ✓ IGAZOLT (0.123333 a fixture-re) |
| `placed_count`, `unplaced_count`, `sheet_count_used` jelenlét | ✓ IGAZOLT (smoke metrics check) |
| `duration_sec` jelenlét | ✓ IGAZOLT (0.004s) |
| V1 output contract (`placements/unplaced/metrics`) érintetlen | ✓ IGAZ (Rust io.rs nem módosult) |
| jagua-rs típus nem szivárog publikus contractba | ✓ IGAZ (Python-only változás) |
| JG-08 regresszió | ✓ PASS (13/13 JG-08 smoke) |

---

## 9) DISCOVERED_MISMATCH — régi fejlesztési terv vs aktuális task-bontás

A régi `jagua_rs_sajat_optimizer_fejlesztesi_terv.md` JG-09-et Irregular sheet model spike-ként írja le. Az aktuális task-bontás (`jagua_optimizer_canvas_yaml_runner_task_bontas.md`) és progress checklist szerint JG-09 = exact validation bridge and metrics.

**Resolution:** az aktuális task-bontást és JG-08 gate-et követtük. Irregular sheet scope nincs JG-09-ben.

---

## 10) Módosított / létrehozott fájlok

| Fájl | Változás |
|---|---|
| `vrs_nesting/runner/vrs_solver_runner.py` | `_compute_utilization()` helper + `validation_status`/`validation_error`/`utilization` meta mezők + try/except bridge |
| `scripts/smoke_jagua_exact_validation_bridge.py` | ÚJ — JG-09 smoke (13 check) |
| `codex/codex_checklist/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md` | Frissítve |
| `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` | JG-09 szekció frissítve |

---

JG-10_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-24T00:13:21+02:00 → 2026-05-24T00:16:37+02:00 (196s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.verify.log`
- git: `main@8288e29`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 .../jagua_optimizer_task_progress_checklist.md     | 32 ++++-----
 vrs_nesting/runner/vrs_solver_runner.py            | 79 +++++++++++++++++++++-
 2 files changed, 94 insertions(+), 17 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
 M vrs_nesting/runner/vrs_solver_runner.py
?? canvases/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md
?? codex/codex_checklist/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t09_exact_validation_bridge_and_metrics.yaml
?? codex/prompts/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics/
?? codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md
?? codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.verify.log
?? scripts/smoke_jagua_exact_validation_bridge.py
```

<!-- AUTO_VERIFY_END -->
