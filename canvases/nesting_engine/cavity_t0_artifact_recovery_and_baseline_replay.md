# Cavity T0 - Artifact recovery es baseline replay

## Cel
Javitsd a production/trial run artifact URL es letoltesi utvonalat ugy, hogy a
`solver_input` es `engine_meta` artifactok 1:1 visszajatszashoz elerhetok
legyenek. A task vegere legyen bizonyitott legacy baseline egy valos hibas
runrol, de cavity prepack implementacio meg ne keszuljon.

## Nem-celok
- Nem cavity packer, normalizer vagy UI feature task.
- Nem timeout/work_budget noveles.
- Nem warning suppression.
- Nem engine fallback logika modositas.
- Nem OTSZOG/NEGYZET/MACSKANYELV vagy filename hardcode.

## Repo-kontekstus
- `codex/reports/nesting_engine/otszog_bodypad_runtime_root_cause_20260428.md`
  szerint a konkret production replayet blokkolja a `solver_input` es
  `engine_meta` artifact URL `status=400 artifact url failed` allapot.
- `api/routes/runs.py` normalizalja a run artifact sorokat
  `artifact_kind/storage_path/metadata_jsonb` mezokbol, es a signed URL
  letrehozasnal `storage_bucket` + `storage_key` parost hasznal.
- `worker/main.py` ma feltolti a `runs/<run_id>/inputs/solver_input_snapshot.json`
  es `runs/<run_id>/artifacts/engine_meta.json` objektumokat.
- A viewer-data mar tartalmaz fallbacket a jol ismert solver input snapshot
  pathra, de az artifact URL endpointnak es a listazott artifact rekordoknak is
  konzisztensnek kell lenniuk.

## Erintett fajlok
- `api/routes/runs.py`
- `api/supabase_client.py` csak akkor, ha a signed/download helper contractja
  tenylegesen ezt igenyli.
- `worker/main.py` csak akkor, ha az artifact rekord irasa bizonyitottan hibas
  storage bucket/path adatot ad.
- `tests/test_run_artifact_url_recovery.py` vagy repo-kompatibilis uj teszt.
- `scripts/smoke_cavity_t0_artifact_recovery_and_baseline_replay.py`
- `tmp/repro_f683e6f7/solver_input_snapshot.json` csak olvasasra hasznalhato.

## Implementacios lepesek
1. Olvasd el az AGENTS/Codex/QA szabalyokat es a root-cause reportot.
2. Terkepzd fel a run artifact rekordok schemajat, a legacy `metadata_jsonb`
   mezoket es a signed URL helper hasznalatat.
3. Irj unit/smoke tesztet, amely fake Supabase klienssel bizonyitja:
   `solver_input` es `engine_meta` artifact sorbol signed URL kerheto, es a
   bucket/path nem ures.
4. Javitsd a legszukebb API/worker storage-key inkonzisztenciat.
5. Ha elerheto real artifact, toltsd le es futtasd legacy replaykent; ha nem,
   dokumentald a fennmarado hozzaferesi blokkot.

## Checklist
- [ ] `solver_input` artifact URL fake/teszt kornyezetben PASS.
- [ ] `engine_meta` artifact URL fake/teszt kornyezetben PASS.
- [ ] A javitas backward kompatibilis legacy `artifact_kind=log` sorokkal.
- [ ] Van baseline replay parancs es eredmeny, vagy bizonyitott kulso blokk.
- [ ] Nincs cavity implementacio.
- [ ] Repo gate reporttal lefutott.

## Tesztterv
- `python3 -m pytest -q tests/test_run_artifact_url_recovery.py`
- `python3 scripts/smoke_cavity_t0_artifact_recovery_and_baseline_replay.py`
- Ha a valos snapshot elerheto: Rust engine legacy NFP+SA replay
  `NESTING_ENGINE_EMIT_NFP_STATS=1` mellett.
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.md`

## Elfogadasi kriteriumok
- A run artifact URL endpoint konzisztensen tud signed URL-t adni
  `solver_input` es `engine_meta` artifactra.
- A reportban szerepel a storage bucket/key lineage.
- A baseline legacy futas kimutatja a fallbacket, vagy a report explicit
  bizonyitja, hogy a production artifact tovabbra is kulso okbol nem erheto el.

## Rollback
Az API/worker artifact normalizacio diff egyben visszavonhato. DB migrationt
csak akkor szabad nyitni, ha a repo bizonyitja, hogy a schema nelkul nem
javithato a hiba.

## Kockazatok
- Regi artifact rekordok tobbfele legacy formatumban lehetnek.
- Storage bucket fallback rossz bucketre mutathat.
- Production replayhez credential vagy signed URL policy is szukseges lehet.

## Vegso reportban kotelezo bizonyitek
- Konkret path/line hivatkozas az artifact normalizalasra es URL generalasra.
- Teszt parancsok exit code-dal.
- Letoltott vagy fallbackbol olvasott artifact pathok.
- Legacy replay stderr/stdout osszegzes, ha elerheto.
