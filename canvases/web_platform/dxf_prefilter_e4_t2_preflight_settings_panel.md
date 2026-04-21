# DXF Prefilter E4-T2 — Preflight settings panel

## Cel
Az E4-T1 ota mar letezik kulon `DXF Intake / Project Preparation` oldal,
file-szintu latest preflight statuszlistaval es canonical `source_dxf` upload
nyelvezettel. A preflight lane backend oldalon mar vegigfut upload utan, de az
intake oldalon ma meg mindig csak egy read-only placeholder van:
- nincs tenyleges settings panel;
- az upload flow nem tud semmilyen rules-profile snapshotot atadni a backendnek;
- a runtime tovabbra is hardcoded `rules_profile=None` modban fut.

Az E4-T2 celja egy **minimal, repo-grounded preflight settings panel**
bevezetese az intake oldalra ugy, hogy a user altal megadott beallitasok egy
upload session soran bekeruljenek a preflight runtime-ba es a persisted
`rules_profile_snapshot_jsonb` truth-ba.

Ez a task most **nem** teljes rules-profile domain, nem named profile editor,
nem project-szintu settings persistence, es nem diagnostics/review UI. A helyes
V1 bridge most: **frontend draft settings -> optional complete_upload payload ->
preflight runtime -> persisted snapshot**.

## Miert most?
A jelenlegi, kodbol igazolt helyzet:
- `frontend/src/pages/DxfIntakePage.tsx` ma csak read-only `Current defaults`
  blokkot mutat, explicit azzal a szoveggel, hogy a settings editor E4-T2-ben
  jon;
- `api/routes/files.py` `FileCompleteRequest` modellje nem fogad preflight
  settings vagy rules-profile snapshot mezot;
- `api/services/dxf_preflight_runtime.py` a pipeline-t fixen
  `rules_profile=None`-nal futtatja;
- ezzel szemben az E2 service-ek mar ma is tudnak minimal rules-profile slice-ot
  fogyasztani:
  - role resolver: `strict_mode`, `interactive_review_on_ambiguity`,
    `cut_color_map`, `marking_color_map`;
  - gap repair: `auto_repair_enabled`, `max_gap_close_mm`, `strict_mode`,
    `interactive_review_on_ambiguity`;
  - duplicate dedupe: `auto_repair_enabled`,
    `duplicate_contour_merge_tolerance_mm`, `strict_mode`,
    `interactive_review_on_ambiguity`;
  - normalized writer: `canonical_layer_colors` (de ez UI-szinten most meg nem
    kotelezo szerkesztoi scope);
- `api/services/dxf_preflight_persistence.py` mar ma is tud
  `rules_profile_snapshot_jsonb` truth-ot tarolni.

Ez azt jelenti, hogy a legkisebb ertelmes E4-T2 feladat nem backend rules-profile
CRUD, hanem a mar meglevo E2/E3 plumbing **bekotese a frontend intake oldalrol**.

## Scope boundary

### In-scope
- A `DxfIntakePage` read-only defaults blokkjanak lecserelese valodi,
  szerkesztheto preflight settings panelre.
- Minimal frontend draft settings modell es defaults bevezetese.
- Az upload finalize (`completeUpload`) API payload optional bovitese ugy, hogy
  rules-profile snapshotot tudjon atadni.
- A backend `FileCompleteRequest` / `complete_upload` bridge bovitese ugy, hogy
  a snapshot bekeruljon a preflight background task hivashoz.
- A `run_preflight_for_upload(...)` runtime signatura es pipeline hivasai
  bovuljenek optional `rules_profile` argumentummal.
- A runtime a kapott snapshotot tenylegesen adja tovabb az E2 service-eknek es a
  persistence-nek.
- Determinisztikus backend unit teszt es smoke bizonyitek a settings-panel ->
  upload payload -> runtime plumbing szerzodesre.
- Opcionális frontend build evidence.

### Out-of-scope
- Named rules profile CRUD, owner/version domain vagy kulon rules-profile API.
- Project-szintu vagy user-szintu tartos settings-mentes a backendben.
- E4-T3 runs table, E4-T4 diagnostics drawer, E4-T5 review modal, E4-T6
  accepted->parts flow.
- Full `canonical_layer_colors` ACI editor.
- `IGNORE` / `BEND_LINE` / `TEXT_GUIDE` vagy egyeb kesobbi role-ok UI kezelese.
- Replace/rerun, feature flag vagy rollout gate.
- NewRunPage tovabbi foltozasa.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `frontend/src/pages/DxfIntakePage.tsx`
  - current-code truth: upload panel + latest status tabla + read-only defaults
    blokk; nincs settings editor.
- `frontend/src/lib/api.ts`
  - current-code truth: `completeUpload(...)` nem tud rules-profile snapshotot
    kuldeni.
