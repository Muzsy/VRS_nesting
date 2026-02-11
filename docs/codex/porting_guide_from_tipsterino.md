# Codex workflow portolása Tipsterino-ból egy új repóba

## 🎯 Funkció

Ez a dokumentum összefoglalja, hogyan lehet a Tipsterino-ban bevezetett **canvas + goal YAML + checklist + report + verify** módszert átültetni egy másik projektre (példa: VRS Nesting).

A lényeg: a módszer **nem Flutter/Supabase specifikus**, hanem egy általános, repo‑auditálható fejlesztési protokoll.

---

## 🧠 Fejlesztési részletek

## 1) Mit érdemes egy az egyben átvenni?

A Tipsterino csomagból ezek a modulok általánosíthatók:

1) **Artefakt struktúra**
   - `canvases/` – feladat specifikáció
   - `codex/goals/canvases/` – goal YAML (steps)
   - `codex/codex_checklist/` – pipálható DoD
   - `codex/reports/` – report + verify log

2) **YAML outputs-szabály**
   - csak azokat a fájlokat szabad módosítani, amik szerepelnek a step `outputs` listájában

3) **Report Standard v2**
   - DoD → Evidence Matrix kényszeríti az auditálható lezárást

4) **verify wrapper** (`scripts/verify.sh`)
   - mindig a projekt saját `scripts/check.sh`-ját futtatja
   - logot ír a report mellé
   - frissít egy auto-managed blokkot a reportban

## 2) Mit kell projektspecifikusan cserélni?

### 2.1 `scripts/check.sh`

Ez a portolás kulcsa.

A `check.sh` feladata: **egy darab standard kapu** biztosítása, ami lefedi a projekt minimum elvárásait.

Tipsterino-ban ez Flutter analyze+test volt.
VRS Nesting-ben ez:

* Sparrow build (ha nincs bináris)
* IO smoketest futtatás (`scripts/run_sparrow_smoketest.sh`)
* validator futtatás (`scripts/validate_sparrow_io.py`)

**Szabály:** a CI és a lokál ugyanazt a `check.sh`-t futtassa.

### 2.2 Dokumentáció

A Tipsterino doksik közül sok Flutter/Supabase specifikus (routing, theme, localization, service boundaries).
Egy új repóba csak a workflow-hoz szükséges minimumot vidd át:

* `docs/codex/overview.md`
* `docs/codex/prompt_template.md`
* `docs/codex/yaml_schema.md`
* `docs/codex/report_standard.md`
* `docs/qa/testing_guidelines.md`

És ezekben cseréld ki:

* a “mi a minőségkapu” részt a projekt saját parancsaira
* a “milyen tesztek vannak” részt a projekt saját tesztelési modelljére

## 3) Minimális “bootstrap” lépéssor egy új repóban

1. Hozd létre a könyvtárakat:
   - `canvases/`
   - `codex/goals/canvases/`
   - `codex/codex_checklist/`
   - `codex/reports/`
   - `docs/codex/`
   - `docs/qa/`

2. Add hozzá:
   - `AGENTS.md` (repo-szabályok + gate parancsok)
   - `scripts/check.sh` (standard gate)
   - `scripts/verify.sh` (report+log wrapper)

3. CI-ben (GitHub Actions) a gate futtatása:
   - `./scripts/check.sh`

4. Készíts egy első “bootstrap” feladatot:
   - `canvases/codex_bootstrap.md`
   - `codex/goals/canvases/fill_canvas_codex_bootstrap.yaml`
   - `codex/reports/codex_bootstrap.md`
   - és futtasd: `./scripts/verify.sh --report codex/reports/codex_bootstrap.md`

## 4) Tipikus buktatók (és a megoldás)

* **A Codex inventál fájlneveket:** outputs-szabály + `AGENTS.md` “valós repó elv” fix.
* **Kétféle gate (lokál vs CI):** mindkettő `scripts/check.sh`-t futtasson.
* **Nem auditálható lezárás:** Report Standard v2 + DoD→Evidence kötelező.
* **Flaky smoketest:** pin commit (`poc/.../sparrow_commit.txt`) + fix seed + time limit.

---

## 🧪 Tesztállapot

A portolás akkor tekinthető késznek, ha:

* a repo tartalmazza a fenti “bootstrap” csomagot,
* a CI futtatja a `check.sh`-t,
* és legalább egy Codex futás reportja AUTO_VERIFY blokkal létrejött.

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

* `AGENTS.md`
* `docs/codex/overview.md`
* `docs/codex/prompt_template.md`
* `docs/codex/yaml_schema.md`
* `docs/codex/report_standard.md`
* `docs/qa/testing_guidelines.md`
