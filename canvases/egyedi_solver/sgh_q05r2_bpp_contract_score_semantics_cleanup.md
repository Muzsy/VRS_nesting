# SGH-Q05R2 — BPP contract score semantics cleanup

## Státusz

Revision cleanup task. SGH-Q05R kódszinten rendben javította a BPP diagnostics és `PhaseResult.best_score` szemantikát, de a Q05 contract dokumentumban maradt egy régi, ellentmondó állítás:

```text
PhaseResult.best_score = min(final_score, compression_best, exploration_best, initial_score)
```

Ez ellentmond a Q05R-ben bevezetett tényleges szerződésnek:

```text
PhaseResult.score = ScoreModel::score(final_returned_layout)
PhaseResult.best_score = PhaseResult.score.total_cost
```

Q06 előtt ezt tisztítani kell, mert a LossModel task a score/diagnostics szerződésre fog építeni.

## Cél

A Q05 contract dokumentáció legyen egyértelmű, önellentmondás-mentes, és feleljen meg a valós Q05R kódnak.

## Scope

Engedélyezett módosítások:

```text
docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md
codex/codex_checklist/egyedi_solver/sgh_q05r2_bpp_contract_score_semantics_cleanup.md
codex/reports/egyedi_solver/sgh_q05r2_bpp_contract_score_semantics_cleanup.md
codex/reports/egyedi_solver/sgh_q05r2_bpp_contract_score_semantics_cleanup.verify.log
```

Tiltott production scope:

```text
rust/vrs_solver/src/**
api/**
frontend/**
DXF/import pipeline
Q06 LossModel implementáció
Q07 RotationPolicy
Q08 CDE backend
```

Ez dokumentációs javítás; production Rust kódot nem módosíthat.

## Javítandó pontok

### 1. Régi `PhaseResult.best_score = min(...)` állítás eltávolítása

A `docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md` `Score vs sheet-count decision rule` szakaszából töröld vagy írd át az alábbi régi állítást:

```text
PhaseResult.best_score = min(final_score, compression_best, exploration_best, initial_score)
```

Helyette egyértelműen ezt rögzítse:

```text
PhaseResult.score = ScoreModel::score(final_returned_layout)
PhaseResult.best_score = PhaseResult.score.total_cost
```

### 2. Best-seen metrika különválasztása

Rögzítsd, hogy:

```text
best_seen_score / min across phases jelenleg NEM része a PhaseResult-nak.
Ha később kell, külön mezőként kell bevezetni, például PhaseResult.best_seen_score.
```

Ne legyen olyan állítás, hogy a `PhaseResult.best_score` olyan layout score-ja, amit a `PhaseResult` nem ad vissza.

### 3. BppPhaseDiagnostics.best_score pontosítása

A `BppPhaseDiagnostics.best_score` mezőnél legyen egyértelmű:

```text
BPP phase local diagnostic.
Sheet-count-first commit után a legutolsó committed incumbent score-ja.
Nem globális best-seen score, és nem feltétlenül ugyanaz a jelentése, mint a PhaseResult.best_score.
```

Ha a név félrevezető, dokumentáld a naming caveat-et, de Rust átnevezés most tilos.

### 4. Q05R report advisory félreértés megelőzése

A contract dokumentum tartalmazzon rövid tisztázást:

```text
PhaseResult.improved() a Q05R után final_score < initial_score logikával értelmezhető, mert best_score == final_score.total_cost.
```

Nem kell a korábbi Q05R reportot átírni; a Q05R2 report tisztázza a hibát.

## Kötelező ellenőrzések

```bash
grep -n "min(final_score, compression_best, exploration_best, initial_score)" docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md
# elvárt: nincs találat

grep -n "PhaseResult.best_score = PhaseResult.score.total_cost" docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md
# elvárt: van találat

git diff --name-only
# elvárt: nincs rust/vrs_solver/src/** módosítás
```

Futtasd a repo standard verify-t is:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q05r2_bpp_contract_score_semantics_cleanup.md
```

Ha a környezetben ésszerűen futtatható, futtasd:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
```

## PASS feltétel

PASS csak akkor adható, ha:

```text
- report első sora: PASS
- nincs régi min(...) PhaseResult.best_score állítás a contract doksiban
- contract egyértelműen rögzíti: PhaseResult.best_score == PhaseResult.score.total_cost
- nincs production Rust módosítás
- verify.sh zöld, vagy ha valami környezeti okból nem fut, az BLOCKED/REVISE reportban szerepel
- report vége: SGH-Q06_STATUS: READY
```

Ha bármi fail:

```text
report első sora: REVISE vagy BLOCKED
ne legyen SGH-Q06_STATUS marker
```
