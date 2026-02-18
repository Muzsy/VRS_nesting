# Web platform implementacios terv - master checklist

Forrasok:
- `tmp/MVP_Web_ui_audit/VRS_nesting_implementacios_terv.docx`
- `tmp/MVP_Web_ui_audit/VRS_nesting_web_platform_spec.md`

Szabaly:
- A checklist a docx feladatpontjait koveti (Phase 0-4).
- A Phase 0 checkpointok keszre vannak jelolve.
- A checklist allapota folyamatosan frissul; a P1.2-P1.9 pontok mar tobbsegeben keszek,
  a P1.1 blokk es a login/signup DoD checkpoint jelenleg nyitott.
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

- [ ] P2.1/a Worker Dockerfile letrehozasa.
- [ ] P2.1/b Image tartalmazza Python 3.12 runtime-ot.
- [ ] P2.1/c Image tartalmazza `requirements.txt` python fuggosegeket.
- [ ] P2.1/d Image tartalmazza a `vrs_nesting/` csomagot.
- [ ] P2.1/e Image tartalmazza a `vrs_solver` binarist (`/usr/local/bin/vrs_solver`).
- [ ] P2.1/f Image tartalmazza a Sparrow binarist (`/usr/local/bin/sparrow`).
- [ ] P2.1/g Image publish container registry-be.

- [ ] P2.2/a `worker/main.py` worker loop implementacio.
- [ ] P2.2/b Queue poll: feldolgozatlan feladat lekerdezese.
- [ ] P2.2/c Queue lock: feladat zarolasa (`FOR UPDATE SKIP LOCKED`).
- [ ] P2.2/d `runs.status` atmenet: `queued -> running`.
- [ ] P2.2/e Temp workdir letrehozas: `/tmp/vrs_worker/{run_id}/`.
- [ ] P2.2/f Input fajlok letoltese Storage-bol.
- [ ] P2.2/g CLI futtatasa: `python3 -m vrs_nesting.cli dxf-run ...`.
- [ ] P2.2/h Artifact feltoltes Storage-ba (DXF/SVG/JSON).
- [ ] P2.2/i DB frissites: `run_artifacts` + `runs.status = done`.
- [ ] P2.2/j Temp mappa torles.

- [ ] P2.3/a Worker ellenorzi a `out/sheet_NNN.svg` fajlok letezeset.
- [ ] P2.3/b Ha hianyzik/ures, fallback SVG generalas `solver_output.json` alapjan.
- [ ] P2.3/c Fallback SVG artifactok feltoltese Storage-ba.

- [ ] P2.4/a `POST /projects/:id/runs` implementacio.
- [ ] P2.4/b `GET /projects/:id/runs` implementacio.
- [ ] P2.4/c `GET /projects/:id/runs/:run_id` implementacio.
- [ ] P2.4/d `DELETE /projects/:id/runs/:run_id` implementacio (cancel).
- [ ] P2.4/e `POST /projects/:id/runs/:run_id/rerun` implementacio.

- [ ] P2.5/a `GET /projects/:id/runs/:run_id/log?offset=0&lines=100` implementacio.
- [ ] P2.5/b `run.log` eleres biztositasa worker futas kozben.
- [ ] P2.5/c 3s polling logika tamogatasa (`offset` alapu incrementalitas).
- [ ] P2.5/d Polling leallitasa DONE/FAILED allapotban.

- [ ] P2.6/a Worker timeout kezeles (`time_limit_s + 120s`).
- [ ] P2.6/b Retry logika max 3 kiserletig.
- [ ] P2.6/c Input snapshot tarolasa reprodukalhatosaghoz.
- [ ] P2.6/d Ertheto `error_message` kitoltese hiba eseten.

- [ ] P2.7/a `POST /projects/:id/run-configs` implementacio.
- [ ] P2.7/b `GET /projects/:id/run-configs` implementacio.
- [ ] P2.7/c Futas inditas presetbol vagy manualis parameterekkel.

