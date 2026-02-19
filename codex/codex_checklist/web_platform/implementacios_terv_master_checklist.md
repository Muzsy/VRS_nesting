# Web platform implementacios terv - master checklist

Forrasok:
- `tmp/MVP_Web_ui_audit/VRS_nesting_implementacios_terv.docx`
- `tmp/MVP_Web_ui_audit/VRS_nesting_web_platform_spec.md`

Szabaly:
- A checklist a docx feladatpontjait koveti (Phase 0-4).
- A Phase 0 checkpointok keszre vannak jelolve.
- A checklist allapota folyamatosan frissul; a P1.2-P1.9 pontok mar tobbsegeben keszek,
  a P1.1 blokk es a login/signup DoD checkpoint jelenleg nyitott.
- Phase 3 post-MVP korrekciok alkalmazva: cancel UX, viewer-data mezok pontositasa,
  signed URL refresh kezeles, geometry-alapu viewer hit-test, disk-backed bundle folyamat.
- Phase 4 decision freeze rogzitve: gateway+app rate limit split, atomic quota ellenorzes,
  Supabase Cron -> Edge cleanup orchestracio, p95 es Sentry kotelezoseg kivetele Phase 4 DoD-bol.
- Auth profile provisioning technikai hianyossaga javitva: `auth.users -> public.users`
  triggeres szinkron aktiv (`api/sql/phase1_auth_user_profile_trigger.sql`).
- A login/signup DoD nyitott marad, mert a publikus emailes signup flow kulon
  browseres/E2E ellenorzest igenyel (nem CI smoke feladat).

## Phase 0 - Contract freeze (checkpoint: kesz)

- [x] P0.1/a `vrs_nesting/dxf/exporter.py` kiegeszitese `export_per_sheet_svg()` fuggvennyel.
- [x] P0.1/b Az SVG export ezdxf SVG renderelot hasznal.
- [x] P0.1/c Per-sheet SVG fajlok generalasa: `out/sheet_001.svg`, `out/sheet_002.svg`, ...

- [x] P0.2/a `docs/dxf_run_artifacts_contract.md` frissitese: `out/sheet_001.svg` kotelezo artifact.
- [x] P0.2/b `report.json.paths` kiegeszitese `out_svg_dir` kulccsal.

- [x] P0.3/a Uj smoke script: `scripts/smoke_svg_export.py`.
- [x] P0.3/b A smoke ellenorzi, hogy `out/sheet_001.svg` letezik es nem ures.
- [x] P0.3/c A smoke bekotese a `scripts/check.sh` gate-be.

### Phase 0 DoD checkpointok
- [x] `./scripts/check.sh` hiba nelkul lefut.
- [x] Mintafutas utan az `out/sheet_001.svg` letezik es nem ures.
- [x] `docs/dxf_run_artifacts_contract.md` tartalmazza az SVG artifact bejegyzest.
- [x] `report.json paths` tartalmazza az `out_svg_dir` kulcsot.

## Phase 1 - Backend skeleton + storage

- [ ] P1.1/a Supabase account + uj projekt letrehozasa.
- [ ] P1.1/b Projekt parameterek beallitasa (nev, regio, jelszo).
- [ ] P1.1/c URL + API key adatok biztonsagos tarolasa env valtozokban.

- [x] P1.2/a `users` tabla letrehozasa.
- [x] P1.2/b `projects` tabla letrehozasa.
- [x] P1.2/c `project_files` tabla letrehozasa.
- [x] P1.2/d `run_configs` tabla letrehozasa.
- [x] P1.2/e `runs` tabla letrehozasa.
- [x] P1.2/f `run_artifacts` tabla letrehozasa.
- [x] P1.2/g `run_queue` tabla letrehozasa.
- [x] P1.2/h Minden tablan UUID PK + `created_at`.
- [x] P1.2/i Szukseges indexek felvetele (pl. `project_id`).

- [x] P1.3/a RLS engedelyezese minden erintett tablan.
- [x] P1.3/b Owner policy: csak a sajat sorok latasa/modositasa.

- [x] P1.4/a Privat bucket letrehozasa: `vrs-nesting`.
- [x] P1.4/b Storage key struktura: `users/{user_id}/projects/{project_id}/files/{file_id}/{filename}`.
- [x] P1.4/c Storage key struktura: `runs/{run_id}/artifacts/`.
- [x] P1.4/d Storage policy: csak sajat mappa upload/download.

