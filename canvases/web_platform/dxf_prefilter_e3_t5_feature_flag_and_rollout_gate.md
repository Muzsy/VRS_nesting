# DXF Prefilter E3-T5 — Feature flag es rollout gate

## Cel
Az E3-T2 ota a source DXF finalize automatikusan elinditja a preflight runtime-ot,
az E3-T3 ota a geometry import csak gate-pass utan indul, az E3-T4 ota pedig replacement
flow is van. A jelenlegi repoban viszont **nincs hivatalos rollout gate**: a prefilteres
utvonal mindig aktiv, nincs env-szintu visszakapcsolasi lehetoseg, es nincs minimalis
frontend-visible kapuzas sem.

A DXF-E3-T5 celja egy minimalis, current-code grounded **feature flag + rollout gate**
bevezetese ugy, hogy:
- a DXF prefilter/pipeline env-szinten ki-be kapcsolhato legyen;
- kikapcsolt allapotban a rendszer vissza tudjon allni a legacy upload -> direct geometry import
  lancra;
- a replacement flow csak akkor legyen elerheto, ha a prefilter lane aktiv;
- a DXF Intake entrypoint csak akkor jelenjen meg, ha a feature tenyleg rolloutolt;
- ne kelljen uj project-settings domain vagy runtime config endpoint.

## Miert most?
A jelenlegi repo-grounded helyzet:
- az E2 T1..T7 es az E3 T1..T4 backend lanc mar bent van;
- az E4 T1..T4 UI is mar kesz az intake/preflight status + diagnostics megjelenitesere;
- a jelenlegi rendszerben viszont nincs biztonsagos visszaallasi pont, ha a prefilter rolloutot
  fokozatosan akarjuk bevezetni vagy ideiglenesen visszavonni.

Az E3-T5 a legkisebb helyes kovetkezo lepest vezeti be: **env-level canonical flag,
legacy fallback, backend route gate, minimalis frontend visibility gate**.

## Scope boundary

### In-scope
- Canonical backend feature flag a Settings/config retegben.
- A `complete_upload` source DXF finalize flow kapuzasa:
  - flag ON -> jelenlegi validate + preflight runtime utvonal;
  - flag OFF -> validate + legacy direct geometry import utvonal.
- A replacement route kapuzasa (feature OFF eseten ne legyen hasznalhato replacement flow).
- Minimalis frontend visibility gate:
  - DXF Intake route/CTA csak rolloutolt allapotban legyen lathato.
- Task-specifikus deterministic unit teszt es smoke.

### Out-of-scope
- Project-level persisted feature flag domain.
- Runtime API config endpoint a frontendnek.
- UI redesign vagy uj intake komponens.
- Review/download/artifact route scope.
- E4-T5/T6/T7 UX.
- New migration vagy DB schema valtozas.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `api/config.py`
  - jelenleg nincs DXF prefilter feature flag a Settings-ben.
- `api/routes/files.py`
  - current-code truth: `complete_upload` mindig validate + preflight runtime-ot indit;
  - current-code truth: `replace_file` route mindig aktiv.
- `api/services/dxf_preflight_runtime.py`
  - current-code truth: a teljes T1->T7 + E3-T1 pipeline entrypointja.
- `api/services/dxf_geometry_import.py`
  - current-code truth: tartalmaz legacy async helper utat (`import_source_dxf_geometry_revision_async`),
    ami rollback/fallback alapkent felhasznalhato.
- `frontend/src/App.tsx`
  - current-code truth: a DXF Intake route mindig bent van.
- `frontend/src/pages/ProjectDetailPage.tsx`
  - current-code truth: a DXF Intake CTA mindig latszik.
- `frontend/src/pages/DxfIntakePage.tsx`
  - current-code truth: az oldal feltetelezi, hogy a backend prefilter lane aktiv.

## Jelenlegi repo-grounded helyzetkep

### 1. A backendben nincs rollout gate
Ma a `complete_upload` source DXF branch mindig ezt csinalja:
1. `validate_dxf_file_async(...)`
2. `run_preflight_for_upload(...)`

Nincs olyan settings truth, amely ezt visszakapcsolna legacy geometria-import utra.

### 2. A legacy fallback kod mar letezik
A repoban mar bent van az `import_source_dxf_geometry_revision_async(...)` helper,
amely a prefilter elotti, kozvetlen geometry import utvonal current-code megfeleloje.
Ez azt jelenti, hogy E3-T5-ben **nem** kell uj fallback architekturat kitalalni.

### 3. A frontend jelenleg mindig prefilteres vilagot mutat
Az `App.tsx` route-ja es a `ProjectDetailPage` CTA-ja ma mindig latszik.
Ha a backend prefilter lane ki lenne kapcsolva, a jelenlegi UI felulet felig igaz,
felig nem mukodo allapotot mutatna.

### 4. Nincs project-level settings domain
A jelenlegi kodban nincs olyan project settings truth, amelyhez feature rollout kotheto.
Ezert a helyes V1 current-code megoldas **env-level canonical gate**, nem project-level flag.