- `frontend/src/lib/types.ts`
  - current-code truth: nincs dedikalt preflight settings draft/snapshot tipus.
- `api/routes/files.py`
  - current-code truth: `FileCompleteRequest` nem fogad rules-profile snapshotot;
    a route a preflight runtime-ot snapshot nelkul inditja.
- `api/services/dxf_preflight_runtime.py`
  - current-code truth: a pipeline `rules_profile=None`-nal fut, de a persistence
    mar tudna snapshotot tarolni.
- `api/services/dxf_preflight_persistence.py`
  - current-code truth: `persist_preflight_run(...)` opcionális
    `rules_profile`-t fogad es `rules_profile_snapshot_jsonb`-ba menti.
- `api/services/dxf_preflight_role_resolver.py`
- `api/services/dxf_preflight_gap_repair.py`
- `api/services/dxf_preflight_duplicate_dedupe.py`
- `api/services/dxf_preflight_normalized_dxf_writer.py`
  - current-code truth: a pipeline reszegysegei mar ma is elfogadnak minimal
    rules-profile mezoket.
- `canvases/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md`
- `codex/reports/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md`

## Jelenlegi repo-grounded helyzetkep

### 1. A settings panel helye megvan, de csak placeholder szinten
A `DxfIntakePage.tsx` ma mar kulon intake oldal, de a settings resz egy egyszeru
read-only info blokk. Ez pontosan azt bizonyitja, hogy az E4-T2 a logikus kovetkezo
lepés, nem egy uj UI entrypoint tervezese.

### 2. A backend pipeline mar kepes lenne fogyasztani a snapshotot
Az E2 service-ek a sajat minimal rules-profile mezokeszletuket mar ma is
normalizaljak/validaljak. Emiatt az E4-T2-ben **nem** kell uj backend policy
motor; csak a jelenlegi upload/runtime hidat kell megnyitni.

### 3. Nincs rules-profile domain, ezert a panel nem lehet “saved profiles” UI
Mivel current-code truth szerint nincs implementalt owner/version rules-profile
API domain, az E4-T2-ben a helyes UX:
- in-page draft settings,
- deterministic defaults,
- optional reset,
- upload-session szintu alkalmazas.

Anti-pattern lenne most project-level persisted profile listat vagy selector API-t
kitalalni.

### 4. A persisted snapshot mar most is resze a backend domainnek
Az E3-T1 ota a preflight run row mar tarol `rules_profile_snapshot_jsonb` truth-ot.
Ez azt jelenti, hogy az E4-T2 nem ideiglenes hack, hanem a mar letezo persistence
alak konkret kihasznalasa.

### 5. A teljes writer color editor most tul nagy scope lenne
A T5 writer ugyan tud `canonical_layer_colors`-t fogyasztani, de egy teljes ACI
szineditor most aranytalanul nagy UI feladat lenne. Ezert az E4-T2 helyes minimal
scope-ja: a user-facing preflight policy mezók, amelyek mar kozvetlenul befolyasoljak
az E2-T2/T3/T4 viselkedest.

## Konkret elvarasok

### 1. Legyen tenyleges settings panel a `DxfIntakePage` oldalon
A jelenlegi read-only blokk helyen jelenjen meg egy szerkesztheto panel.

Minimum user-facing controls:
- `strict_mode` (checkbox vagy toggle)
- `auto_repair_enabled` (checkbox)
- `interactive_review_on_ambiguity` (checkbox)
- `max_gap_close_mm` (numeric input, mm)
- `duplicate_contour_merge_tolerance_mm` (numeric input, mm)
- `cut_color_map` (egyszeru comma-separated ACI lista)
- `marking_color_map` (egyszeru comma-separated ACI lista)

UX boundary:
- legyen egyertelmu helper szoveg, hogy a beallitasok **az innen inditott uj uploadokra**
  vonatkoznak;
- legyen `Reset to defaults` muvelet;
- ne legyen mentett profile lista, ne legyen profile nev/saved preset editor.

### 2. A frontend tartson fenn minimal draft settings shape-et
A frontendben legyen dedikalt, explicit tipus vagy helper a panel draft allapotara.
Nem jo irany a nyers `Record<string, unknown>` allapot a komponensben.

Javasolt minimum alak:
- `strict_mode: boolean`
- `auto_repair_enabled: boolean`
- `interactive_review_on_ambiguity: boolean`
- `max_gap_close_mm: number`
- `duplicate_contour_merge_tolerance_mm: number`
- `cut_color_map_text: string`
- `marking_color_map_text: string`

A page kulon, determinisztikusan alakitson ebbol backendre kuldheto snapshotot.

