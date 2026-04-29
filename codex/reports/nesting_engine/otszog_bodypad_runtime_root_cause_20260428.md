# 1. Összefoglaló

A valós hibaút reprodukálható: ha a bemenetben lyukas mozgó part van, a `--placer nfp` globálisan BLF-re esik vissza, SA work-budget módba kényszerül, és részleges (unplaced) kimenet keletkezik `TIME_LIMIT_EXCEEDED` okokkal. Ez kódszinten és futási artifactokkal is bizonyított.

Bizonyított tények:
- Globális fallback feltétel: `rust/nesting_engine/src/main.rs:431-446`.
- SA stop mód kényszer: `rust/nesting_engine/src/search/sa.rs:351-360`.
- Work-budget és hard grace: `rust/nesting_engine/src/multi_bin/greedy.rs:65-90,170-181`.
- Reprodukciós futásban tényleges profilok: `tmp/repro_f683e6f7/manual_repro_20260427/stderr.log`.

Kritikus blokkoló: a konkrét production runok 1:1 visszajátszásához több helyen hiányzik letölthető `solver_input`/`engine_meta` artifact URL (`status=400 artifact url failed`), ezért az OTSZOG/NEGYZET/MACSKANYELV név szerinti azonosítás lokális artifactokból nem végigvihető.

# 2. A valós hiba reprodukciója vagy reprodukciós akadály

## 2.1 Reprodukció (bizonyított)

Közvetlen engine-futtatás történt az elérhető snapshot inputon (`tmp/repro_f683e6f7/solver_input_snapshot.json`) NFP+SA módban profilozással.

Futási bizonyíték:
- `tmp/repro_f683e6f7/manual_repro_20260427/stderr.log`
- `tmp/repro_f683e6f7/manual_repro_20260427/stdout.json`
- `tmp/repro_f683e6f7/manual_repro_20260427/elapsed.txt`

Kimenet:
- fallback warning: `warning: --placer nfp fallback to blf (hybrid gating: holes or hole_collapsed)`
- SA kényszerített stop: `SA: forcing work_budget stop mode`
- `NEST_NFP_STATS_V1`: `effective_placer="blf"`, `nfp_compute_calls=0`, `cfr_calls=0`
- `SA_PROFILE_V1`: `sa_eval_count=9`, `sa_eval_budget_sec=60`, `sa_time_limit_sec=600`
- stdout összegzés: `status=partial`, `placements=20`, `unplaced=10`, ok: `TIME_LIMIT_EXCEEDED` (10 db)

## 2.2 Reprodukciós akadály (bizonyított)

A valós trial run könyvtárakban több helyen nem kérhető le a `solver_input` és `engine_meta` artifact URL:
- `tmp/runs/20260330T224752Z_sample_dxf_1ebe1445/downloaded_artifact_urls.json`
  - `artifact_type=solver_input`: `status=400`, `{"detail":"artifact url failed"}`
  - `artifact_type=engine_meta`: `status=400`, `{"detail":"artifact url failed"}`

Miközben a rekordok metadata-szinten léteznek:
- `tmp/runs/20260330T224752Z_sample_dxf_1ebe1445/run_artifacts.json`
  - `solver_input` storage key: `runs/<run_id>/inputs/solver_input_snapshot.json`
  - `engine_meta` storage key: `runs/<run_id>/artifacts/engine_meta.json`

Ez blokkolja a teljes production input-visszajátszást minden runra.

# 3. Felhasznált futási bizonyítékok és artefaktumok

