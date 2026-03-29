# Trial run tool new project technology setup fix

## Funkcio
A feladat a local-only trial run tool uj projekt modjanak celzott hibajavitasa.
A konkret hiba az, hogy a tool uj projekt letrehozasa utan nem seedeli a backend
altal kotelezoen elvart `approved` project technology setup rekordot, igy a
`POST /runs` hivas `400 missing approved project technology setup` hibaval all
meg.

A task celja, hogy a trial run tool uj projekt modban teljes, valoban
futtathato workflow-t adjon: projekt letrehozas, approved project technology
setup seedeles, DXF upload, geometry/part/sheet/input lanc, run create,
polling es artifact letoltes.

Ez tovabbra is belso teszt-tool task. Nem product feature, nem a vegleges UI
resze, es nem hoz letre uj frontend vagy uj publikus API boundary-t.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - a trial run core uj projekt workflow-jaba az approved project technology
    setup seedeles bevezetese;
  - a trial run CLI parameterkeszletenek bovitese a technology setuphoz
    szukseges mezokkel vagy dokumentalt default test technology setup logikaval;
  - a Tkinter GUI bovitese explicit Technology setup blokkal vagy legalabb
    egyertelmu default test setup kapcsoloval ugy, hogy a backendhez szukseges
    mezok kontrolaltan megadhatok legyenek;
  - a run directory evidence contract bovitese a technology setup letrehozas
    bizonyitekaival;
  - a smoke-ok erositesa ugy, hogy a `POST /runs` mar ne mehessen at fake
    transportban technology setup nelkul uj projekt modban;
  - hibauzenetek javitasa, hogy egyertelmu legyen: uj projekt modban miert es
    milyen technology setup jott letre vagy miert nem lehet tovabbmenni.
- Nincs benne:
  - uj product API route technology setup kezelesre;
  - manufacturing profile selection teljes beepitese;
  - vegleges product-grade settings persistence;
  - UI polish / packaging / desktop release;
  - rejtett DB vagy SQL mutatas a toolban;
  - a `run_snapshot_builder.py` kontraktus lazitasa.

### A hiba tenyleges oka
A backend run snapshot epitesnel kotelezoen keres egy `approved`
`app.project_technology_setups` rekordot a projekthez. Ha nincs ilyen,
`RunSnapshotBuilderError(status_code=400, detail="missing approved project technology setup")`
hibaval all meg.

A trial run tool mostani core workflow-ja uj projekt modban:
- projekt letrehozas,
- DXF upload,
- geometry poll,
- part creation,
- sheet creation,
- project part requirements,
- project sheet input,
- `POST /runs`.

Ebbol teljesen hianyzik a project technology setup seedeles.

### Jelenlegi relevans fajlok
- `scripts/trial_run_tool_core.py`
  - itt van a teljes uj projekt orchestrator;
  - itt kell a technology setup seedelest es a hozza tartozo evidence mentest
    bevezetni.
- `scripts/run_trial_run_tool.py`
  - CLI shell; itt kell a technology setup parameterk vagy default profile
    opcio CLI felulete.
- `scripts/trial_run_tool_gui.py`
  - Tkinter shell; itt jelenleg nincs olyan mezo, amibol approved technology
    setup helyesen letrehozhato.
- `scripts/smoke_trial_run_tool_cli_core.py`
  - jelenleg tul gyenge; fake `POST /runs` sikeres lehet technology setup nelkul.
- `scripts/smoke_trial_run_tool_tkinter_gui.py`
  - a GUI config/validacio smoke-ot ki kell boviteni a technology setup
    adatokkal es uj projekt prerequisite-ekkel.
- `api/services/run_snapshot_builder.py`
  - source-of-truth arra, hogy approved project technology setup kotelezo.
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
  - source-of-truth a `app.project_technology_setups` oszlopkeszletre.
