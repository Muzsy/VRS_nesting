-- H0-E2-T1 base migration: app schema + core enums
-- Scope intentionally limited to extensions, schema, and enum inventory.
-- No domain tables are created in this migration.

create extension if not exists pgcrypto;

create schema if not exists app;

-- Project lifecycle
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app' AND t.typname = 'project_lifecycle'
  ) THEN
    CREATE TYPE app.project_lifecycle AS ENUM (
      'draft',
      'active',
      'archived'
    );
  END IF;
END
$$;

-- Revision lifecycle (part/sheet revision state)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app' AND t.typname = 'revision_lifecycle'
  ) THEN
    CREATE TYPE app.revision_lifecycle AS ENUM (
      'draft',
      'approved',
      'deprecated'
    );
  END IF;
END
$$;

-- File/object kind
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app' AND t.typname = 'file_kind'
  ) THEN
    CREATE TYPE app.file_kind AS ENUM (
      'source_dxf',
      'source_svg',
      'import_report',
      'artifact'
    );
  END IF;
END
$$;

-- Geometry role (definition side)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app' AND t.typname = 'geometry_role'
  ) THEN
    CREATE TYPE app.geometry_role AS ENUM (
      'part',
      'sheet'
    );
  END IF;
END
$$;

-- Geometry validation status
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app' AND t.typname = 'geometry_validation_status'
  ) THEN
    CREATE TYPE app.geometry_validation_status AS ENUM (
      'uploaded',
      'parsed',
      'validated',
      'approved',
      'rejected'
    );
  END IF;
END
$$;

-- Canonical geometry derivative kind
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app' AND t.typname = 'geometry_derivative_kind'
  ) THEN
    CREATE TYPE app.geometry_derivative_kind AS ENUM (
      'nesting_canonical',
      'manufacturing_canonical',
      'viewer_outline'
    );
  END IF;
END
$$;

-- Sheet modelling enums
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app' AND t.typname = 'sheet_geometry_type'
  ) THEN
    CREATE TYPE app.sheet_geometry_type AS ENUM (
      'rect',
      'polygon'
    );
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app' AND t.typname = 'sheet_source_kind'
  ) THEN
    CREATE TYPE app.sheet_source_kind AS ENUM (
      'manual_rect',
      'source_dxf',
      'derived_remnant'
    );
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app' AND t.typname = 'sheet_availability_status'
  ) THEN
    CREATE TYPE app.sheet_availability_status AS ENUM (
      'available',
      'reserved',
      'consumed',
      'quarantined'
    );
  END IF;
END
$$;

-- Snapshot-first run lifecycle split:
-- request state != snapshot state != attempt state
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app' AND t.typname = 'run_request_status'
  ) THEN
    CREATE TYPE app.run_request_status AS ENUM (
      'draft',
      'requested',
      'snapshot_building',
      'snapshot_ready',
      'queued',
      'completed',
      'cancelled'
    );
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app' AND t.typname = 'run_snapshot_status'
  ) THEN
    CREATE TYPE app.run_snapshot_status AS ENUM (
      'building',
      'ready',
      'invalid'
    );
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app' AND t.typname = 'run_attempt_status'
  ) THEN
    CREATE TYPE app.run_attempt_status AS ENUM (
      'leased',
      'running',
      'succeeded',
      'failed',
      'timed_out',
      'cancelled',
      'lost_lease'
    );
  END IF;
END
$$;

-- Result/projection/export-side enums
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app' AND t.typname = 'artifact_kind'
  ) THEN
    CREATE TYPE app.artifact_kind AS ENUM (
      'solver_output',
      'report_json',
      'sheet_dxf',
      'sheet_svg',
      'bundle_zip',
      'machine_program',
      'log'
    );
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'app' AND t.typname = 'placement_policy'
  ) THEN
    CREATE TYPE app.placement_policy AS ENUM (
      'hard_first',
      'soft_prefer',
      'normal',
      'defer'
    );
  END IF;
END
$$;

-- NOTE:
-- This migration intentionally does not create domain tables (`profiles`, `projects`, `run_*`, etc.).
-- Table-level schema rollout belongs to follow-up H0-E2 tasks.
