# Report — lv8_density_t01_phase0_fixture_inventory

**Státusz:** PASS

A `./scripts/verify.sh` (repo gate) zöld: `check.sh` exit 0, 175s teljes
futási idő. Tartalmazza: pytest 302 passed, mypy clean, Sparrow IO smoketest
+ validator, DXF import/export + multisheet + valós DXF pipeline smokes,
`vrs_solver` validator + determinisztika + timeout/perf guard — mind PASS.
Minden T01 DoD pont PASS (lásd 5) szekció). Production diff guard üres halmaz.

## 1) Meta

- **Task slug:** `lv8_density_t01_phase0_fixture_inventory`
- **Kapcsolódó canvas:** [canvases/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md](../../../canvases/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md)
- **Kapcsolódó goal YAML:** [codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t01_phase0_fixture_inventory.yaml](../../goals/canvases/nesting_engine/fill_canvas_lv8_density_t01_phase0_fixture_inventory.yaml)
- **T00 index:** [canvases/nesting_engine/lv8_density_task_index.md](../../../canvases/nesting_engine/lv8_density_task_index.md)
- **T00 master runner:** [codex/prompts/nesting_engine/lv8_density_master_runner.md](../../prompts/nesting_engine/lv8_density_master_runner.md)
- **Forrásterv:** [codex/reports/nesting_engine/development_plan_packing_density_20260515.md](development_plan_packing_density_20260515.md) v2.2
- **Futás dátuma:** 2026-05-16
- **Branch / commit:** `main` @ `1e6f642`
- **Fókusz terület:** Docs (Phase 0 fixture audit, `tmp/` inventory artefaktok)

## 2) Scope

### 2.1 Cél

1. A Phase 0 shadow run három fixture-családjának valós repo-alapú auditálása
   (`lv8`, `web_platform_contract_freeze`, `small_synthetic_sa_guard`).
2. LV8 276, LV8 179, és SA guard fixture státuszának dokumentálása JSON parse
   + méret-ellenőrzéssel.
3. web_platform / contract_freeze családhoz konkrét anchorok rögzítése a
   `find` találatok alapján (canvas + report + harness + DXF input-pár).
4. LV8 179 fixture helyreállítási receptjének rögzítése `tmp/` notes-ban
   (a fixture jelenleg PRESENT, placeholder létrehozása tilos).
5. Inventory MD + JSON artefakt készítése, T02–T06 számára explicit
   blocking/non-blocking jelzéssel.
6. T01 checklist + report lezárása a Report Standard v2 szerint.

### 2.2 Nem-cél (explicit)

1. Nem módosít Rust engine kódot.
2. Nem módosít Python production kódot.
3. Nem módosít quality profile-t (`nesting_quality_profiles.py` érintetlen).
4. Nem futtat hosszú nesting benchmarkot.
5. Nem ír polygon-aware validátort.
6. Nem hoz létre placeholder fixture-t (sem LV8 179-re, sem contract_freeze-re).
7. Nem dönt újra a végleges fejlesztési terv tartalmáról.

## 3) Változások összefoglalója (Change summary)

### 3.1 Érintett fájlok

- **Inventory artefaktok (`tmp/`):**
  - [tmp/lv8_density_fixture_inventory.md](../../../tmp/lv8_density_fixture_inventory.md) (új)
  - [tmp/lv8_density_fixture_inventory.json](../../../tmp/lv8_density_fixture_inventory.json) (új)
  - [tmp/lv8_density_fixture_restore_notes.md](../../../tmp/lv8_density_fixture_restore_notes.md) (új; LV8 179 regenerálási recept)
- **Codex checklist + report:**
  - [codex/codex_checklist/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md](../../codex_checklist/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md) (új)
  - [codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md](lv8_density_t01_phase0_fixture_inventory.md) (új, ez a fájl)
  - `codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.verify.log`
    (a `./scripts/verify.sh` írja a repo gate-ben)

A T01 saját canvas + YAML + runner csomag korábbi taskban már a helyén volt:

- `canvases/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t01_phase0_fixture_inventory.yaml`
- `codex/prompts/nesting_engine/lv8_density_t01_phase0_fixture_inventory/run.md`

Az opcionálisan engedélyezett
`tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json` fájlt
**nem hoztuk létre / nem módosítottuk**, mert a fixture jelenleg PRESENT
(122854 byte, JSON parse OK, commit `0cd40b3`-ben jött létre 2026-05-14-én).

