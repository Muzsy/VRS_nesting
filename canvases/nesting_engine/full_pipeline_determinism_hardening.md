# full_pipeline_determinism_hardening

## 🎯 Funkció

**Cél:** az F3-4 körben a `nesting_engine` jelenlegi repóállapotához igazítva zárjuk le a **kimeneti és gate-szintű determinizmus szerződést**.

A backlog szövegét itt a valós repóhoz kell igazítani:
- már létezik `meta.determinism_hash`,
- már létezik `docs/nesting_engine/json_canonicalization.md`,
- már van külön platform-rotációs determinism workflow,
- már vannak touching / determinism regressziós tesztek több modulban,
- és a `scripts/check.sh` már több targeted `cargo test` + smoke kört futtat.

Ezért az F3-4 ebben a körben **nem teljes geometriai újraírás**, és **nem "bizonyítsuk be, hogy nincs többé egyetlen f64 sem"** jellegű feladat.

Ez a task ezt zárja le:
- a **hash-view canonicalization contract** legyen egyértelmű és doksi-kód szinten ugyanaz,
- legyen **10 egymást követő futásos, bit-azonos full-output gate** azonos input + azonos seed mellett,
- legyen explicit és bizonyított policy: **touching = infeasible**,
- és ez a determinism gate fusson **minden PR-ban automatikusan** a már meglévő `repo-gate.yml` útvonalon keresztül.

## Nem cél

- az összes geometriai / feasibility / overlay kód teljes integer-only átírása,
- új placer vagy új search mód bevezetése,
- az objective sorrend módosítása,
- a timeout-bound viselkedés újradefiniálása,
- új IO contract verzió bevezetése,
- platformfüggetlen matematikai bizonyítás minden elképzelhető jövőbeli toolchainre.

## Véglegesítés (repo-állapothoz igazítva)

- A jelenlegi repóban a kritikus drift **nem az, hogy nincs determinism infrastruktúra**, hanem az, hogy a doksi és a tényleges canonicalization contract nincs teljesen egyre zárva.
- Az F3-4 első célja ezért: **repo-native contract hardening**, nem elméleti újratervezés.
- A backlogban szereplő „CI determinism gate minden PR-nál” cél teljesíthető úgy, hogy a `scripts/check.sh` lefuttat egy **10-run determinism smoke**-ot; ezt a `repo-gate.yml` már automatikusan futtatja PR-on.
- A `platform-determinism-rotation.yml` megmarad külön, extra platform-ellenőrző rétegnek; ezt a task ne bontsa meg.

## 🧠 Fejlesztési részletek

### 1) Canonicalization contract lezárása

A jelenlegi repóban a `docs/nesting_engine/json_canonicalization.md` normatív része RFC 8785 / JCS nyelvezetet használ, miközben a tényleges Rust/Python útvonal **repo-stabil, kompakt, kulcsrendezett JSON** megközelítést használ.

Ebben a körben a minimál-invazív, helyes megoldás:
- **nem** új JCS implementáció bevezetése,
- hanem a dokumentáció **egyértelmű igazítása a tényleges contracthoz**.

Kötelező állítások a doksiban:
- a `determinism_hash` a `nesting_engine.hash_view.v1` derived hash-view-ból képződik;
- a hash-view mezői és sorrendje normatívak;
- a canonical JSON byte-forma a repo által használt **kompakt, sort_keys-alapú** reprezentáció;
- a cél a **repo-on-belüli, Rust↔Python egyező contract**, nem általános RFC 8785-kompatibilis canonicalizer.

### 2) Full-output byte identity gate

A backlog F3-4 DoD-ja szerint azonos seed-del 10 futás bit-azonos kimenetet kell adni.

Ebben a repóban ezt a legjobban a meglévő `scripts/smoke_nesting_engine_determinism.sh` keményítésével lehet lezárni.

Követelmény:
- default `RUNS=10`;
- a smoke a **teljes `nest` stdout JSON**-t hasonlítsa össze futásról futásra;
- a fő assert ne csak a `meta.determinism_hash` egyezése legyen, hanem a **teljes output byte-identitása**;
- ha eltérés van, mentse ki a baseline és az eltérő outputot diagnosztikára.

