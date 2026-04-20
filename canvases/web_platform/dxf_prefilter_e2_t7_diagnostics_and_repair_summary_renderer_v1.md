# DXF Prefilter E2-T7 — Diagnostics and repair summary renderer V1

## Cel
A DXF prefilter lane-ben a T1→T6 backend truth retegek mar kulon-kulon rendelkezésre allnak,
viszont jelenleg nincs olyan **egyseges, UI-barát backend diagnostics/repair summary reteg**,
amely egyetlen, stabil objektumba rendezi a preflight futas eredmenyet.

A T7 feladata egy kulon backend renderer/service bevezetese, amely a mar meglevo local truthokra ulve
osszerakja a **diagnostics and repair summary** objektumot, legalabb az alabbiak egységes visszaadasaval:
- talalt layer-ek,
- talalt szinek,
- role mapping eredmeny,
- talalt hibak / review / blocking jelek,
- alkalmazott javitasok,
- acceptance outcome,
- local letoltesre alkalmas artifact-referenciak.

A T7 nem uj parser, nem uj validator, nem route, nem persistence es nem frontend task.
Ez egy **backend oldali, local renderer boundary**, hogy a kovetkezo E3/E4 pipeline es UI retegeknek
ne 6 kulon service outputot kelljen osszehegeszteniuk.

## Miert most?
A jelenlegi repo-grounded helyzet:
- az E2-T1 inspect mar ad inventory/candidate truth-ot (`entity_inventory`, `layer_inventory`, `color_inventory`, `linetype_inventory`, diagnostics);
- az E2-T2 role resolver mar ad canonical role truth-ot (`layer_role_assignments`, `entity_role_assignments`, review/blocking);
- az E2-T3 gap repair mar ad repair truth-ot (`applied_gap_repairs`, `remaining_open_path_candidates`, review/blocking);
- az E2-T4 duplicate dedupe mar ad dedupe truth-ot (`applied_duplicate_dedupes`, `remaining_duplicate_candidates`, review/blocking);
- az E2-T5 writer mar ad normalized artifact truth-ot (`normalized_dxf`, `writer_layer_inventory`, `skipped_source_entities`, diagnostics);
- az E2-T6 acceptance gate mar ad canonical verdict truth-ot (`acceptance_outcome`, `importer_probe`, `validator_probe`, `blocking_reasons`, `review_required_reasons`).

A gap jelenleg az, hogy ezeket a truth retegeket **nincs egyetlen, kovetkezo retegeknek stabilan atadhato summary objektum**.
Ha ezt most nem vezetjuk be backend oldalon, akkor az E3 pipeline vagy az E4 UI fog ad hoc modon
6 kulon kimenetet osszefesulni, ami torekeny lesz es ujranyitja a korabbi taskok boundary-jat.

A T7 helyes iranya ezert:
- uj, kulon renderer service, amely kizárólag a mar letezo T1→T6 output shape-ekre ul;
- strukturalt, UI-barat summary objektumot ad;
- de **nem** csinal meg storage linket, API response contractot vagy frontend komponenst.

## Scope boundary

### In-scope
- Kulon backend renderer/service a T1→T6 truth retegekre epitve.
- A summary object determinisztikus osszeallitasa, legalabb a kovetkezo retegzett tartalommal:
  - source inventory summary,
  - role mapping summary,
  - issue summary,
  - repair summary,
  - acceptance summary,
  - artifact references.
- Structured severity/source/family alapu issue-normalizalas.
- Applied repair summary normalizalas kulon gap-repair / duplicate-dedupe / writer skip csaladokkal.
- A T5 normalized artifact local referenciainak summary-ba emelese.
- Task-specifikus unit teszt es smoke.

### Out-of-scope
- DB persistence, `preflight_runs` / `preflight_diagnostics` / `preflight_artifacts` record iras.
- API route, upload trigger, worker orchestration, feature flag vagy UI komponens.
- Signed URL vagy storage-backed artifact link generalas.
- Uj error catalog policy vagy T1→T6 logika ujranyitasa.
- Acceptance gate precedence vagy validator/importer logika modositasa.
- Full localization / i18n render layer.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `api/services/dxf_preflight_inspect.py`
  - current-code truth: source inventoryk + contour/open/duplicate candidates + diagnostics.
