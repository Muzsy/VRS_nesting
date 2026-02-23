# canvases/nesting_engine/nesting_engine_phase1_p1_fixes.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nesting_engine_phase1_p1_fixes.md`
> **TASK_SLUG:** `nesting_engine_phase1_p1_fixes`
> **Terület (AREA):** `nesting_engine`

---

# Nesting Engine Fázis 1 – P1 Javítások (Truth Layer robusztusság)

## 🎯 Funkció

Ez a canvas a Fázis 1 utólagos auditja által feltárt három P1-es hiányosságot kezeli:

1. **Geometriai validátor a gate-ben** – a `determinism_hash` csak reprodukálhatóságot
   igazol, geometriai helyességet (0 overlap, OOB-mentesség) nem. Szándékosan hibás
   fixture-rel meg kell pirosítani a gate-et, hogy a Truth Layer fő garanciája
   ténylegesen ellenőrzött legyen.

2. **Shapely fallback kizárása stock ágon (default OFF + teszt)** – az
   `ALLOW_SHAPELY_FALLBACK_ENV` env flag jelenleg a stock ágon is engedi a Shapely
   visszaesést, ami csendesen elveszíti a determinizmust. Ezt teszttel lefedett,
   `default=OFF` állapotba kell hozni, és ha bekapcsolt, hangosan kell loggolni.

3. **`elapsed_sec` / idő-alapú mezők kiszervezése a Rust outputból** – a Rust kernel
   stdout kimenetébe kerülő időmérési értékek miatt a lemezre írt
   `nesting_output.json` két futás között eltérhet, ami külső checksum-alapú
   rendszereket hamisan „változónak" láttat. Az időmérést a Python runner szintjére
   kell vinni.

Ez a task **nem** tartalmaz NFP vagy Fázis 2 munkát; kizárólag a meglévő Fázis 1
motor robusztosítása.

---

## 🧠 Fejlesztési részletek

### Felderitesi jegyzetek (2026-02-22)

- A `scripts/validate_nesting_solution.py` jelenleg csak backward-compatible CLI wrapper, a v1 validacio
  implementacioja a `vrs_nesting/validate/solution_validator.py` modulban van.
- Az `offset_stock_geometry` agban a fallback mar most is `default=OFF`:
  - env flag nelkul (`VRS_OFFSET_ALLOW_SHAPELY_FALLBACK` hianyzik / `"0"`): Rust hiban `GeometryOffsetError` tovabbdobodik,
    nincs csendes Shapely fallback.
  - env flag truthy esetben (`"1"`, `"true"`, stb.): warning log mellett explicit Shapely fallback aktiv.
- `git grep elapsed_sec` talalatok kozul a P1-C szempontjabol erintett helyek:
  - `rust/nesting_engine/src/export/output_v2.rs` (Rust stdout `meta.elapsed_sec` kibocsatas)
  - `vrs_nesting/runner/nesting_engine_runner.py` (runner-level idomeres es artifact metadata)
  - `docs/nesting_engine/io_contract_v2.md` (kimeneti contract leiras)
  - `poc/nesting_engine/sample_output_v2.json` (pelda output dokumentacios minta)
  - `scripts/smoke_platform_determinism_rotation.sh` (normalizalo smoke script megjegyzes)
- A repoban tovabbi `elapsed_sec` emlitesek leginkabb korabbi canvas/goals/report artefaktokban szerepelnek;
  ezek nem futtatasi kodutvonalak.

### P1-A: Geometriai validátor gate-be

#### Érintett fájlok
- `scripts/validate_nesting_solution.py` – meglévő validátor kiterjesztése:
  overlap ellenőrzés (i_overlay vagy bounding-box alapú), OOB ellenőrzés.
- `scripts/check.sh` – új smoke lépés: szándékosan hibás fixture → validátor
  FAIL-el, gate piros.
- `poc/nesting_engine/invalid_overlap_fixture.json` – új fixture: két egymásba
  csúsztatott alkatrész, amelynek átfedése szándékos.

#### DoD
- [ ] `scripts/validate_nesting_solution.py` overlap-ellenőrzést végez minden
  placement párra (legalább AABB, ideálisan i_overlay narrow-phase).
- [ ] `scripts/validate_nesting_solution.py` OOB-ellenőrzést végez (minden
  placement befér a sheet határán belül, margin figyelembevételével).
- [ ] `poc/nesting_engine/invalid_overlap_fixture.json` létezik, és a validátor
  non-zero exittel tér vissza rá.
- [ ] `scripts/check.sh` tartalmaz egy lépést, ami az `invalid_overlap_fixture`-t
  megfuttatja és elvárja a non-zero exitkódot (FAIL = elvárt).
- [ ] `scripts/check.sh` a valós golden output-on (`baseline_benchmark` eredménye)
  is futtatja a validátort, és ott PASS-t vár.

#### Kockázatok / rollback
- A validátor bővítése nem módosítja a solver logikát; csak olvasó szkript.
- Ha a meglévő `validate_nesting_solution.py` nem importálható modulként, a
  bővítés a meglévő CLI interfészt megtartva történjen.

---

### P1-B: Shapely fallback stock ágon – default OFF + teszt

#### Érintett fájlok
- `vrs_nesting/geometry/offset.py` – az `offset_stock_geometry` fallback ágában
  az `ALLOW_SHAPELY_FALLBACK_ENV` ellenőrzés már jelen van; a cél annak igazolása
  teszttel, hogy `default=OFF` valóban érvényes, és Shapely aktiválódásakor
  egyértelmű WARNING kerül a logba.