- `tmp/runs/20260330T224752Z_sample_dxf_1ebe1445/solver_stderr.log`
- `tmp/runs/20260330T224752Z_sample_dxf_1ebe1445/solver_stdout.log`
- `tmp/runs/20260330T224752Z_sample_dxf_1ebe1445/viewer_data.json`
- `tmp/runs/20260330T224752Z_sample_dxf_1ebe1445/run_artifacts.json`
- `tmp/runs/20260330T224752Z_sample_dxf_1ebe1445/downloaded_artifact_urls.json`
- `tmp/runs/20260330T224752Z_sample_dxf_1ebe1445/created_parts.json`
- `tmp/runs/20260330T224752Z_sample_dxf_1ebe1445/project_part_requirements.json`
- `tmp/repro_f683e6f7/solver_input_snapshot.json`
- `tmp/repro_f683e6f7/manual_repro_20260427/stderr.log`
- `tmp/repro_f683e6f7/manual_repro_20260427/stdout.json`
- `tmp/repro_f683e6f7/manual_repro_20260427/elapsed.txt`
- `.cache/web_platform/logs/worker.log`

# 4. Engine runtime lánc

## 4.1 Quality profile

- Alapértelmezett profil: `quality_default`
- Registry: `vrs_nesting/config/nesting_quality_profiles.py:35-40`
  - `placer=nfp`
  - `search=sa`
  - `part_in_part=auto`
  - `compaction=slide`

## 4.2 Worker policy

- Profil feloldás és runtime policy: `worker/main.py:1211-1276`
- CLI arg építés a policy-ból: `worker/main.py:1256-1258`
- Snapshot `sa_eval_budget_sec` felülírás támogatott: `worker/main.py:1250-1254`

## 4.3 Engine CLI args

- Runner CLI paraméterezés: `vrs_nesting/runner/nesting_engine_runner.py:198-231`
- Worker invokáció nesting v2-höz: `worker/main.py:1322-1345`

## 4.4 nesting_engine_input

- Adapter lyukakat explicit átadja: `worker/engine_adapter_input.py:360-367` (`holes_points_mm`)
- Reprodukciós input: `tmp/repro_f683e6f7/solver_input_snapshot.json`
  - `parts=5`, ebből 1 part `holes=1`.

## 4.5 NFP/BLF/SA profilok

- `NEST_NFP_STATS_V1` (repro stderr): `effective_placer="blf"`, `nfp_compute_calls=0`, `cfr_calls=0`
- `BLF_PROFILE_V1` (repro stderr): nagy `can_place`/`narrow_phase` költség, `progress_stalled=true`
- `SA_PROFILE_V1` (repro stderr): `sa_eval_count=9`, `sa_eval_budget_sec=60`, `sa_time_limit_sec=600`

# 5. Gyökérok

## 5.1 OTSZOG_BODYPAD hole

Bizonyított tény:
- A hiba mechanizmusa bármely lyukas mozgó parttal reprodukálható (repro input 1 lyukas part).
- A helyi artifactokban konkrétan lyukas példa: `rect_with_hole_400x400_D200.dxf`.

Akadály:
- `OTSZOG_BODYPAD` név szerinti tétel lokális artifactban nem található (`rg` találat nincs `tmp/runs tmp/repro_f683e6f7 samples poc` alatt).

## 5.2 NFP→BLF fallback

Bizonyított tény:
- A fallback implementáció globális és run-szintű (`main.rs:431-446`):
  - ha `has_nominal_holes || has_hole_collapsed`, akkor `effective_placer=blf`.
- Ez minden partra hat, nem csak a lyukasra.

## 5.3 SA/work_budget kimerülés

Bizonyított tény:
- SA explicit `NESTING_ENGINE_STOP_MODE` nélkül work_budget módot állít: `sa.rs:351-360`.
- Work-budget default: `50_000` unit/s, stop policy: `greedy.rs:65-90`.
- Work-budget kifogyás és/vagy hard deadline (`time_limit + grace`) stopol: `greedy.rs:170-181`.
- Repro futásban unplaced ok kizárólag `TIME_LIMIT_EXCEEDED`.

Megjegyzés:
- A user által jelzett „~93-110 s-cel korábban” jelenség ebben a lokális reprodukcióban nem lett 1:1 visszaigazolva; a repro wall time `ELAPSED_SEC=654.19` (`elapsed.txt`), ami konzisztens a 600s + runner/engine oldali ráhagyásokkal.