### Phase 2 DoD checkpointok
- [ ] Docker image sikeresen buildelodik es fut.
- [ ] Worker elindul es figyeli a `run_queue` tablat.
- [ ] `POST /runs` utan status: QUEUED -> RUNNING -> DONE.
- [ ] DONE futas utan `run_artifacts` sorok megjelennek DB-ben.
- [ ] Storage-ban elerhetok DXF/SVG/JSON eredmenyek.
- [ ] `GET /runs/:id/log` visszaadja a naplot.
- [ ] FAILED futasnal ertheto hiba jelenik meg.
- [ ] Re-run determinizmus ellenorzes reprodukalhato.

## Phase 3 - Layout viewer + export

- [ ] P3.1/a Frontend projekt inicializalas (React+Vite vagy ekvivalens).
- [ ] P3.1/b Tailwind CSS integracio.
- [ ] P3.1/c API kliens wrapper beallitas.
- [ ] P3.1/d Supabase JS kliens auth state integracio.
- [ ] P3.1/e Routing beallitas (`/auth`, `/projects`, `/projects/:id`, run, viewer).

- [ ] P3.2/a Login oldal implementacio.
- [ ] P3.2/b Signup oldal implementacio.
- [ ] P3.2/c Password reset oldal implementacio.
- [ ] P3.2/d Auth guard vedett oldalakra.
- [ ] P3.2/e Sikeres login utani redirect `/projects` oldalra.

- [ ] P3.3/a Projects list oldal implementacio (nev, run count, last modified, uj projekt).
- [ ] P3.3/b Empty state implementacio.
- [ ] P3.3/c Project detail oldal: fajlok + futasok panel.
- [ ] P3.3/d Fajlfeltoltes UX: drag&drop/file picker/progress/hiba.

- [ ] P3.4/a Wizard Step 1 (fajlok): stock + part valasztas, quantity, rotations.
- [ ] P3.4/b Wizard Step 2 (parameterek): seed, time limit, spacing, margin.
- [ ] P3.4/c Wizard Step 3 (osszefoglalo + inditas): `POST /runs` + redirect.
- [ ] P3.4/d Wizard validacio: kotelezo stock + minimum 1 part.

- [ ] P3.5/a Run detail status badge allapotok implementacioja.
- [ ] P3.5/b Metrics panel (DONE allapotban).
- [ ] P3.5/c Log viewer 3s pollinggel RUNNING allapotban.
- [ ] P3.5/d Artifact szekcio signed URL letoltesekkel.
- [ ] P3.5/e `Nezet megnyitasa` gomb viewer oldalra.
- [ ] P3.5/f FAILED allapotban hiba + ujrafuttatas UX.
- [ ] P3.5/g `unplaced > 0` figyelmezteto banner.

- [ ] P3.6/a SVG betoltes signed URL-rol es render panelben.
- [ ] P3.6/b Pan funkcionalitas.
- [ ] P3.6/c Zoom funkcionalitas + fit-to-screen.
- [ ] P3.6/d Multi-sheet navigacio (gomb + billentyuzet).
- [ ] P3.6/e Part hover tooltip.
- [ ] P3.6/f Part click info panel.
- [ ] P3.6/g Fallback renderer `solver_output.json` alapjan (ha SVG nincs).
- [ ] P3.6/h Auto Canvas fallback > 300 alkatresz/sheet.
- [ ] P3.6/i Teljesitmeny validalas nagy part-szamnal.

- [ ] P3.7/a `GET /projects/:id/runs/:run_id/viewer-data` implementacio.
- [ ] P3.7/b `viewer-data.sheet_count` mezo kiszolgalasa.
- [ ] P3.7/c `viewer-data.sheets[]` (signed SVG URL + meretek + metrics).
- [ ] P3.7/d `viewer-data.placements[]` fallbackhez.
- [ ] P3.7/e `viewer-data.unplaced[]` lista.

- [ ] P3.8/a Export center oldal implementacio (artifact lista + jelolok).
- [ ] P3.8/b `POST /runs/:id/artifacts/bundle` ZIP bundle endpoint implementacio.
- [ ] P3.8/c `GET /runs/:id/artifacts/:artifact_id/url` egyeni letoltes endpoint.

