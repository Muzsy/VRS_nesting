# VRS Nesting Codex Task — NFP Nesting Engine: IO Contract v2 dokumentáció + példa JSON-ok
TASK_SLUG: nesting_engine_io_contract_v2

## 1) Kötelező olvasnivaló (prioritási sorrend)

Olvasd el és tartsd be, ebben a sorrendben:

1. `AGENTS.md` — repo-szabályok, gate parancsok
2. `docs/codex/overview.md` — workflow és DoD
3. `docs/codex/yaml_schema.md` — steps-séma kötelező
4. `docs/codex/report_standard.md` — report struktúra + AUTO_VERIFY blokk
5. `docs/nesting_engine/tolerance_policy.md` — CCW/CW irány, mm, scale policy (F1-1 output)
6. `docs/nesting_engine/json_canonicalization.md` — determinism_hash normatív kanonikalizáció (meglévő doksi)
7. `rust/nesting_engine/src/geometry/types.rs` — Point64, Polygon64, PartGeometry (F1-1 output)
8. `docs/solver_io_contract.md` — v1 contract (referencia, **NEM módosítjuk**)
9. `canvases/nesting_engine/nesting_engine_io_contract_v2.md` — feladat specifikációja
10. `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_io_contract_v2.yaml` — lépések

Ha bármelyik fájl nem létezik: állj meg, és írd le pontosan mit kerestél és hol.

---

## 2) Cél

Az NFP nesting motor JSON IO contract v2-jének teljes dokumentálása és példa
input/output JSON fájlok létrehozása. Ez az a szerződés, amit a Python runner
(F1-4 task) és a Rust motor között használunk — a fejlesztés egyetlen
source of truth-ja mindkét oldalon.

Deliverable-ök:
- `docs/nesting_engine/io_contract_v2.md` — minden mező, egység, invariáns
- `poc/nesting_engine/sample_input_v2.json` — valid JSON, 3 part típus
- `poc/nesting_engine/sample_output_v2.json` — valid JSON, illusztrációs értékek

## 3) Nem cél

- A Rust motor implementálása (F1-4 task)
- Python runner megírása (F1-4 task)
- `docs/solver_io_contract.md` (v1) bármilyen módosítása — ez **tiltott**
- Backward kompatibilitás a v1-gyel
- Valós DXF fájlok importálása (a poc JSON-ok kézzel összerakottak)

---

## 4) Fontos kontextus az F1-1 taskból

Az F1-1 során a `clipper2` crate helyett `i_overlay = "=4.4.0"` lett bevezetve
(pure Rust, jóváhagyott stratégiai döntés). Ez az IO contract szempontjából
**transzparens** — a JSON határfelület nem függ a belső geometriai könyvtártól.
Az input/output koordináták mm-alapú f64-ek, a belső SCALE konverzió (→ i64)
a motor belsejében történik, kívülről láthatatlan.

Szintén F1-1-ből: az `offset.rs` `inflate_part()` előtt `simplify_shape`
előfeldolgozást végez, és az outer CCW / holes CW kontúr-irányt explicit kezeli.
Ezek az egyezmények az io_contract_v2.md geometria-szekciójában dokumentálandók.

---

## 5) Munkaszabályok (nem alkuképes)

- **Valós repó elv:** nem találhatsz ki fájlokat, mezőket, parancsokat.
- **Outputs szabály:** csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel
  az adott YAML step `outputs` listájában.
- **v1 tiltás:** `docs/solver_io_contract.md` nem módosítható. A gate előtt
  ellenőrizd: `git diff docs/solver_io_contract.md` — üresnek kell lennie.
- **Gate csak wrapperrel:** ne rögtönözz párhuzamos check parancsokat.

---

## 6) Adminisztratív javítás (F1-1-ből áthúzódó)

Az F1-1 task során a `nesting_engine` build lépés a `scripts/check.sh`-ban a
`vrs_solver` lépés **elé** került, holott utána kellett volna. Ez funkcionálisan
nem okoz problémát, de ha ebben a taskban érintjük a `check.sh`-t, a sorrendet
korrigáld: a `nesting_engine` build lépés a `vrs_solver` build lépés **után**
szerepeljen.

Ha ebben a taskban nem érinted a `check.sh`-t (a YAML outputs listája alapján
nem szerepel benne), a korrekció az F1-3 vagy F1-4 taskra halasztható.

---

## 7) Végrehajtás

Hajtsd végre a YAML `steps` lépéseit **sorrendben**:

```
codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_io_contract_v2.yaml
```

---

## 8) Kötelező gate (a végén, egyszer)

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_io_contract_v2.md
```

A gate futtatása előtt ellenőrizd:
```bash
python3 -m json.tool poc/nesting_engine/sample_input_v2.json  > /dev/null && echo OK
python3 -m json.tool poc/nesting_engine/sample_output_v2.json > /dev/null && echo OK
git diff docs/solver_io_contract.md   # üres kell legyen
```

---

## 9) Elvárt kimenetek

**Új fájlok:**
- `docs/nesting_engine/io_contract_v2.md`
- `poc/nesting_engine/sample_input_v2.json`
- `poc/nesting_engine/sample_output_v2.json`
- `codex/codex_checklist/nesting_engine/nesting_engine_io_contract_v2.md`
- `codex/reports/nesting_engine/nesting_engine_io_contract_v2.md`
- `codex/reports/nesting_engine/nesting_engine_io_contract_v2.verify.log`

**Érintetlen (ellenőrizd):**
- `docs/solver_io_contract.md` — byte-azonos
- `rust/nesting_engine/` — egyetlen fájl sem változik
- `rust/vrs_solver/` — egyetlen fájl sem változik

---

## 10) Elfogadási kritériumok

1. `python3 -m json.tool poc/nesting_engine/sample_input_v2.json` — PASS (valid JSON)
2. `python3 -m json.tool poc/nesting_engine/sample_output_v2.json` — PASS (valid JSON)
3. `git diff docs/solver_io_contract.md` — üres (v1 nem változott)
4. `docs/nesting_engine/io_contract_v2.md` tartalmazza: input séma, output séma, geometria egyezmények, reason kódok, determinism_hash leírás **és normatív hivatkozás** a `docs/nesting_engine/json_canonicalization.md`-re, v1↔v2 táblázat
5. `./scripts/verify.sh` gate — PASS
