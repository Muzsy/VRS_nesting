import { createClient } from "@supabase/supabase-js";

const metaEnv = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env;
const url = metaEnv.VITE_SUPABASE_URL;
const anonKey = metaEnv.VITE_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  // Keep runtime failure explicit for local setup issues.
  // eslint-disable-next-line no-console
  console.error("Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY");
}

export const supabase = createClient(url ?? "", anonKey ?? "");

export async function getAccessToken(): Promise<string> {
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
