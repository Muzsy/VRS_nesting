# H1-E3-T4 — Project sheet input management (H1 minimum)

## Kontextus
A H0 mar letette a `app.project_sheet_inputs` schema- es RLS-alapjait.
A H1-E3-T2 ota owner-szintu `sheet_definition` + `sheet_revision` truth mar
letezik backend service-en es endpointon keresztul.

A kovetkezo H1-minimum lepes az, hogy a projekt tulajdonosa a sajat
sheet revision rekordjai kozul tudjon projektbe valaszthato sheet inputot
rogziteni es frissiteni. Ez a task a `project_sheet_inputs` workflowot nyitja
meg, de tovabbra sem csuszhat at run snapshot, inventory/remnant vagy solver-
input generalas iranyba.

## Feladat
Olvasd el es kovessed pontosan a kovetkezo canvas-t:
- `canvases/web_platform/h1_e3_t4_project_sheet_input_management_h1_minimum.md`

A feladatot a repo jelenlegi H0/H1 truth-jara epitsd:
- `app.projects`
- `app.sheet_definitions`
- `app.sheet_revisions`
- `app.project_sheet_inputs`
- H0 RLS policyk
- a frissen elkeszult `sheet_creation` service/route mintai

## Fontos korlatok
- Ne vezess be inventory/remnant logikat.
- Ne epits run snapshotot, solver payloadot vagy engine adapter inputot.
- Ne hozz be UI-t vagy frontend allapotkezelest.
- Ne hasznalj legacy `phase1_*` vagy ad hoc tablakepet.
- Ne duplikalj rekordot ugyanarra a `(project_id, sheet_revision_id)` parra.
- Az `is_default` kezeles legyen projekt-szinten kontrollalt.

## Elvart megvalositas
- Keszits explicit `api/services/project_sheet_inputs.py` service-t.
- Keszits minimalis `api/routes/project_sheet_inputs.py` endpoint(ek)et, es kotd
  be az `api/main.py`-ba.
- A workflow create-or-update legyen ugyanarra a `(project_id, sheet_revision_id)`
  parra.
- A service ellenorizze a projekt-owner es sheet-owner hozzaferest.
- A response egyertelmuen jelezze, hogy uj rekord jott letre vagy meglevo lett
  frissitve.
- Keszits listazo endpointot is a projekt sheet inputokhoz.
- A smoke script bizonyitsa az uj rekord, update, default-switch, idegen projekt,
  idegen sheet revision es ervenytelen qty/priority agak mukodeset.

A reportban kulon nevezd meg:
- hogy a task mit szallit le a H1 minimum project sheet input workflowhoz;
- hogy mit NEM szallit le meg (kulonosen run snapshot, inventory/remnant,
  solver-input generalas es manufacturing iranyokban);
- ha barmilyen plusz migracio vagy runtime-fuggoseg kell, azt explicit
  dokumentald.

A vegén futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t4_project_sheet_input_management_h1_minimum.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