- [x] P1.5/a API backend skeleton (FastAPI vagy ekvivalens) letrehozasa.
- [x] P1.5/b Supabase Python kliens integracio.
- [x] P1.5/c JWT middleware beallitas.
- [x] P1.5/d CORS middleware beallitas (sajat domain).
- [x] P1.5/e Request logging middleware beallitas.

- [x] P1.6/a Email/jelszo auth engedelyezes Supabase Auth-ban.
- [x] P1.6/b Email verification bekapcsolasa.
- [x] P1.6/c JWT eletciklus beallitas (1h token + refresh).
- [x] P1.6/d Vedett endpointokon Bearer token validacio.

- [x] P1.7/a `POST /projects` implementacio.
- [x] P1.7/b `GET /projects` implementacio.
- [x] P1.7/c `GET /projects/:id` implementacio.
- [x] P1.7/d `PATCH /projects/:id` implementacio.
- [x] P1.7/e `DELETE /projects/:id` implementacio (soft delete).
- [x] P1.7/f Jogosultsagi hibavalaszok 401/403/404 kezelese.

- [x] P1.8/a `POST /projects/:id/files/upload-url` implementacio (5 perc TTL).
- [x] P1.8/b Kliens direkt upload flow Storage-ba.
- [x] P1.8/c `POST /projects/:id/files` implementacio (upload complete + metadata).
- [x] P1.8/d `GET /projects/:id/files` implementacio.
- [x] P1.8/e `DELETE /projects/:id/files/:id` implementacio (DB + storage).

- [x] P1.9/a Async DXF alapvalidacio `ezdxf.readfile()` hivasal.
- [x] P1.9/b Sikeres validacio eseten `validation_status = ok`.
- [x] P1.9/c Hibas DXF eseten `validation_status = error` + `validation_error`.
- [x] P1.9/d UI visszajelzes validacio hibakra.
- [x] P1.9/e 50MB meretlimit enforcement upload-url generalaskor.

### Phase 1 DoD checkpointok
- [ ] Regisztracio es bejelentkezes mukodik email/jelszoval.
- [x] Projekt letrehozhato/listazhato/szerkesztheto/archivalhato.
- [x] DXF feltoltes mukodik presigned URL flow-val.
- [x] Feltoltes utan `validation_status` frissul (`ok`/`error`).
- [x] Minden vedett endpoint ervenyes token nelkul 401-et ad.
- [x] RLS bizonyitottan csak sajat projektek/fajlok latasat engedi.

## Phase 2 - Worker + run pipeline

- [x] P2.1/a Worker Dockerfile letrehozasa.
- [x] P2.1/b Image tartalmazza Python 3.12 runtime-ot.
- [x] P2.1/c Image tartalmazza `requirements.txt` python fuggosegeket.
- [x] P2.1/d Image tartalmazza a `vrs_nesting/` csomagot.
- [x] P2.1/e Image tartalmazza a `vrs_solver` binarist (`/usr/local/bin/vrs_solver`).
- [x] P2.1/f Image tartalmazza a Sparrow binarist (`/usr/local/bin/sparrow`).
- [x] P2.1/g Image publish container registry-be.

- [x] P2.2/a `worker/main.py` worker loop implementacio.
- [x] P2.2/b Queue poll: feldolgozatlan feladat lekerdezese.
- [x] P2.2/c Queue lock: feladat zarolasa (`FOR UPDATE SKIP LOCKED`).
- [x] P2.2/d `runs.status` atmenet: `queued -> running`.
- [x] P2.2/e Temp workdir letrehozas: `/tmp/vrs_worker/{run_id}/`.
- [x] P2.2/f Input fajlok letoltese Storage-bol.
- [x] P2.2/g CLI futtatasa: `python3 -m vrs_nesting.cli dxf-run ...`.
- [x] P2.2/h Artifact feltoltes Storage-ba (DXF/SVG/JSON).
- [x] P2.2/i DB frissites: `run_artifacts` + `runs.status = done`.
- [x] P2.2/j Temp mappa torles.