- `api/supabase_client.py`
  - ha indokolt, a tool ujrahasznalhatja a meglevo Supabase REST kliens logikat,
    de ne vezess be uj product API route-ot csak a tool kedveert.

### Megvalositasi irany

#### 1. Uj projekt modban explicit technology setup seedeles kell
A core runner uj projekt modban a projekt letrehozas utan hozzon letre legalabb
egy approved, default project technology setup rekordot ugyanahhoz a projekthez.

Mivel jelenleg nincs dedikalt product API route erre, a local-only tool
hasznalhatja a meglvo Supabase REST boundary-t a felhasznalo bearer tokenjevel
es az explicit `SUPABASE_URL` / `SUPABASE_ANON_KEY` runtime beallitasokkal.
Ez mar most is megjelenik a GUI-ban optional mezokent, tehat a task ezt a
meglevo teszt-tool boundary-t formalizalja, nem ujitja fel product feature-re.

Jo minimum elvaras:
- ha `existing_project_id` van, a tool ne seedeljen uj technology setupot,
  csak opcionálisan ellenorizze vagy dokumentalja a feltetelezest;
- ha uj projekt mod van, es a Supabase REST elereshez szukseges adatok nincsenek
  meg, a tool ne menjen tovabb a `POST /runs`-ig, hanem koran, magyarazhatoan
  hibazzon;
- a technology setup seedeles sikeres valaszat mentse evidence fajlba.

#### 2. A technology setup mezok legyenek explicitek vagy dokumentalt defaulttal menjenek
A teszt-toolhoz nem kell bonyolult product settings oldal, de nem maradhat
rejtett, hardcode-olt, megmagyarazatlan technologiai seedeles.

Elfogadhato iranyok:
- explicit CLI args + GUI mezok a minimum technology setup mezoire, es ezekhez
  egyszeru, dokumentalt defaultok;
- vagy "Use default test technology setup" opcio, amely mogott ugyanezek a
  mezok lathatok/szerkeszthetők.

A minimum kezelt mezokeszlet a migration szerint:
- `display_name`
- `machine_code`
- `material_code`
- `thickness_mm`
- `kerf_mm`
- `spacing_mm`
- `margin_mm`
- `rotation_step_deg`
- `allow_free_rotation`
- `lifecycle = approved`
- `is_default = true`

A task ne talaljon ki ettol eltero schema-mezot.

#### 3. Run directory evidence bovuljon
A tool run directory contractja bovuljon legalabb ezekkel:
- `project_technology_setup.json`
- opcionálisan `technology_setup_input.json` vagy hasonlo, ha ez segiti az
  auditot, de plaintext token nelkul.

A `summary.md` mondja ki:
- uj projekt modban seedelt-e technology setupot;
- milyen display_name / machine_code / material_code / thickness ment be;
- milyen `technology_setup_id` jott letre;
- ha nem tudott seedelni, mi volt a blocker.

#### 4. GUI oldalon legyen ertelmes UX uj projekt modhoz
A GUI jelenleg optional `SUPABASE_URL` es `SUPABASE_ANON_KEY` mezoket mutat,
viszont technology setup mezok nincsenek.

Minimum elvaras:
- uj projekt modban a GUI tudja bekerni vagy defaulttal mutatni a technology
  setup adatokat;
- egyertelmu legyen, hogy uj projekt mod + run create csak approved technology
  setup seedelessel mehet;
- validacio blokkolja a futast, ha a tool a valasztott uzemmodban nem tudna
  technology setupot letrehozni.

A GUI tovabbra is vekony shell maradjon; az API/Supabase logika a core modulban
legyen.

#### 5. Smoke-ok legyenek eleg erossek
A core smoke bizonyitsa legalabb:
- uj projekt modban technology setup seedeles tortenik a run create elott;
- a `project_technology_setup.json` evidence fajl letrejon;
- ha a technology setup seedeleshez szukseges Supabase runtime adat hianyzik,
  a tool koran, erthetoen hibazik;
