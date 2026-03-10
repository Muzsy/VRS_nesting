PASS

## 1) Meta
- Task slug: `h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa`
- Kapcsolodo canvas: `canvases/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.yaml`
- Futas datuma: `2026-03-10`
- Branch / commit: `main @ 47d624b (dirty working tree)`
- Fokusz terulet: `Docs`

## 2) Scope

### 2.1 Cel
- Snapshot-first futasi modell formalizalasa.
- Run request/snapshot/attempt/state/result/projection/export vilagok explicit szeparacioja.
- Worker input/output boundary es tiltott olvasas/iras szabalyok rogzitese.
- Retry/timeout/lease/cancel/idempotencia szemantika dokumentalasa.

### 2.2 Nem-cel
- Queue/API/worker implementacio modositas.
- SQL migracio vagy OpenAPI schema kodszintu valtoztatas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/README.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `codex/codex_checklist/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md`
- `codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md`

### 3.2 Miert valtoztak?
- A H0-E1-T1 es H0-E1-T2 utan a futasi/adatkontraktus layer konkret source-of-truth dokumentuma hianyzott.
- A H0-E2 schema taskhoz explicit run-lifecycle es snapshot-contract alapokra volt szukseg.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md` -> PASS

### 4.2 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejon a `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md` dokumentum. | PASS | `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:1` | Letrejott a dedikalt snapshot-first source-of-truth dokumentum. | `./scripts/verify.sh --report ...` |
| Elvalasztja a run request, run snapshot, run state, run result, projection es export artifact vilagokat. | PASS | `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:21`; `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:29`; `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:155` | A fogalmi kulonvalasztas es matrix explicit rogzitve van. | `./scripts/verify.sh --report ...` |
| Dokumentalva van a worker boundary: input, output, tilos olvasas/iras. | PASS | `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:71`; `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:75`; `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:82`; `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:90` | Kulon worker contract blokk rogzit minden kotelezo elemet. | `./scripts/verify.sh --report ...` |
| Dokumentalva van a magas szintu run lifecycle es allapotgep. | PASS | `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:99` | Kulon allapotgep lista es atmeneti szabalyok szerepelnek. | `./scripts/verify.sh --report ...` |
| Dokumentalva van timeout, retry, lease, cancel es idempotencia szemantika. | PASS | `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:121` | Kulon alfejezetekben formalizalt operational szemantika. | `./scripts/verify.sh --report ...` |
| Dokumentalva van, hogy a snapshot immutable truth, es a worker nem elo domain allapotbol dolgozik. | PASS | `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:166`; `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:173` | Snapshot immutabilitas es worker olvasasi tiltasi szabaly explicit. | `./scripts/verify.sh --report ...` |
| README + architecture + domain entitasterkep + H0 roadmap hivatkozik az uj dokumentumra. | PASS | `docs/web_platform/README.md:29`; `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md:21`; `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md:16`; `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md:46` | A 4 cel-doksi explicit source-of-truth hivatkozast kapott. | `./scripts/verify.sh --report ...` |
| A dokumentum H0-E2 schema taskhoz hasznalhato bemenetkent. | PASS | `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md:176` | Kulon schema kovetkezmeny szekcio rogzit kotelezo modellezesi pontokat. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md` PASS. | PASS | `codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.verify.log:1`; `codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md:69` | A gate lefutott, a report AUTO_VERIFY blokk PASS eredmenyt rogzit. | `./scripts/verify.sh --report ...` |

## 6) Doksi szinkron
- A web_platform dokumentacioban most kulon source-of-truth dokumentum kezeli a snapshot-first futasi es adatkontraktus reteget.

## 7) Advisory notes
- A dokumentum szandekosan semleges az implementacios mechanizmusokra (queue backend, API endpoint forma), es a schema-level kovetelmenyekre fokuszal.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-10T22:06:39+01:00 → 2026-03-10T22:10:13+01:00 (214s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.verify.log`
- git: `main@47d624b`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 docs/web_platform/README.md                                            | 3 +++
 .../dxf_nesting_platform_architektura_es_supabase_schema.md            | 2 ++
 .../architecture/h0_domain_entitasterkep_es_ownership_matrix.md        | 3 +++
 docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md         | 2 ++
 4 files changed, 10 insertions(+)
```

**git status --porcelain (preview)**

```text
 M docs/web_platform/README.md
 M docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
 M docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
 M docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
?? canvases/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md
?? codex/codex_checklist/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md
?? codex/goals/canvases/web_platform/fill_canvas_h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.yaml
?? codex/prompts/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa/
?? codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.md
?? codex/reports/web_platform/h0_e1_t3_snapshot_first_futasi_es_adatkontraktus_formalizalasa.verify.log
?? docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
```

<!-- AUTO_VERIFY_END -->
