# simulated_annealing_search_part_order_policy_gate_p1

## 🎯 Funkció

**P1 hardening feladat:**
a már elkészült `PartOrderPolicy` wiring evidence kerüljön be a merge gate-be is, hogy a
BLF és NFP placer ordering-viselkedése ne csak reporttal, hanem kötelező repo gate-tel is védett legyen.

A konkrét cél:
- a `PartOrderPolicy::ByInputOrder` és `PartOrderPolicy::ByArea` viselkedését bizonyító meglévő unit tesztek
  célzottan lefussanak a `scripts/check.sh` alatt is.

## Miért kell ez?

A repo-ban már vannak bizonyító unit tesztek:

- `rust/nesting_engine/src/placement/blf.rs`
- `rust/nesting_engine/src/placement/nfp_placer.rs`

Ezek igazolják, hogy:
- `ByInputOrder` esetén nincs belső átrendezés,
- `ByArea` esetén a baseline area-desc rendezés érvényesül.

Viszont a jelenlegi `scripts/check.sh` nem futtat rájuk külön célzott gate-et,
így ez a viselkedés nincs közvetlenül merge-gate szinten lezárva.

## ✅ Nem cél

- SA algoritmus módosítása
- új CLI flag
- placement quality/perf tuning
- dokumentációs nagy rendrakás
- architecture.md bővítése

## 🔎 Érintett fájlok

- `scripts/check.sh`
- `rust/nesting_engine/src/placement/blf.rs`
- `rust/nesting_engine/src/placement/nfp_placer.rs`
- `codex/codex_checklist/nesting_engine/simulated_annealing_search_part_order_policy_gate_p1.md`
- `codex/reports/nesting_engine/simulated_annealing_search_part_order_policy_gate_p1.md`

## 🧠 Megoldási elv

### 1) A meglévő tesztek gate-be emelése
A repo már tartalmazza a két ordering evidence tesztet.
A task célja elsődlegesen az, hogy ezek a `check.sh` során is lefussanak.

Preferált megoldás:
- `scripts/check.sh` kapjon külön targeted stepet, ami a megfelelő teszt-szűrővel futtatja az order policy teszteket.

### 2) Tesztnév-egységesítés csak ha tényleg kell
Ha a jelenlegi tesztnevek már jól szűrhetők közös substringgel, ne legyen felesleges Rust módosítás.
Csak akkor nevezz át tesztet, ha a gate olvashatósága vagy stabil szűrése ezt tényleg indokolja.

### 3) Elvárt gate viselkedés
A verify logból látszódjon, hogy:
- lefutott a BLF ordering test,
- lefutott a NFP ordering test,
- a gate PASS.

## 🧪 Tesztelés

### Kötelező gate
- `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search_part_order_policy_gate_p1.md`

### Elvárt evidence
A verify logban látszódjon egy külön order-policy blokk, amely a célzott teszteket futtatja.

## ✅ DoD

- [ ] A `scripts/check.sh` tartalmaz külön célzott order-policy tesztfuttatást.
- [ ] A gate lefuttatja a BLF ordering evidence tesztet.
- [ ] A gate lefuttatja az NFP ordering evidence tesztet.
- [ ] A taskhoz tartozó checklist és report elkészült.
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search_part_order_policy_gate_p1.md` PASS.

## ⚠️ Kockázatok + rollback

Kockázat:
- ha a túl tág tesztszűrő más, nem ide tartozó teszteket is meghúz, a gate zajosabb lesz.

Mitigáció:
- szűk, egyértelmű tesztfilter használata.

Rollback:
- `scripts/check.sh` order-policy step visszavétele
- opcionálisan a Rust tesztnevek revertje, ha át lettek nevezve