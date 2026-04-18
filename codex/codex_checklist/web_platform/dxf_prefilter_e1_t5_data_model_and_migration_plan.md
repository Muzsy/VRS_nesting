# Codex checklist - dxf_prefilter_e1_t5_data_model_and_migration_plan

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a data-model dokumentum: `docs/web_platform/architecture/dxf_prefilter_data_model_and_migration_plan.md`
- [x] A dokumentum explicit kulonvalasztja a current-code truth es a future canonical prefilter data-model reteget
- [x] A dokumentum rogziti, hogy a future rules profile domain owner-scoped + versioned mintat kovessen
- [x] A dokumentum rogziti, hogy a preflight run persistence kulon truth a geometry revision/validation truth mellett
- [x] A dokumentum tartalmaz magas szintu, table-by-table javaslatot profile/version, preflight run, diagnostics, artifact es review-decision retegre
- [x] A dokumentum tartalmaz FK / ownership / uniqueness / indexing elveket docs-szinten
- [x] A dokumentum tartalmaz migration slicing tervet logikai szeletekre bontva
- [x] A dokumentum kulon jeloli a current-code truth, a future canonical contract es a later extension reszeket
- [x] A dokumentum repo-grounded hivatkozasokat ad a meglevo migrationokra es kodhelyekre
- [x] A task docs-only maradt (nincs SQL migration / route / service / RLS / UI implementacio)
- [x] A YAML outputs listaja csak valos, szukseges fajlokat tartalmaz
- [x] A runner prompt explicit tiltja a data-model implementacios scope creep-et
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t5_data_model_and_migration_plan.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
