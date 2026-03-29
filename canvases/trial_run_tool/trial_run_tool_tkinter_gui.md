# Trial run tool Tkinter GUI

## Funkcio
A feladat egy nagyon vekony, helyi desktop GUI reteg letrehozasa a mar meglevo
trial-run CLI core fole. A GUI celja, hogy a kezelo szemelynek ne kelljen minden
probafuttatast kezzel, hosszu CLI paranccsal vagy kulon Codex prompttal elinditania,
hanem egy egyszeru ablakban meg tudja adni a futashoz szukseges parametereket,
es a hatterben ugyanaz a core runner dolgozzon.

Ez a task szigoruan teszt-tool UI. Nem kerul be a vegleges termek frontendjebe,
es nem valik product feature-re.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - egyszeru helyi GUI `tkinter` alapon;
  - DXF directory valaszto;
  - token mező (maszkolt input);
  - tablmeret mezok;
  - uj projekt / meglevo projekt valaszto;
  - project_id mező meglevo projekt uzemmodhoz;
  - output base dir mező;
  - automatikusan felismert DXF lista es darabszam mezok;
  - Start gomb;
  - log / status panel;
  - futas utan run directory megnyitasi lehetoseg vagy egyertelmu path kijelzes;
  - GUI-bol a core runner meghivasa nem-blokkoló modon.
- Nincs benne:
  - web UI;
  - frontend integracio;
  - SVG preview canvas;
  - DXF vizualizacio;
  - drag&drop;
  - settings persistence vagy komplex app state;
  - desktop installer / packaging.

### GUI technologiai dontes
A task hasznaljon `tkinter`-t, nem `PySide6`-ot. Indok:
- stdlib-ben elerheto;
- belso teszt-toolhoz eleg;
- uj dependency nelkul kisebb kockazat;
- a repo gate headless jellegu kornyezete mellett is alacsonyabb a bevezetesi koltseg.

### Elofeltetel
Ez a task a `trial_run_tool_cli_core` taskra epul. A GUI nem implementalhat kulon,
masodik API logikat; a futtatast a core modulra kell delegalnia.

### Erintett, valosan letezo kiindulasi fajlok
- `scripts/trial_run_tool_core.py`
  - az elozo task altal bevezetett core modul.
- `scripts/run_trial_run_tool.py`
  - CLI referencia a parameterezeshez.
- `docs/dxf_nesting_app_terv_sparrow_jagua_rs_alap.md`
  - CLI-first, GUI-second iranyelv.
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`

### Uj, task altal bevezetendo fajlok
- `scripts/trial_run_tool_gui.py`
  - a vekony Tkinter GUI shell.
- `scripts/smoke_trial_run_tool_tkinter_gui.py`
  - headless-barati smoke a GUI nem-ablakos helper logikajara.

### Konkret elvarasok

#### 1. A GUI csak shell legyen
A GUI ne masolja le a CLI core logikajat. A GUI feladata:
- inputok bekérése;
- validacios hibak jelzese;
- futas hatterben inditasa;
- log/status kirajzolas;
- futas vegen eredmeny directory megmutatasa.

Az API hivasok, file upload, pollolas, summary generation a core modulban maradjanak.

#### 2. A GUI maradjon nagyon egyszeru
Eleg egy ablak, nagyjabol ezekkel a mezokkel:
- DXF directory
- bearer token
- API base URL
- sheet width
- sheet height
- output base dir
- new project checkbox/radiobutton
- project_id mezo (csak meglevo projekt eseten aktiv)
- automatikusan felismert DXF lista + qty inputok
- start gomb
- log/status text area

Ne legyen tulterjeszkedes preview, theme, docking vagy egyeb UX iranyba.

#### 3. A GUI ne fagyassza be az ablakot
A futas ne a UI event loopban blokkoljon. A jo minimum:
- hatterszal vagy hasonlo egyszeru nem-blokkolo mechanizmus;
- thread-safe log/status atadas a GUI fele;
- futas kozben a Start gomb legyen vedett a dupla inditastol.

#### 4. Titokkezeles itt is legyen korrekt
A token mező maszkolt legyen. A GUI se mentsen plaintext tokent local configba.
Ha a GUI mutat input snapshotot vagy summary-t, ott is redakalt forma jelenjen meg.

#### 5. Headless smoke legyen reális
A repo gate alatt ne kelljen valodi ablakot nyitni. A smoke jo minimuma:
- a GUI modul importalhatosaga;
- a parameter-epito / validalo helper logika tesztje;
- annak bizonyitasa, hogy a GUI a core runnernek megfelelo konfiguraciot allit elo;
- display nelkuli kornyezetben is futhato ellenorzes.

#### 6. Ne keveredjen a vegleges UI-val
A GUI fajl a `scripts/` alatt maradjon, ne a `frontend/` ala keruljon, es ne hozzon
letre Vite/React oldali kotest.

### DoD
- [ ] Letrejon a vekony `scripts/trial_run_tool_gui.py` Tkinter shell.
- [ ] A GUI a core runnerre delegalja a futast.
- [ ] A GUI kezeli az uj projekt / meglevo projekt uzemmodot.
- [ ] A GUI DXF directory alapjan fel tudja sorolni a DXF-eket es mennyiseg mezoket ad.
- [ ] A GUI futas kozben nem blokkolja teljesen az ablakot.
- [ ] A token mező maszkolt, plaintext token nincs lokalis configba mentve.
- [ ] Keszul headless smoke a GUI helper logikajara.
- [ ] Checklist es report evidence-alapon frissitve.
- [ ] `./scripts/verify.sh --report codex/reports/trial_run_tool/trial_run_tool_tkinter_gui.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a GUI sajat logikaval elter a CLI runner viselkedesetol;
  - headless kornyezetben torik a smoke;
  - a GUI scope elkezd product UI iranyba csuszni.
- Mitigacio:
  - core runnerre delegalas;
  - display-fuggetlen smoke;
  - `scripts/` alatti elhelyezes es explicit non-goals.
- Rollback:
  - a diff a `scripts/trial_run_tool_gui.py` es a kapcsolodo smoke fajlra korlatozhato,
    egy commitban visszavonhato;
  - a core runner es a frontend erintetlen marad.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/trial_run_tool/trial_run_tool_tkinter_gui.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile scripts/trial_run_tool_gui.py scripts/smoke_trial_run_tool_tkinter_gui.py`
  - `python3 scripts/smoke_trial_run_tool_tkinter_gui.py`

## Lokalizacio
Nem relevans. Belso teszt-tool GUI.

## Kapcsolodasok
- `canvases/trial_run_tool/trial_run_tool_cli_core.md`
- `scripts/trial_run_tool_core.py`
- `scripts/run_trial_run_tool.py`
- `docs/dxf_nesting_app_terv_sparrow_jagua_rs_alap.md`
