-- H2-E5-T3: machine-neutral exporter — artifact kind + bridge update.
-- Scope: introduce manufacturing_plan_json artifact kind and update
-- the legacy <-> enum bridge functions so the generic artifact list/signed
-- URL flow handles this type consistently.
-- Does NOT modify earlier truth tables (run_manufacturing_plans, etc.).
-- Does NOT create machine-specific adapter, worker auto-hook, or export UI scope.

-- 1) Add manufacturing_plan_json to artifact_kind enum --------------------

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_enum e
    JOIN pg_type t ON t.oid = e.enumtypid
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app'
      AND t.typname = 'artifact_kind'
      AND e.enumlabel = 'manufacturing_plan_json'
  ) THEN
    ALTER TYPE app.artifact_kind ADD VALUE 'manufacturing_plan_json';
  END IF;
END
$$;

-- 2) Update legacy_artifact_type_to_kind bridge -----------------------------

CREATE OR REPLACE FUNCTION app.legacy_artifact_type_to_kind(legacy_artifact_type text)
RETURNS app.artifact_kind
LANGUAGE sql
IMMUTABLE
SET search_path = app
AS $$
  SELECT CASE coalesce(legacy_artifact_type, '')
    WHEN 'sheet_dxf' THEN 'sheet_dxf'::app.artifact_kind
    WHEN 'sheet_svg' THEN 'sheet_svg'::app.artifact_kind
    WHEN 'bundle_zip' THEN 'bundle_zip'::app.artifact_kind
    WHEN 'machine_program' THEN 'machine_program'::app.artifact_kind
    WHEN 'report_json' THEN 'report_json'::app.artifact_kind
    WHEN 'run_log' THEN 'log'::app.artifact_kind
    WHEN 'solver_output' THEN 'solver_output'::app.artifact_kind
    WHEN 'solver_input' THEN 'solver_output'::app.artifact_kind
    WHEN 'manufacturing_preview_svg' THEN 'manufacturing_preview_svg'::app.artifact_kind
    WHEN 'manufacturing_plan_json' THEN 'manufacturing_plan_json'::app.artifact_kind
    ELSE 'log'::app.artifact_kind
  END;
$$;

-- 3) Update artifact_kind_to_legacy_type bridge -----------------------------
-- The existing function already falls back to metadata->>'legacy_artifact_type'
-- when present, and otherwise uses kind::text. For manufacturing_plan_json
-- the kind::text fallback produces the correct legacy type string, so no
-- structural change is needed. We recreate it here to document the addition.

CREATE OR REPLACE FUNCTION app.artifact_kind_to_legacy_type(
  kind app.artifact_kind,
  metadata jsonb DEFAULT '{}'::jsonb
)
RETURNS text
LANGUAGE sql
STABLE
SET search_path = app
AS $$
  SELECT coalesce(
    metadata->>'legacy_artifact_type',
    CASE kind
      WHEN 'log' THEN 'run_log'
      ELSE kind::text
    END
  );
$$;

-- 4) Re-grant execute on bridge functions -----------------------------------

GRANT EXECUTE ON FUNCTION app.legacy_artifact_type_to_kind(text) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION app.artifact_kind_to_legacy_type(app.artifact_kind, jsonb) TO authenticated, service_role;
