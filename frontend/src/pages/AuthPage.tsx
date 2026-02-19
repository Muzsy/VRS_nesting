import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import type { Session } from "@supabase/supabase-js";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabase";

type AuthMode = "login" | "signup" | "reset";

function normalizeMode(raw: string | null): AuthMode {
  if (raw === "signup" || raw === "reset") {
    return raw;
  }
  return "login";
}

export function AuthPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const queryMode = useMemo(() => normalizeMode(new URLSearchParams(location.search).get("mode")), [location.search]);

  const [mode, setMode] = useState<AuthMode>(queryMode);
  const [session, setSession] = useState<Session | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  useEffect(() => {
    setMode(queryMode);
  }, [queryMode]);

  useEffect(() => {
    let mounted = true;
    supabase.auth
      .getSession()
      .then(({ data }) => {
        if (mounted) {
          setSession(data.session);
          if (data.session) {
            navigate("/projects", { replace: true });
          }
        }
      })
      .catch(() => {
        if (mounted) {
          setSession(null);
        }
      });

    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      if (nextSession) {
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
      if (!trimmedEmail) {
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
      } else {
        const redirectTo = `${window.location.origin}/auth?mode=login`;
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
    const params = new URLSearchParams();
    params.set("mode", nextMode);
    navigate(`/auth?${params.toString()}`, { replace: true });
  }

  if (session) {
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
          </div>
        </article>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <h2 className="text-xl font-semibold text-ink">
            {mode === "login" ? "Sign in" : mode === "signup" ? "Create account" : "Reset password"}
          </h2>

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

          {mode === "signup" && (
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
            {loading ? "Please wait..." : mode === "login" ? "Sign in" : mode === "signup" ? "Create account" : "Send reset email"}
          </button>

          <p className="text-xs text-slate">
            Use Supabase email/password auth. Verification email flow depends on project auth settings.
          </p>
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
        </form>
      </section>
    </main>
  );
}
