PASS

## 1) Meta
- Task slug: `h3_quality_t3_snapshot_to_nesting_engine_v2_adapter`
- Kapcsolodo canvas: `canvases/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.yaml`
- Futas datuma: `2026-03-29`
- Branch / commit: `main @ 0580b3e (dirty working tree)`
- Fokusz terulet: `Worker adapter boundary (snapshot -> nesting_engine_v2 input)`

## 2) Scope

### 2.1 Cel
- Keszult explicit snapshot -> `nesting_engine_v2` input builder a worker adapter modulban.
- Keszult determinisztikus canonical hash helper a v2 input payloadhoz.
- Keszult fail-fast sheet-family szabaly a single-sheet v2 contract korlat miatt.
- Keszult dedikalt task-smoke a sikeres es hibas adapter-agak bizonyitasara.

### 2.2 Nem-cel (explicit)
- Worker runtime backend atkotese `nesting_engine_runner` modulra.
- Dual-engine backend switch / feature flag.
- Result normalizer vagy viewer v2 tamogatas.
- Benchmark A/B diff logika vagy H3-E4 domain valtoztatas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `worker/engine_adapter_input.py`
- `scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py`
- `codex/codex_checklist/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md`
- `codex/reports/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md`

### 3.2 Mi valtozott es miert
- A `worker/engine_adapter_input.py` uj `build_nesting_engine_input_from_snapshot(...)` buildert kapott: a snapshotot a `docs/nesting_engine/io_contract_v2.md` minimum input mezore kepezi (`version`, `seed`, `time_limit_sec`, `sheet`, `parts`).
- A rotacio policy kulon lett valasztva a v1 es v2 builder kozott: a v1 tovabbra is 0/90/180/270 korlatos, a v2 builder pedig `rotation_step_deg` alapjan explicit teljes veges halmazt ad (pl. 45 fok -> 8 elem).
- A single-sheet-family preview korlat explicit fail-fast szaballyal lett bevezetve: ha a snapshot tobb eltero `width_mm/height_mm` sheet tipust hordoz, a v2 builder determinisztikus hibaval all meg, mert a v2 contract inputban egyetlen `sheet` objektum szerepel.
- A task tudatosan nem valt runtime backendet: a worker tovabbra is `build_solver_input_from_snapshot(...)`-ot hasznal, `sparrow_v1` backend metadata-t ir, es `vrs_solver_runner` modullal fut.

### 3.3 Snapshot -> v2 mezo lekotes (explicit)
- `solver_config_jsonb.seed` -> `seed`
- `solver_config_jsonb.time_limit_s` -> `time_limit_sec`
- `solver_config_jsonb.kerf_mm` -> `sheet.kerf_mm`
- `solver_config_jsonb.spacing_mm` -> `sheet.spacing_mm`
- `solver_config_jsonb.margin_mm` -> `sheet.margin_mm`
- `sheets_manifest_jsonb[].width_mm/height_mm` -> `sheet.width_mm/sheet.height_mm` (single-sheet-family validacio utan)
- `parts_manifest_jsonb[].part_revision_id` -> `parts[].id`
- `parts_manifest_jsonb[].required_qty` -> `parts[].quantity`
- `solver_config_jsonb.rotation_step_deg` + `allow_free_rotation` -> `parts[].allowed_rotations_deg`
- `geometry_manifest_jsonb[].polygon.outer_ring/hole_rings` -> `parts[].outer_points_mm/holes_points_mm`

## 4) Verifikacio (How tested)

### 4.1 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md` -> PASS

### 4.2 Opcionalis, feladatfuggo ellenorzes
- `python3 -m py_compile worker/engine_adapter_input.py scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py` -> PASS
- `python3 scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| #1 Letezik explicit snapshot -> `nesting_engine_v2` input builder | PASS | `worker/engine_adapter_input.py:305`; `worker/engine_adapter_input.py:359` | A builder kulon fuggvenyben, explicit v2 payload szerkezettel jon letre. | `python3 scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py` |
| #2 A v2 builder nem tori el a meglevo v1 build utat | PASS | `worker/engine_adapter_input.py:212`; `worker/engine_adapter_input.py:295`; `worker/main.py:1209` | A v1 `build_solver_input_from_snapshot` es worker hivashelye valtozatlanul megmaradt. | `./scripts/verify.sh --report ...` |
| #3 A v2 input kompatibilis a minimum io_contract_v2 input contracttal | PASS | `worker/engine_adapter_input.py:359`; `worker/engine_adapter_input.py:363`; `worker/engine_adapter_input.py:346`; `docs/nesting_engine/io_contract_v2.md:15` | A payload pontosan a `version/seed/time_limit_sec/sheet/parts` mezoket adja a contract szerint. | `python3 scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py` |
| #4 A rotation policy v2-ben mar nem a v1 0/90/180/270 korlat | PASS | `worker/engine_adapter_input.py:129`; `worker/engine_adapter_input.py:145`; `worker/engine_adapter_input.py:317`; `scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py:137` | A v2 helper teljes veges ciklust general step alapon; a smoke explicit ellenorzi a 45 fokos listat. | `python3 scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py` |
| #5 A multi-sheet / nem reprezentalhato snapshot fail-fast hibaval all meg | PASS | `worker/engine_adapter_input.py:179`; `worker/engine_adapter_input.py:201`; `scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py:157` | Elteto sheet-mereteknel a mapper explicit hibara fut, nincs csendes veszteseges fallback. | `python3 scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py` |
| #6 A v2 input canonical hash determinisztikus | PASS | `worker/engine_adapter_input.py:373`; `scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py:144` | A canonical JSON hash helper ket azonos snapshoton azonos SHA-256 erteket ad. | `python3 scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py` |
| #7 A task-specifikus smoke zold | PASS | `scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py:109`; `scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py:196` | A smoke lefedi a sikeres map-et es a fo fail-fast agat (allow_free, multi-sheet, hianyos geometry, ures parts). | `python3 scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py` |
| #8 Standard verify wrapper lefut, report + log frissul | PASS | `codex/reports/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.verify.log` | A kotelezo wrapper futtatja a teljes gate-et es frissiti az AUTO_VERIFY blokkot. | `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md` |

## 6) Advisory notes
- A v2 adapter ebben a taskban tudatosan single-sheet-family preview: a multi-stock runtime sem input, sem backend oldalon nincs bevezetve.
- A v2 builder manufacturing mezokre (`kerf_mm`, `spacing_mm`, `margin_mm`) fail-fast modon relyel; hianyzo snapshot mezonel explicit hibat ad.

## 7) Follow-ups
- T4-ben worker backend kapcsolas: `build_nesting_engine_input_from_snapshot` + `nesting_engine_runner` runtime ut integracioja.
- T5-ben result normalizer/viewer v2 support, hogy a v2 output artifactok megjelenitesi oldalon is first-class entitasok legyenek.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-29T23:42:03+02:00 → 2026-03-29T23:45:36+02:00 (213s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.verify.log`
- git: `main@0580b3e`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 worker/engine_adapter_input.py | 134 +++++++++++++++++++++++++++++++++++++++++
 1 file changed, 134 insertions(+)
```

**git status --porcelain (preview)**

```text
A  docs/nesting_quality/nesting_quality_konkret_feladatok.md
 M worker/engine_adapter_input.py
?? canvases/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md
?? codex/codex_checklist/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md
?? codex/goals/canvases/web_platform/fill_canvas_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.yaml
?? codex/prompts/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter/
?? codex/reports/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md
?? codex/reports/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.verify.log
?? scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py
```

<!-- AUTO_VERIFY_END -->
