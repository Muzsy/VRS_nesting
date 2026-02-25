# Codex Report — nfp_real_dxf_pairs_proof

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `nfp_real_dxf_pairs_proof`
- **Kapcsolódó canvas:** `canvases/nesting_engine/nfp_real_dxf_pairs_proof.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_real_dxf_pairs_proof.yaml`
- **Futás dátuma:** 2026-02-25
- **Branch / commit:** `main` / `58cc26d` (uncommitted changes)
- **Fókusz terület:** Geometry

## 2) Scope

### 2.1 Cél

1. Három valós DXF párhoz (`stock x part`, `part x stock`, `part x part`) determinisztikus, canonical i64 fixture létrehozása.
2. A fixture-ekhez golden `expected_nfp` és `expected_vertex_count` rögzítése futtatható Rust helperrel.
3. Olyan smoke bevezetése, ami egyszerre bizonyítja a DXF->fixture kötést és a computed NFP == expected egyezést.
4. A smoke bekötése a repo quality gate-be (`scripts/check.sh`), hogy `verify.sh` is lefedje.

### 2.2 Nem-cél (explicit)

1. F2-2 core concave algoritmus módosítása.
2. Holes-os NFP támogatás bevezetése.
3. `scripts/verify.sh` wrapper módosítása.
4. `rust/vrs_solver/**` módosítása.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- **Scripts:**
  - `scripts/export_real_dxf_nfp_pairs.py`
  - `scripts/smoke_real_dxf_nfp_pairs.py`
  - `scripts/check.sh`
- **Rust:**
  - `rust/nesting_engine/src/bin/nfp_fixture.rs`
- **Fixtures:**
  - `poc/nfp_regression/real_dxf_pair_01_stock_x_part.json`
  - `poc/nfp_regression/real_dxf_pair_02_part_x_stock.json`
  - `poc/nfp_regression/real_dxf_pair_03_part_x_part.json`
- **Codex artefaktok:**
  - `canvases/nesting_engine/nfp_real_dxf_pairs_proof.md`
  - `codex/codex_checklist/nesting_engine/nfp_real_dxf_pairs_proof.md`
  - `codex/reports/nesting_engine/nfp_real_dxf_pairs_proof.md`

### 3.2 Miért változtak?

- Az export script determinisztikus DXF->canonical i64 ring konverziót ad, és létrehozza a 3 required fixture-vázat.
- Az `nfp_fixture` bináris reprodukálható módon számítja a fixture-alapú NFP-t, kanonizált ringgel és vertex counttal.
- Az új real-DXF smoke objektíven ellenőrzi a DXF eredetet (ring egyezés), a hole evidence-et és a golden NFP egyezést.
- A `check.sh` gate-be kötés biztosítja, hogy a proof a standard repo kapu részeként is fusson.

## 4) Verifikáció

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_real_dxf_pairs_proof.md` -> PASS (lásd AUTO_VERIFY blokk).

### 4.2 Opcionális, task-specifikus parancsok

- `python3 scripts/smoke_real_dxf_nfp_pairs.py` -> PASS (`[OK] real DXF NFP pairs smoke passed`).
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` -> PASS.

### 4.3 Ha valami kimaradt