### Phase 3 DoD checkpointok
- [ ] Login/signup/password reset mukodik browserben.
- [ ] Projekt listazhato/letrehozhato/torolheto.
- [ ] DXF feltoltes mukodik drag&drop-pal es file pickerrel.
- [ ] Uj futtatas wizard 3 lepesben mukodik.
- [ ] Run detail log stream 3s pollinggel mukodik.
- [ ] DONE futas utan SVG viewer megnyithato.
- [ ] Pan/zoom + hover tooltip mukodik.
- [ ] Multi-sheet navigacio mukodik.
- [ ] ZIP bundle letoltheto.

## Phase 4 - Hardening (security + QA)

- [ ] P4.1/a Rate limit beallitas API gateway szinten (60 req/perc/user).
- [ ] P4.1/b 429 + `Retry-After` valasz limit tullepeskor.
- [ ] P4.1/c Kulon upload limit (pl. 10 upload/perc).

- [ ] P4.2/a `users.quota_runs_per_month` default 50/honap.
- [ ] P4.2/b `POST /runs` elott havi quota ellenorzes.
- [ ] P4.2/c Quota tullepeskor 429 + felhasznalobarat uzenet.

- [ ] P4.3/a Playwright teszt framework beallitas.
- [ ] P4.3/b E2E#1 Happy path (login -> project -> upload -> run -> poll -> viewer).
- [ ] P4.3/c E2E#2 Invalid DXF upload -> validation error badge.
- [ ] P4.3/d E2E#3 FAILED run -> hiba megjelenik Run detail oldalon.
- [ ] P4.3/e E2E#4 ZIP bundle letoltes -> DXF + SVG a zipben.
- [ ] P4.3/f E2E#5 Re-run -> azonos elhelyezesi metrikak (determinizmus).
- [ ] P4.3/g E2E tesztek CI pipeline-ba kotese.

- [ ] P4.4/a SQL injection ellenorzes (parameteres query gyakorlat).
- [ ] P4.4/b Auth ellenorzes (JWT expiry, refresh rotation, jelszoerosseg).
- [ ] P4.4/c Sensitive data vedelem (rovid signed URL TTL, private bucket).
- [ ] P4.4/d Path traversal vedelem (`Path(filename).name`).
- [ ] P4.4/e CORS production domainre korlatozasa.
- [ ] P4.4/f Dependency audit (`pip-audit`, `npm audit`).

- [ ] P4.5/a 10 parhuzamos run terhelesi teszt.
- [ ] P4.5/b 50 parhuzamos viewer session terhelesi teszt.
- [ ] P4.5/c API p95 latencia cel validalas (<500ms).
- [ ] P4.5/d Bottleneck tuning (index/query cache) szukseg eseten.

- [ ] P4.6/a `GET /health` endpoint implementacio (`status`, `db`, `storage`).
- [ ] P4.6/b Sentry integracio API + frontend oldalon.
- [ ] P4.6/c Worker idle/failure alert (5 perc backlog mellett nincs feldolgozas).
- [ ] P4.6/d Uptime monitor beallitas (pl. 5 perces ping `/health`).

- [ ] P4.7/a Lifecycle rule: FAILED/CANCELLED artifact torles 7 nap utan.
- [ ] P4.7/b Lifecycle rule: archivalt projektek fajljai 30 nap utan torles.
- [ ] P4.7/c Lifecycle rule: ideiglenes bundle ZIP torles 24 ora utan.
- [ ] P4.7/d DB sorok kaszkad torlesi logikajanak osszehangolasa.

- [ ] P4.8/a OpenAPI schema automatikus generalas.
- [ ] P4.8/b Swagger UI eleres `/docs` alatt.
- [ ] P4.8/c `README.md` quick-start frissites (local env + tesztfuttatas).

### Phase 4 DoD checkpointok
- [ ] Rate limit mukodik (429 60 req/perc felett).
- [ ] Soft quota mukodik (50 run/honap felett hiba).
- [ ] Mind az 5 E2E teszt zold.
- [ ] `pip-audit` es `npm audit` 0 kritikus sebezhetoseggel fut.
- [ ] Terheles alatt 10 concurrent worker runnal nincs dupla feldolgozas.
- [ ] API p95 latencia < 500ms terheles alatt.
- [ ] `GET /health` endpoint elerheto es OK.
- [ ] Sentry rogzit API hibakat.
- [ ] S3 lifecycle rule aktiv a FAILED futasokra (7 nap).
- [ ] API dokumentacio elerheto `/docs` URL-en.