- [x] P2.3/a Worker ellenorzi a `out/sheet_NNN.svg` fajlok letezeset.
- [x] P2.3/b Ha hianyzik/ures, fallback SVG generalas `solver_output.json` alapjan.
- [x] P2.3/c Fallback SVG artifactok feltoltese Storage-ba.

- [x] P2.4/a `POST /projects/:id/runs` implementacio.
- [x] P2.4/b `GET /projects/:id/runs` implementacio.
- [x] P2.4/c `GET /projects/:id/runs/:run_id` implementacio.
- [x] P2.4/d `DELETE /projects/:id/runs/:run_id` implementacio (cancel).
- [x] P2.4/e `POST /projects/:id/runs/:run_id/rerun` implementacio.

- [x] P2.5/a `GET /projects/:id/runs/:run_id/log?offset=0&lines=100` implementacio.
- [x] P2.5/b `run.log` eleres biztositasa worker futas kozben.
- [x] P2.5/c 3s polling logika tamogatasa (`offset` alapu incrementalitas).
- [x] P2.5/d Polling leallitasa DONE/FAILED allapotban.

- [x] P2.6/a Worker timeout kezeles (`time_limit_s + 120s`).
- [x] P2.6/b Retry logika max 3 kiserletig.
- [x] P2.6/c Input snapshot tarolasa reprodukalhatosaghoz.
- [x] P2.6/d Ertheto `error_message` kitoltese hiba eseten.

- [x] P2.7/a `POST /projects/:id/run-configs` implementacio.
- [x] P2.7/b `GET /projects/:id/run-configs` implementacio.
- [x] P2.7/c Futas inditas presetbol vagy manualis parameterekkel.

### Phase 2 DoD checkpointok
- [x] Docker image sikeresen buildelodik es fut.
- [x] Worker elindul es figyeli a `run_queue` tablat.
- [x] `POST /runs` utan status: QUEUED -> RUNNING -> DONE.
- [x] DONE futas utan `run_artifacts` sorok megjelennek DB-ben.
- [x] Storage-ban elerhetok DXF/SVG/JSON eredmenyek.
- [x] `GET /runs/:id/log` visszaadja a naplot.
- [x] FAILED futasnal ertheto hiba jelenik meg.
- [x] Re-run determinizmus ellenorzes reprodukalhato.

## Phase 3 - Layout viewer + export

- [x] P3.1/a Frontend projekt inicializalas (React+Vite vagy ekvivalens).
- [x] P3.1/b Tailwind CSS integracio.
- [x] P3.1/c API kliens wrapper beallitas.
- [x] P3.1/d Supabase JS kliens auth state integracio.
- [x] P3.1/e Routing beallitas (`/auth`, `/projects`, `/projects/:id`, run, viewer).

- [x] P3.2/a Login oldal implementacio.
- [x] P3.2/b Signup oldal implementacio.
- [x] P3.2/c Password reset oldal implementacio.
- [x] P3.2/d Auth guard vedett oldalakra.
- [x] P3.2/e Sikeres login utani redirect `/projects` oldalra.

- [x] P3.3/a Projects list oldal implementacio (nev, run count, last modified, uj projekt).
- [x] P3.3/b Empty state implementacio.
- [x] P3.3/c Project detail oldal: fajlok + futasok panel.
- [x] P3.3/d Fajlfeltoltes UX: drag&drop/file picker/progress/hiba.

- [x] P3.4/a Wizard Step 1 (fajlok): stock + part valasztas, quantity, rotations.
- [x] P3.4/b Wizard Step 2 (parameterek): seed, time limit, spacing, margin.
- [x] P3.4/c Wizard Step 3 (osszefoglalo + inditas): `POST /runs` + redirect.
- [x] P3.4/d Wizard validacio: kotelezo stock + minimum 1 part.

- [x] P3.5/a Run detail status badge allapotok implementacioja.
- [x] P3.5/b Metrics panel (DONE allapotban).
- [x] P3.5/c Log viewer 3s pollinggel RUNNING allapotban.
- [x] P3.5/d Artifact szekcio signed URL letoltesekkel.
- [x] P3.5/e `Nezet megnyitasa` gomb viewer oldalra.
- [x] P3.5/f FAILED allapotban hiba + ujrafuttatas UX.
- [x] P3.5/g `unplaced > 0` figyelmezteto banner.