- `tests/test_geometry_offset.py` – új teszteset: `ALLOW_SHAPELY_FALLBACK_ENV`
  nincs beállítva → Rust hiba esetén `GeometryOffsetError` dobódik (nem csendes
  fallback). Másik teszteset: env=`"1"` → Shapely meghívódik, WARNING loggolódik.

#### DoD
- [ ] `offset_stock_geometry`: ha `ALLOW_SHAPELY_FALLBACK_ENV` nincs beállítva
  (vagy `""` / `"0"`), Rust hiba esetén `GeometryOffsetError` dobódik – nincs
  csendes Shapely fallback.
- [ ] Ha `ALLOW_SHAPELY_FALLBACK_ENV="1"` és Rust hiba történik, a log
  WARNING szinten tartalmazza az env neve (`VRS_OFFSET_ALLOW_SHAPELY_FALLBACK`)
  és a hiba kódját.
- [ ] `tests/test_geometry_offset.py` lefedi mindkét ágat (monkeypatch-el, cargo
  build nélkül futtatható unit szinten).
- [ ] `scripts/check.sh` (`./scripts/verify.sh`) PASS marad.

#### Kockázatok / rollback
- Az `offset.py` módosítása minimális: csak az `offset_stock_geometry` fallback
  ágát érinti. A `offset_part_geometry` és a Rust-első útvonal érintetlen marad.
- Ha valaki élesben bekapcsolta az env flagot: a változtatás után a fallback
  bekapcsolt állapotban még működik, csak hangosabb lesz. Default OFF = a flag
  nélküli futásban nincs regresszió.

---

### P1-C: Idő-alapú mezők kiszervezése Rust outputból

#### Érintett fájlok
- `rust/nesting_engine/src/export/output_v2.rs` – az `elapsed_sec` (és egyéb
  idő-alapú) mező(k) eltávolítása a Rust kernel stdout JSON-jából. Ha a mező
  jelenleg kötelező az IO contract v2-ben, a contract `meta` szekciójában
  `"elapsed_sec": null` / elhagyható mezőként kell rögzíteni.
- `docs/nesting_engine/io_contract_v2.md` – a `meta.elapsed_sec` mező
  dokumentálása mint Python-runner-szintű, nem Rust-kernel-szintű adat.
- `vrs_nesting/runner/nesting_engine_runner.py` – az elapsed mérés ideirányítása:
  a runner méri a subprocess időtartamát és adja hozzá a saját artifact
  metaadataihoz (pl. `run_meta.json` vagy a meglévő artifact struktúra szerint).
- `rust/nesting_engine/src/export/output_v2.rs` – a `determinism_hash` számítása
  ne változzon; az `elapsed_sec` eltávolítása után a hash input stabilabb lesz.

#### DoD
- [ ] A Rust bináris stdout outputjában (`nesting_output.json`) nincs futásfüggő
  időadat: két egymást követő `nest` futás byte-azonos stdout-ot ad (az
  `elapsed_sec` / `time_limit_sec` mező eltávolítva vagy `null`-ra fixált).
- [ ] A Python runner a subprocess mért időtartamát saját metaadatként menti
  (a meglévő artifact könyvtárstruktúra szerint).
- [ ] `docs/nesting_engine/io_contract_v2.md` `meta` szekciója frissítve:
  `elapsed_sec` → "Python runner-level, not in Rust kernel output".
- [ ] A meglévő `check.sh` determinizmus smoke (`[NEST] CLI determinism OK`) és
  `scripts/check.sh` gate PASS marad.
- [ ] Ha van meglévő integráció/teszt, ami az `elapsed_sec` mezőt olvassa a
  Rust outputból, az frissítve van (repo-ban keresendő).

#### Kockázatok / rollback
- IO contract breaking change lehet, ha külső fogyasztó olvassa az `elapsed_sec`
  mezőt a Rust outputból. Ellenőrizni kell a repóban összes `elapsed_sec`
  hivatkozást (grep).
- Rollback: ha a mező eltávolítása törést okoz, `"elapsed_sec": null` a
  biztonságos átmenet (kontrakt szerint opcionális).

---

## 🧪 Tesztállapot

### Minőségkapu
- `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_phase1_p1_fixes.md`

### Feladat-specifikus ellenőrzések
- `python3 scripts/validate_nesting_solution.py poc/nesting_engine/invalid_overlap_fixture.json`
  → non-zero exit (P1-A smoke).
- `python3 -m pytest tests/test_geometry_offset.py -q` → PASS (P1-B egység).
- `cat poc/nesting_engine/sample_input_v2.json | ./rust/nesting_engine/target/release/nesting_engine nest > /tmp/out1.json && cat poc/nesting_engine/sample_input_v2.json | ./rust/nesting_engine/target/release/nesting_engine nest > /tmp/out2.json && diff /tmp/out1.json /tmp/out2.json` → üres diff (P1-C byte-azonos).

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

- `canvases/nesting_engine/nesting_engine_backlog.md` – backlog kontextus
- `rust/nesting_engine/src/export/output_v2.rs` – Rust export
- `vrs_nesting/geometry/offset.py` – Python offset logika
- `vrs_nesting/runner/nesting_engine_runner.py` – Python runner
- `scripts/validate_nesting_solution.py` – meglévő validátor
- `scripts/check.sh` – minőségkapu
- `docs/nesting_engine/io_contract_v2.md` – IO contract
- `docs/nesting_engine/tolerance_policy.md` – policy
- `codex/reports/nesting_engine/nesting_engine_baseline_placer.md` – Fázis 1 baseline
