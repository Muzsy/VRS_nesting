# T03 Checklist — lv8_density_t03_phase0_nfp_diag_gate

Pipálható DoD lista a canvas
[lv8_density_t03_phase0_nfp_diag_gate.md](../../../canvases/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md)
alapján. Egy pont csak akkor pipálható, ha a bizonyíték a reportban szerepel
([codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md](../../reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md)).

## Repo szabályok és T0x előzmények

- [x] `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
      `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`,
      `development_plan_packing_density_20260515.md` v2.2 beolvasva.
- [x] T00 outputok jelen, T01 / T02 reportok PASS.
- [x] T03 canvas + YAML beolvasva.

## Helper + gate-elés

- [x] `is_concave_nfp_diag_enabled()` helper létrejött a `concave.rs`-ben,
      `NESTING_ENGINE_NFP_DIAG=1` env flag-re true-t ad
      ([rust/nesting_engine/src/nfp/concave.rs:25-30](../../../rust/nesting_engine/src/nfp/concave.rs#L25-L30)).
- [x] `compute_concave_nfp_default()` ENTRY eprintln gate alatt
      ([rust/nesting_engine/src/nfp/concave.rs:234-243](../../../rust/nesting_engine/src/nfp/concave.rs#L234-L243)).
- [x] `compute_stable_concave_nfp()` decompose_done eprintln gate alatt
      (a `diag_enabled` lokális bool a ciklus előtt kiszámolva).
- [x] `partial_nfp` és `partial_nfp_done` eprintln-ek a beágyazott ciklusban
      `diag_enabled` lokális bool-lal gate-elve — env nem olvasódik
      iterációnként.
- [x] `union_done` eprintln gate alatt.
- [x] Default off: `NESTING_ENGINE_NFP_DIAG` nélkül nincs `[CONCAVE NFP DIAG]`
      stderr kimenet.

## Tesztelés

- [x] `#[cfg(test)] mod tests` blokkba `concave_nfp_diag_env_gate` unit teszt
      hozzáadva; 4 állapotot ellenőriz (unset → false, `0` → false, `1` → true,
      `true` (nem `1`) → false). A teszt menti és visszaállítja az eredeti
      env állapotot.
- [x] Env-touching teszt szerializálva (`static DIAG_ENV_LOCK: Mutex<()>`),
      hogy a cargo párhuzamos test runner ne race-eljen a process-global
      env-en.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml concave_nfp_diag`
      → `1 passed; 0 failed`.

## nfp_placer.rs audit (változás nélkül)

- [x] `nfp_placer.rs` meglévő hot-path diag gate-jei (`is_candidate_diag_enabled`,
      `is_hybrid_cfr_diag_enabled`, `is_nfp_runtime_diag_enabled`,
      `is_cfr_diag_enabled`, `is_active_set_diag_enabled`) auditálva, nem
      módosultak.
- [x] A T03 nem nyúl a `nfp_placer.rs`-hez (production diff guard üres
      halmaz erre a fájlra).

## Harness stderr policy audit

- [x] `scripts/experiments/lv8_2sheet_claude_search.py` `LV8_HARNESS_QUIET=1`
      default megmaradt (konzervatív log-size guard).
- [x] A diag-spam komment pontosítva: a `[CONCAVE NFP DIAG]` mostantól
      opt-in (`NESTING_ENGINE_NFP_DIAG=1`); a quiet policy maradt általános
      stderr-méret védelemként, T06 dönthet a lazításról a no-SA shadow
      run mérés alapján.
- [x] A subprocess viselkedés és a quiet-default policy nem változott
      (csak komment szövege + marker file üzenete).

## Tilalmak betartása

- [x] NFP algoritmus nem módosult (cargo check: csak meglévő warningok,
      semmilyen új viselkedési változás).
- [x] Cache logika nem módosult (`rust/nesting_engine/src/nfp/cache.rs`
      érintetlen, production diff guard üres).
- [x] `search/sa.rs` érintetlen.
- [x] Quality profile registry érintetlen.
- [x] Nincs hosszú LV8 benchmark futtatva.
- [x] Nincs Phase 2+ scoring / lookahead / beam / LNS funkció.
- [x] `LV8_HARNESS_QUIET` default policy nem változott (csak komment).

## Verifikáció

- [x] T03 grep sanity zöld (`T03 concave diag grep PASS`).
- [x] `cargo check --manifest-path rust/nesting_engine/Cargo.toml`
      → `Finished dev profile` (csak meglévő warningok).
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml concave_nfp_diag`
      → `1 passed`.
- [x] Production diff guard zöld (whitelist: `concave.rs` +
      `lv8_2sheet_claude_search.py`).
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md`
      lefutott. Eredmény: **PASS** (`check.sh` exit 0, 201s). 302 pytest pass,
      mypy clean, Sparrow + DXF + multisheet + `vrs_solver` determinisztika +
      timeout/perf guard zöld. Log:
      `codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.verify.log`.
- [x] Report DoD → Evidence Matrix kitöltve (lásd a report 5) szekcióját);
      mind a 11 DoD pont PASS.