- fake transport mellett a `POST /runs` ne lehessen "zold", ha a scenario
  technology setup nelkul maradt.

A GUI smoke bizonyitsa legalabb:
- a GUI config builder uj projekt modban a technology setup parametereket is
  tovabbitja a core runnernek;
- hianyos technology setup/supabase adat eseten validacios hibat ad;
- meglvo projekt modban nem kovetel felesleges uj setup adatot.

### Javasolt bontas
Ez egyetlen taskkent is vallalhato, mert egy hibat kell zarni, de a javitas
mind a core, mind a GUI, mind a smoke reteget erinti. Kulon taskra most nincs
szukseg, mert a problema egyetlen, jol korulhatarolhato prerequisite-hiany.

### DoD
- [ ] Letrejon a task teljes artefaktlanca kulon `trial_run_tool_fix/` konyvtarban.
- [ ] A `scripts/trial_run_tool_core.py` uj projekt modban approved project technology setupot seedel.
- [ ] A seedeleshez szukseges adatok runtime szinten explicitek vagy dokumentalt default test setupbol jonnek.
- [ ] A `scripts/run_trial_run_tool.py` CLI felulete tudja a technology setuphoz szukseges parameterket.
- [ ] A `scripts/trial_run_tool_gui.py` uj projekt modban kezeli a technology setup adatokat es prerequisite-eket.
- [ ] A run directory evidence contract bovul a technology setup bizonyitekaival.
- [ ] A summary kimondja, hogy milyen technology setup jott letre vagy miert nem.
- [ ] A core smoke mar nem engedi at technology setup nelkul az uj projekt modot.
- [ ] A GUI smoke validalja az uj technology setup workflow-t.
- [ ] `./scripts/verify.sh --report codex/reports/trial_run_tool_fix/trial_run_tool_new_project_technology_setup_fix.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a tool tul sok product logikat vesz at;
  - rejtett hardcoded technology setup marad a kodban magyarazat nelkul;
  - a Supabase REST hasznalat tokenkezeles vagy evidence redakcio szempontbol
    csunyan oldodik meg;
  - a GUI tulterjeszkedik UX feature-okba.
- Mitigacio:
  - local-only teszt-tool boundary maradjon;
  - explicit minimal mezokeszlet + dokumentalt default test setup;
  - token ne keruljon plaintext formaban summary-ba vagy snapshot evidence-be;
  - core-ban legyen a tenyleges logika, a GUI csak shell;
  - smoke-ok modellezzek a missing technology setup blokkert.
- Rollback:
  - a core/CLI/GUI/smoke/report diff egy commitban visszavonhato;
  - product API es frontend erintetlen marad.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/trial_run_tool_fix/trial_run_tool_new_project_technology_setup_fix.md`
- Task-specifikus minimum:
  - `python3 -m py_compile scripts/trial_run_tool_core.py scripts/run_trial_run_tool.py scripts/trial_run_tool_gui.py scripts/smoke_trial_run_tool_cli_core.py scripts/smoke_trial_run_tool_tkinter_gui.py`
  - `python3 scripts/smoke_trial_run_tool_cli_core.py`
  - `python3 scripts/smoke_trial_run_tool_tkinter_gui.py`

## Lokalizacio
Nem relevans. Belso teszt-tool.

## Kapcsolodasok
- `canvases/trial_run_tool/trial_run_tool_cli_core.md`
- `canvases/trial_run_tool/trial_run_tool_tkinter_gui.md`
- `scripts/trial_run_tool_core.py`
- `scripts/run_trial_run_tool.py`
- `scripts/trial_run_tool_gui.py`
- `scripts/smoke_trial_run_tool_cli_core.py`
- `scripts/smoke_trial_run_tool_tkinter_gui.py`
- `api/services/run_snapshot_builder.py`
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- `api/supabase_client.py`
