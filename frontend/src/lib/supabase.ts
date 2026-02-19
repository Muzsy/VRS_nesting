import { createClient } from "@supabase/supabase-js";

const metaEnv = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env;
const url = metaEnv.VITE_SUPABASE_URL;
const anonKey = metaEnv.VITE_SUPABASE_ANON_KEY;
export const E2E_BYPASS_AUTH = metaEnv.VITE_E2E_BYPASS_AUTH === "1";
export const E2E_BYPASS_TOKEN = "e2e-bypass-access-token";

if (!url || !anonKey) {
  // Keep runtime failure explicit for local setup issues.
  // eslint-disable-next-line no-console
  console.error("Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY");
}

export const supabase = createClient(url ?? "", anonKey ?? "");

export async function getAccessToken(): Promise<string> {
  if (E2E_BYPASS_AUTH) {
    return E2E_BYPASS_TOKEN;
  }
  const { data, error } = await supabase.auth.getSession();
  if (error) {
    throw new Error(error.message);
  }
  const token = data.session?.access_token;
  if (!token) {
    throw new Error("No active session");
  }
  return token;
}
