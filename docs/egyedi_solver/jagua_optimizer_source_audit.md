# JG-01 Source Audit — jagua-rs + saját optimizer

**Dátum:** 2026-05-22  
**Task:** `jagua_optimizer_t01_repo_and_source_audit`  
**Státusz:** PASS (JG-02 READY)

---

## Scope and sources

Ez az audit a következő fájlokat vizsgálta kódszintű anchorokkal:

| Fájl | Megvizsgálva | Line ref |
|---|---|---|
| `rust/vrs_solver/Cargo.toml` | IGEN | - |
| `rust/vrs_solver/Cargo.lock` | IGEN | L212 |
| `rust/vrs_solver/src/main.rs` | IGEN | L1-649 |
| `docs/solver_io_contract.md` | IGEN | - |
| `vrs_nesting/runner/vrs_solver_runner.py` | IGEN | L1-346 |
| `vrs_nesting/runner/solver_adapter.py` | IGEN | L1-118 |
| `vrs_nesting/nesting/instances.py` | IGEN | L1-374 |
| `scripts/validate_nesting_solution.py` | IGEN | L1-90 |
| `worker/cavity_prepack.py` | IGEN | L1-80 (1120 sor) |
| `worker/cavity_validation.py` | IGEN | L1-80 (721 sor) |
| `worker/result_normalizer.py` | IGEN | L1-80 (1414 sor) |
| `scripts/ensure_sparrow.sh` | IGEN | L1-20 |
| `scripts/run_sparrow_smoketest.sh` | IGEN | L1-20 |
| `vrs_nesting/runner/sparrow_runner.py` | IGEN | L1-80 (376 sor) |
| `poc/sparrow_io/sparrow_commit.txt` | IGEN | - |

Nem vizsgált (nem létezik):
- `canvases/egyedi_solver/jagua_rs_feasibility_integration.md` — LÉTEZIK (referencia-audit)
- `codex/reports/egyedi_solver/jagua_rs_feasibility_integration.md` — LÉTEZIK (referencia-audit)

---

## Repo rules and task source extraction

**Repo szabályfájlok beolvasva:** AGENTS.md, docs/codex/overview.md, docs/codex/yaml_schema.md, docs/codex/report_standard.md, docs/qa/testing_guidelines.md.

**JG-01 forrásai igazoltak:**

- Task bontás: `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md` — JG-01 explicit „Phase 0 / audit" taskként definiálva.
- Progress checklist: `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` — JG-01 ellenőrző lista megtalálva (L121–L153).
- Task index: `canvases/egyedi_solver/jagua_optimizer_task_index.md` — JG-01 sorban felsorolva, dependency: JG-00, acceptance gate: anchor/képesség/kockázat audit táblázat.

**JG-00 dependency státusza:** `codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md` — státusz PASS (első sor alapján igazolva). JG-00 kész, JG-01 indítható volt.

**Globális invariánsok (repo):**
- `REAL_CODE_ONLY` — csak valós fájlokra támaszkodtunk
- `NO_SILENT_GEOMETRY_LOSS` — lyukak, kontúrok, instance azonosítók elvesztése tiltott
- `EXACT_VALIDATION_REQUIRED` — invalid layout nem lehet sikeres
- `CHECKLIST_REQUIRED` — bizonyíték nélkül nincs PASS

---

## Current vrs_solver state

**Fájl:** `rust/vrs_solver/src/main.rs` (649 sor, egyetlen binary crate)

**Azonosított architektúra:**

Egyetlen monolit `main.rs`. Nincs modul-szétbontás.