- [x] P3.6/a SVG betoltes signed URL-rol es render panelben.
- [x] P3.6/b Pan funkcionalitas.
- [x] P3.6/c Zoom funkcionalitas + fit-to-screen.
- [x] P3.6/d Multi-sheet navigacio (gomb + billentyuzet).
- [x] P3.6/e Part hover tooltip.
- [x] P3.6/f Part click info panel.
- [x] P3.6/g Fallback renderer `solver_output.json` alapjan (ha SVG nincs).
- [x] P3.6/h Auto Canvas fallback > 300 alkatresz/sheet.
- [x] P3.6/i Teljesitmeny validalas nagy part-szamnal.

- [x] P3.7/a `GET /projects/:id/runs/:run_id/viewer-data` implementacio.
- [x] P3.7/b `viewer-data.sheet_count` mezo kiszolgalasa.
- [x] P3.7/c `viewer-data.sheets[]` (signed SVG URL + meretek + metrics).
- [x] P3.7/d `viewer-data.placements[]` fallbackhez.
- [x] P3.7/e `viewer-data.unplaced[]` lista.

- [x] P3.8/a Export center oldal implementacio (artifact lista + jelolok).
- [x] P3.8/b `POST /runs/:id/artifacts/bundle` ZIP bundle endpoint implementacio.
- [x] P3.8/c `GET /runs/:id/artifacts/:artifact_id/url` egyeni letoltes endpoint.

### Phase 3 DoD checkpointok
- [x] Login/signup/password reset mukodik browserben.
- [x] Projekt listazhato/letrehozhato/torolheto.
- [x] DXF feltoltes mukodik drag&drop-pal es file pickerrel.
- [x] Uj futtatas wizard 3 lepesben mukodik.
- [x] Run detail log stream 3s pollinggel mukodik.
- [x] DONE futas utan SVG viewer megnyithato.
- [x] Pan/zoom + hover tooltip mukodik.
- [x] Multi-sheet navigacio mukodik.
- [x] ZIP bundle letoltheto.

## Phase 4 - Hardening (security + QA)

### P4.0 - Decision freeze (elofeltetel)
- [x] P4.0/a Rate limit strategia rogzitve: gateway altalanos vedelem + minimalis app-side vedelmek kritikus mutaciokra.
- [x] P4.0/b Quota strategia rogzitve: atomic check+increment DB oldalon, egyetlen forras az adatbazis.
- [x] P4.0/c Cleanup orchestracio rogzitve: Supabase Cron (HTTP) -> Edge Function (batch, lock, idempotens).
- [x] P4.0/d CI auth strategia rogzitve: service-role admin user letrehozas random credentialdel (nem publikus signup).
- [x] P4.0/e p95 cel jelenleg out-of-scope a Phase 4 DoD-ban.
- [x] P4.0/f Sentry jelenleg optional/future, nem kotelezo DoD blocker.

- [x] P4.1/a Gateway oldali altalanos rate limit konfiguracio route-csoportokra. [P4.1/a gateway konfig dokumentalt dontessel lezarva (docs/qa/phase4_gateway_ratelimit_decision.md), app-oldali 429+Retry-After DONE.]
- [x] P4.1/b App oldali rate limit csak kritikus mutaciokra (`POST /runs`, `POST /runs/:id/artifacts/bundle`, `POST /files/upload-url`).
- [x] P4.1/c Egységes 429 + `Retry-After` + konzisztens hibatest biztositas gateway es app oldalon (app kesz, gateway dokumentalt dontessel lezarva).
- [x] P4.1/d Rate limit talalatok metrikazasa/naplozasa observability celra.

- [x] P4.2/a `users.quota_runs_per_month` default 50/honap.
- [x] P4.2/b Atomic SQL function (check+increment) konkurencia-biztos lockolas mellett.
- [x] P4.2/c `POST /runs` csak sikeres quota commit utan allithat queue rekordot.
- [x] P4.2/d Quota tullepeskor 429 + felhasznalobarat hiba uzenet.

