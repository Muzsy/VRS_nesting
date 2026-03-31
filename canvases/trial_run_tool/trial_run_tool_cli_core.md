# Trial run tool CLI core

## Funkcio
A feladat egy kulonallo, kifejezetten tesztelesre szolgalo local trial-run tool
magjanak es CLI bellepesi pontjanak letrehozasa. A tool celja, hogy a mostani
hosszu, kezi web_platform nesting probafuttatasi procedurat egyetlen,
auditolhato Python futtatova valtsa ki ugy, hogy az ne epuljon be a vegleges
termek UI-ba es ne hozzon letre uj product feature boundary-t.

A tool feladata:
- DXF konyvtar beolvasasa;
- bearer token runtime megadasa mellett authenticated API hivassor vegrehajtasa;
- uj projekt letrehozasa vagy meglevo projekt hasznalata;
- file upload -> geometry import -> part/sheet/run lanc vegigvezetese;
- pollolas es artifact letoltes;
- teljes evidence run directory letrehozasa `tmp/runs/...` alatt;
- olvashato vegso summary kiirasa.

Ez a task a motor + CLI reteget valositja meg. A GUI kulon, raepulo task lesz.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - kulonallo trial-run orchestrator Python modul;
  - CLI entrypoint, amely argumentumokkal futtathato es hianyzo parameter eseten
    csak a szukseges minimumot kerdezi be interaktivan;
  - uj projekt vs meglevo projekt uzemmod;
  - DXF directory alapjan partlista felallitasa;
  - egyseges vagy fajlankenti darabszam tamogatas;
  - `tmp/runs/<slug>/` audit kimeneti struktura;
  - API response-ok, letoltott artifactok, local logok es summary mentese;
  - token redakcios szabaly: titok ne keruljon plaintext formaban a repoba vagy
    a run summary-ba;
  - headless smoke / regresszio a tool magjara.
- Nincs benne:
  - frontend/web UI integracio;
  - repo-beli vegleges product UI bekotese;
  - auth flow redesign vagy token megszerzo UI;
  - run_queue lease reset SQL hack vagy rejtett DB mutatok kozvetlen irasa;
  - valodi DXF preview/render GUI;
  - PyInstaller / desktop csomagolas.

### Miert ketlepcsos projekt
A repo sajat doksijai is azt ajanljak, hogy eloszor stabil CLI/motor legyen, es
csak azutan jojjon a GUI (`docs/dxf_nesting_app_terv_sparrow_jagua_rs_alap.md`).
Ez a task ezt a sorrendet koveti: eloszor az ujrafelhasznalhato futtatomotor,
majd a kovetkezo taskban a vekony Tkinter shell.

### Erintett, valosan letezo kiindulasi fajlok
- `scripts/run_web_platform.sh`
  - meglevo start/stop/status/log bellepesi pont a platformhoz.
- `scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py`
  - meglevo end-to-end lanc referencia a web_platform pipeline-hoz.
- `scripts/smoke_h1_real_infra_closure.py`
  - eleresi / HTTP / artifact mintak referenciaja.