| Struktúra | Sor | Szerep |
|---|---|---|
| `SolverInput` | L10 | JSON input deszializálás (serde) |
| `Stock` | L19 | Stock/sheet definíció (width/height vagy outer_points+holes_points) |
| `Part` | L29 | Part definíció (id, width, height, quantity, allowed_rotations_deg) |
| `PointInput` | L39 | `[x,y]` vagy `{x,y}` JSON parse |
| `SheetShape` | L53 | Belső sheet reprezentáció (bbox + jagua SPolygon) |
| `SolverOutput` | L64 | JSON output (placements, unplaced, metrics) |
| `Placement` | L73 | Elhelyezési rekord (instance_id, part_id, sheet_index, x, y, rotation_deg) |
| `Unplaced` | L84 | Nem elhelyezett part rekord |
| `Metrics` | L90 | placed_count, unplaced_count, sheet_count_used, seed, time_limit_s, project_name |
| `Instance` | L101 | Expand-elt part instance |
| `SheetCursor` | L110 | **ROW/CURSOR ÁLLAPOT** (x, y, row_h) |
| `Rect` | L117 | Tengelyillesztett téglalap |

**Heurisztika jellege (FONTOS):**

A jelenlegi solver **nem optimizer**, hanem row/cursor alapú greedy placer:

- `SheetCursor` (L110): `x, y, row_h` — soros elhelyezés balról jobbra, soronként
- `try_place_on_sheet()` (L413-475): ha nem fér az aktuális sorba, sort lép; ha a következő sorba sem fér, a sheet kimarad
- Nincs keresés, nincs score model, nincs repair loop, nincs candidate generation
- Csak 0/90/180/270 fokos rotáció támogatott (L275: `matches!(rot, 0 | 90 | 180 | 270)`)
- `expand_instances()` (L331): ábécé-rendezett instance lista (`sort_by instance_id`)

**f32 konverzió (kockázat):**

`to_jag_point()` (L171-173): `JagPoint(p.x as f32, p.y as f32)` — a jagua-rs primitívek `f32`-t használnak. A solver egyéb számítása `f64`. Ennél a konverziónál precizitásveszteség lép fel (tipikusan ~1e-7 mm). Mm-alapú nesting esetén marginálisan elfogadható, de sub-mm toleranciáknál kockázat.

**Egyetlen unit teszt modul** (L581-648): `rotated_bbox_min_offset` és `placement_anchor_from_rect_min` tesztek.

**Összefoglalás:** A jelenlegi `main.rs` csak baseline feasibility check + row-cursor placer. **Jó kiindulópont JG-02 modularizáláshoz**, mert nincs optimizer logika, amit le kellene bontani.

---

## jagua-rs dependency and API usage

**Verzió:** `jagua-rs = "0.6.4"` (Cargo.toml), pinned: `version = "0.6.4"`, `checksum = "1345e8e0a29acb34bf17bccc02475ebe2374d98030d9e77221fadf8e5ce493aa"` (Cargo.lock L212+).

**Tényleges import (main.rs L1-2):**

```rust
use jagua_rs::geometry::geo_traits::CollidesWith;
use jagua_rs::geometry::primitives::{Edge as JagEdge, Point as JagPoint, SPolygon};
```

**Valós API használat:**

| Primitív | Sor | Szerep |
|---|---|---|
| `SPolygon::new(vertices)` | L176-178 | Polygon létrehozás (Vec<JagPoint>) |
| `hole.collides_with(&to_jag_point(c))` | L393 | Pont-polygon ütközés |
| `rect_edge.collides_with(&hole_edge)` | L402 | Él-él ütközés |
| `hole.edge_iter()` | L401 | Polygon él-iterátor |
| `JagEdge::try_new(a, b)` | L351 | Él létrehozás |

**Nem használt (de 0.6.4-ben elérhető jagua-rs képességek):**

A 0.6.4 jagua-rs valószínűleg tartalmaz fejlettebb collision/placement struktúrákat (pl. `Container`, `Item`, `Hazard`, NFP primitívek), de ezeket a jelenlegi main.rs nem importálja — csak a geometriai primitíveket és a `CollidesWith` traitet használja.

