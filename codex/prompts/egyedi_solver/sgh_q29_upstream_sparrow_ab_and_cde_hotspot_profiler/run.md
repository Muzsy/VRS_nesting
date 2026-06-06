# Run prompt — SGH-Q29 upstream Sparrow A/B + local CDE hotspot profiler

You are working in the VRS_nesting repo.

Execute exactly this task:

- Canvas: `canvases/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.yaml`
- Checklist: `codex/codex_checklist/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.md`
- Report: `codex/reports/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.md`

Hard rules:

1. Read `AGENTS.md`, `docs/codex/yaml_schema.md`, and `docs/codex/report_standard.md` first.
2. Follow the YAML outputs rule. Do not edit files not listed in the active step outputs.
3. This is a measurement task, not an optimization task.
4. Do not change solver semantics, GLS, worker ordering, sample budgets, touching policy, compression, LBF behavior, or search acceptance logic.
5. Do not call any local no-session/reference/fallback build "upstream Sparrow".
6. A true upstream comparison requires `.cache/sparrow`, an upstream commit hash, and a real upstream build/run.
7. If upstream cannot be built/run, mark Phase A as `BLOCKED` and state clearly: no upstream runtime claim is made.
8. Phase B local profiling must still run and must produce a cost breakdown.

Required final commands:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
python3 scripts/bench_sgh_q29_upstream_sparrow_ab.py
python3 scripts/profile_sgh_q29_local_cde_hotspot.py
python3 scripts/smoke_sgh_q29_upstream_ab_and_cde_hotspot_profiler.py
cargo test --manifest-path rust/vrs_solver/Cargo.toml
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.md
```

The final report must include:

```text
## Final answer to the two questions

1. Upstreamhez képest hol állunk?
2. A saját CDE/search útvonalon mi viszi el az időt?
```
