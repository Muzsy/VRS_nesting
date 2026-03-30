# Nesting quality lane — konkrét elvégzendő feladatok

## Döntés

A H3-E4 előtt külön **nesting quality / engine integration lane** indul.
A cél nem a remnant domain bővítése, hanem az, hogy a web_platform végre
olyan engine-utat hajtson, amelyből iparilag értelmezhető layout-minőség
jöhet.

## Miért most ez a prioritás

A jelenlegi repo alapján:
- `worker/engine_adapter_input.py` még `contract_version: v1` solver inputot gyárt;
- `worker/main.py` a `vrs_nesting.runner.vrs_solver_runner` utat hívja;
- `worker/result_normalizer.py` kizárólag v1 solver outputot fogad el;
- `api/routes/runs.py` viewer route a `solver_input.json` + `solver_output.json` világra épül;
- közben a repóban már ott van a `vrs_nesting.runner.nesting_engine_runner`,
  a `docs/nesting_engine/io_contract_v2.md`, valamint a Rust `nesting_engine`
  CLI `--placer blf|nfp`, `--part-in-part off|auto`, `--search none|sa`
  támogatással.

Ezért a következő szakasz célja: **v1 shelf/bbox útból → mérhetően jobb v2 engine út**.

---

## Task 1 — h3_quality_t1_engine_observability_and_artifact_truth

### Cél
A runokhoz kapcsolódó input/output truth és quality-debug láthatóság rendberakása.

### Fő eredmény
- a worker hivatalos solver input artifactot ment;
- a run metadata egyértelműen jelzi az engine backend-et és a contract verziót;
- a viewer nem esik szét attól, hogy az input snapshot és a runtime input eltérő fájlnéven él;
- a trial tool summary kimondja, milyen backend futott és mennyire teljesek az artifactok.

### Elsődlegesen érintett fájlok
- `worker/main.py`
- `api/routes/runs.py`
- `scripts/trial_run_tool_core.py`
- új smoke: `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py`

### DoD
- egy runból visszaolvasható: engine backend, contract version, input artifact, output artifact;
- a viewer helyes sheet-size és utilization képet ad, ha az input artifact elérhető;
- a smoke bizonyítja a fallback és az artifact truth működését.

---

## Task 2 — h3_quality_t2_benchmark_fixtures_and_kpi_baseline

### Cél
Fix benchmark-csomag és KPI-alap létrehozása.

### Fő eredmény
- golden benchmark fixture készlet;
- baseline eredmények a jelenlegi v1 solverre;
- egységes quality summary séma.

### Elsődlegesen érintett fájlok
- `samples/` vagy `docs/qa/fixtures/` alatti benchmark készlet
- új script: `scripts/bench_web_platform_quality_baseline.py`
- kapcsolódó dokumentáció/report

### Minimum KPI-k
- `placed_count`
- `unplaced_count`
- `sheet_count`
- `utilization_ratio`
- `runtime_sec`
- `rotation_histogram`
- `part_in_part_hit_count`
- `determinism_hash`

### DoD
- ugyanazzal a bemenettel ugyanaz a baseline report újra előállítható;
- a v1 solver baseline rögzítve van.

---

## Task 3 — h3_quality_t3_snapshot_to_nesting_engine_v2_adapter

### Cél
A snapshotból a web_platform tudjon `nesting_engine_v2` inputot előállítani.

### Fő eredmény
- új adapter a snapshot → v2 contract világra;
- parts + holes + sheet geometry + rotation policy + runtime policy továbbmegy;
- valid v2 input artifact készül.

### Elsődlegesen érintett fájlok
- új modul: `worker/engine_adapter_input_v2.py`
- `worker/main.py`
- opcionálisan validációs helper / smoke
- új smoke: `scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py`

### DoD
- legalább 1-2 benchmark fixture lefut a `nesting_engine_runner` útig;
- a létrejövő input átmegy a `scripts/validate_nesting_solution.py --input-v2 ...` validáción.

---

## Task 4 — h3_quality_t4_worker_dual_engine_backend

