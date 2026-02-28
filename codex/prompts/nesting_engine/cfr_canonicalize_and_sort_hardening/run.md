# Run: cfr_canonicalize_and_sort_hardening

Olvasd el:
- AGENTS.md
- docs/nesting_engine/f2_3_nfp_placer_spec.md
- canvases/nesting_engine/cfr_canonicalize_and_sort_hardening.md
- codex/goals/canvases/nesting_engine/fill_canvas_cfr_canonicalize_and_sort_hardening.yaml

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

Szabályok:
- Csak olyan fájlokat módosíts / hozz létre, amelyek a YAML `outputs:` listáiban szerepelnek.
- Ne vezess be új crate-et; használd a meglévő hash utilt (cache.rs mintájára).
- A végén kötelező a wrapperes gate futtatás.

Futtasd:
- ./scripts/verify.sh --report codex/reports/nesting_engine/cfr_canonicalize_and_sort_hardening.md