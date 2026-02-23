# VRS Nesting Codex Task — Nesting Engine Fázis 1 P1 Javítások
TASK_SLUG: nesting_engine_phase1_p1_fixes

## 1) Kötelező olvasnivaló (prioritási sorrend)

Olvasd el és tartsd be, ebben a sorrendben:

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/qa/testing_guidelines.md`
6. `canvases/nesting_engine/nesting_engine_phase1_p1_fixes.md` — feladat specifikáció
7. `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_phase1_p1_fixes.yaml` — lépések

Ha bármelyik fájl nem létezik: állj meg, és írd le pontosan mit kerestél és hol.

---

## 2) Cél

Három P1-es auditlelet javítása a Nesting Engine Fázis 1 Truth Layer-en:

**P1-A** — Geometriai validátor (overlap + OOB ellenőrzés) beépítése a CI gate-be,
szándékosan hibás fixture-rel, amely pirosítja a gate-et, ha a validátor átengedi
az átfedő elhelyezéseket.

**P1-B** — Shapely fallback stock ágon teszttel lefedett `default=OFF` állapotba
hozva: env flag nélkül Rust hiba esetén hangos `GeometryOffsetError` keletkezik,
csendes fallback nem lehetséges.

**P1-C** — `elapsed_sec` és egyéb futásfüggő idő-mezők eltávolítása a Rust kernel
stdout JSON-jából; az időmérés a Python runner szintjére kerül, a Rust output
byte-azonos lesz két egymást követő futás között.

---

## 3) Nem cél

- NFP / Fázis 2 fejlesztés
- BLF placer logika módosítása
- `vrs_solver` bármilyen módosítása
- Új nesting algoritmus vagy konfigurációs lehetőség
- IO contract v2 törése (a `meta.elapsed_sec` opcionálissá tétele visszafelé
  kompatibilis; a többi mező változatlan)

---

## 4) Munkaszabályok (nem alkuképes)

- Csak olyan fájlt hozz létre / módosíts, ami szerepel az adott YAML step
  `outputs` listájában.
- Valós repó elv: nem találhatsz ki fájlokat, mezőket, parancsokat.
- Minimal-invazív: a meglévő determinizmus smoke, unit tesztek és gate PASS marad.
- Gate csak wrapperrel: `./scripts/verify.sh --report ...`

---

## 5) Végrehajtás

Hajtsd végre a YAML `steps` lépéseit **sorrendben**:

```
codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_phase1_p1_fixes.yaml
```

Minden step után ellenőrizd:
- A step `outputs` listájában szereplő fájlok létrejöttek / módosultak.
- Más fájl nem változott.

---

## 6) Kritikus ellenőrzési pontok

**P1-A fixture**: az `invalid_overlap_fixture.json` legyen valid JSON, amelyet a
validátor betud olvasni, de overlap miatt non-zero exittel tér vissza. Ne legyen
benne érvényes `determinism_hash` (nem szükséges).

**P1-B tesztek**: cargo build nélkül futtathatók legyenek (subprocess.run
monkeypatch). A meglévő `test_geometry_offset.py` struktúrájához illeszkedjenek.

**P1-C grep**: az `elapsed_sec` keresd meg a teljes repóban (`git grep elapsed_sec`)
és minden érintett helyet frissíts, mielőtt a Rust-ban eltávolítod. Különösen
figyelj a Python oldalra, ahol esetleg a Rust outputból olvasná valaki ezt a mezőt.

**Byte-azonos smoke**: a gate bővítésénél add hozzá a `check.sh`-ba a kétszeri
`nest` futtatás + diff ellenőrzést, ha még nincs benne (opcionális, de erősen
ajánlott P1-C bizonyításához).

---

## 7) Gate futtatás (kötelező)

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_phase1_p1_fixes.md
```

Ez létrehozza / frissíti:
- `codex/reports/nesting_engine/nesting_engine_phase1_p1_fixes.md` (AUTO_VERIFY blokk)
- `codex/reports/nesting_engine/nesting_engine_phase1_p1_fixes.verify.log`

---

## 8) Elvárt végállapot

- `scripts/validate_nesting_solution.py` overlap + OOB ellenőrzést végez.
- `poc/nesting_engine/invalid_overlap_fixture.json` létezik; validátor non-zero exittel tér vissza rá.
- `scripts/check.sh` tartalmaz validátor FAIL smoke lépést (elvárt non-zero exit).
- `tests/test_geometry_offset.py` lefedi a Shapely fallback mindkét ágát (env ON / OFF).
- A Rust `nest` stdout két egymást követő futásban byte-azonos (nincs `elapsed_sec`).
- `docs/nesting_engine/io_contract_v2.md` `meta.elapsed_sec` → Python-runner-level mezőként dokumentálva.
- `vrs_nesting/runner/nesting_engine_runner.py` mér és ment `elapsed_sec`-et saját artifact szinten.
- `./scripts/verify.sh` gate PASS.