### Cél
A worker kapcsolhatóan tudjon v1 és v2 backend közt váltani.

### Fő eredmény
- `v1_vrs_solver` és `nesting_engine_v2` backend választható;
- rollback egyszerű marad;
- a backend a run artifactban egyértelmű.

### Elsődlegesen érintett fájlok
- `worker/main.py`
- `api/services/run_snapshot_builder.py` vagy a run-config/runtime config érintett részei
- kapcsolódó smoke script

### DoD
- ugyanaz a run chain mindkét backenden végigfut;
- a választott backend kimondottan látszik a runban.

---

## Task 5 — h3_quality_t5_result_normalizer_and_viewer_v2

### Cél
A platform tudja beolvasni és megjeleníteni a v2 outputot.

### Fő eredmény
- v2 output parser;
- placements, rotation, sheet geometry és utilization helyesen jelenik meg;
- viewer-data endpoint már nem v1-only logikájú.

### Elsődlegesen érintett fájlok
- `worker/result_normalizer.py`
- `api/routes/runs.py`
- `frontend/src/pages/ViewerPage.tsx` ha kell UI igazítás
- új smoke: `scripts/smoke_h3_quality_t5_result_normalizer_and_viewer_v2.py`

### DoD
- a viewer v2 runokra használható;
- a placements és a sheet metrics helyesek.

---

## Task 6 — h3_quality_t6_trial_run_quality_lab

### Cél
A trial toolból valódi quality lab legyen.

### Fő eredmény
- backend választás;
- optional A/B run ugyanarra az inputra;
- automatikus diff summary;
- benchmark batch mód.

### Elsődlegesen érintett fájlok
- `scripts/trial_run_tool_core.py`
- `scripts/run_trial_run_tool.py`
- `scripts/trial_run_tool_gui.py`
- smoke script(ek)

### DoD
- ugyanazzal a DXF-csomaggal két backend összehasonlítható;
- a mentett run mappában diff report keletkezik.

---

## Task 7 — h3_quality_t7_quality_profiles_and_run_config_integration

### Cél
Legyen legalább három használható quality profile.

### Profilok
- `fast_preview`
- `quality_default`
- `quality_aggressive`

### Fő eredmény
- a run configból kiválasztható profile;
- profile → engine flag mapping dokumentált;
- profile különbség mérhető a benchmarkokon.

### Elsődlegesen érintett fájlok
- run config / snapshot builder / worker runtime policy
- trial tool config mapping
- smoke + report

### DoD
- ugyanaz az input különböző profile-okkal eltérő quality/runtime viselkedést mutat.

---

## Task 8 — h3_quality_t8_engine_tuning_regression_cycle

### Cél
A v2 út fölött célzott quality tuning benchmark alapon.

### Lehetséges fókuszok
- part ordering
- rotation tie-break
- SA params
- cavity / part-in-part heuristics
- compaction
- remnant-aware scoring előkészítés

### DoD
Nem “érzésre jobb”, hanem legalább egy benchmark kategórián mérhető javulás:
- kevesebb sheet, vagy
- jobb utilization, vagy
- jobb priority/full placement, vagy
- kevesebb unplaced.

---

## Végrehajtási sorrend

1. T1 — observability + artifact truth
2. T2 — benchmark + KPI baseline
3. T3 — snapshot → v2 adapter
4. T4 — dual-engine worker
5. T5 — result normalizer + viewer v2
6. T6 — trial tool quality lab
7. T7 — quality profiles
8. T8 — tuning cycle

---

## Mi mehet csak másodlagos sávban

A DXF előszűrő / normalizáló modul maradjon külön, másodlagos előkészítő sáv:
- V1-ben szigorú acceptance gate legyen;
- layer maradjon a kanonikus belső világ;
- a szín csak elsőrangú hint legyen;
- a modul determinisztikus legyen;
- és csak olyan DXF mehessen tovább, ami importer+validator láncon bizonyítottan átment.

Ehhez a teljes dokumentációs csomagból legalább az első 8 kulcsdokumentumot érdemes befagyasztani,
és csak utána kódolni.