**Kulcs-összefoglalás:** A jagua-rs 0.6.4 jelenleg csak geometry backend-ként van bekötve (collision check). Nincs még használva magasabb szintű API. Ez a JG-04 (JaguaAdapter contract PoC) számára ideális állapot.

---

## Solver IO contract and runner boundary

### IO contract (`docs/solver_io_contract.md`)

**Input `solver_input.json`:**
- `contract_version` = `"v1"` (kötelező)
- `project_name`, `seed` (≥0), `time_limit_s` (>0)
- `stocks`: id, quantity, (width+height VAGY outer_points+holes_points)
- `parts`: id, width, height, quantity, allowed_rotations_deg ([0,90,180,270])
- Opcionálisan parts.outer_points, parts.holes_points (geometry-based flow)

**Output `solver_output.json`:**
- `contract_version` = `"v1"`, `status` (ok/partial), `placements`, `unplaced`
- `sheet_index` szemantika: stocks sorrend szerinti expandált lista, 0-indexed
- Opcionálisan `metrics`

**Binary feloldás sorrendje** (`vrs_solver_runner.py` L89-109):
1. `--solver-bin` CLI flag
2. `VRS_SOLVER_BIN` környezeti változó
3. `PATH` lookup (`shutil.which`)

### Runner boundary (`vrs_solver_runner.py`)

- **Run artifacts** (L134-135): `solver_input.json`, `solver_output.json`, `runner_meta.json`, `run.log`, `solver_stdout.log`, `solver_stderr.log`
- **Timeout** (L156-157): `VRS_SOLVER_TIMEOUT_GRACE_S` (default 1.0s), `effective_timeout = time_limit_s + grace`
- **Contract validation** (L112-120): `_validate_contract_fields()` → `validate_multi_sheet_output()` (instances.py-ból)
- **Meta írás** (L179-200): placements_count, unplaced_count, sheet_count_used, sha256, timestamps

### Adapter boundary (`solver_adapter.py`)

- **Protokol** (L19-36): `SolverAdapter` Protocol — `name` property + `run_in_dir()` metódus
- **Két adapter** (L100-117): `build_vrs_solver_adapter()` és `build_sparrow_solver_adapter()`
- `FunctionSolverAdapter` (L41-61): egységes hibakezelés `handled_error_types`-szal
- Az adapter **elrejti** a backend-specifikus runner hibákat, `SolverAdapterError`-ré alakítja

---

## Existing validation anchors

### `vrs_nesting/nesting/instances.py` — `validate_multi_sheet_output()`

Az egyetlen **kötelező, exact** ellenőrzési pont a jelenlegi pipeline-ban.

| Ellenőrzés | Sor | Részlet |
|---|---|---|
| contract_version v1 | L249 | output.contract_version == "v1" |
| status ok/partial | L252 | str check |
| placements/unplaced list | L255-260 | isinstance check |
| sheet_poly.covers(poly) | L317 | Shapely: placement be van-e a sheetben |
| intersection > AREA_EPS | L326 | Átfedés ellenőrzés |
| spacing_mm | L328-329 | Spacing constraint |
| margin_mm | L271-273 | Sheet margin usable region |
| duplicate instance_id | L295 | seen_instance_ids set |
| coverage mismatch | L369-373 | expected_counts vs seen_counts |

**Dependency:** Shapely (`from shapely.affinity import rotate/translate`, `from shapely.geometry import Polygon`) — L10-17. Ha nincs shapely, `_require_shapely()` RuntimeError-t dob.

### `scripts/validate_nesting_solution.py`

- Legacy v1 és nesting_engine v2 validátor
- Narrow-phase opciók: `i_overlay` (preferált) vagy Shapely fallback
- L16-22: `vrs_nesting.validate.solution_validator` modul importja

**Összefoglalás:** Az exact final validation alap **megvan és stabil** (Shapely-alapú, coverage + overlap check). JG-02+ számára közvetlen anchor.

---

## Cavity-prepack / expansion anchors

