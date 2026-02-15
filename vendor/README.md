# vendor/

## Sparrow vendor/submodule út

A repo `scripts/ensure_sparrow.sh` resolvere a következő prioritást használja:

1. `SPARROW_BIN` env
2. `SPARROW_SRC_DIR` env
3. `vendor/sparrow/` (preferált)
4. fallback `.cache/sparrow` clone

### Ajánlott: git submodule

```bash
git submodule add https://github.com/JeroenGar/sparrow.git vendor/sparrow
git submodule update --init --recursive
```

CI oldalon a checkout `submodules: recursive`, így a `vendor/sparrow` automatikusan elérhető.

### Pin kezelés

A pin commit elsődlegesen `SPARROW_COMMIT` env-ből, különben
`poc/sparrow_io/sparrow_commit.txt` fájlból jön.

Ha a `vendor/sparrow` git repo és nem tartalmazza a pinelt commitot,
a resolver hibát dob; ilyenkor frissítsd a submodule állapotot vagy a pinelt commitot.

### Nem-submodule vendored copy

Támogatott a sima bemásolt forrás is (`vendor/sparrow/Cargo.toml` esetén).
Ebben az esetben a resolver pin-validációt nem tud git alapon kikényszeríteni.
