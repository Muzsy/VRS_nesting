import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { Session } from "@supabase/supabase-js";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { E2E_BYPASS_AUTH, supabase } from "../lib/supabase";

type AuthMode = "login" | "signup" | "reset" | "update-password";

function normalizeMode(raw: string | null): AuthMode {
  if (raw === "signup" || raw === "reset") {
    return raw;
  }
  return "login";
}

function isRecoveryFlow(search: string, hash: string): boolean {
  const searchParams = new URLSearchParams(search);
  if (searchParams.get("type") === "recovery") {
    return true;
  }
  const hashRaw = hash.startsWith("#") ? hash.slice(1) : hash;
  if (!hashRaw) {
    return false;
  }
  const hashParams = new URLSearchParams(hashRaw);
  return hashParams.get("type") === "recovery";
}

export function AuthPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const queryMode = useMemo(() => normalizeMode(new URLSearchParams(location.search).get("mode")), [location.search]);
  const recoveryFromUrl = useMemo(() => isRecoveryFlow(location.search, location.hash), [location.search, location.hash]);

  const [mode, setMode] = useState<AuthMode>(recoveryFromUrl ? "update-password" : queryMode);
  const [session, setSession] = useState<Session | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const inRecoveryFlowRef = useRef(recoveryFromUrl);

  useEffect(() => {
    inRecoveryFlowRef.current = recoveryFromUrl;
    setMode(recoveryFromUrl ? "update-password" : queryMode);
  }, [queryMode, recoveryFromUrl]);

  useEffect(() => {
    if (E2E_BYPASS_AUTH) {
      navigate("/projects", { replace: true });
      return;
    }

    let mounted = true;
    supabase.auth
      .getSession()
      .then(({ data }) => {
        if (mounted) {
          setSession(data.session);
          if (data.session) {
            if (inRecoveryFlowRef.current) {
              setMode("update-password");
            } else {
              navigate("/projects", { replace: true });
            }
          }
        }
      })
      .catch(() => {
        if (mounted) {
          setSession(null);
        }
      });

    const { data } = supabase.auth.onAuthStateChange((event, nextSession) => {
      setSession(nextSession);
      if (event === "PASSWORD_RECOVERY") {
        inRecoveryFlowRef.current = true;
        setMode("update-password");
        setError("");
        setInfo("Reset link confirmed. Set a new password.");
        return;
      }
      if (nextSession && !inRecoveryFlowRef.current) {
        navigate("/projects", { replace: true });
      }
    });
    return () => {
      mounted = false;
      data.subscription.unsubscribe();
    };
  }, [navigate]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setInfo("");
    setLoading(true);
    try {
      const trimmedEmail = email.trim();
      if (mode !== "update-password" && !trimmedEmail) {
        throw new Error("Email is required.");
      }

      if (mode === "login") {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email: trimmedEmail,
          password,
        });
        if (signInError) {
          throw new Error(signInError.message);
        }
        navigate("/projects", { replace: true });
      } else if (mode === "signup") {
        if (password.length < 6) {
          throw new Error("Password must be at least 6 characters.");
        }
        if (password !== passwordConfirm) {
          throw new Error("Password confirmation does not match.");
        }
        const { data, error: signUpError } = await supabase.auth.signUp({
          email: trimmedEmail,
          password,
        });
        if (signUpError) {
          throw new Error(signUpError.message);
        }
        if (data.session) {
          navigate("/projects", { replace: true });
        } else {
          setInfo("Registration succeeded. Check your email to verify the account, then sign in.");
        }
      } else if (mode === "update-password") {
        if (password.length < 6) {
          throw new Error("Password must be at least 6 characters.");
        }
        if (password !== passwordConfirm) {
          throw new Error("Password confirmation does not match.");
        }
        const { error: updateError } = await supabase.auth.updateUser({ password });
        if (updateError) {
          throw new Error(updateError.message);
        }
        inRecoveryFlowRef.current = false;
        setInfo("Password updated successfully. Redirecting...");
        navigate("/projects", { replace: true });
      } else {
        const redirectTo = `${window.location.origin}/auth`;
        const { error: resetError } = await supabase.auth.resetPasswordForEmail(trimmedEmail, { redirectTo });
        if (resetError) {
          throw new Error(resetError.message);
        }
        setInfo("Password reset email sent. Check your inbox.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  function handleModeChange(nextMode: AuthMode) {
    if (nextMode === "update-password") {
      return;
    }
    inRecoveryFlowRef.current = false;
    const params = new URLSearchParams();
    params.set("mode", nextMode);
    navigate(`/auth?${params.toString()}`, { replace: true });
  }

  if (session && mode !== "update-password") {
    return null;
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl items-center justify-center px-6 py-10">
      <section className="grid w-full max-w-4xl gap-8 rounded-2xl border border-mist bg-white p-6 shadow-sm md:grid-cols-[1.2fr_1fr] md:p-10">
        <article>
          <h1 className="text-3xl font-bold tracking-tight text-ink">VRS Nesting web platform</h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate">
            Auth-protected workflow for project setup, DXF uploads, run execution, viewer inspection and export.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            {mode !== "update-password" ? (
              <>
                <button
                  className={`rounded-md px-3 py-2 text-sm font-medium ${mode === "login" ? "bg-accent text-white" : "bg-sky-100 text-slate"}`}
                  onClick={() => handleModeChange("login")}
                  type="button"
                >
                  Login
                </button>
                <button
                  className={`rounded-md px-3 py-2 text-sm font-medium ${mode === "signup" ? "bg-accent text-white" : "bg-sky-100 text-slate"}`}
                  onClick={() => handleModeChange("signup")}
                  type="button"
                >
                  Signup
                </button>
                <button
                  className={`rounded-md px-3 py-2 text-sm font-medium ${mode === "reset" ? "bg-accent text-white" : "bg-sky-100 text-slate"}`}
                  onClick={() => handleModeChange("reset")}
                  type="button"
                >
                  Password reset
                </button>
              </>
            ) : (
              <p className="rounded-md border border-mist bg-sky-50 px-3 py-2 text-sm text-slate">
                Password recovery flow is active. Set your new password below.
              </p>
            )}
          </div>
        </article>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <h2 className="text-xl font-semibold text-ink">
            {mode === "login" ? "Sign in" : mode === "signup" ? "Create account" : mode === "reset" ? "Reset password" : "Set new password"}
          </h2>

          {mode !== "update-password" && (
            <label className="block space-y-1">
              <span className="text-sm font-medium text-slate">Email</span>
              <input
                autoComplete="email"
                className="w-full rounded-md border border-mist px-3 py-2 outline-none ring-accent focus:ring-2"
                onChange={(event) => setEmail(event.target.value)}
                type="email"
                value={email}
              />
            </label>
          )}

          {mode !== "reset" && (
            <label className="block space-y-1">
              <span className="text-sm font-medium text-slate">Password</span>
              <input
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                className="w-full rounded-md border border-mist px-3 py-2 outline-none ring-accent focus:ring-2"
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                value={password}
              />
            </label>
          )}

          {(mode === "signup" || mode === "update-password") && (
            <label className="block space-y-1">
              <span className="text-sm font-medium text-slate">Confirm password</span>
              <input
                autoComplete="new-password"
                className="w-full rounded-md border border-mist px-3 py-2 outline-none ring-accent focus:ring-2"
                onChange={(event) => setPasswordConfirm(event.target.value)}
                type="password"
                value={passwordConfirm}
              />
            </label>
          )}

          {error && <p className="rounded-md border border-danger/40 bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}
          {info && <p className="rounded-md border border-success/40 bg-green-50 px-3 py-2 text-sm text-success">{info}</p>}

          <button className="w-full rounded-md bg-accent px-4 py-2 font-semibold text-white disabled:opacity-60" disabled={loading} type="submit">
            {loading ? "Please wait..." : mode === "login" ? "Sign in" : mode === "signup" ? "Create account" : mode === "reset" ? "Send reset email" : "Update password"}
          </button>

          <p className="text-xs text-slate">
            Use Supabase email/password auth. Verification email flow depends on project auth settings.
          </p>
          {mode !== "update-password" && (
            <p className="text-xs text-slate">
              Quick access:{" "}
              <Link className="text-accent underline" to="/auth?mode=login">
                login
              </Link>{" "}
              /{" "}
              <Link className="text-accent underline" to="/auth?mode=signup">
                signup
              </Link>{" "}
              /{" "}
              <Link className="text-accent underline" to="/auth?mode=reset">
                reset
              </Link>
            </p>
          )}
        </form>
      </section>
    </main>
  );
}
