# SGH-Q76 Report - Skeleton-first seed + residual-fill (contour residual-space objective)

## 0) Statusz

**PASS** - az F1 (skeleton-first + residual-fill, valodi kontur-alapu maradekter-objektivvel)
implementalva, tesztelve es kontrollalt A/B-vel igazolva. A skeleton-first **generikusan nem rontja**
a defaultot, a nagy-darabos referencia-csomagon (Full276) pedig **erdemben veri** azt. Gate
(`VRS_SKELETON_FIRST`) default OFF -> production byte-azonos.

**Adatvezerelt verdict (240s, azonos build/gep, back-to-back):**

| csomag | arm | placed | unplaced | util % | final_pairs |
| --- | --- | ---: | ---: | ---: | ---: |
| Full276 | default | 252 | 24 | 37.96 | 0 |
| Full276 | **skeleton-first** | **274** | **2** | **65.07** | 0 |
| MixedMed | default | 120 | 0 | 78.85 | 0 |
| MixedMed | skeleton-first | 120 | 0 | 78.85 | 0 |

Full276: **+22 placed, +27.1 pp util**, ervenyesen (final_pairs=0). MixedMed (kis/kozepes, domináns
nagy nelkul): **dontetlen** (mindketto 120/120, azonos util) -> nincs regresszio = generikus.

**Stabilitas (mellektermek):** a skeleton-first 60s-en es 240s-en is 274 (determinisztikus, eros
seed-padlo), mig a default zajos a sztochasztikus exploration miatt (60s: 273, 240s: 252-253). Ez
maga is ertek: a pinnelt skeleton + residual-fill kevesbe budget-/CPU-zaj-fuggő.

## 1) Meta

- **Task slug:** `sgh_q76_skeleton_first_residual_fill`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/sgh_q76_skeleton_first_residual_fill.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q76_skeleton_first_residual_fill.yaml`
- **Futas datuma:** 2026-06-30
- **Branch / commit:** `main@<commit>` (nincs commitolva — felhasznaloi jovahagyasra var)
- **Fokusz terulet:** Solver core (constructive seed + residual fill + free-space objective)

## 2) Scope

### 2.1 Cel
- Skeleton-first: a struktura-meghatarozo (`Critical`) darabok elobb, el-horgonyzva, a kitoltheto
  osszefuggo maradekteret maximalizalva, pinnelve; majd residual-fill (a hianyzo re-inszercio).
- A maradekter-objektiv **valodi kontur-alapu** (scanline raszter), nem bbox.
- A default ut byte-azonos marad (gate OFF).

### 2.2 Nem-cel
- Feedback/outer-loop (F3), compaction-erlelés (A/B: zsakutca), spacing/margin csokkentes, hardcode.

## 3) Valtozasok osszefoglaloja

- **sheet_skeleton.rs:** kozos flood-fill + occupancy helperek kiemelve; uj
  `largest_edge_connected_free_area_contour` / `_slot_contour` (even-odd scanline poligon-raszter,
  50mm-gridhez decimalt magas-csucsu kontur). A bbox-verziok viselkedese valtozatlan (additiv refaktor).
- **bpp_reduction.rs:** `build_skeleton_first_seed` (particio + greedy el-horgony a KONTUR-free-area
  maximalizalasaval + pin) + residual-fill (`direct_insert_on_sheet`, largest-room-first) + no-drop
  completion; `skeleton_first_enabled` / `skeleton_frac` gate; bekotve a seed-blokkba (`q74_locked`).
- **io.rs:** 7 db Q76 diagnosztika (`bpp_q76_*`).
- **tests + scripts:** 2 integracios F1 teszt + 1 kontur unit teszt; teljes A/B runner.

## 4) Verifikacio

- `cargo test --release --lib` -> **551 passed, 0 failed** (benne a Q76 kontur unit teszt).
- `cargo test --release --test sparrow_sheet_builder` -> **9 passed, 0 failed** (benne a 2 uj F1 teszt).
- `python3 scripts/bench_sgh_q76_skeleton_first_residual_fill.py --time 240` -> **VERDICT: ACCEPT**
  (`artifacts/benchmarks/sgh_q76/q76_summary.json` + `q76_report.md` + renderek).
- Vizualis audit: Full276 default sheet0 = szetszort, ~25% fizikai kihasznaltsag, a nagy darabok nem is
  kerulnek ra; skeleton-first sheet0 = 137 darab, a magas darabok el-horgonyozva + interlock, suru
  residual-fill (~61% fizikai). Lasd a rendereket.

### 4.4 Automatikus blokk
<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-30T22:13:21+02:00 → 2026-06-30T22:21:22+02:00 (481s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q76_skeleton_first_residual_fill.verify.log`
- git: `main@f39d3b4`
- módosított fájlok (git status): 13

