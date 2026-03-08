# tolerance_policy_f64_determinism_alignment

## 🎯 Funkció

**Cél:** a `nesting_engine` determinisztikus szerződését pontosítani úgy, hogy
- egyértelmű legyen hol kötelező integer-only működés,
- hol maradhat float-assisted geometria,
- és hol tilos a float döntési forrás.

Ez a kör **stabilizációs / policy-alignment task**, nem teljes geometriai újraírás.

## Nem cél

- teljes integer-only rewrite az összes geometriai útvonalon,
- új placer vagy search algoritmus,
- performance optimalizálás,
- IO contract verzióváltás.

## Repo-állapothoz igazított scope

- A `rust/nesting_engine/src/geometry/offset.rs` és `rust/nesting_engine/src/geometry/pipeline.rs`
  tartalmaz aktív f64 útvonalakat.
- A `rust/nesting_engine/src/feasibility/narrow.rs` döntési útvonala jelenleg integer domináns;
  itt a cél policy-evidence és guard teszt hardening.
- A KI-007 jelenleg túl tág gyűjtő issue, ezt a kör végén lezárható állapotba kell hozni
  (vagy RESOLVED, vagy szűkebb issue-ra bontás).

## 🧠 Fejlesztési részletek

### 1) Determinism boundary modell (A/B/C zóna)

Doksi-kód szinten legyen explicit:

- **A-zóna (kötelező integer-only):**
  - placement acceptance/rejection döntések,
  - ordering/ranking,
  - determinism hash-view + canonical JSON contract.

- **B-zóna (float-assisted, de policy-vezérelt):**
  - offset/simplify/polygon self-intersection jellegű geometriai előfeldolgozás,
  - külső float predikátumot használó helper útvonalak,
  - de csak központosított epsilon/tie-break policy mellett.

- **C-zóna (tiltott):**
  - ad hoc, szétszórt epsilonok,
  - implicit float ordering, nem dokumentált branch boundary,
  - raw float összehasonlítás döntési logikában policy nélkül.

### 2) Központosított float policy helper

Vezess be közös helper modult:

- `rust/nesting_engine/src/geometry/float_policy.rs`

Minimum API:

- `is_near_zero(...)`
- `eq_eps(...)`
- `cmp_eps(...)`
- dokumentált epsilon konstans(ok)

Cél: ne legyen szétszórt, dokumentálatlan float compare a kritikus modulokban.

### 3) Offset és pipeline hardening

Kötelező fájlok:

- `rust/nesting_engine/src/geometry/offset.rs`
- `rust/nesting_engine/src/geometry/pipeline.rs`

Követelmények:

- ahol float-összehasonlítás döntési határt ad, ott a közös helper legyen használva,
- legyen stabil ordering / canonicalization ott, ahol több azonos értelmű geometriai kimenet lehetséges,
- maradjon minimál invazív: viselkedésváltozás csak policy-harmonizáció miatt történjen.

### 4) Feasibility evidence hardening

`rust/nesting_engine/src/feasibility/narrow.rs`:

- explicit `narrow_float_policy_` prefixű evidence tesztek,
- touching policy továbbra is változatlanul `touching = infeasible`.

### 5) Célzott regresszió és gate evidence

Adj hozzá:

- célzott tesztprefixek:
  - `offset_determinism_`
  - `pipeline_float_policy_`
  - `narrow_float_policy_`
- egy dedikált float-boundary determinism smoke-ot fix fixture-rel,
- és kösd be `scripts/check.sh`-ba.

### 6) Dokumentáció és issue lezárási stratégia

Frissítendő:

- `docs/nesting_engine/tolerance_policy.md`
- `docs/nesting_engine/architecture.md`
- `docs/known_issues/nesting_engine_known_issues.md`

A KI-007 állapota ne maradjon elavult gyűjtő státuszban:

- ha a scope ebben a körben lezárul: `RESOLVED (tolerance_policy_f64_determinism_alignment, 2026-03-08)`,
- ha marad nyitott rész: szűkített új issue-ra bontás és a KI-007 gyűjtő issue lezárása.

## 🧪 Tesztállapot

### DoD

- [ ] A/B/C determinism boundary modell dokumentálva van, doc-code drift nélkül.
- [ ] Van központosított float-policy helper, és az érintett geometry modulok ezt használják.
- [ ] Nincs ad hoc epsilon szétszórva az érintett döntési pontokon.
- [ ] Van dedikált `offset_determinism_` regressziós evidence.
- [ ] Van dedikált `pipeline_float_policy_` regressziós evidence.
- [ ] Van dedikált `narrow_float_policy_` regressziós evidence.
- [ ] Van célzott float-boundary repeated-run determinism smoke.
- [ ] A smoke a `scripts/check.sh` része (PR gate útvonalon fut).
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/tolerance_policy_f64_determinism_alignment.md` PASS.
- [ ] KI-007 lezárása/leszűkítése explicit és követhető.

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- `AGENTS.md`
- `docs/nesting_engine/tolerance_policy.md`
- `docs/nesting_engine/architecture.md`
- `docs/known_issues/nesting_engine_known_issues.md`
- `rust/nesting_engine/src/geometry/offset.rs`
- `rust/nesting_engine/src/geometry/pipeline.rs`
- `rust/nesting_engine/src/feasibility/narrow.rs`
- `scripts/check.sh`
- `.github/workflows/repo-gate.yml`
