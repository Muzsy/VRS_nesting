# Codex Report — nesting_engine_spacing_margin_bin_offset_model

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `nesting_engine_spacing_margin_bin_offset_model`
- **Kapcsolodo canvas:** `canvases/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_spacing_margin_bin_offset_model.yaml`
- **Futas datuma:** 2026-02-27
- **Branch / commit:** `main` / `9ca4b15` (implementacio kozben, uncommitted)
- **Fokusz terulet:** Mixed

## 2) Scope

### 2.1 Cel

1. A spacing/margin clearance modell atallitasa az uj kanonra (`inflate_delta=spacing/2`, `bin_offset=spacing/2-margin`).
2. `pipeline_v1` es `nesting_engine_v2` spacing mezo bovitese legacy fallbackkal.
3. Rust stock preprocess szetvalasztasa: outer `bin_offset`, hole/defect `inflate_delta`.
4. Python stock fallback modell szinkronizalasa ugyanarra a clearance kanonra.
5. Doksi + POC mintak frissitese az uj offset szabalyokkal.

### 2.2 Nem-cel (explicit)

1. NFP placer vagy F2-3 placement engine teljes implementacioja.
2. Determinizmus hash/canonicalization szabalyrendszer modositas.
3. `scripts/validate_nesting_solution.py` spacing-ellenorzesse bovitese.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok

- `docs/dxf_nesting_app_4_spacing_margin_implementacio_offsettel_reszletes.md`
- `docs/nesting_engine/io_contract_v2.md`
- `poc/nesting_engine/sample_input_v2.json`
- `poc/nesting_engine/pipeline_smoke_input.json`
- `poc/nesting_engine/pipeline_smoke_expected.json`
- `rust/nesting_engine/src/io/pipeline_io.rs`
- `rust/nesting_engine/src/geometry/pipeline.rs`
- `rust/nesting_engine/src/main.rs`
- `vrs_nesting/geometry/offset.py`
- `tests/test_geometry_offset.py`
- `codex/codex_checklist/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md`
- `codex/reports/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md`

### 3.2 Miert valtoztak?

- A regi modell (`margin + kerf/2`) osszemosta a spacing/margin szerepeket, es nem fedte a `margin < spacing/2` esetet.
- Az uj kanon explicit separationt kovetel part inflate, stock outer offset es hole/defect obstacle inflate kozott.
- A contract + POC frissites kellett a backward kompatibilitas melletti uj `spacing_mm` szemantika egyertelmusitesehez.