- `api/services/dxf_preflight_role_resolver.py`
  - current-code truth: canonical role assignments + review/blocking jelek.
- `api/services/dxf_preflight_gap_repair.py`
  - current-code truth: `applied_gap_repairs`, `remaining_open_path_candidates`, review/blocking.
- `api/services/dxf_preflight_duplicate_dedupe.py`
  - current-code truth: `applied_duplicate_dedupes`, `remaining_duplicate_candidates`, review/blocking.
- `api/services/dxf_preflight_normalized_dxf_writer.py`
  - current-code truth: `normalized_dxf`, `writer_layer_inventory`, `skipped_source_entities`, diagnostics.
- `api/services/dxf_preflight_acceptance_gate.py`
  - current-code truth: canonical outcome, importer probe, validator probe, blocking/review reasons.
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
  - E1-T7 freeze; grounding a reason family / user-facing message vilagra.
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
  - E1-T6 freeze; rogziti, hogy a route/API szerzodes kulon task, nem T7.
- `canvases/web_platform/dxf_prefilter_e2_t6_acceptance_gate_v1.md`
  - immediate predecessor; explicit mondja, hogy a diagnostics renderer a T7 scope.

## Jelenlegi repo-grounded helyzetkep
A T6 utan mar minden alapjel rendelkezesre all egy summary reteghez, es a renderernek
**nem kell uj helper boundaryt nyitnia** a jelenlegi kodban, ha a T1→T6 output shape-eket korrektul olvassa.

A T7 helyes boundary-ja ezert:
- bemenet: `inspect_result`
- bemenet: `role_resolution`
- bemenet: `gap_repair_result`
- bemenet: `duplicate_dedupe_result`
- bemenet: `normalized_dxf_writer_result`
- bemenet: `acceptance_gate_result`
- kimenet: egyetlen, deterministic, JSON-serialisable summary objektum.

Kulcsfontossagu current-code teny:
- a T6 mar kulon tartja a `blocking_reasons` es `review_required_reasons` csaladot;
- a T5 mar kulon tartja a `skipped_source_entities` es `writer_layer_inventory` vilagot;
- a T3/T4 mar kulon tartjak az `applied_*` es `remaining_*` repair truth-ot;
- az inspect mar kulon inventory-kat ad layer/color/linetype bontasban.

Kovetkezmeny:
- a T7 ne alkosson uj domain-truthot,
- hanem a meglevo truthokat **presentation-ready backend summary-va** rendezze.

## Konkret elvarasok

### 1. Kulon renderer service szülessen, ne a T6 bovuljon tovabb
A T7 ne novelje tovabb a `dxf_preflight_acceptance_gate.py` felelosseget.
A helyes boundary egy uj service, peldaul:
- `api/services/dxf_preflight_diagnostics_renderer.py`

Indok:
- a T6 mar gate-logika;
- a T7 mar presentation/summary reteg;
- a ket felelosseg kulon maradjon.

### 2. A renderer csak T1→T6 outputokra uljon, ne nyisson uj parser/validator/world state-et
A renderer ne olvasson DXF-et, ne fusson importer/validator probe-ot, ne szamoljon uj gap/duplicate truthot.
Kizarolag a meglevo service-output shape-eket fogyassza.

### 3. A kimenet legyen retegzett es UI-barat
A minimum output shape legalabb kulon retegekben adja vissza:
- `source_inventory_summary`
  - found layers
  - found colors
  - found linetypes
  - entity count / contour count / open-path count / duplicate-candidate count
- `role_mapping_summary`
  - canonical layer role assignments
  - resolved role inventory
  - role-level conflicts/review counts
- `issue_summary`
  - blocking issues
  - review-required issues
  - importer/validator highlights
  - soft probe errors / notes
- `repair_summary`
  - applied gap repairs
  - applied duplicate dedupes
  - remaining unresolved repair signals
  - skipped source entities
- `acceptance_summary`
  - acceptance outcome
  - precedence rule applied
  - importer pass/fail summary
  - validator pass/fail summary
- `artifact_references`
  - normalized DXF local artifact reference
  - source path echo where relevant