### 3. A `completeUpload(...)` API tudjon optional snapshotot kuldeni
A `frontend/src/lib/api.ts` `completeUpload(...)` payloadja bovuljon optional
mezovel, pl.:
- `rules_profile_snapshot_jsonb?: Record<string, unknown> | null`

A frontend ne kuldje kotelezoen; csak intake page uploadnal keruljon be.

### 4. A backend `complete_upload` route fogadja es adja tovabb a snapshotot
A `FileCompleteRequest` minimal, optional mapping mezot fogadjon.
A route ezt **ne** probalja frontend-szinten ujravalidalni policy motorral; csak
annyit ellenorizzen, hogy JSON-serializable mapping jellegu objektum legyen.

A snapshot menjen tovabb a preflight runtime background tasknak.

### 5. A runtime szuntesse meg a `rules_profile=None` hardcode-ot
A `run_preflight_for_upload(...)` es a belso pipeline kapjon optional
`rules_profile` argumentumot.

A runtime ezt adja tovabb:
- `resolve_dxf_roles(...)`
- `repair_dxf_gaps(...)`
- `dedupe_dxf_duplicate_contours(...)`
- `write_normalized_dxf(...)`
- `persist_preflight_run(...)`

Az acceptance gate es diagnostics renderer mar a pipeline outputjaibol dolgozik,
ezekhez kulon `rules_profile` parameter nem kell.

### 6. A panelhez deterministic defaultok tartozzanak
A page defaultjai igazodjanak a backend jelenlegi service-defaultjaihoz:
- `strict_mode = false`
- `auto_repair_enabled = false`
- `interactive_review_on_ambiguity = true`
- `max_gap_close_mm = 1.0`
- `duplicate_contour_merge_tolerance_mm = 0.05`
- `cut_color_map = []`
- `marking_color_map = []`

A T5 `canonical_layer_colors` maradjon backend default, read-only scope-on kivul.

### 7. A task bizonyitasa
Minimum deterministic coverage:

#### Backend unit teszt a route bridge-re
- ha nincs snapshot, a route tovabbra is mukodik;
- ha van snapshot, a `run_preflight_for_upload(...)` background task a snapshotot
  is megkapja;
- a legacy validation task bent marad;
- a response shape nem torik el.

#### Runtime unit teszt
- a runtime a kapott `rules_profile` mappinget tenylegesen tovabbadja a role/gap/
  dedupe/writer/persistence hivasoknak;
- ha `rules_profile=None`, a korabbi viselkedes valtozatlan.

#### Smoke
- az intake page source code-jaban tenylegesen megjelennek a settings panel mezók,
  a reset action, es az upload helper snapshotot epit;
- az API helper tud optional `rules_profile_snapshot_jsonb`-t;
- a route es runtime mar nem hardcoded `rules_profile=None` workflow-ban el.

#### Opcionális frontend ellenorzes
- `npm --prefix frontend run build`

## DoD
- [ ] A `DxfIntakePage` read-only defaults blokkja valodi preflight settings panelre valtozott.
- [ ] A panel minimal draft settings alakot tart fenn, deterministic backend-aligned defaults-szal.
- [ ] A panel altal hasznalt upload flow optional rules-profile snapshotot tud kuldeni a backendnek.
- [ ] A `complete_upload` route optional snapshotot fogad es tovabbad a preflight runtime-nak.
- [ ] A runtime megszunteti a `rules_profile=None` hardcode-ot, es a snapshotot tenylegesen atvezeti az E2/T7 + persistence lancba.
- [ ] A task nem vezet be named rules profile CRUD-ot vagy project-level settings persistence-t.
- [ ] A task-specifikus backend unit teszt(ek) es smoke bizonyitjak a settings panel -> upload payload -> runtime plumbing szerzodest.
- [ ] A standard repo gate wrapperrel fut es a report evidence alapon frissul.

## Javasolt verify / evidence
- `python3 -m py_compile api/routes/files.py api/services/dxf_preflight_runtime.py tests/test_dxf_preflight_runtime.py tests/test_project_file_complete_preflight_settings.py scripts/smoke_dxf_prefilter_e4_t2_preflight_settings_panel.py`
- `python3 -m pytest -q tests/test_dxf_preflight_runtime.py tests/test_project_file_complete_preflight_settings.py`
- `python3 scripts/smoke_dxf_prefilter_e4_t2_preflight_settings_panel.py`
- `npm --prefix frontend run build`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md`

## Erintett fajlok (tervezett)
- `frontend/src/pages/DxfIntakePage.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- `api/routes/files.py`
- `api/services/dxf_preflight_runtime.py`
- `tests/test_dxf_preflight_runtime.py`
- `tests/test_project_file_complete_preflight_settings.py`
- `scripts/smoke_dxf_prefilter_e4_t2_preflight_settings_panel.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md`
- `codex/reports/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md`