### 3.2 Miért változtak?

- **Inventory MD + JSON:** a Phase 0 shadow run csomagok (T02–T06) eddig nem
  rendelkeztek egységes, gépileg követhető fixture státusszal. A canvas
  Stop feltételei expliciten kérik a fixture-jelöltek 1:1 dokumentálását,
  a hiányzó status mezőket pótolja az inventory.
- **Restore notes:** a LV8 179 fixture `tmp/` alatt él → snapshot-érzékeny.
  A T01 rögzíti a determinisztikus helyreállítási receptet (LV8 276 fixture
  + a 179 riport Sheet 1 összetétele + `spacing_mm=10` / `margin_mm=10`),
  hogy jövőbeli snapshot-vesztés esetén ne legyen blocking.
- **Checklist + report:** a T01 DoD-jainak ellenőrizhetősége és a verify
  futtatás bekötése a Report Standard v2 szerint.

## 4) Verifikáció (How tested)

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`
  → eredmény az AUTO_VERIFY blokkban (4.4 alatt).
- Log: `codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.verify.log`

### 4.2 Opcionális, feladatfüggő parancsok

- **Előfeltétel ellenőrzés:** 10/10 kötelező rule + T00 + T01 fájl `OK`
  (`AGENTS.md`, `docs/codex/{overview,yaml_schema,report_standard}.md`,
  `docs/qa/testing_guidelines.md`,
  `codex/reports/nesting_engine/development_plan_packing_density_20260515.md`,
  T00 task index + master runner, T01 canvas + YAML).
- **Fixture JSON parse + méret:**
  - `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` — `exists=True`,
    `size=122855`, `json_parse_ok=True`, top-keys
    `parts/seed/sheet/time_limit_sec/version`.
  - `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json` — `exists=True`,
    `size=583`, `json_parse_ok=True`, top-keys
    `parts/seed/sheet/time_limit_sec/version`.
  - `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json` —
    `exists=True`, `size=122854`, `json_parse_ok=True`, top-keys
    `parts/seed/sheet/time_limit_sec/version`.
- **LV8 179 keresés:** `find . -path '*lv8_sheet1_179.json' -o -path '*lv8_singlesheet*'`
  — a `tmp/lv8_singlesheet_etalon_20260514/` fa teljes egészében jelen,
  beleértve a riport-állományt és az `inputs/lv8_sheet1_179.json`-t is.
- **contract_freeze keresés:** `find . \( -iname '*contract*freeze*' -o
  -path '*contract_freeze*' -o -iname '*freeze*' \)` — 4 canvas/report
  anchor a `web_platform` területen + a `smoke_svg_export.py` driver
  meglétét DXF input-páros (samples/dxf_demo/`{stock_rect_1000x2000,
  part_arc_spline_chaining_ok}.dxf`) erősítette meg.
- **Inventory sanity check (runner Python blokk):** `T01 inventory sanity PASS`.
- **Production diff guard:** `git diff --name-only HEAD -- '*.rs' '*.py'
  '*.ts' '*.tsx' | grep -v '^codex/' | grep -v '^canvases/'` → üres
  halmaz (a T01 csak `canvases/`, `codex/`, `tmp/` alá írt).

### 4.3 Ha valami kimaradt

Semmilyen kötelező ellenőrzés nem maradt ki. Az opcionális
`tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json` fájlt
azért **nem** írtuk át, mert a fixture jelenleg PRESENT — placeholder /
újra-generálás létrehozása a canvas tilalmába ütközne. Helyette egy
restore notes dokumentum készült.

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-16T10:05:20+02:00 → 2026-05-16T10:08:15+02:00 (175s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.verify.log`
- git: `main@1e6f642`
- módosított fájlok (git status): 6

**git status --porcelain (preview)**

```text
?? canvases/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md
?? codex/codex_checklist/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md
?? codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t01_phase0_fixture_inventory.yaml
?? codex/prompts/nesting_engine/lv8_density_t01_phase0_fixture_inventory/
?? codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md
?? codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.verify.log
```

