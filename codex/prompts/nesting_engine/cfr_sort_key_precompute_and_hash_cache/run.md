# Run: cfr_sort_key_precompute_and_hash_cache

Olvasd el:
- AGENTS.md
- canvases/nesting_engine/cfr_sort_key_precompute_and_hash_cache.md
- codex/goals/canvases/nesting_engine/fill_canvas_cfr_sort_key_precompute_and_hash_cache.yaml

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

Szabályok:
- Csak olyan fájlokat módosíts / hozz létre, amelyek a YAML `outputs:` listáiban szerepelnek.
- A kimenetnek determinisztikusan egyeznie kell a korábbi CFR kimenettel (viselkedésváltozás tilos).
- A végén kötelező a wrapperes gate futtatás.

Futtasd:
- ./scripts/verify.sh --report codex/reports/nesting_engine/cfr_sort_key_precompute_and_hash_cache.md