# Codex Report — part_in_part_pipeline

**Status:** PASS

---

## 1) Meta

- **Task slug:** `part_in_part_pipeline`
- **Kapcsolodo canvas:** `canvases/nesting_engine/part_in_part_pipeline.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_part_in_part_pipeline.yaml`
- **Fokusz terulet:** `rust/nesting_engine` BLF cavity-aware pipeline (F3-2)

## 2) Scope

### 2.1 Cel

1. Opt-in part-in-part kapcsoló bevezetése (`--part-in-part off|auto`, default `off`).
2. BLF cavity-aware candidate generation implementálása determinisztikus hole-anchor stratégiával.
3. F3-2 off-grid fixture + CLI smoke bevezetése, és gate integráció.
4. Architecture + tolerance policy dokumentáció szinkron.

### 2.2 Nem-cel (explicit)

1. Hole-aware NFP/CFR implementáció.
2. Hybrid gating policy módosítása (`--placer nfp` holes/hole_collapsed esetre).
3. IO contract bővítése.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok

- `rust/nesting_engine/src/main.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `rust/nesting_engine/src/placement/blf.rs`
- `rust/nesting_engine/src/search/sa.rs`
- `poc/nesting_engine/f3_2_part_in_part_offgrid_fixture_v2.json`
- `scripts/smoke_part_in_part_pipeline.py`
- `scripts/check.sh`
- `docs/nesting_engine/architecture.md`
- `docs/nesting_engine/tolerance_policy.md`
- `codex/codex_checklist/nesting_engine/part_in_part_pipeline.md`
- `codex/reports/nesting_engine/part_in_part_pipeline.md`

### 3.2 Miert valtoztak?

- Az F3-2 scope a jelenlegi repóállapothoz igazítva BLF cavity-aware candidate generationre lett szűkítve.
- A default viselkedés változatlanul tartása miatt a feature explicit opt-in CLI kapcsolót kapott.
- Az off-grid cavity fixture bizonyítja, hogy az `auto` mód új elhelyezést talál, amit a baseline grid scan nem.

## 4) Verifikacio

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/part_in_part_pipeline.md` -> PASS

### 4.2 Task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml blf_part_in_part_` -> PASS
- `python3 scripts/smoke_part_in_part_pipeline.py --bin rust/nesting_engine/target/debug/nesting_engine --input poc/nesting_engine/f3_2_part_in_part_offgrid_fixture_v2.json` -> PASS

## 5) Fixture eredmeny (baseline vs auto)

- Fixture: `poc/nesting_engine/f3_2_part_in_part_offgrid_fixture_v2.json`
- Baseline (`--part-in-part off`): `sheets_used = 2`
- Auto (`--part-in-part auto`): `sheets_used = 1`
- Auto ismételt futás ugyanazzal a seed-del: `meta.determinism_hash` stabil

## 6) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek | Magyarazat | Ellenorzes |
|---|---|---|---|---|
| CLI flag `--part-in-part off|auto` elérhető, default `off` | PASS | `rust/nesting_engine/src/main.rs` | Új parser + enum mapping, default `Off`. | cargo test + verify |
| `Off` mellett baseline viselkedés változatlan | PASS | `rust/nesting_engine/src/placement/blf.rs` (`blf_part_in_part_off_mode_preserves_baseline`) | No-hole inputon `Off` és `Auto` kimenet azonos. | `cargo test ... blf_part_in_part_` |
| `Auto` módban cavity-aware jelöltgenerálás fut | PASS | `rust/nesting_engine/src/placement/blf.rs` (`collect_cavity_candidates`, `hole_anchor_points`) | Hole-anchor alapú jelöltek BLF scan előtt futnak. | `cargo test ... blf_part_in_part_` |
| Outer-only / `hole_collapsed`-like source nem cavity forrás | PASS | `rust/nesting_engine/src/placement/blf.rs` (`blf_part_in_part_hole_collapsed_like_outer_only_source_is_ignored`) | `holes=[]` mellett nincs cavity előny, viselkedés megegyezik. | `cargo test ... blf_part_in_part_` |
| F3-2 off-grid fixture létrejött és különbséget ad | PASS | `poc/nesting_engine/f3_2_part_in_part_offgrid_fixture_v2.json` | Tudatosan off-grid hole anchorok. | smoke script |
| Smoke script baseline vs auto assert + auto hash stabilitás | PASS | `scripts/smoke_part_in_part_pipeline.py` | `off=2`, `auto=1`, auto hash stabil ismételt futáson. | python smoke |
| check gate integráció megtörtént | PASS | `scripts/check.sh` | Targeted unit test + új smoke a nesting_engine blokkban. | `./scripts/verify.sh ...` |
| Architecture + tolerance doksi szinkron | PASS | `docs/nesting_engine/architecture.md`, `docs/nesting_engine/tolerance_policy.md` | F3-2 scope, CLI jelentés, cavity-source policy dokumentálva. | docs review |
| Kötelező verify futás PASS | PASS | `codex/reports/nesting_engine/part_in_part_pipeline.verify.log` | AUTO_VERIFY blokk automatikusan frissül. | `./scripts/verify.sh ...` |

## 7) Advisory notes

- Az F3-2 kör továbbra is BLF-layer bővítés; hole-aware NFP/CFR külön backlog tétel marad.
- `auto` mód cavity-próbálás után mindig visszaesik a meglévő globális BLF scanre, így backward compatibility megmarad.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-08T00:15:13+01:00 → 2026-03-08T00:18:18+01:00 (185s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/part_in_part_pipeline.verify.log`
- git: `main@da9c39c`
- módosított fájlok (git status): 15

**git diff --stat**

```text
 docs/nesting_engine/architecture.md         |  24 +-
 docs/nesting_engine/tolerance_policy.md     |  23 +-
 rust/nesting_engine/src/main.rs             |  41 ++-
 rust/nesting_engine/src/multi_bin/greedy.rs |  19 +-
 rust/nesting_engine/src/placement/blf.rs    | 413 +++++++++++++++++++++++++++-
 rust/nesting_engine/src/search/sa.rs        |  68 ++++-
 scripts/check.sh                            |   9 +
 7 files changed, 571 insertions(+), 26 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/nesting_engine/architecture.md
 M docs/nesting_engine/tolerance_policy.md
 M rust/nesting_engine/src/main.rs
 M rust/nesting_engine/src/multi_bin/greedy.rs
 M rust/nesting_engine/src/placement/blf.rs
 M rust/nesting_engine/src/search/sa.rs
 M scripts/check.sh
?? canvases/nesting_engine/part_in_part_pipeline.md
?? codex/codex_checklist/nesting_engine/part_in_part_pipeline.md
?? codex/goals/canvases/nesting_engine/fill_canvas_part_in_part_pipeline.yaml
?? codex/prompts/nesting_engine/part_in_part_pipeline/
?? codex/reports/nesting_engine/part_in_part_pipeline.md
?? codex/reports/nesting_engine/part_in_part_pipeline.verify.log
?? poc/nesting_engine/f3_2_part_in_part_offgrid_fixture_v2.json
?? scripts/smoke_part_in_part_pipeline.py
```

<!-- AUTO_VERIFY_END -->
