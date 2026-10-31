"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, mutationOptions } from "./api";
import { errorMessage } from "./format";
import { ensureArchitecture } from "./legacy-upgrade";
import type {
  BuildingSnapshot,
  ProjectSummary,
  BriefTurn,
  DesignResponse,
  ChatMessage,
  ConversationResponse,
  ExportRecord,
  Method,
  Mutation,
  Result,
  Revision,
} from "./types";
export function useStudio(
  onSnapshot?: (
    snapshot: BuildingSnapshot,
    previous: BuildingSnapshot | null,
  ) => void,
) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [ready, setReady] = useState(false);
  const lastDesignRequest = useRef<{ body: string; key: string } | null>(null);
  const [snap, setSnap] = useState<BuildingSnapshot | null>(null),
    [results, setResults] = useState<Result[]>([]),
    [methods, setMethods] = useState<Method[]>([]),
    [history, setHistory] = useState<Revision[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [activity, setActivity] = useState("Opening your studio…");
  const [artifact, setArtifact] = useState<ExportRecord | null>(null),
    [provider, setProvider] = useState<boolean | null>(null),
    [canUndo, setCanUndo] = useState(false),
    [canRedo, setCanRedo] = useState(false);
  const undoStack = useRef<string[]>([]),
    redoStack = useRef<string[]>([]),
    init = useRef(false),
    current = useRef<BuildingSnapshot | null>(null),
    lock = useRef(false);
  const addMessage = useCallback(
    (message: Omit<ChatMessage, "id">) =>
      setMessages((m) => [...m, { ...message, id: crypto.randomUUID() }]),
    [],
  );
  async function load(pid: string, rid: string, upgradeLegacy = false) {
    let snapshot = await api<BuildingSnapshot>(
      `/api/v1/projects/${pid}/revisions/${rid}`,
    );
    let upgraded = false;
    if (upgradeLegacy) {
      setBusy("Opening your saved building");
      const opened = await ensureArchitecture(snapshot, api);
      snapshot = opened.snapshot;
      rid = snapshot.revision_id;
      upgraded = opened.upgraded;
      if (opened.error) setError(errorMessage(opened.error));
    }
    const previous = current.current;
    current.current = snapshot;
    setSnap(snapshot);
    setProjects((list) => [
      {
        project_id: snapshot.project_id,
        revision_id: snapshot.revision_id,
        revision_number: snapshot.revision_number,
        title: snapshot.title,
        created_at: snapshot.created_at,
        content_hash: snapshot.content_hash,
      },
      ...list.filter((p) => p.project_id !== snapshot.project_id),
    ]);
    onSnapshot?.(snapshot, previous);
    setResults([]);
    setArtifact(null);
    setMethods([]);
    setHistory([]);
    localStorage.setItem("nodesnap.project", pid);
    setBusy("Updating calculations");
    const [a, c, h] = await Promise.allSettled([
      api<{ results: Result[] }>(`/api/v1/projects/${pid}/analyses`, {
        method: "POST",
        body: JSON.stringify({ revision_id: rid }),
      }),
      api<{ methods: Method[] }>(
        `/api/v1/projects/${pid}/coverage?revision_id=${rid}`,
      ),
      api<Revision[]>(`/api/v1/projects/${pid}/revisions`),
    ]);
    if (current.current?.revision_id !== rid) return;
    if (a.status === "fulfilled")
      setResults(a.value.results.filter((r) => r.revision_id === rid));
    else
      setError(
        `Model saved. Calculations need a retry: ${errorMessage(a.reason)}`,
      );
    if (c.status === "fulfilled") setMethods(c.value.methods);
    if (h.status === "fulfilled") setHistory(h.value);
    return upgraded;
  }
  async function loadConversation(pid: string) {
    const rows = await api<
      Array<{
        id: string;
        text: string;
        explanation?: string;
        issue?: { message: string };
        committed_revision_number?: number;
      }>
    >(`/api/v1/projects/${pid}/conversations`);
    setMessages(
      rows.length
        ? rows.flatMap((v) => [
            { id: v.id + "-user", role: "user" as const, text: v.text },
            {
              id: v.id + "-reply",
              role: "assistant" as const,
              text: v.explanation ?? v.issue?.message ?? "Request recorded.",
              revision: v.committed_revision_number,
            },
          ])
        : [
            {
              id: "intro",
              role: "assistant",
              text: "Your building is ready to explore. Choose a floor, describe a change, or start a completely new design.",
            },
          ],
    );
  }
  function resetHistory() {
    undoStack.current = [];
    redoStack.current = [];
    setCanUndo(false);
    setCanRedo(false);
  }
  async function start() {
    if (lock.current) return;
    lock.current = true;
    setBusy("Opening studio");
    setError("");
    try {
      await api("/api/v1/demo/sessions", { method: "POST" });
      setReady(true);
      const [list, health] = await Promise.allSettled([
        api<ProjectSummary[]>("/api/v1/projects"),
        api<{ meta_configured?: boolean; meta?: { configured?: boolean } }>(
          "/health",
        ),
      ]);
      if (list.status === "fulfilled") setProjects(list.value);
      if (health.status === "fulfilled")
        setProvider(
          health.value.meta_configured ?? health.value.meta?.configured ?? null,
        );
      const pid = localStorage.getItem("nodesnap.project");
      if (pid) {
        try {
          const project = await api<ProjectSummary>(`/api/v1/projects/${pid}`);
          const upgraded = await load(pid, project.revision_id, true);
          resetHistory();
          await loadConversation(pid);
          if (upgraded) restoredVillaMessage();
          setActivity("Model saved. Explore a floor or describe a change.");
        } catch (e) {
          if (e instanceof ApiError && [403, 404].includes(e.status)) {
            localStorage.removeItem("nodesnap.project");
            setActivity("Describe your first building.");
          } else throw e;
        }
      } else setActivity("Describe your first building.");
    } catch (e) {
      setError(errorMessage(e));
      setActivity("Studio could not connect. Retry to continue.");
    } finally {
      lock.current = false;
      setBusy("");
    }
  }
  async function openProject(pid: string) {
    if (lock.current) return;
    lock.current = true;
    setBusy("Opening building");
    setError("");
    try {
      const project = await api<ProjectSummary>(`/api/v1/projects/${pid}`);
      setMessages([]);
      const upgraded = await load(pid, project.revision_id, true);
      resetHistory();
      await loadConversation(pid);
      if (upgraded) restoredVillaMessage();
      setActivity("Building opened. Continue where you left off.");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      lock.current = false;
      setBusy("");
    }
  }
  function restoredVillaMessage() {
    addMessage({
      role: "assistant",
      text: "Your original villa is ready again. Its rooms, pool and saved history are retained. Stair access and service zones were coordinated in a new revision; the adjustments are recorded with the design.",
      revision: current.current?.revision_number,
    });
  }
  async function openDemo() {
    if (lock.current) return;
    lock.current = true;
    setBusy("Opening example villa");
    setError("");
    try {
      const project = await api<ProjectSummary>("/api/v1/projects", {
        method: "POST",
        body: JSON.stringify({ seed: true }),
      });
      setMessages([]);
      await load(project.project_id, project.revision_id);
      resetHistory();
      await loadConversation(project.project_id);
      setActivity(
        "Example villa opened. You can edit it or create your own building.",
      );
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      lock.current = false;
      setBusy("");
    }
  }
  async function createDesign(
    text: string,
    briefHistory: BriefTurn[],
  ): Promise<DesignResponse> {
    if (lock.current)
      return {
        execution_status: "blocked",
        explanation: "Please wait for the current request to finish.",
      };
    lock.current = true;
    setBusy("Developing your building brief");
    setError("");
    const body = JSON.stringify({ text, brief_history: briefHistory });
    if (lastDesignRequest.current?.body !== body)
      lastDesignRequest.current = { body, key: crypto.randomUUID() };
    try {
      const result = await api<DesignResponse>("/api/v1/designs", {
        method: "POST",
        body,
        headers: { "Idempotency-Key": lastDesignRequest.current!.key },
      });
      if (result.project_id && result.committed_revision_id) {
        setBusy("Opening your new building");
        setMessages([]);
        await load(result.project_id, result.committed_revision_id);
        resetHistory();
        await loadConversation(result.project_id);
        lastDesignRequest.current = null;
        setActivity(
          "Your new building is ready. Explore its plans or keep designing.",
        );
      }
      if (!result.project_id && result.execution_status === "error")
        lastDesignRequest.current = null;
      return result;
    } catch (e) {
      const message = errorMessage(e);
      setError(message);
      return { execution_status: "error", explanation: message };
    } finally {
      lock.current = false;
      setBusy("");
    }
  }
  // Session initialization is intentionally once per mount; mutable current state is read by commands.
  useEffect(() => {
    if (init.current) return;
    init.current = true;
    void start();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initialize one session per mount
  }, []); // one session, even with development Strict Mode
  async function failure(e: unknown) {
    const msg = errorMessage(e);
    setError(msg);
    setActivity("Request needs attention. Saved revisions are preserved.");
    if (e instanceof ApiError && e.status === 412 && current.current) {
      const s = current.current;
      const p = await api<{ revision_id: string }>(
        `/api/v1/projects/${s.project_id}`,
      );
      await load(s.project_id, p.revision_id);
      setError(
        "Another edit advanced this model. The latest revision is loaded; please try your change again.",
      );
    }
  }
  async function mutate(
    path: string,
    body: Record<string, unknown>,
    label: string,
  ) {
    const s = current.current;
    if (!s || lock.current) return;
    lock.current = true;
    setBusy(label);
    setError("");
    try {
      const r = await api<Mutation>(
        `/api/v1/projects/${s.project_id}/${path}`,
        mutationOptions(s.revision_id, body),
      );
      if (r.execution_status === "blocked")
        throw new Error(
          r.issue?.message ?? "This change is outside the supported layout.",
        );
      undoStack.current.push(s.revision_id);
      redoStack.current = [];
      await load(s.project_id, r.revision_id);
      setActivity(`${label} complete · Revision ${r.revision_number}`);
      return r;
    } catch (e) {
      await failure(e);
    } finally {
      lock.current = false;
      setCanUndo(undoStack.current.length > 0);
      setCanRedo(redoStack.current.length > 0);
      setBusy("");
    }
  }
  async function command(commands: Record<string, unknown>[], label: string) {
    return mutate(
      "commands",
      {
        commands: commands.map((c) => ({
          command_id: crypto.randomUUID(),
          ...c,
        })),
      },
      label,
    );
  }
  async function send(text: string) {
    const s = current.current;
    if (!s || lock.current || !text.trim()) return;
    lock.current = true;
    setError("");
    setBusy("Interpreting your request");
    addMessage({ role: "user", text });
    try {
      const r = await api<ConversationResponse>(
        `/api/v1/projects/${s.project_id}/conversations`,
        mutationOptions(s.revision_id, { text }),
      );
      if (r.committed_revision_id) {
        undoStack.current.push(s.revision_id);
        redoStack.current = [];
        setBusy("Building your changes");
        await load(s.project_id, r.committed_revision_id);
      }
      if (r.issue?.code === "STALE_REVISION") {
        const head = await api<{ revision_id: string }>(
          `/api/v1/projects/${s.project_id}`,
        );
        await load(s.project_id, head.revision_id);
      }
      const blocked = ["blocked", "error", "unsupported"].includes(
        r.execution_status,
      );
      addMessage({
        role: "assistant",
        text:
          r.explanation ||
          r.issue?.message ||
          (blocked
            ? "This request could not be completed. Your saved model is unchanged."
            : "I’ve updated your design."),
        revision: r.committed_revision_number,
        status: blocked ? "blocked" : "completed",
      });
      setActivity(
        r.committed_revision_id
          ? `Design updated · Revision ${r.committed_revision_number}`
          : blocked
            ? "Request needs attention. Your model is saved."
            : "Ready for your next idea.",
      );
    } catch (e) {
      addMessage({ role: "assistant", text: errorMessage(e), status: "error" });
      await failure(e);
    } finally {
      lock.current = false;
      setCanUndo(undoStack.current.length > 0);
      setCanRedo(redoStack.current.length > 0);
      setBusy("");
    }
  }
  async function restore(direction: "undo" | "redo") {
    const s = current.current,
      from = direction === "undo" ? undoStack : redoStack,
      to = direction === "undo" ? redoStack : undoStack;
    const target = from.current.at(-1);
    if (!s || !target || lock.current) return;
    lock.current = true;
    setBusy("Restoring revision");
    setError("");
    try {
      const r = await api<Mutation>(
        `/api/v1/projects/${s.project_id}/restore`,
        mutationOptions(s.revision_id, { target_revision_id: target }),
      );
      from.current.pop();
      to.current.push(s.revision_id);
      await load(s.project_id, r.revision_id);
      setActivity(`Restored as revision ${r.revision_number}.`);
    } catch (e) {
      await failure(e);
    } finally {
      lock.current = false;
      setCanUndo(undoStack.current.length > 0);
      setCanRedo(redoStack.current.length > 0);
      setBusy("");
    }
  }
  async function exportPdf() {
    const s = current.current;
    if (!s || lock.current) return;
    lock.current = true;
    setBusy("Preparing review package");
    setError("");
    try {
      const r = await api<ExportRecord>(
        `/api/v1/projects/${s.project_id}/exports`,
        {
          method: "POST",
          body: JSON.stringify({ revision_id: s.revision_id }),
        },
      );
      setArtifact(r);
      setActivity(`Review package ready · Revision ${s.revision_number}`);
      return r;
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      lock.current = false;
      setCanUndo(undoStack.current.length > 0);
      setCanRedo(redoStack.current.length > 0);
      setBusy("");
    }
  }
  return {
    snap,
    projects,
    ready,
    openProject,
    openDemo,
    createDesign,
    results,
    methods,
    history,
    messages,
    busy,
    error,
    activity,
    artifact,
    provider,
    send,
    command,
    mutate,
    restore,
    exportPdf,
    start,
    addMessage,
    setError,
    canUndo,
    canRedo,
  };
}
