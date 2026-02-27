# nesting_engine_hole_collapsed_solid_policy

## 🎯 Funkció

A HOLE_COLLAPSED policy véglegesítése és kódszintű invariánsok bevezetése:

- **Export/gyártási geometria**: a nominális (input) geometriát változatlanul megőrizzük exporthoz (a lyuk valós kontúrja megmarad).
- **Nesting geometriában** a HOLE_COLLAPSED esetén a lyuk **nem létezik**: nincs cavity/part-in-part lehetőség.
- **Offset alkalmazás** HOLE_COLLAPSED esetén a lyukakra nesting szempontból **nem történik** (mert nestinghez úgyis solidként kezeljük a partot).
- A part **továbbra is elhelyezhető** legyen: kell egy működő **nesting-envelope** (outer-only fallback).

Konkrét repó-policy:

Ha `status == "hole_collapsed"` (akár `inflate_part` HoleCollapsed Err ág, akár a `detect_collapsed_holes(...)` alapján):

- `inflated_holes_points_mm == []` **mindig**
- `inflated_outer_points_mm` **nem üres** (outer-only envelope inflálva)
- `diagnostics` tartalmaz HOLE_COLLAPSED elemet:
  - `preserve_for_export=true`
  - `usable_for_nesting=false`

## 🧠 Fejlesztési részletek

### Kontextus (miért kell)
A `rust/nesting_engine/src/geometry/pipeline.rs` már tartalmaz outer-only fallbackot (`handle_hole_collapsed`),
ami üres holes-t ad vissza. Viszont az `Ok(inflated)` ágban a `detect_collapsed_holes(...)` beállíthat
`status=hole_collapsed`-et úgy, hogy közben **még visszaad inflated hole-okat**. Ez félreérthető és lehetővé
teszi, hogy valaki “cavityként” használja a lyukat.

### Felderítés snapshot (2026-02-27)
- `pipeline.rs`: az `Ok(inflated)` + `detect_collapsed_holes(...)` útvonalon a státusz lehet `hole_collapsed`,
  miközben `inflated_holes_points_mm` nem garantáltan üres.
- `main.rs`: a `run_nest` jelenleg minden esetben a `resp.inflated_holes_points_mm` alapján épít placer-polygon holes-t,
  ezért defense-in-depth hiányzik `hole_collapsed` státuszra.
- `tolerance_policy.md`: jelenleg fatális OffsetError kezelést ír a HOLE_COLLAPSED esetre, ami eltér a tényleges
  pipeline-viselkedéstől (outer-only fallback + diagnosztika).

### Elvárt viselkedés (kód szinten)
1) **Pipeline invariáns:**
   - `inflate_single_part` esetén, ha `has_hole_collapse == true` és a status HOLE_COLLAPSED:
     - a nesting-geometry outer-only legyen (holes=[]),
     - és `inflated_holes_points_mm` legyen üres.
   - Ajánlott megoldás: a detect path is ugyanazt a logikát használja, mint a hard fallback:
     - outer-only polygon → `inflate_outer(...)`
     - holes=[]

2) **Defense-in-depth a nest entrypointban:**
   - `rust/nesting_engine/src/main.rs` amikor `resp.status == "hole_collapsed"`,
     akkor **ignorálja** a `resp.inflated_holes_points_mm` mezőt és `holes: Vec::new()`-t ad a placernek.

3) **Teszt:**
   - `pipeline.rs` unit teszt, ami a “detect path” esetet lefedi:
     - olyan part, ahol `detect_collapsed_holes(...)` talál collapse-t,
     - de az inflate pipeline ettől még ad vissza outer-t,
     - elvárt: `status == hole_collapsed` ⇒ `inflated_holes_points_mm.is_empty()`.

4) **Doksi szinkron:**
   - `docs/nesting_engine/tolerance_policy.md` jelenleg fatal-ként írja le a HoleCollapsed-et.
     Ezt a valós policy-hez kell igazítani:
     - HOLE_COLLAPSED → diagnosztika + outer-only fallback (nesting mehet tovább, de cavity tiltott)
     - SELF_INTERSECT maradhat fatal pipeline reject (ahogy a repó policy kívánja).

### Érintett fájlok
- Kód:
  - `rust/nesting_engine/src/geometry/pipeline.rs`
  - `rust/nesting_engine/src/main.rs`
- Doksik:
  - `docs/nesting_engine/tolerance_policy.md`
  - (opcionális) `docs/known_issues/nesting_engine_known_issues.md` (KI-004/KI-010 státusz frissítés)
- Codex artefaktok:
  - `codex/codex_checklist/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md`
  - `codex/reports/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md`
  - `codex/reports/nesting_engine/nesting_engine_hole_collapsed_solid_policy.verify.log`

## 🧪 Tesztállapot

### DoD (Definition of Done)
- [ ] `pipeline.rs`: HOLE_COLLAPSED esetén **mindig** `inflated_holes_points_mm == []` (hard + detect ág).
- [ ] `pipeline.rs`: HOLE_COLLAPSED esetén az outer-only envelope **nem üres** (elhelyezhetőség megmarad).
- [ ] `pipeline.rs`: HOLE_COLLAPSED diagnosztika: `preserve_for_export=true`, `usable_for_nesting=false`.
- [ ] `main.rs`: HOLE_COLLAPSED státusznál a placer felé átadott polygon `holes == []` (defense-in-depth).
- [ ] Új unit teszt lefedi a “detect path” HOLE_COLLAPSED esetet és passzol.
- [ ] `tolerance_policy.md` frissítve a valós policy-hez (HOLE_COLLAPSED nem fatal, outer-only fallback).
- [ ] Repo gate lefut: `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md`
- [ ] Report + checklist kitöltve (Report Standard v2 szerint).

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- `AGENTS.md` (outputs szabály + verify kötelező)
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/nesting_engine/tolerance_policy.md`
- `docs/known_issues/nesting_engine_known_issues.md` (KI-004, KI-010)
- `rust/nesting_engine/src/geometry/pipeline.rs`
- `rust/nesting_engine/src/main.rs`
