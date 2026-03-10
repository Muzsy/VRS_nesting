# canvases/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md

# H0-E1-T3 snapshot-first futasi es adatkontraktus formalizalasa

## Funkcio
A feladat a web platform snapshot-first futasi modelljenek es a futashoz kapcsolodo
adatkontraktusoknak a vegleges formalizalasa. A cel, hogy a H0-E2 core schema mar
ne csak modul- es domain-szinten legyen helyes, hanem futasi oldalrol is lezart
adat- es allapotmodellre epuljon.

Ez a task kozvetlenul a H0-E1-T2 domain entitasterkep veglegesitese utan kovetkezik.
A modulhatarak es a domain entitasok mar le vannak zarva; most azt kell egzaktan
rogziteni, hogy hogyan lesz egy elo domain allapotbol determinisztikus run snapshot,
mit kap meg a worker, mit allithat elo, mit NEM olvashat kozvetlenul, es hogyan
kulonul el a run request, a snapshot, a run state, a run result, a projection es az export.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - snapshot-first futasi modell formalizalasa;
  - run request / run snapshot / run execution / run result / projection / export
    vilagok explicit kulonvalasztasa;
  - worker input es output boundary rogzitese;
  - futasi allapotgep magas szintu definialasa;
  - idempotencia, retry, timeout, lease es cancel szabalyok rogzitese;
  - immutable snapshot contract es manifest-szintu adatkezeles formalizalasa;
  - dedikalt H0 snapshot-first dokumentum letrehozasa;
  - fo web_platform dokumentumok hivatkozasainak frissitese.
- Nincs benne:
  - SQL migraciok irasa;
  - tenyleges queue implementacio;
  - API endpoint kodolas;
  - worker kod vagy orchestracio modositas;
  - frontend polling vagy streaming implementacio;
  - OpenAPI schema vagy JSON Schema veglegesitese kodszinten.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi a kulonbseg a run request es a run snapshot kozott?
- [ ] Mikor jon letre a snapshot, es mibol epul fel?
- [ ] Mit olvashat a worker kozvetlenul, es mit nem?
- [ ] Mi szamit snapshot tartalomnak, es mi csak hivatkozasnak/manifestnek?
- [ ] Mi a run allapotgepe a requesttol a lezart eredmenyig?
- [ ] Hogyan kezeljuk a retry-t, timeoutot, cancel-t es lease-t?
- [ ] Hogyan valik kulon a run result, a projection es az export artifact?
- [ ] Mi az idempotencia alapja: request key, snapshot hash, config hash, vagy ezek kombinacioja?
- [ ] Milyen schema-kovetkezmenyei vannak ennek a H0-E2 core schema feladatra?

### Feladatlista
- [ ] Kesz legyen egy dedikalt H0 snapshot-first futasi es adatkontraktus dokumentum.
- [ ] Legyen kulon szekcio a run request, run snapshot, run state, run result,
      projection es export artifact fogalmakra.
- [ ] Legyen worker boundary szabaly: input, output, tilos direkt olvasas/iras.
- [ ] Legyen magas szintu run allapotgep.
- [ ] Legyen timeout / retry / lease / cancel / idempotencia szabaly.
- [ ] Legyen snapshot content vs blob reference vs derived artifact kulonvalasztas.
- [ ] README + architecture + domain entitasterkep + H0 roadmap frissuljon az uj
      dokumentum hivatkozasaval.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.yaml`
- `codex/prompts/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa/run.md`
- `codex/codex_checklist/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md`
- `codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md`
- `docs/web_platform/README.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tartalom az uj snapshot-first dokumentumban
- dokumentum szerepe es dontesi elsoseg
- fogalmi kulonvalasztas:
  - Run Request
  - Run Snapshot
  - Run Attempt / Execution
  - Run State
  - Run Result
  - Projection
  - Export Artifact
- snapshot-letrehozas trigger pontja
- snapshot build source matrix:
  - mely elo domain entitasokbol epul
  - mi masolodik bele immutable formaban
  - mi marad blob/manifest referencia
- worker contract:
  - mit kap bemenetnek
  - mi a kotelezo output
  - mit tilos kozvetlenul olvasni
  - mit tilos visszairni
- run allapotgep javaslat:
  - draft/requested
  - snapshot_building
  - snapshot_ready
  - queued
  - leased/running
  - succeeded
  - failed
  - timed_out
  - cancelled
- retry es attempt-szabalyok
- lease ownership es heartbeat elvek
- timeout politika magas szinten
- idempotencia es deduplikacio elvek
- result vs projection vs export matrix
- H0-E2 schema kovetkezmenyek
- anti-pattern lista:
  - worker elo domain tablakbol olvas
  - worker snapshotot modosit helyben
  - result/projection/export osszemosasa
  - retry uj snapshot nelkul rossz okból
  - cancel utan tovabb futo side effectek truth-kent kezelese

### DoD
- [ ] Letrejon a `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
      dokumentum.
- [ ] A dokumentum egyertelmuen elvalasztja a run request, run snapshot, run state,
      run result, projection es export artifact vilagokat.
- [ ] Dokumentalva van a worker boundary: milyen inputot kap, milyen outputot ad,
      es mit nem olvashat/irhat kozvetlenul.
- [ ] Dokumentalva van a magas szintu run lifecycle es allapotgep.
- [ ] Dokumentalva van timeout, retry, lease, cancel es idempotencia szemantika.
- [ ] Dokumentalva van, hogy a snapshot immutable futasi truth, es a worker nem
      elo domain allapotbol dolgozik.
- [ ] A `docs/web_platform/README.md`,
      `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`,
      `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
      es `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      hivatkozik az uj dokumentumra.
- [ ] A dokumentum explicit inputkent hasznalhato a kovetkezo H0-E2 core schema taskhoz.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - a dokumentum tul kozel megy implementaciohoz, de megsem lesz schema-szinten hasznos;
  - vagy tul absztrakt marad, es a H0-E2 schema tasknak nem ad fogodzot;
  - az allapotgep vagy retry-szabalyok ellentmondanak a korabbi docs-only elveknek.
- Mitigacio:
  - fogalmi szint, de schema-elokeszito precizitas;
  - kulon matrix a request / snapshot / result / projection / export vilagokra;
  - osszhang kotelezo a H0-E1-T1 es H0-E1-T2 dokumentumokkal.
- Rollback:
  - docs-only modositasok tortenjenek;
  - egy commitban visszafordithato legyen az egesz task.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md`
- Manualis ellenorzes:
  - nincs keveredese a request / snapshot / result / projection / export vilagoknak;
  - a worker boundary explicit;
  - az allapotgep es retry/timeout logika ertelmesen formalizalt;
  - a kovetkezo schema task szamara eleg konkret a fogalmazas.

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/README.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/platform_roadmap_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_master_roadmap_h0_h3.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`