# H0 snapshot-first futasi es adatkontraktus (source of truth)

## 1. Dokumentum szerepe

Ez a dokumentum a H0 futasi modell es adatkontraktus source-of-truth leirasa.
A cel: a run requesttol a run resultig minden allapot, input es output egyertelmu
es schema-tervezeshez hasznalhato legyen.

Prioritas konfliktus eseten:
1. modulhatar tiltasok: `h0_modulhatarok_es_boundary_szerzodes.md`
2. domain entitas ownership: `h0_domain_entitasterkep_es_ownership_matrix.md`
3. futasi allapot es worker contract: ez a dokumentum

Kapcsolodo dokumentumok:
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`

## 2. Fogalmi kulonvalasztas

- Run Request: felhasznaloi vagy API inditasi szandek, amely meghatarozza a futas celjat.
- Run Snapshot: immutable futasi truth, amely a request idopontjaban befagyasztott bemenet.
- Run Attempt (Execution): egy konkret worker-lease alatt lefutott probalkozas ugyanarra a snapshotra.
- Run State: a request/attempt eletciklus allapota (queued, running, failed, stb.).
- Run Result: canonical futasi eredmeny (placements, unplaced, core metrics).
- Projection: query/view reteg, amely a resultbol szarmaztatott, ujraepitheto adat.
- Export Artifact: kulso atadasra kesz fajl/blob (DXF, SVG, ZIP, machine program).

Nem ekvivalens objektumok:
- Run Request != Run Snapshot
- Run Snapshot != Run Result
- Run Result != Projection
- Projection != Export Artifact
- Export Artifact != domain truth

## 3. Snapshot build trigger es forrasok

### 3.1 Trigger pont

Snapshot letrehozasa akkor tortenik, amikor a rendszer a Run Requestet futtathato allapotba
emeli (`requested -> snapshot_building`).

### 3.2 Snapshot build source matrix

| Elo domain forras | Snapshotba kerulo adat | Tarolasi mod |
| --- | --- | --- |
| Project + active settings | Run-level policy flags, idempotency key input | Immutable copy |
| PartDemand + PartRevision | Mennyiseg, prioritas, canonical geometry ref | Immutable copy + stable ref |
| SheetInventoryUnit + SheetRevision | Felhasznalhato sheet input lista | Immutable copy + stable ref |
| TechnologySetup version | Kerf/spacing/margin/rotation policy | Immutable copy |
| Manufacturing selection (ha relevans) | Manufacturing profile version ref | Immutable copy |
| Geometry derivatives | Canonical geometry pointer + hash | Reference/manifest |
| Solver config | Time limit, placer mode, seed policy | Immutable copy |

### 3.3 Mi masolodik, mi referencia

Immutable snapshot content:
- input mennyisegek es prioritasok
- policy parameterek
- worker futast befolyasolo opciok

Reference/manifest jellegu adat:
- nagy blobok (pl. geometria blob, export forras)
- artifact storage URI-k
- content hash + media kind metadata

Szabaly:
- a snapshotnak onmagaban verifikalhatonak kell lennie (hash + referencia integritas),
  de nem kotelezo minden nagy blob fizikailag beembedelve legyen.

## 4. Worker boundary contract

### 4.1 Worker input

A worker kizarolag ezt kapja bemenetnek:
- `run_snapshot_id`
- snapshot payload (immutable)
- attempt metadata (attempt_no, lease_owner, deadline)

### 4.2 Kotelezo worker output

Minden attempt utan kotelezoen eloallitando:
- attempt statusz (`succeeded` / `failed` / `timed_out` / `cancelled`)
- canonical run result payload vagy hibatortenet
- artifact manifest (ha keletkezett artifact)
- telemetry (duration, exit reason, retry eligibility hint)

### 4.3 Tilos direkt olvasas/iras

Tilos direkt olvasni:
- elo project/domain tablakat a snapshoton kivul
- aktualis inventory allapotot futas kozben ujraszamolashoz

Tilos direkt irni:
- snapshot tartalom felulirasa
- domain definiciok (part/sheet revision) modositas
- projection truth kozvetlen mutalasa canonical result nelkul

## 5. Run allapotgep (magas szint)

Javasolt allapotok:
1. `draft`
2. `requested`
3. `snapshot_building`
4. `snapshot_ready`
5. `queued`
6. `leased`
7. `running`
8. `succeeded`
9. `failed`
10. `timed_out`
11. `cancelled`

Atmeneti elvek:
- `requested -> snapshot_building -> snapshot_ready` sikeres snapshot epites eseten.
- `snapshot_ready -> queued -> leased -> running` scheduler/worker lease alapjan.
- `running -> succeeded|failed|timed_out|cancelled` terminal allapot.
- Terminal allapotbol ujrainditas csak uj attempttel, ugyanarra a snapshotra vagy uj snapshotra,
  policytol fuggoen.

## 6. Retry, timeout, lease, cancel, idempotencia szemantika

### 6.1 Retry

- Retry egy uj `run_attempt` ugyanahhoz a `run_snapshot_id`-hoz.
- Uj snapshot csak akkor keszulhet, ha explicit uj request vagy inputvaltozas tortenik.
- Retry policy max attempt szamot es backoffot tartalmaz.

### 6.2 Timeout

- Timeout a worker attemptre vonatkozik, nem a snapshotra.
- Timeout eseten attempt `timed_out`, run aggregate `failed` vagy `queued_for_retry` policy alapjan.

### 6.3 Lease es heartbeat

- Lease ownership egyszerre egy workerhez kotott.
- Heartbeat hianyaban lease lejarnak minosul, es a rendszer ujraqueue-zhat.
- Lejart lease outputja csak idempotencia ellenorzes utan fogadhato el.

### 6.4 Cancel

- Cancel signal `cancel_requested` allapotot allit be.
- Running attempt cooperativan all le; terminal allapot `cancelled`.
- Cancel utan keson beerkezo artifact nem lehet automatikusan truth.

### 6.5 Idempotencia es deduplikacio

Idempotencia kulcs javaslat:
- `project_id + run_purpose + snapshot_hash + engine_profile_hash`

Szabaly:
- azonos idempotencia kulcsu, azonos terminal eredmenyu futas deduplikalhato.
- dedup soha nem keverheti ossze a kulonbozo snapshot hashu futasokat.

## 7. Result vs projection vs export matrix

| Objektum | Mi ez | Source of truth statusz | Ujraepitheto |
| --- | --- | --- | --- |
| RunResult | Canonical futasi eredmeny | Igen (result vilag) | Nem, ez a referencia alap |
| PlacementProjection | UI/API query nezet | Nem (derived) | Igen, RunResult-bol |
| RunMetricsProjection | Riport-nezet | Nem (derived) | Igen, RunResult-bol |
| ViewerSvgArtifact | Render artifact | Nem | Igen, projection/result alapjan |
| SheetDxfArtifact | Export artifact | Nem | Igen, result/manufacturing alapjan |
| MachineProgramArtifact | Gepfuggo export | Nem | Igen, manufacturing package alapjan |

## 8. Snapshot immutabilitas szabaly

- A `run_snapshot` append-only, futas kozben nem modosithato.
- A worker mindig ugyanazt a snapshot payloadot latja egy adott snapshot azonositohoz.
- Barmely inputvaltozas uj snapshotot igenyel.

Kovetkezmeny:
- a worker nem elo domain allapotbol dolgozik,
- a futas reprodukalhato hash es snapshot_id alapjan.

## 9. H0-E5 schema kovetkezmenyek

A H0-E5-T1 ota a run-vilag fogalmi/fizikai megfeleltetese:
- Fogalmi Run Request aggregate fizikai taroloja: `app.nesting_runs`.
- Fogalmi Run Snapshot immutable truth fizikai taroloja: `app.nesting_run_snapshots`.

Aktualis source-of-truth migraciok:
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`