## 4) Verifikacio

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md` -> PASS

### 4.2 Opcionális, task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` -> PASS
- `python3 -m pytest -q tests/test_geometry_offset.py` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt |
|---|---|---|---|---|
| `pipeline_v1` optional `spacing_mm`, fallback `kerf_mm` | PASS | `rust/nesting_engine/src/io/pipeline_io.rs:4`, `rust/nesting_engine/src/geometry/pipeline.rs:26` | A request schema optional spacing mezot kapott, es a pipeline effektive spacing fallbackot szamol. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` |
| Part inflate csak `inflate_delta=spacing/2` | PASS | `rust/nesting_engine/src/geometry/pipeline.rs:27`, `rust/nesting_engine/src/geometry/pipeline.rs:34`, `rust/nesting_engine/src/geometry/pipeline.rs:49` | A part agban az inflate delta mar kizaroalagosan spacing-bol jon, margin nem resze. | `rust/nesting_engine/src/geometry/pipeline.rs:551` |
| Stock outer `bin_offset=spacing/2-margin` (pozitiv is) | PASS | `rust/nesting_engine/src/geometry/pipeline.rs:29`, `rust/nesting_engine/src/geometry/pipeline.rs:127`, `rust/nesting_engine/src/geometry/pipeline.rs:182` | Stock outer offset kulon `bin_offset` szerint fut, negativ/pozitiv tartomanyban is. | `rust/nesting_engine/src/geometry/pipeline.rs:801` |
| Stock hole/defect `inflate_delta=spacing/2` margin nelkul | PASS | `rust/nesting_engine/src/geometry/pipeline.rs:202`, `rust/nesting_engine/src/geometry/pipeline.rs:267`, `rust/nesting_engine/src/geometry/pipeline.rs:842` | Hole akadaly kulon helperrel spacing alapjan tagul, margin komponens nelkul. | `rust/nesting_engine/src/geometry/pipeline.rs:842` |
| `nesting_engine_v2` optional `sheet.spacing_mm` + fallback | PASS | `rust/nesting_engine/src/main.rs:86`, `rust/nesting_engine/src/main.rs:118`, `rust/nesting_engine/src/main.rs:279` | `NestSheet` optional spacing mezot kapott; effective spacing fallback kerf-re. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` |
| `nest` rect-bin `bin_offset` + clamp + `margin < spacing/2` teszt | PASS | `rust/nesting_engine/src/main.rs:202`, `rust/nesting_engine/src/main.rs:290`, `rust/nesting_engine/src/main.rs:320` | Rect bin bounds a `bin_offset` szerint szamolodik, invertalodas eseten determinisztikus clamp. | `rust/nesting_engine/src/main.rs:320` |
| Python shapely fallback uj stock modell | PASS | `vrs_nesting/geometry/offset.py:388`, `vrs_nesting/geometry/offset.py:394`, `vrs_nesting/geometry/offset.py:416` | Shapely stock fallback outer-only `bin_offset`-ot es hole `inflate_delta`-t hasznal. | `tests/test_geometry_offset.py:207` |
| Python rust request explicit `spacing_mm` mezot kuld | PASS | `vrs_nesting/geometry/offset.py:339`, `vrs_nesting/geometry/offset.py:369`, `tests/test_geometry_offset.py:16` | Rust pipeline requestben a spacing kulon mezo is megjelenik (kerf legacy mellett). | `python3 -m pytest -q tests/test_geometry_offset.py` |
| Doksi + POC sync az uj kanonra | PASS | `docs/nesting_engine/io_contract_v2.md:22`, `docs/dxf_nesting_app_4_spacing_margin_implementacio_offsettel_reszletes.md:27`, `poc/nesting_engine/sample_input_v2.json:5` | Az io contract, implementacios doksi es mintak explicit uj spacing/bin_offset modelre valtottak. | N/A |
| Repo gate wrapperrel lefut | PASS | `codex/reports/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.verify.log` | A `verify.sh` lefutott, es az AUTO_VERIFY blokk PASS-ra frissult. | `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md` |

## 8) Advisory notes

- A `docs/dxf_nesting_app_4_...` fajl tovabbra is MVP jellegu vegyes nyelvu dokumentum, a kanon frissites megtortent, de stilisztikai homogenizacio kesobbre maradhat.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-27T23:22:20+01:00 → 2026-02-27T23:25:40+01:00 (200s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.verify.log`
- git: `main@9ca4b15`
- módosított fájlok (git status): 17

**git diff --stat**

```text
 ...ing_margin_implementacio_offsettel_reszletes.md |  42 ++--
 docs/nesting_engine/io_contract_v2.md              |  15 +-
 poc/nesting_engine/pipeline_smoke_expected.json    |   6 +-
 poc/nesting_engine/pipeline_smoke_input.json       |   1 +
 poc/nesting_engine/sample_input_v2.json            |   3 +-
 rust/nesting_engine/src/geometry/pipeline.rs       | 262 ++++++++++++++++-----
 rust/nesting_engine/src/io/pipeline_io.rs          |   2 +
 rust/nesting_engine/src/main.rs                    |  64 ++++-
 tests/test_geometry_offset.py                      |  33 +++
 vrs_nesting/geometry/offset.py                     |  15 +-
 10 files changed, 350 insertions(+), 93 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/dxf_nesting_app_4_spacing_margin_implementacio_offsettel_reszletes.md
 M docs/nesting_engine/io_contract_v2.md
 M poc/nesting_engine/pipeline_smoke_expected.json
 M poc/nesting_engine/pipeline_smoke_input.json
 M poc/nesting_engine/sample_input_v2.json
 M rust/nesting_engine/src/geometry/pipeline.rs
 M rust/nesting_engine/src/io/pipeline_io.rs
 M rust/nesting_engine/src/main.rs
 M tests/test_geometry_offset.py
 M vrs_nesting/geometry/offset.py
?? canvases/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md
?? codex/codex_checklist/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md
?? codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_spacing_margin_bin_offset_model.yaml
?? codex/prompts/nesting_engine/nesting_engine_spacing_margin_bin_offset_model/
?? codex/reports/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md
?? codex/reports/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.verify.log
?? project_log.md
```

<!-- AUTO_VERIFY_END -->