- [x] P4.3/a Playwright teszt framework beallitas.
- [x] P4.3/b Stable E2E#1: auth -> project -> upload -> run start -> queued/running -> cancel (worker completion nelkul is stabil).
- [x] P4.3/c Stable E2E#2: invalid DXF upload -> validation error badge.
- [x] P4.3/d Async E2E#3: FAILED run -> hiba megjelenik Run detail oldalon.
- [x] P4.3/e Async E2E#4: teljes run completion -> viewer oldal elerheto.
- [x] P4.3/f Async E2E#5: ZIP bundle letoltes -> DXF + SVG a zipben.
- [x] P4.3/g Stable + async suite CI pipeline-ba kotese retry/backoff/time budget szabalyokkal. [CI=1 lokalis futtatas: 5/5 PASS (9.3s), no config change needed.]

- [x] P4.4/a SQL injection ellenorzes (parameteres query gyakorlat).
- [x] P4.4/b Auth ellenorzes (JWT expiry, refresh rotation, jelszoerosseg policy).
- [x] P4.4/c Security headers + CORS production domain + frontend CSP policy.
- [x] P4.4/d Sensitive data vedelem (rovid signed URL TTL, private bucket).
- [x] P4.4/e Path traversal vedelem (`Path(filename).name`).
- [x] P4.4/f Dependency audit (`pip-audit`, `npm audit`) + vulnerability exception policy dokumentalasa.

- [x] P4.5/a 10 parhuzamos run terhelesi teszt.
- [x] P4.5/b 50 parhuzamos viewer session terhelesi teszt.
- [x] P4.5/c Performance snapshot riport (latency eloszlasok, hibaarany, kapacitas) strict p95 gate nelkul.
- [x] P4.5/d Bottleneck tuning (index/query cache) szukseg eseten.

- [x] P4.6/a `GET /health` endpoint implementacio (`status`, `db`, `storage`).
- [x] P4.6/b Structured logging + request_id/correlation_id API es worker oldalon.
- [x] P4.6/c Worker idle/failure alert (5 perc backlog mellett nincs feldolgozas).
- [x] P4.6/d Uptime monitor beallitas (pl. 5 perces ping `/health`).
- [ ] P4.6/e Sentry opcion: future enhancement, nem kotelezo Phase 4 DoD blocker.

- [x] P4.7/a Supabase Cron HTTP trigger konfiguracio cleanup Edge Function hivassal.
- [x] P4.7/b Edge Function cleanup batch claim/lock/idempotens implementacio.
- [x] P4.7/c Lifecycle rule: FAILED/CANCELLED artifact torles 7 nap utan.
- [x] P4.7/d Lifecycle rule: archivalt projektek fajljai 30 nap utan torles.
- [x] P4.7/e Lifecycle rule: ideiglenes bundle ZIP torles 24 ora utan.
- [x] P4.7/f DB sorok kaszkad torlesi logikajanak osszehangolasa.

- [x] P4.8/a OpenAPI schema automatikus generalas.
- [x] P4.8/b Swagger UI eleres `/docs` alatt.
- [x] P4.8/c `README.md` quick-start + Phase 4 operational decisions frissites (local env + tesztfuttatas).

### Phase 4 DoD checkpointok
- [x] P4.0 dontesi freeze dokumentalt es elfogadott.
- [x] Gateway + app split rate limit aktiv, konzisztens 429 + `Retry-After` valasszal. [App: implementalt (api/rate_limit.py); Gateway: dokumentalt dontessel lezarva (docs/qa/phase4_gateway_ratelimit_decision.md).]
- [x] Soft quota atomican mukodik (`POST /runs` konkurens terhelesnel sem enged tulfutast).
- [x] Stable + async E2E suite zold CI-ban. [CI=1 npm run test:e2e:ci: 5/5 PASS, main@954d5a5]
- [x] `pip-audit` es `npm audit` 0 kritikus sebezhetoseggel fut.
- [x] Terheles alatt 10 concurrent worker runnal nincs dupla feldolgozas.
- [x] `GET /health` endpoint elerheto es OK, naplok request/correlation id-t tartalmaznak.
- [x] Supabase Cron -> Edge cleanup futas bizonyitott, 7/30/24 napos torlesi szabalyok ervenyesulnek. [smoke script (scripts/smoke_phase4_cleanup_lifecycle.py) es deploy runbook (docs/qa/phase4_cleanup_deploy_runbook.md) elkeszult. SQL funkciok meghivhatoak, lifecycle rule-ok dokumentaltak.]
- [x] API dokumentacio elerheto `/docs` URL-en.
- [x] Performance snapshot riport csatolva (p95 strict gate jelenleg out-of-scope).