## 5.4 Nem elhelyezett parttípusok

Bizonyított tény:
- Repro kimenetben `unplaced=10`, ok: `TIME_LIMIT_EXCEEDED`.
- Egyes trial runokban akár teljesen üres placement is előfordul (`solver_stdout.log`: `placements=[]`, `status=partial`, tömeges timeout unplaced).

Akadály:
- A konkrét `NEGYZET/OTSZOG/MACSKANYELV` névcsoportot a lokális artifactok nem tartalmazzák, ezért név szerinti 1:1 mapping jelen adatokból nem igazolható.

# 6. DXF Intake / Project Preparation hibák vizsgálata

## 6.1 Bizonyított hibák

1) Smoke E3-T3 hiba:
- Parancs: `python3 scripts/smoke_dxf_prefilter_e3_t3_geometry_import_gate_integration.py`
- Exit: `1`
- Hiba: `AttributeError: 'types.SimpleNamespace' object has no attribute 'dxf_preflight_required'`
- Trigger pont: `api/routes/files.py:827`

2) Smoke E4-T6 hiba:
- Parancs: `python3 scripts/smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.py`
- Exit: `1`
- Hiba: hiányzó token: `'Accepted files -&gt; parts'`
- UI string jelenleg: `"Accepted files → parts"` (`frontend/src/lib/dxfIntakePresentation.ts:48`)

3) Worker runtime instabilitás:
- `.cache/web_platform/logs/worker.log`
- Nyom: `fetch_backlog_metrics -> _management_query -> TimeoutError: The read operation timed out`

## 6.2 Értelmezés

- E3-T3: tesztfixture drift (beállítás-objektum hiányzó mező) + route elvárás mismatch.
- E4-T6: smoke token elavult (HTML entity vs Unicode nyíl) vagy túl szigorú string assert.
- Worker log timeout: valós futás közbeni management query sérülékenység, nem pusztán UI-probléma.

# 7. Fix opciók összehasonlítása

## 7.1 Option 1 — engine-level fix

Előny:
- A valódi gyökérokot célozza: ne legyen globális fallback az összes partra.
- No-hole partok megtarthatók NFP ágon.

Kockázat:
- Közepes/magas implementációs komplexitás (hibrid placer útvonal, regressziós felület).

## 7.2 Option 2 — DXF/preflight fix

Előny:
- Ha a lyuk nem valódi vágó lyuk, gyorsabb és üzletileg tisztább.
- Jobb user élmény: hamarabb derül ki, mi nem nesting-kompatibilis.

Kockázat:
- Rossz szabály esetén legitim belső kivágások is elveszhetnek.
- Erős role/layer/color alapú policy kell, nem filename hack.

## 7.3 Option 3 — preflight reject + user-facing message

Előny:
- Megakadályozza a 600s körüli késői futáshibát.
- Gyorsan bevezethető védőkorlát.

Kockázat:
- Nem oldja meg az engine korlátot, csak korábban leállít.

# 8. Javasolt valódi fix

Elsődleges javaslat: **Option 1 (engine-level hibrid)**.

Konkrét irány:
- A globális `has_nominal_holes || has_hole_collapsed => BLF` gating kiváltása part-szintű stratégiával.
- No-hole partok NFP-n maradjanak, lyukas partok menjenek biztonságos fallback ágon.
- Kötelező regresszió:
  - lyukas part jelenléte mellett no-hole partoknál `NEST_NFP_STATS_V1.nfp_compute_calls > 0`.
  - ne legyen teljes run-szintű `effective_placer=blf` kizárólag 1 lyukas part miatt.

Rövid távú védőháló (amíg az engine fix kész): **Option 3** preflight reject világos üzenettel.

# 9. Lefuttatott parancsok exit code-okkal

## 9.1 Mostani ellenőrzésben