### `worker/cavity_prepack.py` (1120 sor)

- `_PLAN_VERSION = "cavity_plan_v1"` (L11), `_PLAN_VERSION_V2 = "cavity_plan_v2"` (L12)
- `_VIRTUAL_PART_PREFIX = "__cavity_composite__"` (L13)
- Kulcs dataclassok: `_PartRecord` (L26), `_CavityPlacement` (L41), `_PlacementTreeNode` (L51), `_CavityRecord` (L66)
- Shapely-alapú: `from shapely import affinity`, `from shapely.geometry import Polygon`
- **Cavity plan v1 és v2** mindkét verziót kezeli

### `worker/cavity_validation.py` (721 sor)

- `CavityValidationError` (L14) — hard fail
- `ValidationIssue` (L19) — code, message, context
- `_build_part_index()` (L72): part_id → `_PartGeom` mapping
- Importálja: `from worker.result_normalizer import placement_transform_point` (L9)

### `worker/result_normalizer.py` (1414 sor)

- `ProjectionSummary` (L18): placed_count, unplaced_count, used_sheet_count
- `NormalizedProjection` (L24): sheets, placements, unplaced, metrics, summary
- `placement_transform_point()` — cavity_validation.py által importált

**Összefoglalás:** A cavity pipeline meglévő, Shapely-alapú, kétverziós plan (v1/v2), virtuális part prefix alapú macro-part logikával. JG-21+ számára közvetlen és auditálható alap.

---

## Sparrow / search-pattern reuse anchors

### `vrs_nesting/runner/sparrow_runner.py` (376 sor)

- Sparrow-runner struktúrája tükrözi a `vrs_solver_runner.py`-t
- Error hierarchy (L20-57): `SparrowRunnerError` → `SparrowBinaryNotFoundError`, `SparrowNonZeroExitError`, `SparrowTimeoutError`, `SparrowOutputNotFoundError`, `SparrowOutputParseError`
- Minden error-nak van string `code` (pl. `"E_SPARROW_BIN_NOT_FOUND"`)
- Binary resolution: `SPARROW_BIN` env var

### `scripts/ensure_sparrow.sh`

- Sparrow binary download/fallback script
- Pattern: vendor/fallback binary management

### `scripts/run_sparrow_smoketest.sh`

- Input: `poc/sparrow_io/swim.json` (default), `SEED`, `TIME_LIMIT`
- Overlap check: `OVERLAP_CHECK=auto|0|1`, `OVERLAP_AREA_EPS`
- `latest_run_dir()` helper

### `poc/sparrow_io/sparrow_commit.txt`

- Sparrow commit: `c95454e390276231b278c879d25b39708398b7d3`

**Átvehető minták Sparrowból:**

| Minta | Szerep | JG task |
|---|---|---|
| Runner error hierarchy + kódok | Adapter hibakezelés | JG-04 |
| Binary resolution + fallback | JaguaAdapter binary resolve | JG-04 |
| Timeout + grace period | Optimizer time budget | JG-10 |
| Overlap auto/manual check | Smoke gate pattern | JG-09, JG-14 |
| per-run artifacts (meta, log, sha256) | Benchmark repeatability | JG-14 |
| `swim.json` IO format (Sparrow) | Összehasonlítási referencia | JG-14 |

**NEM átvehető Sparrowból:**
- Sparrow strip-packing outer-loop (nem fixed-sheet/multi-sheet kompatibilis)
- Sparrow belső layout state (Sparrow-specifikus strip-modell)

---

## Rectangular Phase 1 readiness