<!-- AUTO_VERIFY_END -->

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| #1 Repo szabályfájlok és T00 index/master runner elolvasva | PASS | Előfeltétel `ls` 10/10 OK; T00 outputok: `canvases/nesting_engine/lv8_density_task_index.md` (418 sor), `codex/prompts/nesting_engine/lv8_density_master_runner.md` (332 sor) | Az összes szabályfájl + T00 + T01 anchor jelen; verziók megegyeznek a runner kötelező olvasnivaló listájával. | Step "Előfeltétel ellenőrzés" |
| #2 `tmp/lv8_density_fixture_inventory.md` létrejött | PASS | [tmp/lv8_density_fixture_inventory.md](../../../tmp/lv8_density_fixture_inventory.md) | Emberileg olvasható MD összefoglaló a három családra; családonként státusz + méret + JSON parse jelzés. | Manuális olvasás |
| #3 `tmp/lv8_density_fixture_inventory.json` létrejött és valid JSON | PASS | [tmp/lv8_density_fixture_inventory.json](../../../tmp/lv8_density_fixture_inventory.json) | Inventory JSON; a runner sanity check (`T01 inventory sanity PASS`) ellenőrizte a kötelező family_id-ket, fixture id-ket és státusz halmazt. | Runner Python sanity check |
| #4 LV8 276 fixture státusza dokumentált | PASS | inventory.json `families[0].fixtures[0]` (`lv8_276_full`, status `PRESENT`); fizikai fájl: `tests/fixtures/nesting_engine/ne2_input_lv8jav.json:1` | 122 855 byte, JSON parse OK, top-keys `parts/seed/sheet/time_limit_sec/version`, 12 part-típus, 276 instance. | `python3` json parse + `Path.stat()` |
| #5 LV8 179 fixture státusza dokumentált, nem feltételezett | PASS | inventory.json `families[0].fixtures[1]` (`lv8_179_single_sheet`, status `PRESENT`); fizikai fájl: `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json` | 122 854 byte, JSON parse OK, 12 part-típus, 179 instance. Származás dokumentálva (riport 2026-05-14, commit `0cd40b3`). Helyreállítási recept: [tmp/lv8_density_fixture_restore_notes.md](../../../tmp/lv8_density_fixture_restore_notes.md). | `python3` json parse + `find` |
| #6 Kis-synthetic / SA guard fixture státusza dokumentált | PASS | inventory.json `families[2].fixtures[0]` (`f2_4_sa_quality_fixture_v2`, status `PRESENT`); fizikai fájl: `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json:1` | 583 byte, JSON parse OK, top-keys konzisztensek a többi fixture-rel. A v2.2 plan explicit elsődleges választása. | `python3` json parse |
| #7 web_platform / contract_freeze fixture-jelöltek konkrét fájlokra bontva | PASS | inventory.json `families[1]`: `web_platform_contract_freeze_stock_dxf`, `web_platform_contract_freeze_part_dxf`, `web_platform_contract_freeze_harness` | `samples/dxf_demo/stock_rect_1000x2000.dxf`, `samples/dxf_demo/part_arc_spline_chaining_ok.dxf`, `scripts/smoke_svg_export.py:31-52` — mind PRESENT. Nincs `BLOCKED`. A plan által nyitva hagyott contract-freeze fixture-lista itt lezárva. | `find` + `ls` |
| #8 Nincs placeholder fixture | PASS | `git status --short` nem mutat új `tmp/.../lv8_sheet1_179.json` írást | A meglévő LV8 179 fixture érintetlen; restore notes csak dokumentum. | `git status --short` |
| #9 Nincs Rust / Python / TypeScript production kódmódosítás | PASS | Production diff guard kimenete (üres) | `git diff --name-only HEAD -- '*.rs' '*.py' '*.ts' '*.tsx' \| grep -v '^codex/' \| grep -v '^canvases/'` → üres. | Diff guard |
| #10 T01 checklist létrejött és ki van töltve | PASS | [codex/codex_checklist/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md](../../codex_checklist/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md) | Pipálható DoD-lista; a verify run előtt 2 sor nyitott (`./scripts/verify.sh` + Evidence Matrix kitöltés), ezek a repo gate után pipálódnak. | Manuális olvasás |
| #11 T01 report Report Standard v2 szerint, DoD → Evidence Matrix-szal | PASS | Ez a fájl 5) szekciója (12 sor DoD bizonyítékkal) | A report struktúra Report Standard v2 szerint; minden DoD ponthoz path + line / parancs bizonyíték. | `./scripts/verify.sh --report …` |
| #12 `./scripts/verify.sh --report …` lefutott | PASS | AUTO_VERIFY blokk a 4.4 alatt: `eredmény: PASS`, `check.sh exit 0`, 175s | A repo gate teljes `check.sh`-t futtatott (pytest + mypy + Sparrow + DXF + multisheet + vrs_solver + determinisztika + perf guard) — mind zöld. | `./scripts/verify.sh --report …` |