- `rg -n 'fallback to blf' tmp/runs -S` -> `0`
- `python3 -c "... tmp/repro_f683e6f7/manual_repro_20260427/stdout.json ..."` -> `0`
- `python3 scripts/smoke_dxf_prefilter_e3_t3_geometry_import_gate_integration.py` -> `1`
- `python3 scripts/smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.py` -> `1`
- `rg -n 'TimeoutError|fetch_backlog_metrics|_management_query' .cache/web_platform/logs/worker.log` -> `0`

## 9.2 Korábbi futásból (azonos workspace)

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml` -> `101`
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml -- --test-threads=1` -> `0`
- `cd frontend && npm run build` -> `0`
- `cd frontend && npx playwright test e2e/dxf_prefilter_e5_t3_dxf_intake.spec.ts` -> `0`
- E2/E4/E5 smoke csomag vegyesen futott; E3-T3 és E4-T6 fail bizonyított, több E2/E5 smoke `0`.

# 10. Átnézett fájlok

- `rust/nesting_engine/src/main.rs`
- `rust/nesting_engine/src/placement/blf.rs`
- `rust/nesting_engine/src/placement/nfp_placer.rs`
- `rust/nesting_engine/src/search/sa.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `rust/nesting_engine/src/geometry/pipeline.rs`
- `worker/engine_adapter_input.py`
- `worker/main.py`
- `vrs_nesting/config/nesting_quality_profiles.py`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `api/routes/files.py`
- `frontend/src/lib/dxfIntakePresentation.ts`
- valamint a fenti `tmp/runs/...` és `tmp/repro_f683e6f7/...` artifactok.

# 11. Módosított fájlok, ha voltak

- `codex/reports/nesting_engine/otszog_bodypad_runtime_root_cause_20260428.md` (új riport)

# 12. Tesztbizonyítékok

- Engine fallback bizonyíték: `solver_stderr.log` több runban (`tmp/runs/.../solver_stderr.log`).
- Direkt repro profilok: `tmp/repro_f683e6f7/manual_repro_20260427/stderr.log`.
- Unplaced okok: `tmp/repro_f683e6f7/manual_repro_20260427/stdout.json` (`TIME_LIMIT_EXCEEDED`).
- DXF Intake smoke hibák: E3-T3 és E4-T6 exit `1` stack trace-ekkel.

# 13. Megmaradt kockázatok/blokkolók

## 13.1 Blokkoló probléma részletezve (külön)

**Blokkoló #1: hiányzó letölthető `solver_input`/`engine_meta` artifact URL production runokban.**

Bizonyíték:
- `downloaded_artifact_urls.json` -> `status=400 artifact url failed` (`solver_input`, `engine_meta`).
- Ugyanezekhez tartozó `run_artifacts.json` rekordok léteznek.

Hatás:
- Nem lehet minden érintett production runon 1:1 bemenet-visszajátszást végigvinni.
- Az OTSZOG_BODYPAD és a NEGYZET/OTSZOG/MACSKANYELV név szerinti végső bizonyítás részben adat-hozzáférési korlátba ütközik.

Szükséges következő technikai lépés:
- Artifact URL kiadás útvonal javítása (`api/routes/runs.py` + storage key/prefix konzisztencia), hogy a snapshot inputok letölthetők legyenek.

## 13.2 További kockázatok

- Engine fix nélkül a lyukas part továbbra is globális fallbacket okoz.
- Preflight oldalon nincs még kellően expliciten kommunikált, korai reject a nem támogatott lyukas topológiára.
- Worker management query timeout instabilitás időszakos run-folyamat zavart okozhat.

# Bizonyíték-minősítés

- **Bizonyított tény:** kódszint + futási log közvetlenül alátámasztja.
- **Valószínű ok:** artifact hiány miatt közvetett, de több forrás konzisztensen ugyanabba az irányba mutat.
- **Hipotézis:** OTSZOG/NEGYZET/MACSKANYELV névcsoport 1:1 mappingja további, most nem letölthető production snapshotot igényel.
- **Ajánlott következő implementációs feladat:** engine-level hibrid fallback megszüntetés + artifact URL javítás + preflight guard.