| Kérdés | Válasz | Bizonyíték |
|---|---|---|
| jagua-rs bekötve? | IGEN, 0.6.4 | Cargo.toml, Cargo.lock |
| IO contract v1 stabil? | IGEN | docs/solver_io_contract.md |
| Python runner artifact-ok? | IGEN | vrs_solver_runner.py |
| Adapter boundary? | IGEN (Protocol) | solver_adapter.py L19-36 |
| Exact validation? | IGEN (Shapely) | instances.py L247+ |
| Rotáció 0/90/180/270? | IGEN | main.rs L275 |
| Stock quantity expand? | IGEN | main.rs L253-265 |
| sheet_index szemantika? | IGEN, dokumentált | solver_io_contract.md |
| Binary feloldás? | IGEN, 3 lépéses | vrs_solver_runner.py L89-109 |
| Cargo build OK? | IGEN | cargo metadata PASS |
| Unit tesztek? | IGEN, L581-648 (2 teszt) | main.rs |
| pytest sanity? | IGEN, 38/38 PASS | lokális futtatás |

**Rectangular Phase 1 readiness: READY** — nincs showstopper.

---

## Irregular/remnant Phase 2 risks

| Kockázat | Szint | Részlet |
|---|---|---|
| jagua-rs 0.6.4 irregular sheet support? | ISMERETLEN | Nem auditált; JG-15 spike task feladata |
| Saját boundary validator szükséges? | LEHETSÉGES | Ha jagua natívan nem kezeli az irregular boundary-t |
| f32 precizitás irregular kontúroknál | ALACSONY-KÖZEPES | `to_jag_point()` (main.rs L171-173) f64→f32 cast |
| Margin policy (usable polygon) | NINCS MÉG | Csak rectangular bbox van a contract-ban |
| Container hole tiltva (Phase 1/2) | KÖTELEZŐ TARTANI | `NO_SILENT_GEOMETRY_LOSS` invariáns |

**Ezeket JG-15 spike dönti el; JG-01 nem blokkol rájuk.**

---

## Hole/cavity Phase 3 risks

| Kockázat | Szint | Részlet |
|---|---|---|
| Part hole (holes_points) parsing | MEGVAN | main.rs L207-222, instances.py L110-116 |
| Part hole silent drop Phase 1 | KOCKÁZAT | main.rs-ben holes_points parse-olva, de collision check csak hole_polys-szal, nem item-hole szintjén |
| cavity_prepack kompatibilitás jagua optimizer inputtal | RÉSZLEGESEN ISMERETLEN | Meglévő API audit szükséges (JG-21) |
| Expansion + exact validation (Phase 3) | MEGLÉVŐ ALAP | result_normalizer.py, cavity_validation.py |

**Hole gate szükséges JG-03-ban:** a jelenlegi main.rs-ben a part-nak nincs `holes_points` mezője (csak `Stock`-nak van). A `Part` struktúra (L29-37) outer-only rect-alapú — jó, mert Phase 1 tiltja a part hole-okat. Viszont explicit unsupported/error státuszt kell bevezetni (JG-03 feladata).

---

## License / dependency / build risks

| Téma | Kockázat | Részlet |
|---|---|---|
| jagua-rs licenc | ELLENŐRZENDŐ | Nem auditált a Cargo.lock-ból; crates.io-ban valószínűleg Apache-2.0 vagy MIT |
| jagua-rs 0.6.x → 0.7.x breakage | ALACSONY | Cargo.toml `^0.6.4` semver — patchre automatikus, minor-ra manuális |
| f32 precizitás | ALACSONY-KÖZEPES | Dokumentálva (audit 2. szekció) |
| Shapely dependency | MEGLÉVŐ | Exact validation feltétele; Python env-ben szükséges |
| ezdxf hiány | ISMERT | verify.sh `ezdxf` import hiba 6 tesztben — **környezeti dependency, nem JG-01 tartalmi hiba** |

**Build:** `cargo metadata --manifest-path rust/vrs_solver/Cargo.toml --no-deps` — PASS (lokálisan igazolva).

---

## Reusable anchors table