Kotelezo bazis-integritas (T1):
- A request status az `app.run_request_status` enumot hasznalja.
- A snapshot status az `app.run_snapshot_status` enumot hasznalja.
- A request es snapshot kulon tablakban van, 1:1 kapcsolattal.
- A snapshot append-only szemantikaju (nincs `updated_at` mezot igenylo mutacios modell).
- A snapshot hash + strukturalt manifest blokkok explicit oszlopokban vannak.

Kotelezo bazis-integritas (T2):
- A queue/lease/allapot reteg fizikai taroloja: `app.run_queue`.
- A log/audit event reteg fizikai taroloja: `app.run_logs`.
- A T2-ben az attempt szemantika a queue sorban jelenik meg (`attempt_no`, `attempt_status`), kulon `run_attempts` tabla nelkul.
- A `attempt_status` az `app.run_attempt_status` enumot hasznalja.

Kovetkezo, kulon H0-E5 taskban letrehozando:
- `run_results`, `run_artifacts`, `run_layout_*`, `run_metrics` tablavilag (T3).

## 10. Anti-pattern lista

- Worker elo domain tablakbol olvas snapshot helyett.
- Worker snapshotot modosit helyben.
- Run result, projection es export artifact osszemosasa.
- Retry uj snapshot nelkul olyan esetben, amikor input valtozott.
- Cancel utan keson beerkezo side effect truth-kent kezelese.

## 11. Dontesi szabaly konfliktus eseten

Futasi allapot, attempt szemantika, idempotencia, retry/timeout/lease/cancel kerdesben
 ez a dokumentum az elsosegi forras.
Modulhatar tiltasi kerdesben a `h0_modulhatarok_es_boundary_szerzodes.md` ervenyes.
