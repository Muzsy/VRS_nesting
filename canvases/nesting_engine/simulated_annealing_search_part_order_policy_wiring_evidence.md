# simulated_annealing_search_part_order_policy_wiring_evidence

## 🎯 Funkció

**Cél:** Bizonyítani (teszttel + reporttal), hogy az F2-4 előfeltételeként bevezetett **PartOrderPolicy** end-to-end működik, és az SA későbbi „part order” state-je valóban átadható a placereknek.

Konkrétan bizonyítandó:

1) `PartOrderPolicy::ByInputOrder` esetén **nincs belső rendezés** a placerekben (BLF + NFP), a bemeneti sorrend megmarad.
2) `PartOrderPolicy::ByArea` esetén a **jelenlegi baseline** rendezés érvényesül (area-desc + determinisztikus tie-break a meglévő kód szerint).
3) `main.rs` defaultja `ByArea`, tehát **baseline viselkedés változatlan** (SA nélkül).

**Nem cél:**
- SA implementáció (`--search sa`, move-set, acceptance, cooling, evaluator).
- IO contract / output mezők módosítása.
- Optimalizáció/perf tuning.

## 🧠 Fejlesztési részletek

### Kontextus (valós kód)
- A `greedy_multi_sheet(..., order_policy)` már 6 paraméteres, és továbbadja a policy-t a placereknek.
- A `blf_place(..., order_policy)` és `nfp_place(..., order_policy)` fogadja a policy-t, és jelenleg `ByArea` esetén rendez, `ByInputOrder` esetén nem.
- A `main.rs` default futása explicit `PartOrderPolicy::ByArea` policy-vel hivja a `greedy_multi_sheet`-et.

**A task célja nem “javítás”, hanem “bizonyítás + repo-szabály szerinti lezárás”.**

### Implementációs stratégia (minimális, alacsony kockázat)
A tesztelhetőség miatt mindkét placerben vezess be egy **kis privát helper** függvényt, ami kizárólag az orderinget adja vissza, és a `*_place` hívás ezt használja.

- `rust/nesting_engine/src/placement/blf.rs`
  - új privát helper (példa név): `fn order_parts_for_policy(parts: &[InflatedPartSpec], order_policy: PartOrderPolicy) -> Vec<InflatedPartSpec>`
  - a helper logikája **bitazonos** a jelenlegi kóddal:
    - `ByArea` → a meglévő comparator (area-desc + a meglévő tie-break)
    - `ByInputOrder` → nincs rendezés
  - `blf_place` a helper kimenetét használja (funkció nem változik, csak factoring)

- `rust/nesting_engine/src/placement/nfp_placer.rs`
  - ugyanez a helper + használat.

### Új unit tesztek (evidence)
Mindkét fájlban készíts 1-1 új tesztet, ami csak az orderinget vizsgálja (ne a teljes placementet), így stabil és olcsó.

**BLF:**
- tesztnév: `order_policy_by_input_order_preserves_input_order`
- minta:
  - készíts 3 darab `InflatedPartSpec`-et olyan módon, ahogy a fájl meglévő tesztjei is csinálják (ne találj ki új mezőket/konstansokat; copy-paste mintát a meglévő unit test setupból).
  - állítsd be úgy, hogy a 3 part area-ja **különböző** legyen (hogy a `ByArea` tényleg átrendezzen).
  - input sorrend legyen pl. `[small, large, medium]`.
  - assert:
    - `ByInputOrder` → id-k sorrendje megegyezik az inputtal
    - `ByArea` → id-k sorrendje area-desc szerint (és ha szükséges, legyen determinisztikus tie-break assert is)

**NFP:**
- tesztnév: `order_policy_by_input_order_preserves_input_order`
- ugyanaz a logika, az NFP-s helperrel.

Megjegyzés:
- Ha a comparator tie-breaket használ (pl. id), a tesztet úgy állítsd össze, hogy ne legyen egyenlő area (vagy legyen külön mini-assert a tie-breakre, ha könnyű).

### Repo-szabály szerinti lezárás
- Készüljön checklist + report Report Standard v2 szerint.
- A reportban legyen DoD → Evidence Matrix, amiben:
  - új tesztek path+név
  - érintett kód path+fn (helper + place fn)
  - verify log hivatkozás

## 🧪 Tesztállapot

### DoD
- [ ] Új teszt BLF orderingre: `order_policy_by_input_order_preserves_input_order`
- [ ] Új teszt NFP orderingre: `order_policy_by_input_order_preserves_input_order`
- [ ] `cargo test --manifest-path rust/nesting_engine/Cargo.toml` PASS
- [ ] Repo gate: `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search_part_order_policy_wiring_evidence.md` PASS
- [ ] Report Standard v2: AUTO_VERIFY blokk kitöltve (verify.sh által), `.verify.log` elmentve

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- F2-4 kontextus: `canvases/nesting_engine/simulated_annealing_search.md`
- Backlog/DoD: `canvases/nesting_engine/nesting_engine_backlog.md` (F2-4)
- Repo szabályok: `AGENTS.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`
- Érintett kód:
  - `rust/nesting_engine/src/placement/blf.rs`
  - `rust/nesting_engine/src/placement/nfp_placer.rs`
