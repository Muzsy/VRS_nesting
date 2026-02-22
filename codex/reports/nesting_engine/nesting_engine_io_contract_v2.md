# Codex Report - nesting_engine_io_contract_v2

**Status:** PASS

---

## 1) Meta

- **Task slug:** `nesting_engine_io_contract_v2`
- **Kapcsolodo canvas:** `canvases/nesting_engine/nesting_engine_io_contract_v2.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_io_contract_v2.yaml`
- **Futas datuma:** 2026-02-22
- **Branch / commit:** `main / e4ceec8`
- **Fokusz terulet:** Docs | IO Contract | POC

## 2) Scope

### 2.1 Cel

- IO contract v2 dokumentacio letrehozasa (`docs/nesting_engine/io_contract_v2.md`)
- Minta input JSON letrehozasa (`poc/nesting_engine/sample_input_v2.json`)
- Minta output JSON letrehozasa (`poc/nesting_engine/sample_output_v2.json`)
- Checklist es report artefaktok kitoltese verify-integracioval

### 2.2 Nem-cel

- Rust nesting motor implementalasa
- Python runner implementalasa
- v1 contract (`docs/solver_io_contract.md`) modositasa
- Backward kompatibilitas biztositasa v1 iranyba

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok

- **Docs:**
  - `docs/nesting_engine/io_contract_v2.md`
- **POC JSON:**
  - `poc/nesting_engine/sample_input_v2.json`
  - `poc/nesting_engine/sample_output_v2.json`
- **Codex artefaktok:**
  - `codex/codex_checklist/nesting_engine/nesting_engine_io_contract_v2.md`
  - `codex/reports/nesting_engine/nesting_engine_io_contract_v2.md`
  - `codex/reports/nesting_engine/nesting_engine_io_contract_v2.verify.log`

### 3.2 Miert valtoztak?

- Az uj `nesting_engine_v2` JSON boundary egyertelmu, mezoszintu dokumentaciot kapott.
- A ket POC JSON a fejlesztoi es teszteloi oldalon referencia input/output formatumot ad.
- A checklist/report biztosítja a standard audit trailt es verify-integraciot.

## 4) Verifikacio

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_io_contract_v2.md` -> PASS

### 4.2 Opcionális, feladatfuggo parancsok

- `python3 -m json.tool poc/nesting_engine/sample_input_v2.json` -> PASS
- `python3 -m json.tool poc/nesting_engine/sample_output_v2.json` -> PASS
- `git diff docs/solver_io_contract.md` -> PASS (ures diff)

### 4.3 Ha valami kimaradt

- Nem maradt ki kotelezo ellenorzes.

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-22T11:32:35+01:00 → 2026-02-22T11:34:36+01:00 (121s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nesting_engine_io_contract_v2.verify.log`
- git: `main@e4ceec8`
- módosított fájlok (git status): 5

**git status --porcelain (preview)**

```text
?? codex/codex_checklist/nesting_engine/nesting_engine_io_contract_v2.md
?? codex/reports/nesting_engine/nesting_engine_io_contract_v2.md
?? codex/reports/nesting_engine/nesting_engine_io_contract_v2.verify.log
?? docs/nesting_engine/io_contract_v2.md
?? poc/nesting_engine/
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
|---|---|---|---|---|
| #1 Input JSON valid | PASS | `poc/nesting_engine/sample_input_v2.json:1` | A minta input JSON szintaktikailag valid. | `python3 -m json.tool poc/nesting_engine/sample_input_v2.json` |
| #2 Output JSON valid | PASS | `poc/nesting_engine/sample_output_v2.json:1` | A minta output JSON szintaktikailag valid. | `python3 -m json.tool poc/nesting_engine/sample_output_v2.json` |
| #3 v1 contract valtozatlan | PASS | `docs/solver_io_contract.md:1` | A `git diff docs/solver_io_contract.md` parancs ures kimenetet adott. | `git diff docs/solver_io_contract.md` |
| #4 `io_contract_v2.md` tartalom teljes | PASS | `docs/nesting_engine/io_contract_v2.md:10`, `docs/nesting_engine/io_contract_v2.md:36`, `docs/nesting_engine/io_contract_v2.md:64`, `docs/nesting_engine/io_contract_v2.md:76`, `docs/nesting_engine/io_contract_v2.md:83`, `docs/nesting_engine/io_contract_v2.md:91` | Dokumentalt input schema, output schema, geometria egyezmenyek, reason kodok, determinism_hash normativ hivatkozas es v1<->v2 tablazat. | Dokumentacio review |
| #5 verify.sh PASS | PASS | `codex/reports/nesting_engine/nesting_engine_io_contract_v2.verify.log:1` | A standard repo gate teljes futasa sikeres (`check.sh` exit kod 0). | `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_io_contract_v2.md` |

## 6) IO contract / mintak

- `poc/nesting_engine/sample_input_v2.json`: 3 part-tipus (teglalap, konkav L, lyukas ring), explicit mm mezokkel.
- `poc/nesting_engine/sample_output_v2.json`: illusztracios partial output, `unplaced.reason` kodokkal.

## 7) Doksi szinkron

- Uj dokumentacio: `docs/nesting_engine/io_contract_v2.md`.
- Normativ hivatkozas: `docs/nesting_engine/json_canonicalization.md`.

## 8) Advisory notes

- A sample output illusztracios, a tenyleges solver viselkedest az F1-4 implementacio fogja konkretizalni.

## 9) Follow-ups

- F1-4: runner + solver integracio utan a sample output es hash mezok veglegesitese.
