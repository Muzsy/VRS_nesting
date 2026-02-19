import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabase";

export function Layout() {
  const [user, setUser] = useState<User | null>(null);
  const [signingOut, setSigningOut] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    let mounted = true;

    supabase.auth
      .getUser()
      .then(({ data }) => {
        if (mounted) {
          setUser(data.user);
        }
      })
      .catch(() => {
        if (mounted) {
          setUser(null);
        }
      });

    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => {
      mounted = false;
      data.subscription.unsubscribe();
    };
  }, []);

  async function handleSignOut() {
    setSigningOut(true);
    await supabase.auth.signOut();
    setSigningOut(false);
    navigate("/auth", { replace: true });
  }

  const projectsActive = location.pathname.startsWith("/projects");

  return (
    <div className="min-h-screen text-ink">
      <header className="border-b border-mist bg-white/80 backdrop-blur">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-5">
            <span className="text-lg font-bold tracking-tight">VRS Nesting Platform</span>
            <Link
              className={`rounded-md px-3 py-2 text-sm font-medium ${
                projectsActive ? "bg-accent text-white" : "text-slate hover:bg-sky-100"
              }`}
              to="/projects"
            >
              Projects
            </Link>
          </div>
          <div className="flex items-center gap-3">
            <span className="max-w-[280px] truncate text-sm text-slate">{user?.email ?? "Signed in"}</span>
            <button
              className="rounded-md border border-mist bg-white px-3 py-2 text-sm font-medium text-slate hover:bg-slate-100 disabled:opacity-60"
              disabled={signingOut}
              onClick={handleSignOut}
              type="button"
            >
              {signingOut ? "Signing out..." : "Sign out"}
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl px-6 py-6">
        <Outlet />
      </main>
    </div>
  );
}