| Anchor | Fájl + Sor | JG task | Szerep |
|---|---|---|---|
| `jagua-rs = "0.6.4"` | Cargo.toml | JG-04 | Backend verzió |
| `SPolygon, CollidesWith, Edge, Point` | main.rs L1-2 | JG-04 | API belépési pont |
| `to_jag_point()` f64→f32 | main.rs L171-173 | JG-04 | Precizitás-kockázat |
| `SheetCursor` row/cursor | main.rs L110 | JG-02, JG-08 | Refaktorálandó baseline |
| `expand_sheets()` | main.rs L253 | JG-05 | Sheet provider alap |
| `expand_instances()` | main.rs L331 | JG-06 | Instance expansion |
| `normalize_allowed_rotations()` | main.rs L267 | JG-06 | Rotation policy |
| `try_place_on_sheet()` | main.rs L413 | JG-08 | Lecserélendő placer |
| `rect_inside_sheet_shape()` | main.rs L379 | JG-04, JG-08 | Jagua collision check minta |
| `SolverAdapter` Protocol | solver_adapter.py L19 | JG-04 | Adapter contract |
| `build_vrs_solver_adapter()` | solver_adapter.py L100 | JG-26 | Backend registráció minta |
| `validate_multi_sheet_output()` | instances.py L247 | JG-09 | Exact validation kapocs |
| `VrsSolverRunnerError` hierarchy | vrs_solver_runner.py L24 | JG-04 | Error hierarchy minta |
| timeout + grace period | vrs_solver_runner.py L156 | JG-10 | Time budget minta |
| `_PLAN_VERSION = "cavity_plan_v1"` | cavity_prepack.py L11 | JG-21 | Cavity plan verziók |
| `_VIRTUAL_PART_PREFIX` | cavity_prepack.py L13 | JG-21, JG-23 | Macro-part konvenció |
| `placement_transform_point()` | result_normalizer.py | JG-24 | Expansion transform |
| `SparrowRunnerError` kódok | sparrow_runner.py L20 | JG-04 | Error kód minta |
| `OVERLAP_CHECK=auto` | run_sparrow_smoketest.sh | JG-09, JG-14 | Smoke gate minta |
| `sparrow_commit.txt` | poc/sparrow_io/ | JG-14 | Baseline referencia |

---

## Blockers and REQUIRES_DECISION

**Nem blokkol JG-02 indítást:**

1. `f32` vs `f64` precizitás: alacsony kockázat, dokumentált, JG-04-ben kezelendő.
2. `ezdxf` hiány a pytest collection-ban: ismert, környezeti, nem JG-01 tartalmi hiba.
3. jagua-rs irregular/remnant képesség: JG-15 spike dönti el, nem blokkolja Phase 0.
4. part hole policy: JG-03 implementálja az explicit unsupported gate-et.

**REQUIRES_DECISION (jövőbeli):**

1. **jagua-rs licenc:** Explicit audit szükséges mielőtt termelési release (JG-26 előtt).
2. **jagua-rs 0.6.x API completeness:** A 0.6.4-ben elérhető teljes layout API (Container, Item, NFP) JG-04 spike-ban auditálandó.
3. **Irregular sheet native support:** JG-15 dönt, nem blokkolja Gate 0-t.

---

## Recommendation for JG-02

Az audit alapján:

- A `rust/vrs_solver/src/main.rs` monolit, row/cursor baseline solver — jó kiindulópont, mert nincs bonyolult optimizer logika.
- A `jagua-rs 0.6.4` dependency stabil, kollíziós geometria API megvan.
- A Python runner/adapter boundary (vrs_solver_runner.py, solver_adapter.py) stabil, tesztelt (38/38 PASS).
- Az exact validation (instances.py Shapely) megvan és alkalmas final gate-nek.
- A cavity pipeline (prepack/validation/normalizer) meglévő, auditálható alap Phase 3-hoz.
- Nincs showstopper.

```text
JG-02_STATUS: READY
```

JG-02 (solver module scaffold, viselkedésváltozás nélküli modularizáció) biztonságosan indítható.
