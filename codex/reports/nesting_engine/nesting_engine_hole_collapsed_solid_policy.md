# Codex Report — nesting_engine_hole_collapsed_solid_policy

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `nesting_engine_hole_collapsed_solid_policy`
- **Kapcsolódó canvas:** `canvases/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_hole_collapsed_solid_policy.yaml`
- **Futás dátuma:** 2026-02-27
- **Branch / commit:** `main` / `e3fa4d1` (uncommitted changes)
- **Fókusz terület:** Mixed (Geometry + Nest Entrypoint + Docs)

## 2) Scope

### 2.1 Cél

1. HOLE_COLLAPSED policy invariáns kényszerítése a pipeline detect és hard fallback ágában is (`holes=[]`, outer-only envelope).
2. Defense-in-depth a `run_nest` belépési ponton: `hole_collapsed` státusznál a placer mindig holes nélküli polygon-t kapjon.
3. Új unit teszt hozzáadása a detect-path regresszió lefedésére.
4. `docs/nesting_engine/tolerance_policy.md` szinkronizálása a valós kódpolitikával.

### 2.2 Nem-cél (explicit)

1. IO contract struktúra módosítása.
2. Offset algoritmus (clipper/i_overlay) átírása.
3. Known issues registry státuszainak kötelező frissítése (opcionális scope elem).

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- `canvases/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md`
- `rust/nesting_engine/src/geometry/pipeline.rs`
- `rust/nesting_engine/src/main.rs`
- `docs/nesting_engine/tolerance_policy.md`
- `codex/codex_checklist/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md`
- `codex/reports/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md`

### 3.2 Miért változtak?

- **Geometry:** a detect-path `hole_collapsed` státusz mellett is outer-only fallbackra vált, így a nesting holes mező mindig üres.
- **Entrypoint:** explicit guard került a placer inputra, hogy regresszió esetén se mehessen be hole-os polygon `hole_collapsed` státusszal.
- **Docs:** a tolerance policy most a tényleges enum/pipeline viselkedést írja le.
- **Codex artefaktok:** checklist/report létrehozva a feladathoz.

## 4) Verifikáció

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md` -> PASS

### 4.2 Opcionális, task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml hole_collapsed_detect_path_forces_outer_only_nesting_geometry` -> PASS

### 4.3 Ha valami kimaradt

- Nincs kimaradt kötelező ellenőrzés.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| `pipeline.rs`: HOLE_COLLAPSED esetén mindig `inflated_holes_points_mm == []` (hard + detect ág) | PASS | `rust/nesting_engine/src/geometry/pipeline.rs:66`, `rust/nesting_engine/src/geometry/pipeline.rs:251`, `rust/nesting_engine/src/geometry/pipeline.rs:280` | A detect ág collapse találatnál közös outer-only helperre tér át, amely minden sikeres HOLE_COLLAPSED kimenetnél `holes=[]`-t ad. | `cargo test ... hole_collapsed_detect_path_forces_outer_only_nesting_geometry` |
| `pipeline.rs`: HOLE_COLLAPSED esetén outer-only envelope nem üres | PASS | `rust/nesting_engine/src/geometry/pipeline.rs:279`, `rust/nesting_engine/src/geometry/pipeline.rs:586` | A helper `inflate_outer` eredményét adja vissza outer-only poligonként, és a detect-path teszt explicit nem üres outert assertel. | `cargo test ... hole_collapsed_detect_path_forces_outer_only_nesting_geometry` |
| `pipeline.rs`: HOLE_COLLAPSED diagnosztika `preserve_for_export=true`, `usable_for_nesting=false` | PASS | `rust/nesting_engine/src/geometry/pipeline.rs:336`, `rust/nesting_engine/src/geometry/pipeline.rs:595` | A HOLE_COLLAPSED diagnosztika mezői változatlanul policy-kompatibilisek, a teszt minden ilyen diagnosztikára ellenőrzi a két flaget. | `cargo test ... hole_collapsed_detect_path_forces_outer_only_nesting_geometry` |
| `main.rs`: HOLE_COLLAPSED státusznál placer felé `holes == []` | PASS | `rust/nesting_engine/src/main.rs:143`, `rust/nesting_engine/src/main.rs:146`, `rust/nesting_engine/src/main.rs:170` | A `run_nest` hole_collapsed státusznál explicit `Vec::new()` holes-t épít, így a placer kényszerítetten solidként kapja a partot. | code review |
| Új unit teszt lefedi a detect-path HOLE_COLLAPSED esetet és passzol | PASS | `rust/nesting_engine/src/geometry/pipeline.rs:553` | Új teszt setupja explicit biztosítja a detect ágat (`inflate_part` ok + `detect_collapsed_holes` találat), majd a pipeline kimenet outer-only invariánsait ellenőrzi. | `cargo test ... hole_collapsed_detect_path_forces_outer_only_nesting_geometry` |
| `tolerance_policy.md` frissítve a valós policy-hez | PASS | `docs/nesting_engine/tolerance_policy.md:110`, `docs/nesting_engine/tolerance_policy.md:119`, `docs/nesting_engine/tolerance_policy.md:131` | A dokumentum már nem ír fatális HOLE_COLLAPSED viselkedést; outer-only fallback + diagnosztikai policy szerepel, és a self-intersection kezelést is pontosítja. | docs review |
| Repo gate lefut (`./scripts/verify.sh --report ...`) | PASS | `codex/reports/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md` (AUTO_VERIFY blokk) | A kötelező verify wrapper futott, `check.sh` exit kód 0, log mentve. | `./scripts/verify.sh --report ...` |
| Report + checklist kitöltve | PASS | `codex/codex_checklist/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md`, `codex/reports/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md` | A taskhoz tartozó checklist és report véglegesítve lett a verify PASS után. | docs review |

## 8) Advisory notes

- A `docs/known_issues/nesting_engine_known_issues.md` opcionális státuszfrissítése ebben a futásban nem történt meg.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-27T21:19:03+01:00 → 2026-02-27T21:22:48+01:00 (225s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nesting_engine_hole_collapsed_solid_policy.verify.log`
- git: `main@e3fa4d1`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 docs/nesting_engine/tolerance_policy.md      |  28 +++++--
 rust/nesting_engine/src/geometry/pipeline.rs | 106 +++++++++++++++++++++++----
 rust/nesting_engine/src/main.rs              |  26 ++++---
 3 files changed, 128 insertions(+), 32 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/nesting_engine/tolerance_policy.md
 M rust/nesting_engine/src/geometry/pipeline.rs
 M rust/nesting_engine/src/main.rs
?? canvases/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md
?? codex/codex_checklist/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md
?? codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_hole_collapsed_solid_policy.yaml
?? codex/prompts/nesting_engine/nesting_engine_hole_collapsed_solid_policy/
?? codex/reports/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md
?? codex/reports/nesting_engine/nesting_engine_hole_collapsed_solid_policy.verify.log
?? docs/nesting_engine/f2_3_nfp_placer_spec.md
```

<!-- AUTO_VERIFY_END -->
