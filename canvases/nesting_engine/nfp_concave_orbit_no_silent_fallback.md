# canvases/nesting_engine/nfp_concave_orbit_no_silent_fallback.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nfp_concave_orbit_no_silent_fallback.md`
> **TASK_SLUG:** `nfp_concave_orbit_no_silent_fallback`
> **Terület (AREA):** `nesting_engine`

---

# F2-2 Hardening — ExactOrbit: silent fallback tiltása + bizonyítható “no fallback” teszt

## 🎯 Funkció

Az F2-2 konkáv NFP **ExactOrbit** módjában **meg kell szüntetni a silent fallback-et**.

Jelenleg az ExactOrbit belül (dead-end/loop/max_steps esetén) gyakran `Ok(stable_seed)`-et ad vissza, így:
- `enable_fallback=false` mellett is “fallbackel”, csak nem annak hívjuk,
- a teszt és a report nem tudja bizonyítani, hogy **tényleg orbit boundary** készült.

**Kötelező új viselkedés:**
- Ha `enable_fallback=false` és az orbit nem tud lezárható NFP-t adni:
  - **kötelező** `Err(...)` (nem térhet vissza stable seed-del)
- Ha `enable_fallback=true`:
  - orbit sikertelen esetben: **explicit fallback** a stable baseline-ra, és ezt az outcome jelzi.

**Bizonyíthatóság:**
- A tesztnek képesnek kell lennie kimondani:
  - “ExactOrbit valóban orbit útvonalon készült” (nem stable seed)
  - prefer_exact fixture-eknél, ha `enable_fallback=false`, akkor:
    - vagy orbit tényleg sikerül,
    - vagy hibával megáll (és ezt a fixture elvárhatja).

Nem cél:
- orbit next-event algoritmus további fejlesztése (külön task)
- stable baseline módosítása
- holes támogatás
- scripts wrapper módosítása
- `rust/vrs_solver/**` módosítása

---

## 🧠 Fejlesztési részletek

### Kötelező olvasmány / szabályok

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/nesting_engine/tolerance_policy.md`
6. `canvases/nesting_engine/nesting_engine_backlog.md` (F2-2)
7. `canvases/nesting_engine/nfp_concave_orbit_next_event.md` (P0 #2)
8. `rust/nesting_engine/src/nfp/concave.rs`
9. `rust/nesting_engine/src/nfp/mod.rs` (NfpError)
10. `rust/nesting_engine/tests/nfp_regression.rs`
11. `poc/nfp_regression/concave_*.json`

Ha bármelyik hiányzik: STOP, pontos útvonallal jelezni.

---

### Probléma (auditból)

- ExactOrbit belül dead-end/loop/max_steps esetén `Ok(stable_seed)` jön vissza.
- A teszt prefer_exact ága nem tud különbséget tenni:
  - “orbit boundary” vs “stable seed visszaadva”.

### Felderítési evidencia (konkrét kódpontok)

- Silent fallback helyei `concave.rs`-ben (ExactOrbit belső ág):
  - loop-detekt után: `return Ok(stable_seed.clone())`
  - dead-end (`choose_next_orbit_step == None`) után: `return Ok(stable_seed.clone())`
  - max_steps végén: `return Ok(stable_seed)`
- A prefer_exact jelenlegi jelentése `nfp_regression.rs`-ben:
  - `enable_fallback=false` exact futás kötelezően `Ok(...)`,
  - csak determinizmust és self-intersection hiányt ellenőriz,
  - nem bizonyítja explicit módon, hogy az eredmény valódi orbit lezárásból származik,
  - `exact != stable` ellenőrzés jelenleg nincs.

---

### Kötelező változások (nem alkuképes)

#### 1) Silent fallback tiltása
- `compute_orbit_exact_nfp(...)` (vagy a megfelelő belső függvény) nem adhat vissza stable seedet,
  ha a hívó `enable_fallback=false`.
- Ilyenkor `Err(NfpError::OrbitFallbackUsed)` vagy `Err(NfpError::OrbitLoopDetected|OrbitDeadEnd|OrbitMaxSteps)`.

#### 2) Outcome visszajelzés (teszt / report bizonyíték)
Be kell vezetni egy **belső** (nem publikus API-t törő) jelzést:
- `OrbitOutcome::ExactClosed { steps, events, ... }`
- `OrbitOutcome::FallbackStable { reason, ... }`
- `OrbitOutcome::FailedNoFallback { reason, ... }`

Cél: a teszt és a report **egyértelmű** evidence-et kapjon.

#### 3) Teszt: explicit bizonyítás
- prefer_exact fixture esetén a teszt:
  - lefuttatja a stable baseline-t (default/stable mód)
  - lefuttatja az exact no-fallbackot
  - és **bizonyítja**, hogy:
    - outcome = ExactClosed, és
    - `exact_polygon != stable_polygon` (legalább canonical ring összevetés)
  - Ha egy fixture természeténél fogva exact == stable, akkor **külön flag** kell (pl. `allow_exact_equals_stable: true`) – különben hamis negatív.

#### 4) Report evidence
- A reportban legyen táblázat:
  - fixture → prefer_exact → exact outcome → fallback? → steps/events/ban reason
- AUTO_VERIFY blokkban az új teszt futása is látszódjon (verify log).

---

### Érintett fájlok

**Módosul:**
- `rust/nesting_engine/src/nfp/concave.rs` (silent fallback tiltása + outcome)
- `rust/nesting_engine/src/nfp/mod.rs` (NfpError új variáns(ok), ha kell)
- `rust/nesting_engine/tests/nfp_regression.rs` (explicit proof + új fixture mezők)
- `poc/nfp_regression/*.json` (prefer_exact esetekhez új elvárás mezők)

**Új (ha kell):**
- `rust/nesting_engine/src/nfp/orbit_outcome.rs` (belső outcome típus; csak ha a concave.rs túl nagy)

---

## 🧪 Tesztállapot

### DoD

- [ ] `enable_fallback=false` mellett az orbit dead-end/loop/max_steps **hibával** áll meg (nem stable seed)
- [ ] prefer_exact fixture-ek közül legalább 3 esetben:
  - outcome = `ExactClosed`
  - és `exact != stable` canonical ring alapon (vagy explicit allow flag)
- [ ] verify wrapper PASS:
  - `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_orbit_no_silent_fallback.md`

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

- P0 #1: `nfp_concave_integer_union`
- P0 #2: `nfp_concave_orbit_next_event`
- F2-2 core: `canvases/nesting_engine/nfp_computation_concave.md`
- Kód: `rust/nesting_engine/src/nfp/concave.rs`, `rust/nesting_engine/src/nfp/mod.rs`
- Teszt: `rust/nesting_engine/tests/nfp_regression.rs`
- Fixture: `poc/nfp_regression/concave_*.json`