Másodlagos kötelező assert:
- a smoke számolja újra a hash-view canonical bytes-t Python oldalon,
- ennek SHA-256 értéke egyezzen a solver által visszaadott `meta.determinism_hash` mezővel.

### 3) Touching policy explicit evidence

A repóban a touching tiltás már létezik, de az F3-4-ben ezt explicit, gate-elt policy-vá kell tenni.

Kötelező policy:
- **touching = infeasible**,
- bin-boundary touching is infeasible,
- part-part touching is infeasible,
- ez a konzervatív oldal, és a policy szövegesen is így szerepeljen.

A meglévő `narrow.rs` tesztekre támaszkodva adj hozzá **explicit evidence teszteket** `touching_policy_` prefixszel, hogy a gate-ben külön futtathatók legyenek.

Minimum:
- `touching_policy_part_part_touching_is_infeasible`
- `touching_policy_bin_boundary_touching_is_infeasible`

### 4) Repo gate integráció

A `scripts/check.sh` már PR gate-ben fut a `repo-gate.yml` workflow alatt.

Ezért a szükséges változtatás:
- targeted `cargo test` a determinism hardeninghez,
- targeted `cargo test` a touching policy evidence-hez,
- és az új / keményített 10-run determinism smoke meghívása.

Ajánlott minimál készlet:
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml determinism_`
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml touching_policy_`
- `RUNS=10 ./scripts/smoke_nesting_engine_determinism.sh`

Fontos:
- a `check.sh` meglévő sorrendjét ne borítsd fel,
- a már meglévő smoke-okat ne távolítsd el,
- a platform rotation workflow-t ne helyettesítsd ezzel.

### 5) Doksik frissítése

Kötelezően frissítendő:
- `docs/nesting_engine/json_canonicalization.md`
- `docs/nesting_engine/io_contract_v2.md`
- `docs/nesting_engine/tolerance_policy.md`
- `docs/known_issues/nesting_engine_known_issues.md`

Rögzítendő:
- a tényleges canonicalization contract;
- hogy a `determinism_hash` contract változatlanul `nesting_engine.hash_view.v1`, hacsak a canonical bytes ténylegesen nem változnak;
- a touching policy explicit „touching = infeasible” megfogalmazással;
- hogy a 10-run determinism gate a `check.sh`-n keresztül automatikusan PR gate része;
- a KI-006 státuszát frissíteni kell a ténylegesen választott megoldás szerint.

## 🧪 Tesztállapot

### DoD
- [ ] A `determinism_hash` canonicalization contract doksi-kód szinten egységes.
- [ ] A `json_canonicalization.md` nem állít többet, mint amit a Rust/Python implementáció ténylegesen garantál.
- [ ] Van 10-run determinism smoke ugyanarra az inputra, ugyanazzal a seed-del.
- [ ] A 10-run smoke a teljes output JSON byte-identitását ellenőrzi.
- [ ] A smoke ellenőrzi, hogy a Python oldali canonical hash egyezik a solver `meta.determinism_hash` mezőjével.
- [ ] Explicit evidence tesztek vannak `touching_policy_` prefixszel.
- [ ] `touching = infeasible` dokumentálva van.
- [ ] A determinism smoke a `scripts/check.sh` része, tehát PR-ban automatikusan fut.
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/full_pipeline_determinism_hardening.md` PASS.
- [ ] Checklist + report elkészül Report Standard v2 szerint.

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- `AGENTS.md`
- `canvases/nesting_engine/nesting_engine_backlog.md` (F3-4)
- `docs/nesting_engine/json_canonicalization.md`
- `docs/nesting_engine/io_contract_v2.md`
- `docs/nesting_engine/tolerance_policy.md`
- `docs/known_issues/nesting_engine_known_issues.md`
- `rust/nesting_engine/src/export/output_v2.rs`
- `rust/nesting_engine/src/feasibility/narrow.rs`
- `scripts/smoke_nesting_engine_determinism.sh`
- `scripts/check.sh`
- `.github/workflows/repo-gate.yml`
- `.github/workflows/platform-determinism-rotation.yml`