### 4. Az issue-normalizalas legyen explicit es determinisztikus
A renderernek a kulonbozo elozo taskok csaladjait egy kozos issue listava kell tudnia rendezni,
legalabb ezekkel a minimum mezokkel:
- `severity` (`blocking` / `review_required` / `warning` / `info`)
- `source` (pl. `inspect`, `role_resolver`, `gap_repair`, `duplicate_dedupe`, `normalized_writer`, `acceptance_gate.importer`, `acceptance_gate.validator`)
- `family`
- `code` vagy `display_code`
- `message`
- `details`

Kritikus boundary:
- ne vezessen be uj policy-t,
- csak a meglevo jeleket rendezze kozos formatumba.

### 5. Az applied repair summary kulonitse el a valos javitasokat a nem-javithato maradvanytol
A rendererben kulon retegben jelenjen meg:
- tenylegesen alkalmazott gap repair-ek,
- tenylegesen alkalmazott duplicate dedupe dontesek,
- writer altal kihagyott source entity-k,
- fennmarado open/duplicate/review signals.

A repair summary ne mosson ossze mindent egyetlen “hibak” listaba.

### 6. Az artifact link vilag T7-ben meg local reference maradjon
A taskleirasban szereplo “letoltheto artifact linkek” T7 backend szinten meg csak local reference formaban jelenjenek meg,
peldaul:
- `artifact_kind`
- `path`
- `exists`
- `download_label`

Kritikus boundary:
- nincs signed URL,
- nincs storage upload,
- nincs API endpoint.
Ez majd E3/E4 scope.

### 7. A renderer legyen eleg stabil ahhoz, hogy a kovetkezo retegek egyetlen truthkent hasznaljak
A T7 outputjanak alkalmasnak kell lennie arra, hogy:
- E3 pipeline persistence-be bekeruljon,
- E4 UI ezt jelenitse meg,
- de most meg local service maradjon.

### 8. A teszteles a summary shape-et es a fontos aggregaciokat bizonyitsa
Minimum deterministic coverage:
- accepted flow -> artifact reference + clean acceptance summary + ures blocking lista;
- review-required flow -> review issue-k es unresolved repair jel kulon megjelennek;
- rejected flow -> blocking issue-k es importer/validator fail highlight kulon megjelennek;
- source inventory summary helyesen visszaadja a talalt layer/szin inventoryt;
- repair summary helyesen mutatja az applied gap repair / duplicate dedupe / skipped entities vilagot;
- renderer nem futtat uj importer/validator probe-ot es nem igenyel `ezdxf`-et futasi oldalon, ha a bemenet mar elkeszult;
- kimenet nem tartalmaz DB/API/UI side effectet.

### 9. Kulon legyen kimondva, mi marad a kovetkezo taskokra
A reportban es canvasban is legyen explicit:
- E3: persistence / upload-trigger / gate bekotes
- E4: intake oldal / diagnostics drawer / review modal / accepted files flow

A T7 csak backend summary truth.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1/run.md`
- `api/services/dxf_preflight_diagnostics_renderer.py`
- `tests/test_dxf_preflight_diagnostics_renderer.py`
- `scripts/smoke_dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1.md`
- `codex/reports/web_platform/dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1.md`
- `codex/reports/web_platform/dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1.verify.log`

## DoD
- [ ] Letrejott kulon backend diagnostics renderer service, amely a T1→T6 truth retegekre ul.
- [ ] A service egyetlen, deterministic, JSON-serialisable summary objektumot ad vissza.
- [ ] A summary kulon retegekben tartalmazza a source inventory, role mapping, issue, repair, acceptance es artifact reference vilagot.
- [ ] Az issue-normalizalas explicit severity/source/family alapu.
- [ ] A repair summary kulon visszaadja az alkalmazott javitasokat es a megmaradt unresolved jeleket.
- [ ] Az artifact references local backend referenciak maradnak, nincs storage/API side effect.
- [ ] Keszult task-specifikus unit teszt csomag.
- [ ] Keszult task-specifikus smoke script.
- [ ] A task nem nyitotta meg a persistence / API route / UI scope-ot.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1.md` PASS.
