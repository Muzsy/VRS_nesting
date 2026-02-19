import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { getAccessToken } from "../lib/supabase";
import type { Project } from "../lib/types";

interface ProjectListItem extends Project {
  runCount: number;
}

function formatDate(value?: string | null): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createName, setCreateName] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [creating, setCreating] = useState(false);

  async function loadProjects() {
    setLoading(true);
    setError("");
    try {
      const token = await getAccessToken();
      const response = await api.listProjects(token);
      const enriched = await Promise.all(
        response.items.map(async (project) => {
          try {
            const runs = await api.listRuns(token, project.id);
            return { ...project, runCount: runs.total };
          } catch {
            return { ...project, runCount: 0 };
          }
        })
      );
      setProjects(enriched);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadProjects();
  }, []);

  async function handleCreateProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = createName.trim();
    if (!name) {
      setError("Project name is required.");
      return;
    }

    setCreating(true);
    setError("");
    try {
      const token = await getAccessToken();
      await api.createProject(token, { name, description: createDescription.trim() });
      setCreateName("");
      setCreateDescription("");
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create project failed.");
    } finally {
      setCreating(false);
    }
  }

  async function handleArchiveProject(projectId: string) {
    setError("");
    try {
      const token = await getAccessToken();
      await api.archiveProject(token, projectId);
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Archive project failed.");
    }
  }

  const hasProjects = projects.length > 0;
  const orderedProjects = useMemo(
    () => [...projects].sort((a, b) => (b.updated_at ?? b.created_at ?? "").localeCompare(a.updated_at ?? a.created_at ?? "")),
    [projects]
  );

  return (
    <section className="space-y-6">
      <header className="rounded-xl border border-mist bg-white p-5">
        <h1 className="text-2xl font-bold tracking-tight">Projects</h1>
        <p className="mt-1 text-sm text-slate">Create and manage nesting projects, then drill down to uploads and runs.</p>
        <form className="mt-5 grid gap-3 md:grid-cols-[1fr_1fr_auto]" onSubmit={handleCreateProject}>
          <input
            className="rounded-md border border-mist px-3 py-2 outline-none ring-accent focus:ring-2"
            onChange={(event) => setCreateName(event.target.value)}
            placeholder="Project name"
            value={createName}
          />
          <input
            className="rounded-md border border-mist px-3 py-2 outline-none ring-accent focus:ring-2"
            onChange={(event) => setCreateDescription(event.target.value)}
            placeholder="Description (optional)"
            value={createDescription}
          />
          <button className="rounded-md bg-accent px-4 py-2 font-semibold text-white disabled:opacity-60" disabled={creating} type="submit">
            {creating ? "Creating..." : "New project"}
          </button>
        </form>
        {error && <p className="mt-3 rounded-md border border-danger/40 bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}
      </header>

      <section className="rounded-xl border border-mist bg-white p-5">
        <h2 className="text-lg font-semibold">Project list</h2>
        {loading && <p className="mt-3 text-sm text-slate">Loading projects...</p>}

        {!loading && !hasProjects && (
          <div className="mt-4 rounded-md border border-dashed border-mist bg-slate-50 p-5 text-sm text-slate">
            No projects yet. Create one above to start the DXF upload and run flow.
          </div>
        )}

        {!loading && hasProjects && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[720px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-mist text-left text-slate">
                  <th className="py-2">Name</th>
                  <th className="py-2">Run count</th>
                  <th className="py-2">Last modified</th>
                  <th className="py-2">Description</th>
                  <th className="py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {orderedProjects.map((project) => {
                  const lastModified = project.updated_at ?? project.created_at ?? null;
                  return (
                    <tr className="border-b border-mist/70" key={project.id}>
                      <td className="py-3 font-medium">
                        <Link className="text-accent underline" to={`/projects/${project.id}`}>
                          {project.name}
                        </Link>
                      </td>
                      <td className="py-3">{project.runCount}</td>
                      <td className="py-3">{formatDate(lastModified)}</td>
                      <td className="max-w-[260px] truncate py-3 text-slate">{project.description ?? "-"}</td>
                      <td className="py-3 text-right">
                        <div className="inline-flex items-center gap-2">
                          <Link className="rounded-md border border-mist px-3 py-1.5 text-slate hover:bg-slate-100" to={`/projects/${project.id}`}>
                            Open
                          </Link>
                          <button
                            className="rounded-md border border-danger/30 px-3 py-1.5 text-danger hover:bg-red-50"
                            onClick={() => void handleArchiveProject(project.id)}
                            type="button"
                          >
                            Archive
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}