- `api/routes/projects.py`
- `api/routes/files.py`
- `api/routes/parts.py`
- `api/routes/sheets.py`
- `api/routes/project_part_requirements.py`
- `api/routes/project_sheet_inputs.py`
- `api/routes/runs.py`
- `api/README.md`
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`

### Uj, task altal bevezetendo fajlok
A task a kovetkezo uj lokalis teszt-tool fajlokat vezesse be:
- `scripts/trial_run_tool_core.py`
  - a teljes orchestrator es a file/log/HTTP helper mag.
- `scripts/run_trial_run_tool.py`
  - CLI bellepesi pont.
- `scripts/smoke_trial_run_tool_cli_core.py`
  - headless smoke a mag viselkedesere.

### Konkret elvarasok

#### 1. A tool legyen local-only teszt eszkoz
A trial-run tool ne kapcsolodjon a frontendhez, ne jelenjen meg product feature-kent,
es ne hozzon letre uj API route-ot. Kizarolag a meglevo web_platform API-t es a
meglevo platform indito scriptet hasznalja.

#### 2. A mag legyen GUI-fuggetlen
A CLI task a kovetkezo task GUI-janak is a hattermodulja lesz. Ennek megfeleloen:
- a teljes futasi logika ne a CLI `main()`-be keruljon;
- legyen jol importalhato, parameterobjektummal vagy tiszta Python strukturaval
  hivhato orchestrator reteg;
- a CLI csak parameter parse + futtatasi shell legyen.

#### 3. Parameterek es input modell
A tool minimum a kovetkezo fogalmakat tudja kezelni:
- DXF konyvtar utvonal;
- bearer token;
- API base URL;
- tablmeret (`sheet_width`, `sheet_height`);
- uj projekt vagy meglevo `project_id`;
- default darabszam az osszes DXF-re;
- opcionális fajlankenti darabszam override;
- output base directory.

A jo minimum CLI UX:
- elsodlegesen argumentumos futtatas;
- ha titok vagy kotelezo parameter hianyzik, csak akkor kerdezzen vissza;
- token bekereshez `getpass`-szeru, nem echozo input vagy env fallback legyen.

#### 4. Run directory contract
Minden futas kulon directoryt hozzon letre `tmp/runs/` alatt. Minimum tartalom:
- `run.log`
- `inputs_redacted.json`
- `api_health.json`
- `created_project.json` vagy meglevo projekt summary
- `uploaded_files.json`
- `geometry_revisions.json`
- `created_parts.json`
- `created_sheet.json`
- `project_part_requirements.json`
- `project_sheet_input.json`
- `created_run.json`
- `run_poll_history.json`
- `final_run.json`
- `run_artifacts.json`
- `viewer_data.json`
- `downloaded_artifact_urls.json`
- `summary.md`
- `quality_summary.json`
- a letoltott `sheet_*.svg`, `sheet_*.dxf`
- elerheto `solver_output`, `runner_meta`, `solver_stderr`, `run_log` artifactok

Hiba eseten (sikertelen futas) a run directory megkapja:
- `platform_worker.log` — a worker log utolso 20 000 karaktere
- `platform_api.log` — az API log utolso 20 000 karaktere
- `platform_status_at_failure.json` — a platform allapota a hiba idejen

A summary emberileg olvashato legyen, a JSON-ok pedig teljes auditot tegyenek lehetove.

#### 5. Titokkezeles legyen korrekt
A token sem a repoba, sem default configba, sem run summary-ba nem kerulhet teljes
plain text formaban. A tool legfeljebb redakalt formaban mentheti:
- pl. utolso nehany karakter,
- token hossza,
- bearer jelenlet / forras tipus (`argv`, `env`, `prompt`).

#### 6. Platform indulasi strategia
A tool elsokent health checket vegezzen. Ha a platform nem elerheto, a jo minimum:
- vagy dokumentalt flag mellett meghivja a `scripts/run_web_platform.sh start` scriptet,
- vagy egyertelmu hibaval megall.

A `scripts/run_web_platform.sh start` a kovetkezo readiness ellenorzeseket vegzi:
- API: HTTP GET `/health` valasz
- Worker: `.cache/web_platform/worker.ready` fajl megjelenese (a worker irja, mielott a poll loopba lep)
- Frontend: HTTP GET `/` valasz

Ne legyen rejtett, agressziv auto-healing logika. Kulonosen:
- ne fusson csendben SQL lease reset;
- ne irjon kozvetlenul DB tablakat.

#### 7. Hibakezeles es reszleges siker evidencia
Ha a lanc egy ponton megall, a tool akkor is mentsen eleg evidence-et:
- az utolso sikeres lepesig minden JSON maradjon meg;
- a hiba response/testkornyezet/log bekeruljon a run directoryba;
- a `summary.md` egyertelmuen nevezze meg, hol allt meg.

#### 8. A smoke legyen headless es offline-barati
A repo gate nem tamaszkodhat elo local API-ra vagy elo Supabase-ra. A smoke jo minimuma:
- temp directoryban letrehozott fake DXF fajlok vagy placeholders;
- fake HTTP/session layer vagy monkeypatch-elt request transport;
- determinisztikus, kicsi canned response lanc;
- annak bizonyitasa, hogy a run directory contract es a summary generation mukodik.

#### 9. A task ne akarja mar a GUI-t is megoldani
A CLI core task ne keverjen bele Tkinter widgeteket, threadelt UI logolast vagy
file picker logikat. Ezek a kovetkezo taskba tartoznak.

### DoD
- [ ] Letrejon a GUI-fuggetlen `scripts/trial_run_tool_core.py` orchestrator modul.
- [ ] Letrejon a CLI bellepesi pont `scripts/run_trial_run_tool.py`.
- [ ] A CLI tamogatja az uj projekt es a meglevo projekt uzemmodot.
- [ ] A CLI kezeli a DXF directory + darabszam parametereket.
- [ ] A tool audit run directoryt hoz letre `tmp/runs/...` alatt.
- [ ] A tool nem ment plaintext tokent a repo-ba vagy a run summary-ba.
- [ ] Hibanal is ment eleg evidence-et a run directoryba.
- [ ] Keszul headless smoke a tool magjara.
- [ ] Checklist es report evidence-alapon frissitve.
- [ ] `./scripts/verify.sh --report codex/reports/trial_run_tool/trial_run_tool_cli_core.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a tool tul sok operational kulonutat tartalmaz es nehezen karbantarthato lesz;
  - a token veletlenul logba vagy summary-ba kerul;
  - a CLI es a majdani GUI kulon logikaval kezd mukodni.
- Mitigacio:
  - egyetlen kozos orchestrator modul;
  - redakcios helper;
  - explicit run directory contract;
  - a GUI teljesen kulon task.
- Rollback:
  - a tool teljes diffje a `scripts/trial_run_tool_*` es kapcsolodo smoke fajlokra
    korlatozodik, egy commitban visszavonhato;
  - nem erinti a product UI-t es nem modosit API contractot.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/trial_run_tool/trial_run_tool_cli_core.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile scripts/trial_run_tool_core.py scripts/run_trial_run_tool.py scripts/smoke_trial_run_tool_cli_core.py`
  - `python3 scripts/smoke_trial_run_tool_cli_core.py`

## Lokalizacio
Nem relevans. Ez belso teszt-tool.

## Kapcsolodasok
- `docs/dxf_nesting_app_terv_sparrow_jagua_rs_alap.md`
- `scripts/run_web_platform.sh`
- `scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py`
- `scripts/smoke_h1_real_infra_closure.py`
- `api/routes/projects.py`
- `api/routes/files.py`
- `api/routes/parts.py`
- `api/routes/sheets.py`
- `api/routes/project_part_requirements.py`
- `api/routes/project_sheet_inputs.py`
- `api/routes/runs.py`
