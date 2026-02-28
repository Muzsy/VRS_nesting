# Codex Report — cfr_canonicalize_and_sort_hardening

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `cfr_canonicalize_and_sort_hardening`
- **Kapcsolodo canvas:** `canvases/nesting_engine/cfr_canonicalize_and_sort_hardening.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_cfr_canonicalize_and_sort_hardening.yaml`
- **Futas datuma:** 2026-02-28
- **Branch / commit:** `main` / `820f4c6` (implementacio kozben, uncommitted)
- **Fokusz terulet:** Mixed

## 2) Scope

### 2.1 Cel

1. CFR kimenet ring-szintu kanonizalas hardeningje (dupe/collinear cleanup, orientacio, lex-min startpoint).
2. CFR komponens rendezes totalissa tetele `ring_hash` tie-breakkel.
3. Determinizmus regresszio unit tesztek hozzaadasa.
4. NFP gate smoke bovitese uj F4 noholes fixture-rel es 3x hash ellenorzessel.

### 2.2 Nem-cel (explicit)

1. NFP/IFP geometriai algoritmus alapjainak atirasa.
2. IO contract schema valtoztatas.
3. Placer ranking policy modositas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok

- `canvases/nesting_engine/cfr_canonicalize_and_sort_hardening.md`
- `rust/nesting_engine/src/nfp/cfr.rs`
- `poc/nesting_engine/f2_3_f4_cfr_order_hardening_noholes_v2.json`
- `scripts/check.sh`
- `codex/codex_checklist/nesting_engine/cfr_canonicalize_and_sort_hardening.md`
- `codex/reports/nesting_engine/cfr_canonicalize_and_sort_hardening.md`

### 3.2 Miert valtoztak?

- A CFR kanonizalas mar reszben megvolt, de a komponens sort nem volt teljesen totalis azonos `min_point/area/vertex_count` esetben.
- A `ring_hash` tie-break es a dedikalt unit tesztek bezarjak ezt a drift lehetoseget.
- Az uj F4 smoke coverage CI gate-ben megerositi a hash stabilitast NFP modban.

## 4) Verifikacio

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/cfr_canonicalize_and_sort_hardening.md` -> PASS

### 4.2 Opcionális, task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q nfp::cfr` -> PASS
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` -> PASS
- `bash -n scripts/check.sh` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
|---|---|---|---|---|
| CFR output komponensek minden ringje kanonizalt | PASS | `rust/nesting_engine/src/nfp/cfr.rs:134`, `rust/nesting_engine/src/nfp/cfr.rs:155` | `canonicalize_polygon64` es `canonicalize_ring` tisztit, orientaciot fixal, lex-min startpointra forgat. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q nfp::cfr` |
| 0-area / degeneralt komponensek eldobasa | PASS | `rust/nesting_engine/src/nfp/cfr.rs:55`, `rust/nesting_engine/src/nfp/cfr.rs:152` | A `compute_cfr` csak validalt komponenseket tart meg, a nem pozitiv komponens-terulet kiszuresre kerul. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` |
| Komponens sort totalis (`ring_hash` tie-break) | PASS | `rust/nesting_engine/src/nfp/cfr.rs:256`, `rust/nesting_engine/src/nfp/cfr.rs:272` | A sort kulcs `ring_hash_u64` tie-breakkel totalisra bovult. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q nfp::cfr` |
| Ring startpoint drift teszt | PASS | `rust/nesting_engine/src/nfp/cfr.rs:478` | Uj unit teszt: eltero startpoint ugyanarra a kanonikus ringre fut. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q nfp::cfr` |
| Ring orientacio drift teszt | PASS | `rust/nesting_engine/src/nfp/cfr.rs:499` | Uj unit teszt: CW/CCW variansok azonos kanonikus eredmenyt adnak. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q nfp::cfr` |
| Komponens-sorrend stabil permutalt NFP inputnal | PASS | `rust/nesting_engine/src/nfp/cfr.rs:519` | Uj unit teszt: `nfp_polys` permutacio mellett azonos CFR kimenet. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q nfp::cfr` |
| Uj F4 fixture + check.sh 3x determinism smoke | PASS | `poc/nesting_engine/f2_3_f4_cfr_order_hardening_noholes_v2.json:1`, `scripts/check.sh:462` | Uj noholes fixture es kulon F4 3x hash gate kerult a smoke szakaszba. | `./scripts/verify.sh --report codex/reports/nesting_engine/cfr_canonicalize_and_sort_hardening.md` |
| Gate PASS wrapperrel | PASS | `codex/reports/nesting_engine/cfr_canonicalize_and_sort_hardening.verify.log:1` | A wrapperes check teljesen lefutott, `check.sh` exit kod 0. | `./scripts/verify.sh --report codex/reports/nesting_engine/cfr_canonicalize_and_sort_hardening.md` |

## 8) Advisory notes

- A `ring_hash` csak vegso tie-break, a fo sort kulcs valtozatlan maradt (`min_point`, `abs(area)`, `vertex_count`).

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-28T18:13:38+01:00 → 2026-02-28T18:17:04+01:00 (206s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/cfr_canonicalize_and_sort_hardening.verify.log`
- git: `main@820f4c6`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 rust/nesting_engine/src/nfp/cfr.rs | 150 ++++++++++++++++++++++++++++++-------
 scripts/check.sh                   |  24 ++++++
 2 files changed, 147 insertions(+), 27 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/nesting_engine/src/nfp/cfr.rs
 M scripts/check.sh
?? canvases/nesting_engine/cfr_canonicalize_and_sort_hardening.md
?? codex/codex_checklist/nesting_engine/cfr_canonicalize_and_sort_hardening.md
?? codex/goals/canvases/nesting_engine/fill_canvas_cfr_canonicalize_and_sort_hardening.yaml
?? codex/prompts/nesting_engine/cfr_canonicalize_and_sort_hardening/
?? codex/reports/nesting_engine/cfr_canonicalize_and_sort_hardening.md
?? codex/reports/nesting_engine/cfr_canonicalize_and_sort_hardening.verify.log
?? poc/nesting_engine/f2_3_f4_cfr_order_hardening_noholes_v2.json
```

<!-- AUTO_VERIFY_END -->