- Nincs kimaradt kötelező ellenőrzés.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| 3 fixture létrejött a `poc/nfp_regression` alatt | PASS | `scripts/export_real_dxf_nfp_pairs.py:126`, `scripts/export_real_dxf_nfp_pairs.py:153`, `poc/nfp_regression/real_dxf_pair_01_stock_x_part.json:1`, `poc/nfp_regression/real_dxf_pair_02_part_x_stock.json:1`, `poc/nfp_regression/real_dxf_pair_03_part_x_part.json:1` | Az export script explicit 3 célfájlt állít elő, a fixture fájlok jelen vannak a regressziós könyvtárban. | `python3 scripts/export_real_dxf_nfp_pairs.py` |
| DXF->fixture canonical ring egyezés bizonyított | PASS | `scripts/smoke_real_dxf_nfp_pairs.py:159`, `scripts/smoke_real_dxf_nfp_pairs.py:169`, `scripts/smoke_real_dxf_nfp_pairs.py:184` | A smoke ugyanazon import útvonalon (`build_sparrow_inputs`) építi a ringet, majd pairenként összeveti a fixture `polygon_a/polygon_b` mezőkkel. | `python3 scripts/smoke_real_dxf_nfp_pairs.py` |
| Part DXF hole evidence ellenőrzött | PASS | `scripts/smoke_real_dxf_nfp_pairs.py:172` | A smoke kötelezően validálja, hogy a part importból legalább egy hole jelenik meg (`holes_points`). | `python3 scripts/smoke_real_dxf_nfp_pairs.py` |
| Golden expected (`expected_nfp`, `expected_vertex_count`) kitöltve | PASS | `rust/nesting_engine/src/bin/nfp_fixture.rs:54`, `rust/nesting_engine/src/bin/nfp_fixture.rs:70`, `poc/nfp_regression/real_dxf_pair_01_stock_x_part.json:101`, `poc/nfp_regression/real_dxf_pair_02_part_x_stock.json:101`, `poc/nfp_regression/real_dxf_pair_03_part_x_part.json:161` | A helper bin canonical NFP outputot ad; a 3 fixture expected mezői kitöltöttek és egyezésre ellenőrzöttek. | `python3 scripts/smoke_real_dxf_nfp_pairs.py` |
| Real DXF NFP smoke bekerült a quality gate-be | PASS | `scripts/check.sh:92`, `scripts/check.sh:150` | `check.sh` már chmodolja és futtatja a `smoke_real_dxf_nfp_pairs.py` scriptet. | `./scripts/check.sh` (verify részeként) |
| Kötelező verify wrapper futtatás | PASS | `codex/reports/nesting_engine/nfp_real_dxf_pairs_proof.md` (AUTO_VERIFY blokk) | A task végén a standard `verify.sh` futás PASS eredménnyel rögzül a reportban. | `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_real_dxf_pairs_proof.md` |

## 6) Real DXF párok

- Pair #01: `samples/dxf_demo/stock_rect_1000x2000.dxf` x `samples/dxf_demo/part_arc_spline_chaining_ok.dxf` -> `poc/nfp_regression/real_dxf_pair_01_stock_x_part.json`
- Pair #02: `samples/dxf_demo/part_arc_spline_chaining_ok.dxf` x `samples/dxf_demo/stock_rect_1000x2000.dxf` -> `poc/nfp_regression/real_dxf_pair_02_part_x_stock.json`
- Pair #03: `samples/dxf_demo/part_arc_spline_chaining_ok.dxf` x `samples/dxf_demo/part_arc_spline_chaining_ok.dxf` -> `poc/nfp_regression/real_dxf_pair_03_part_x_part.json`

## 8) Advisory notes

- A 3 valós DXF proof outer-only NFP-re ad bizonyítékot; holes-os NFP továbbra is külön feladat.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-25T21:39:58+01:00 → 2026-02-25T21:42:53+01:00 (175s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nfp_real_dxf_pairs_proof.verify.log`
- git: `main@58cc26d`
- módosított fájlok (git status): 13

**git diff --stat**

```text
 scripts/check.sh | 4 ++++
 1 file changed, 4 insertions(+)
```

**git status --porcelain (preview)**

```text
 M scripts/check.sh
?? canvases/nesting_engine/nfp_real_dxf_pairs_proof.md
?? codex/codex_checklist/nesting_engine/nfp_real_dxf_pairs_proof.md
?? codex/goals/canvases/nesting_engine/fill_canvas_nfp_real_dxf_pairs_proof.yaml
?? codex/prompts/nesting_engine/nfp_real_dxf_pairs_proof/
?? codex/reports/nesting_engine/nfp_real_dxf_pairs_proof.md
?? codex/reports/nesting_engine/nfp_real_dxf_pairs_proof.verify.log
?? poc/nfp_regression/real_dxf_pair_01_stock_x_part.json
?? poc/nfp_regression/real_dxf_pair_02_part_x_stock.json
?? poc/nfp_regression/real_dxf_pair_03_part_x_part.json
?? rust/nesting_engine/src/bin/
?? scripts/export_real_dxf_nfp_pairs.py
?? scripts/smoke_real_dxf_nfp_pairs.py
```

<!-- AUTO_VERIFY_END -->