Minden DoD pont PASS.

## 6) IO contract / minták

Nem releváns: a T01 nem módosította a Sparrow IO contractot, a POC mintákat
vagy a validator-t. Az `f2_4_sa_quality_fixture_v2.json` érintetlen
(`poc/nesting_engine/` alatt él, csak audit).

## 7) Doksi szinkron

- Az inventory MD + JSON a `docs/codex/report_standard.md` v2 szellemiségét
  követi (státuszok zárt halmaza, evidence-orientált jelölés).
- A web_platform contract_freeze családra hivatkozott canvas/report anchorok
  konzisztensek a `canvases/web_platform/` + `canvases/web_platform_phase0_contract_freeze.md`
  fájlokkal.
- A LV8 179 származása összhangban a `codex/reports/nesting_engine/lv8_singlesheet_etalon_179_20260514.md`-vel.

## 8) Advisory notes (max 5)

- A LV8 179 fixture `tmp/` alatti elhelyezkedése miatt snapshot-érzékeny.
  Ha a packing-density fejlesztés tartós, érdemes megfontolni a fixture
  átmozgatását `tests/fixtures/nesting_engine/` alá (külön T01b vagy
  follow-up taskban) — az aktuális helyén nem stabil hosszú távon.
- A web_platform contract_freeze család nem ad density delta mérést, csak
  regresszió-mentesség jelzést. A T06 baseline aggregálás során a
  contract-freeze családot szeparált sorban kell jelenteni; a
  `quality_beam_lns` / `_explore` méréseit ettől függetlenül soha nem
  szabad összevonni.
- A LV8 179 helyreállítási recept manuális transzformáció (276 → 179);
  dedikált CLI script jelenleg nincs. Ha a fixture gyakran kerül
  regenerálásra, érdemes lehet egy `scripts/experiments/restore_lv8_sheet1_179.py`
  létrehozása későbbi taskban — most ez a T01 scope-on kívül.
- A samples/dxf_demo/ alatti DXF-pár (`stock_rect_1000x2000.dxf` +
  `part_arc_spline_chaining_ok.dxf`) szándékosan kis méretű (a
  `smoke_svg_export.py` időbüdzséhez igazítva). A contract-freeze gate
  nem tervezi méretezni; nagyobb fixture-re a Phase 1+ taskok döntenek.
- Az inventory JSON `recommended_next_step` mezője a T02-t jelöli; a
  fixture-készlet teljes és PRESENT, így a Phase 0 wave (T02–T05)
  párhuzamosítható és nincs blokkoló.

## 9) Follow-ups

1. **LV8 179 fixture átmozgatása `tests/fixtures/nesting_engine/` alá** —
   külön T01b vagy follow-up Codex task; nyereség: snapshot-független
   referencia, Phase 0 wave-ben nincs `tmp/` függőség. Kockázat: a
   `lv8_singlesheet_etalon_179_20260514.md` riport `tmp/` útvonalakra
   hivatkozik — a riport linkfrissítését is kötelező magában foglalnia.
2. **`restore_lv8_sheet1_179.py` CLI script** (opcionális) — ha a fixture
   helyreállítása többször ismétlődik. Nem T01 scope, csak akkor érdemes,
   ha a #1 átmozgatás nem történik meg.
3. **T02 packaging** — `lv8_density_t02_phase0_quality_profile_shadow_switch`
   indítható; az inventory PRESENT státuszai megerősítik a Phase 0 alapot.
4. **T03–T05 packaging waveként** — párhuzamosan T02 mellett (canvas:
   `lv8_density_task_index.md` Parallelization notes szekciója).
5. **T06 packaging** — Phase 0 baseline aggregálás az inventory JSON-t mint
   forrás-referenciát hivatkozva; a contract-freeze családot szeparált
   sorban kell jelenteni (lásd Advisory notes).
