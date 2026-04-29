# Cavity T5 - Result normalizer composite expansion

## Cel
Bovitsd a `nesting_engine_v2` result normalizert ugy, hogy opcionalis
`run_dir/cavity_plan.json` alapjan virtual parent placementeket valo parent
placementekke mapeljen, internal child placementeket abszolut sheet placementke
expandaljon, es a top-level child instance szamozast offsetelje.

## Nem-celok
- Nem worker prepack algoritmus.
- Nem artifact persist.
- Nem SVG/DXF exporter fix, csak projection truth.
- Nem UI.
- Nem virtual part ID user-facing output.

## Repo-kontekstus
- `worker/result_normalizer.py` v2 ag ma kozvetlenul a snapshot `part_index`-ben
  keresi a solver output `part_id` erteket.
- A helper `placement_transform_point` mar hasznalt az SVG/DXF exportban.
- `run_layout_placements.metadata_jsonb` alkalmas additiv parent-child metadata
  tarolasra.
- Exporterek projection placementekbol dolgoznak, ezert itt kell eltuntetni a
  virtual ID-kat.

## Erintett fajlok
- `worker/result_normalizer.py`
- `tests/worker/test_result_normalizer_cavity_plan.py` vagy repo-kompatibilis
  teszt path.
- `scripts/smoke_cavity_t5_result_normalizer_expansion.py`

## Implementacios lepesek
1. Opcionalsan olvasd be `run_dir/cavity_plan.json`-t.
2. `enabled=false` vagy hianyzo fajl eseten a regi v2 normalizer viselkedes
   maradjon valtozatlan.
3. Virtual parent `part_id` eseten a `cavity_plan.virtual_parts` alapjan mapelj
   real parent `part_revision_id`-ra.
4. Minden internal child placementet expandalj abszolut transformmal:
   parent rotation + local rotation, parent translation + rotated local point.
5. Alkalmazd `instance_bases.top_level_instance_base` offsetet top-level
   placementekre es unplaced sorokra.
6. Metadata mezok: `placement_scope`, parent ids, cavity index, local transform,
   `cavity_plan_version`.
7. Placement ordering deterministic legyen: parent utan internal child rows.

## Checklist
- [ ] Cavity plan nelkul nincs viselkedesvaltozas.
- [ ] DB projectionben nincs virtual part_revision_id.
- [ ] Internal child abszolut transform helyes.
- [ ] Top-level child instance offset es unplaced offset helyes.
- [ ] Parent-child metadata teljes.
- [ ] Instance ID-k nem utkoznek.
- [ ] Repo gate reporttal lefutott.

## Tesztterv
- `python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py`
- `python3 scripts/smoke_cavity_t5_result_normalizer_expansion.py`
- `python3 scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py`
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t5_result_normalizer_expansion.md`

## Elfogadasi kriteriumok
- Parent es child projection sorok lathatok es instance szinten konzisztensen
  visszakovethetok.
- Internal child nem jelenik meg top-level quantitykent masodszor.
- Regebbi `nesting_engine_v2` output cavity plan nelkul zold marad.

## Rollback
Normalizer diff es tesztek visszavonhatok. T4 artifact persist tovabbra is
letezhet, de expansion nelkul nem tekintheto user-facing kesznek.

## Kockazatok
- Origin reference mismatch pontatlan child helyzethez vezethet.
- Area/utilization duplazas vagy kihagyas, ha child/parent area policy nincs
  explicit reportolva.

## Vegso reportban kotelezo bizonyitek
- Transform formula path/line hivatkozas.
- Unit/smoke evidence a virtual ID eltuntetesre es instance offsetre.
