// deno-lint-ignore-file no-explicit-any
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

type CleanupCandidate = {
  candidate_type: string;
  row_id: string;
  storage_key: string;
};

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
const STORAGE_BUCKET = Deno.env.get("API_STORAGE_BUCKET") ?? "vrs-nesting";
const LOCK_NAME = Deno.env.get("CLEANUP_LOCK_NAME") ?? "cleanup-worker";
const LOCK_TTL_SECONDS = Number.parseInt(Deno.env.get("CLEANUP_LOCK_TTL_SECONDS") ?? "600", 10);
const BATCH_SIZE = Number.parseInt(Deno.env.get("CLEANUP_BATCH_SIZE") ?? "200", 10);

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  throw new Error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set");
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, {
  auth: { persistSession: false },
});

function encodeStorageKeyForPath(storageKey: string): string {
  return storageKey
    .split("/")
    .map((token) => encodeURIComponent(token))
    .join("/");
}

async function deleteStorageObject(storageKey: string): Promise<void> {
  const encodedKey = encodeStorageKeyForPath(storageKey);
  const endpoint = `${SUPABASE_URL}/storage/v1/object/${STORAGE_BUCKET}/${encodedKey}`;
  const response = await fetch(endpoint, {
    method: "DELETE",
    headers: {
      apikey: SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    },
  });
  if (response.status === 404) {
    return;
  }
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`storage delete failed status=${response.status} body=${text.slice(0, 300)}`);
  }
}

async function acquireLock(): Promise<boolean> {
  const { data, error } = await supabase.rpc("try_acquire_cleanup_lock", {
    p_lock_name: LOCK_NAME,
    p_owner: "edge-cleanup-worker",
    p_ttl_seconds: LOCK_TTL_SECONDS,
  });
  if (error) {
    throw new Error(`lock acquire failed: ${error.message}`);
  }
  return Boolean(data);
}

async function releaseLock(): Promise<void> {
  const { error } = await supabase.rpc("release_cleanup_lock", {
    p_lock_name: LOCK_NAME,
  });
  if (error) {
    throw new Error(`lock release failed: ${error.message}`);
  }
}

async function listCandidates(): Promise<CleanupCandidate[]> {
  const { data, error } = await supabase.rpc("list_cleanup_candidates", {
    p_limit: BATCH_SIZE,
  });
  if (error) {
    throw new Error(`list candidates failed: ${error.message}`);
  }
  if (!Array.isArray(data)) {
    return [];
  }
  return data
    .filter((row) => row && typeof row === "object")
    .map((row) => ({
      candidate_type: String((row as any).candidate_type ?? ""),
      row_id: String((row as any).row_id ?? ""),
      storage_key: String((row as any).storage_key ?? ""),
    }))
    .filter((row) => row.candidate_type && row.row_id && row.storage_key);
}

async function deleteCandidateRow(candidate: CleanupCandidate): Promise<boolean> {
  const { data, error } = await supabase.rpc("delete_cleanup_candidate", {
    p_candidate_type: candidate.candidate_type,
    p_row_id: candidate.row_id,
  });
  if (error) {
    throw new Error(`delete candidate row failed: ${error.message}`);
  }
  return Boolean(data);
}

Deno.serve(async () => {
  const startedAt = Date.now();
  let lockAcquired = false;
  try {
    lockAcquired = await acquireLock();
    if (!lockAcquired) {
      return Response.json(
        {
          status: "skipped_locked",
          lock_name: LOCK_NAME,
        },
        { status: 200 },
      );
    }

    const candidates = await listCandidates();
    let deletedStorage = 0;
    let deletedRows = 0;

    for (const candidate of candidates) {
      await deleteStorageObject(candidate.storage_key);
      deletedStorage += 1;

      const rowDeleted = await deleteCandidateRow(candidate);
      if (rowDeleted) {
        deletedRows += 1;
      }
    }

    return Response.json(
      {
        status: "ok",
        lock_name: LOCK_NAME,
        candidates: candidates.length,
        deleted_storage_objects: deletedStorage,
        deleted_rows: deletedRows,
        elapsed_ms: Date.now() - startedAt,
      },
      { status: 200 },
    );
  } catch (error) {
    return Response.json(
      {
        status: "error",
        message: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    );
  } finally {
    if (lockAcquired) {
      try {
        await releaseLock();
      } catch (_err) {
        // lock release best effort
      }
    }
  }
});