## Konkret elvarasok

### 1. Legyen canonical backend flag a Settings retegben
A task vezessen be egy egyertelmu backend settings mezot, pl.:
- `dxf_preflight_required: bool`

Env-level current-code javaslat:
- canonical env: `API_DXF_PREFLIGHT_REQUIRED`
- optional docs-compat alias: `DXF_PREFLIGHT_REQUIRED`

A loader bool szemantikaja maradjon a mostani config stilushoz illeszkedo:
`0/false/no/off` -> false, minden mas -> true.

### 2. Kikapcsolt flag eseten legyen legacy fallback
A `complete_upload` source DXF finalize branch viselkedese legyen:
- **flag ON**:
  1. `validate_dxf_file_async(...)`
  2. `run_preflight_for_upload(...)`
- **flag OFF**:
  1. `validate_dxf_file_async(...)`
  2. `import_source_dxf_geometry_revision_async(...)`

Anti-pattern, amit kerulni kell:
- ne maradjon olyan kod, ahol flag OFF eseten semmi nem indul a source DXF-re;
- ne duplikalodjon a geometry import logika a route-ban;
- ne masoljuk le a preflight runtime-bol a geometry import implementaciot.

### 3. Replacement flow csak rolloutolt allapotban legyen aktiv
A `POST /projects/{project_id}/files/{file_id}/replace` route akkor legyen hasznalhato,
ha a canonical backend flag aktiv.

V1 current-code javaslat:
- feature OFF eseten a route dobjon explicit HTTP hibaat (pl. 404 vagy 409),
  es ne nyisson replacement upload slotot.

A route definicio maradhat a routerben; a gate runtime szintu.

### 4. Frontenden legyen minimalis visibility gate
Mivel nincs runtime config endpoint, a frontend current-code V1 megoldasa egy
**build-time Vite mirror flag** lehet, pl.:
- `VITE_DXF_PREFLIGHT_ENABLED`

Ez nem uj product domain, csak minimalis rollout visibility gate.

Minimum elvaras:
- `App.tsx` csak akkor regisztralja a DXF Intake route-ot, ha a frontend flag aktiv;
- `ProjectDetailPage.tsx` csak akkor mutassa a DXF Intake CTA-t, ha a frontend flag aktiv.

Nem kotelezo most:
- a `DxfIntakePage` belso fallback UX ujrairasa;
- kulon feature-disabled page.

### 5. A projection route-ok maradhatnak valtozatlanok
A `GET /projects/{project_id}/files` optional summary/diagnostics projection current-code truth szerint
maradhat valtozatlan. Ha a feature OFF, egyszeruen nem lesznek uj preflight runok.

### 6. A flag legyen rollout gate, ne per-project policy
Mivel nincs project settings domain, E3-T5-ben a helyes current-code boundary:
- env-level backend gate;
- build-time frontend visibility mirror.

Project-level rollout kesobbi scope.

## Tesztelhetoseg es bizonyitas

### Unit teszt minimum
- settings loader helyesen parse-olja a backend flaget;
- flag ON eseten `complete_upload` validate + preflight runtime taskot regisztral;
- flag OFF eseten `complete_upload` validate + direct geometry import taskot regisztral;
- flag OFF eseten `replace_file` nem hasznalhato;
- frontend helper / gate mezok deterministicen mukodnek (ha current-code szerint erdemes kulon helperbe kerulnek).

### Smoke minimum
- feature ON scenario: source DXF finalize a preflight runtime utvonalat valasztja;
- feature OFF scenario: source DXF finalize a legacy direct geometry import utvonalat valasztja;
- replacement route OFF scenario: replacement flow gate-elve van.

## Mi marad kesobbi scope-ban
- Project-level rollout / per-project flag.
- Runtime config endpoint a frontendnek.
- UI feature-disabled allapot reszletes UX-e.
- Fine-grained route-level artifact/review gate.
- E4-T5/T6/T7 tovabbi mutating UI flow-k.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate/run.md`
- `api/config.py`
- `api/routes/files.py`
- `frontend/src/App.tsx`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/lib/featureFlags.ts`
- `tests/test_dxf_preflight_feature_flag_gate.py`
- `scripts/smoke_dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md`
- `codex/reports/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md`

## DoD
- [ ] A Settings/config retegben megjelenik a canonical backend DXF prefilter rollout flag.
- [ ] Flag ON eseten a jelenlegi preflight runtime-os finalize utvonal marad ervenyben.
- [ ] Flag OFF eseten a source DXF finalize legacy direct geometry import fallbackra all vissza.
- [ ] A replacement route feature OFF eseten gate-elve van.
- [ ] A DXF Intake route/CTA minimalisan kapuzva van frontend oldalon.
- [ ] Nincs uj project settings domain vagy migration.
- [ ] Elkeszul a task-specifikus unit teszt es smoke.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md` PASS.