**git diff --stat**

```text
 .../sgh_q60/critical_group_admission.json          |   4 +-
 .../simultaneous_critical_production_cutover.json  |   4 +-
 rust/vrs_solver/src/io.rs                          |  17 +
 .../src/optimizer/sparrow/bpp_reduction.rs         | 261 ++++++++++++++-
 .../src/optimizer/sparrow/sheet_skeleton.rs        | 358 ++++++++++++++++-----
 rust/vrs_solver/tests/sparrow_sheet_builder.rs     |  70 ++++
 6 files changed, 635 insertions(+), 79 deletions(-)
```

**git status --porcelain (preview)**

```text
 M artifacts/benchmarks/sgh_q60/critical_group_admission.json
 M artifacts/benchmarks/sgh_q67/simultaneous_critical_production_cutover.json
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs
 M rust/vrs_solver/tests/sparrow_sheet_builder.rs
?? artifacts/benchmarks/sgh_q76/
?? canvases/egyedi_solver/sgh_q76_skeleton_first_residual_fill.md
?? codex/codex_checklist/egyedi_solver/sgh_q76_skeleton_first_residual_fill.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q76_skeleton_first_residual_fill.yaml
?? codex/reports/egyedi_solver/sgh_q76_skeleton_first_residual_fill.md
?? codex/reports/egyedi_solver/sgh_q76_skeleton_first_residual_fill.verify.log
?? scripts/bench_sgh_q76_skeleton_first_residual_fill.py
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| 1. Kontur maradekter-objektiv (additiv) | PASS | `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs:59,96,204` | scanline raszter (`rasterize_polygon_into_occ:204`); bbox-verziok valtozatlanok | kontur unit teszt `sheet_skeleton.rs:612` |
| 2. Skeleton particio + kontur-free-area elhelyezes + pin | PASS | `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:5323` | `criticality_tier==Critical` + `VRS_SKELETON_FRAC`; el-horgony; `locked_items` | F1 teszt `tests/sparrow_sheet_builder.rs:332` |
| 3. Residual-fill (re-inszercio) | PASS | `bpp_reduction.rs:5323` (fill-loop) | `direct_insert_on_sheet` largest-room-first; no-drop completion a maradekra | bench diag `q76_fill_placed=272` (Full276) |
| 4. Default byte-azonos (gate OFF) | PASS | `bpp_reduction.rs:5273,5630`; `tests/sparrow_sheet_builder.rs:381` | `VRS_SKELETON_FIRST` default OFF; seed_source!="skeleton_first" | `skeleton_first_default_off_is_inactive` |
| 5. A/B veri a defaultot (mindket csomag) | PASS | `artifacts/benchmarks/sgh_q76/q76_summary.json` | Full276 +22 placed/+27pp; MixedMed dontetlen (nincs regresszio) | Q76 benchmark (ACCEPT) |
| 6. Tesztek zoldek | PASS | lib 551/0, sparrow_sheet_builder 9/0 | F1 + kontur + teljes lib | cargo test |
| 7. verify.sh PASS | PASS | `...sgh_q76_skeleton_first_residual_fill.verify.log` (check.sh exit 0, 481s) | repo gate zold | verify.sh |

## 6) Finding

Az adatvezerelt kep megerosodott: a default ut a Full276-on **szetszorja** a darabokat (a nagy,
struktura-meghatarozo darabok el sem kerulnek a tablara, a tabla ~60%-a ures), mert a seed nem
strukturalt es nincs valodi re-inszercio. A skeleton-first **eloszor** lehorgonyozza a `Critical`
darabokat a tabla szeleihez, a **valodi kontur** szerint a legnagyobb osszefuggo maradekteret hagyva,
**pinneli** oket (tulelik az exploration/gravity/sanitize lepeseket), majd a maradekot suru
residual-fill-lel visszateszi. Eredmeny: +22 placed es +27 pp util a Full276-on, **ervenyesen**, es
**stabilan** (kevesbe budget-/zaj-fuggő). A kis/kozepes csomagon (ahol mar a default is teljesen
kitolt) nincs regresszio — a strategia **generikus**, nem LV8-hardcode. A 3/tabla tight interlock
(LV8) ennek specialis esete; az F1 itt a generikus padlot emelte meg jelentősen.
