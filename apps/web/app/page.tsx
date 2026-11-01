"use client";
import { survivingFloor } from "./lib/levels";
import dynamic from "next/dynamic";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import Icon, { type IconName } from "./components/Icon";
import NewDesign from "./components/NewDesign";
import StudioHome from "./components/StudioHome";
import SiteControls from "./components/SiteControls";
import { useStudio } from "./lib/useStudio";
import { useMicrophone } from "./lib/useMicrophone";
import { area, areaLabel, bounds, length, title } from "./lib/format";
import type { BuildingSnapshot, Result, Units } from "./lib/types";
const Plan2D = dynamic(() => import("./Plan2D"), {
  ssr: false,
  loading: () => <div className="view-loading">Preparing the drawing…</div>,
});
const SitePlan = dynamic(() => import("./SitePlan"), {
  ssr: false,
  loading: () => (
    <div className="view-loading">Preparing the site drawing…</div>
  ),
});
const Villa3D = dynamic(() => import("./Villa3D"), {
  ssr: false,
  loading: () => (
    <div className="view-loading">
      <span className="assembly-mark" />
      Preparing your model…
    </div>
  ),
});
type View = "3d" | "plan" | "site" | "structure" | "systems" | "documents";
const views: { id: View; label: string; icon: IconName }[] = [
  { id: "3d", label: "3D model", icon: "cube" },
  { id: "plan", label: "Floor plan", icon: "plan" },
  { id: "site", label: "Site plan", icon: "site" },
  { id: "structure", label: "Structure", icon: "grid" },
  { id: "systems", label: "Systems", icon: "settings" },
  { id: "documents", label: "Documents", icon: "file" },
];
function Brand({ small = false }: { small?: boolean }) {
  return (
    <span className={`brand ${small ? "small" : ""}`}>
      <span className="brand-mark">
        <Icon name="cube" size={small ? 20 : 25} />
      </span>
      {!small && (
        <span>
          nodesnap<span className="brand-dot">.</span>
        </span>
      )}
    </span>
  );
}
function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="property">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
function JsonQuantities({
  data,
  depth = 0,
}: {
  data: unknown;
  depth?: number;
}) {
  if (data === null || data === undefined)
    return <p className="muted">Not calculated.</p>;
  if (typeof data !== "object")
    return (
      <span>
        {typeof data === "number"
          ? data.toLocaleString("en-US", { maximumFractionDigits: 4 })
          : String(data)}
      </span>
    );
  if (Array.isArray(data))
    return (
      <div className="quantity-items">
        {data.map((v, i) => (
          <div key={i}>
            <JsonQuantities data={v} depth={depth + 1} />
          </div>
        ))}
      </div>
    );
  return (
    <dl className="quantity-list">
      {Object.entries(data).map(([key, value]) => (
        <div
          key={key}
          className={typeof value === "object" ? "quantity-group" : ""}
        >
          <dt>{title(key)}</dt>
          <dd>
            {typeof value === "object" ? (
              <details open={depth < 1}>
                <summary>
                  View{" "}
                  {Array.isArray(value) ? value.length + " items" : "details"}
                </summary>
                <JsonQuantities data={value} depth={depth + 1} />
              </details>
            ) : (
              <JsonQuantities data={value} depth={depth + 1} />
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
function ResultPanel({
  results,
  snap,
  discipline,
}: {
  results: Result[];
  snap: BuildingSnapshot;
  discipline: "structure" | "systems";
}) {
  const selected = results.filter((r) =>
    discipline === "structure"
      ? [
          "structural_frame_analysis",
          "foundation_bearing_review",
          "beam_analysis",
        ].includes(r.method_id)
      : [
          "services_inventories",
          "pool_quantities",
          "pool_environment",
        ].includes(r.method_id),
  );
  return (
    <div className="evidence-view">
      <div className="section-heading">
        <div>
          <h1>
            {discipline === "structure"
              ? "Understand the structure."
              : "A home that works together."}
          </h1>
          <p>
            Calculated evidence for revision {snap.revision_number}. Assumed
            inputs remain open for professional review.
          </p>
        </div>
        <span className="outline-tag">Unreviewed</span>
      </div>
      {discipline === "structure" && (
        <div className="scope-notice">
          <Icon name="info" />
          <p>
            The gravity frame is a declared analytical idealization.
            Architectural walls are not assigned member capacities. Lateral,
            connection, and code design checks remain open.
          </p>
        </div>
      )}
      {selected.length === 0 ? (
        <div className="empty-evidence">
          Calculations are unavailable for this revision. Reopen the project to
          retry.
        </div>
      ) : (
        selected.map((r) => (
          <section className="result-section" key={r.method_id}>
            <div className="result-heading">
              <h2>{title(r.method_id)}</h2>
              <span
                className={`state-label ${r.execution_status === "completed" ? "" : "warning"}`}
              >
                {title(r.execution_status)}
              </span>
            </div>
            <div className="result-states">
              <span>Method: {title(r.method_state)}</span>
              <span>Check: {title(r.check_outcome)}</span>
              <span>Revision {snap.revision_number} · Current</span>
            </div>
            <JsonQuantities data={r.quantities} />
            {r.issues?.length > 0 && (
              <div className="open-items">
                <h3>Open review items</h3>
                {r.issues.map((i, j) => (
                  <p key={j}>
                    <Icon name="info" size={14} />
                    <span>{i.message}</span>
                  </p>
                ))}
              </div>
            )}
          </section>
        ))
      )}
    </div>
  );
}
export default function Home() {
  const [screen, setScreen] = useState<"home" | "new" | "workspace">("home");
  const previousScreen = useRef(screen);
  useEffect(() => {
    if (previousScreen.current !== screen) {
      document
        .querySelector<HTMLElement>("[data-screen-heading]")
        ?.focus({ preventScroll: true });
      previousScreen.current = screen;
    }
  }, [screen]);
  const [view, setView] = useState<View>("3d"),
    [level, setLevel] = useState("ground"),
    [selected, setSelected] = useState(""),
    [units, setUnits] = useState<Units>("imperial");
  const [mode, setMode] = useState<"building" | "cutaway" | "exploded">(
      "building",
    ),
    [material, setMaterial] = useState<"material" | "white">("material"),
    [replay, setReplay] = useState(0);
  const [text, setText] = useState(""),
    [chatOpen, setChatOpen] = useState(true),
    [inspectorOpen, setInspectorOpen] = useState(true),
    [mobileTab, setMobileTab] = useState<"model" | "chat" | "details">("model");
  const [levelHeightDraft, setLevelHeightDraft] = useState<{
      level: string;
      revision: string;
      value: string;
    } | null>(null),
    [terraceDraft, setTerraceDraft] = useState<{
      revision: string;
      value: string;
    } | null>(null),
    [inspectorTab, setInspectorTab] = useState<"design" | "history">("design"),
    [poolDraft, setPoolDraft] = useState<{
      revision: string;
      value: string;
    } | null>(null),
    [roomDraft, setRoomDraft] = useState<{
      id: string;
      revision: string;
      value: string;
    } | null>(null);
  const studio = useStudio((next, previous) => {
    setScreen("workspace");
    const replaced =
      previous?.project_id === next.project_id &&
      previous.levels.every((old) => !next.levels.some((l) => l.id === old.id));
    if (previous?.project_id === next.project_id && !replaced) {
      const added = next.levels.find(
        (l) =>
          l.name !== "roof" &&
          l.name !== "basement" &&
          !previous.levels.some((old) => old.id === l.id),
      );
      if (added) {
        setLevel(added.name);
        setSelected("");
        setView("3d");
        setMode("exploded");
        setMobileTab("model");
      } else {
        setLevel((current) =>
          survivingFloor(current, previous.levels, next.levels),
        );
        setSelected((current) =>
          next.spaces.some((s) => s.id === current) ? current : "",
        );
      }
    } else {
      setLevel("ground");
      setSelected("");
      setView("3d");
      setMode("building");
      setMobileTab("model");
      setInspectorTab("design");
      setText("");
    }
  });
  const { snap, busy, error, results, messages, artifact } = studio;
  const livingLevels =
    snap?.levels.filter(
      (l) =>
        l.name !== "basement" &&
        l.name !== "roof" &&
        snap.spaces.some(
          (s) => s.level_id === l.id && s.classification === "principal",
        ),
    ) ?? [];
  const bedroomCount =
    snap?.spaces.filter((s) => s.use === "bedroom").length ?? 0;
  const canReplan = livingLevels.some((l) => l.name === level);
  const prompts = [
    "Add another level",
    ...(!snap?.site_layout?.yard
      ? ["Add a small yard"]
      : !snap?.site_layout?.garage
        ? ["Add a detached garage"]
        : ["Make the yard deeper"]),
    ...(snap?.pool
      ? ["Make the pool 10 metres long"]
      : ["Use warm concrete finishes"]),
    ...(snap?.roof_terrace_area_m2
      ? ["Make the roof terrace 100 square metres"]
      : []),
  ];
  const activeFloorButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    activeFloorButton.current?.scrollIntoView({
      block: "nearest",
      inline: "nearest",
      behavior: "instant",
    });
  }, [level, snap?.levels.length]);
  const end = useRef<HTMLDivElement>(null),
    composer = useRef<HTMLTextAreaElement>(null),
    inspectorScroll = useRef<HTMLDivElement>(null);
  const mic = useMicrophone(snap?.project_id, setText, studio.setError);
  const selectedSpace = snap?.spaces.find((s) => s.id === selected),
    selectedMetric = snap?.architecture?.space_metrics.find(
      (m) => m.space_id === selected,
    ),
    currentLevel = snap?.levels.find((l) => l.name === level);
  const levelIndex =
    snap?.levels.findIndex((l) => l.id === currentLevel?.id) ?? 0;
  const aboveLevel = snap?.levels[levelIndex + 1];
  const floorHeight =
    levelHeightDraft?.level === level &&
    levelHeightDraft?.revision === snap?.revision_id
      ? (levelHeightDraft?.value ?? "")
      : currentLevel && aboveLevel
        ? String(
            Number(
              (aboveLevel.elevation_m - currentLevel.elevation_m).toFixed(3),
            ),
          )
        : "";
  const terraceArea =
    terraceDraft?.revision === snap?.revision_id
      ? (terraceDraft?.value ?? "")
      : String(snap?.roof_terrace_area_m2?.toFixed(2) ?? "");
  const terraceMin = snap?.building_program ? 0 : 40;
  const terraceMax = snap?.building_program
    ? Math.min(
        3000,
        snap.building_program.width_m * snap.building_program.depth_m,
      )
    : 130;
  const spaces =
    snap?.spaces.filter((s) => s.level_id === currentLevel?.id) ?? [];
  useEffect(() => {
    end.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "nearest",
    });
  }, [messages.length, busy]);
  const poolLength =
    poolDraft?.revision === snap?.revision_id
      ? (poolDraft?.value ?? "")
      : String(snap?.pool?.water_length_m ?? 8);
  const roomArea =
    roomDraft?.id === selected && roomDraft?.revision === snap?.revision_id
      ? (roomDraft?.value ?? "")
      : selectedSpace?.target_area_m2
        ? String(Math.round(selectedSpace.target_area_m2 * 10) / 10)
        : "";
  useLayoutEffect(() => {
    if (selected && inspectorTab === "design" && inspectorOpen) {
      inspectorScroll.current?.scrollTo({ top: 0 });
    }
  }, [selected, inspectorTab, inspectorOpen, mobileTab]);
  function select(id: string) {
    setSelected(id);
    setInspectorTab("design");
    setInspectorOpen(true);
    inspectorScroll.current?.scrollTo({ top: 0 });
    if (snap) {
      const space = snap.spaces.find((s) => s.id === id);
      const l = snap.levels.find((l) => l.id === space?.level_id);
      if (l) setLevel(l.name);
    }
  }
  function chooseFloor(name: string) {
    setLevel(name);
    setSelected("");
    if (view === "3d") setMode("cutaway");
  }
  function submit(e?: React.FormEvent) {
    e?.preventDefault();
    if (!text.trim() || busy) return;
    const request = text.trim();
    setText("");
    void studio.send(request);
  }
  async function generate() {
    if (!snap) return;
    const rooms = spaces
      .filter((s) => s.classification === "principal")
      .map((s) => ({
        name: s.name,
        use: s.use,
        target_area_m2:
          s.id === selected && roomArea
            ? Number(roomArea)
            : (s.target_area_m2 ?? area(s.polygon)),
      }));
    await studio.mutate("generate", { level, rooms }, "Planning rooms");
  }
  function applyPool() {
    const n = Number(poolLength);
    if (!Number.isFinite(n) || n <= 0) {
      studio.setError("Enter a positive pool length in metres.");
      return;
    }
    void studio.command(
      [{ type: "set_pool_dimensions", water_length_m: n }],
      "Updating pool",
    );
  }
  const issues = results.flatMap((r) => r.issues ?? []),
    loading = !snap;
  if (screen === "home")
    return (
      <StudioHome
        busy={busy}
        ready={studio.ready}
        error={error}
        projects={studio.projects}
        onNew={() => {
          studio.setError("");
          setScreen("new");
        }}
        onOpen={(pid) => void studio.openProject(pid)}
        onDemo={() => void studio.openDemo()}
        onRetry={() => void studio.start()}
      />
    );
  if (screen === "new" || !snap)
    return (
      <NewDesign
        busy={busy}
        ready={studio.ready}
        error={error}
        projects={studio.projects}
        onCreate={studio.createDesign}
        onOpen={(pid) => void studio.openProject(pid)}
        onDemo={() => void studio.openDemo()}
        onRetry={() => void studio.start()}
        onError={studio.setError}
        onHome={() => {
          studio.setError("");
          setScreen("home");
        }}
      />
    );
  return (
    <div
      className={`studio ${!chatOpen ? "chat-collapsed" : ""} ${!inspectorOpen ? "inspector-collapsed" : ""} mobile-${mobileTab}`}
    >
      <header className="topbar">
        <button
          className="home-brand"
          aria-label="Go to homepage"
          disabled={!!busy || mic.state !== "idle"}
          onClick={() => {
            studio.setError("");
            setScreen("home");
          }}
        >
          <Brand />
        </button>
        <div className="project-heading">
          <select
            className="project-picker"
            aria-label="Open saved building"
            value={snap.project_id}
            disabled={!!busy || mic.state !== "idle"}
            onChange={(e) => void studio.openProject(e.target.value)}
          >
            {studio.projects.map((p) => (
              <option value={p.project_id} key={p.project_id}>
                {p.title}
              </option>
            ))}
          </select>
          <span className="project-subtitle">
            {snap.building_program
              ? "Your building · Concept design"
              : "Example villa · Demonstration"}
          </span>
        </div>
        <div className="topbar-actions">
          <button
            className="new-building-button"
            aria-label="Design a new building"
            disabled={!!busy || mic.state !== "idle"}
            onClick={() => {
              studio.setError("");
              setScreen("new");
            }}
          >
            <Icon name="plus" size={15} />
            <span>New building</span>
          </button>
          <span className="saved-state">
            <span className={busy ? "status-dot working" : "status-dot"} />
            {busy ? "Updating…" : "All changes saved"}
          </span>
          <button
            className="revision-button"
            onClick={() => {
              setInspectorTab("history");
              setInspectorOpen(true);
              setMobileTab("details");
            }}
            disabled={!snap}
          >
            <Icon name="history" size={15} />R
            {String(snap?.revision_number ?? 1).padStart(2, "0")}
          </button>
          <button
            aria-label="Export review package"
            className="export-button"
            onClick={() => {
              setView("documents");
              setMobileTab("model");
              void studio.exportPdf();
            }}
            disabled={!snap || !!busy}
          >
            <Icon name="download" size={15} />
            <span>Export package</span>
          </button>
        </div>
      </header>
      <nav className="mobile-tabs" aria-label="Workspace area">
        {(["model", "chat", "details"] as const).map((t) => (
          <button
            key={t}
            className={mobileTab === t ? "active" : ""}
            onClick={() => setMobileTab(t)}
          >
            {title(t)}
          </button>
        ))}
      </nav>
      <aside className="conversation-panel">
        <div className="panel-heading">
          <div>
            <Icon name="chat" size={17} />
            <h2>Design conversation</h2>
          </div>
          <button
            className="icon-button desktop-only"
            title="Collapse conversation"
            aria-label="Collapse conversation"
            onClick={() => setChatOpen(false)}
          >
            <Icon name="close" size={16} />
          </button>
        </div>
        <div className="conversation-scroll">
          <div className="conversation-intro">
            <span className="studio-avatar">
              <Icon name="spark" size={22} />
            </span>
            <h1>
              Make room for
              <br />
              your ideas.
            </h1>
            <p>
              Explore the building. Describe a change.
              <br />
              See your ideas take form.
            </p>
          </div>
          <div className="brief-summary">
            <div className="brief-top">
              <Icon name="cube" />
              <strong>Your design brief</strong>
              <span>Concept</span>
            </div>
            <p>
              {snap.building_program
                ? `${title(snap.building_program.building_use)} · ${snap.building_program.width_m} × ${snap.building_program.depth_m} m footprint.`
                : `A contemporary NYC villa${snap.pool ? ` with an ${snap.pool.location === "outdoor" ? "outdoor" : "indoor"} pool` : ""}${snap.roof_terrace_area_m2 ? " and a roof terrace" : ""}.`}
            </p>
            <div className="brief-facts">
              <span>
                {livingLevels.length}{" "}
                {livingLevels.length === 1 ? "floor" : "floors"}
              </span>
              {bedroomCount > 0 && <span>{bedroomCount} bedrooms</span>}
              <span>
                {snap.pool
                  ? snap.pool.location === "outdoor"
                    ? "Outdoor pool"
                    : "Indoor pool"
                  : "Concept layout"}
              </span>
              {snap.site_layout?.yard && <span>Yard</span>}
              {snap.site_layout?.garage && <span>Garage</span>}
            </div>
            <div className="site-note">
              <Icon name="info" size={13} />
              Synthetic site · No surveyed address
            </div>
          </div>
          <div
            className="message-list"
            aria-live="polite"
            aria-relevant="additions"
          >
            {messages.map((m) => (
              <div
                key={m.id}
                className={`message ${m.role} ${m.status === "blocked" || m.status === "error" ? "message-blocked" : ""}`}
              >
                {m.role === "assistant" && (
                  <div className="message-author">
                    <Icon name="spark" size={14} />
                    <span>NodeSnap</span>
                  </div>
                )}
                <p>{m.text}</p>
                {m.revision && (
                  <button
                    className="message-revision"
                    onClick={() => {
                      setView("3d");
                      setReplay((r) => r + 1);
                      setMobileTab("model");
                    }}
                  >
                    <Icon name="check" size={13} />
                    Revision {m.revision} saved
                    <Icon name="chevron" size={12} />
                  </button>
                )}
              </div>
            ))}
            {busy && (
              <div className="thinking" role="status">
                <span className="thinking-dots">
                  <i />
                  <i />
                  <i />
                </span>
                <span>{busy}…</span>
              </div>
            )}
            <div ref={end} />
          </div>
          {messages.length < 3 && (
            <div className="suggestions">
              <p>Try a change</p>
              {prompts.map((p) => (
                <button
                  disabled={!!busy || !snap}
                  key={p}
                  onClick={() => {
                    setText(p);
                    composer.current?.focus();
                  }}
                >
                  {p}
                  <Icon name="chevron" size={13} />
                </button>
              ))}
            </div>
          )}
        </div>
        <form
          className={`composer ${mic.state === "recording" ? "is-recording" : ""}`}
          onSubmit={submit}
        >
          {mic.state === "recording" ? (
            <div className="recording-state">
              <span className="recording-dot" />
              <span>
                Listening ·{" "}
                {String(Math.floor(mic.seconds / 60)).padStart(2, "0")}:
                {String(mic.seconds % 60).padStart(2, "0")}
              </span>
              <div className="waveform">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
                  <i key={i} style={{ animationDelay: `${i * 0.08}s` }} />
                ))}
              </div>
              <button
                type="button"
                className="text-button"
                onClick={() => mic.stop(true)}
              >
                Cancel
              </button>
            </div>
          ) : (
            <textarea
              ref={composer}
              aria-label="Describe your design change"
              placeholder="What would you like to change or create?"
              value={text}
              maxLength={4000}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (
                  e.key === "Enter" &&
                  !e.shiftKey &&
                  !e.nativeEvent.isComposing
                ) {
                  e.preventDefault();
                  submit();
                }
              }}
              rows={3}
              disabled={
                !snap ||
                mic.state === "transcribing" ||
                mic.state === "requesting"
              }
            />
          )}
          <div className="composer-bottom">
            <button
              type="button"
              className={`icon-button ${mic.state === "recording" ? "recording-button" : ""}`}
              aria-label={
                mic.state === "recording"
                  ? "Stop recording"
                  : "Record a design request"
              }
              title="Record with Meta transcription"
              disabled={
                !snap ||
                !!busy ||
                mic.state === "transcribing" ||
                mic.state === "requesting"
              }
              onClick={() =>
                mic.state === "recording" ? mic.stop() : void mic.start()
              }
            >
              <Icon name={mic.state === "recording" ? "stop" : "mic"} />
            </button>
            <span>
              {mic.state === "transcribing"
                ? "Transcribing…"
                : mic.state === "requesting"
                  ? "Opening microphone…"
                  : mic.state === "recording"
                    ? "Stop to review transcript"
                    : studio.provider === false
                      ? "Meta not connected"
                      : "Powered by Meta"}
            </span>
            <button
              className="send-button"
              type="submit"
              aria-label="Send design request"
              disabled={!snap || !text.trim() || !!busy || mic.state !== "idle"}
            >
              <Icon name="arrow" size={18} />
            </button>
          </div>
        </form>
        <p className="composer-footnote">
          Design intent first. Verified geometry always.
        </p>
      </aside>
      <main
        className="workspace"
        data-screen-heading
        tabIndex={-1}
        aria-label="Building workspace"
      >
        <div className="workspace-toolbar">
          {!chatOpen && (
            <button
              className="icon-button"
              aria-label="Open conversation"
              title="Open conversation"
              onClick={() => setChatOpen(true)}
            >
              <Icon name="chat" />
            </button>
          )}
          <nav className="view-tabs" aria-label="Design view">
            {views.map((v) => (
              <button
                key={v.id}
                aria-label={v.label}
                title={v.label}
                onClick={() => setView(v.id)}
                className={view === v.id ? "active" : ""}
                aria-pressed={view === v.id}
              >
                <Icon name={v.icon} size={16} />
                <span>{v.label}</span>
              </button>
            ))}
          </nav>
          <div className="toolbar-end">
            <button
              className="icon-button"
              title="Undo"
              aria-label="Undo last change"
              disabled={!studio.canUndo || !!busy}
              onClick={() => void studio.restore("undo")}
            >
              <Icon name="undo" size={16} />
            </button>
            <button
              className="icon-button"
              title="Redo"
              aria-label="Redo last change"
              disabled={!studio.canRedo || !!busy}
              onClick={() => void studio.restore("redo")}
            >
              <Icon name="redo" size={16} />
            </button>
            <button
              className="icon-button"
              title="Toggle properties"
              aria-label="Toggle properties"
              onClick={() => {
                setInspectorOpen(!inspectorOpen);
                setMobileTab("details");
              }}
            >
              <Icon name="settings" size={17} />
            </button>
          </div>
        </div>
        {error && (
          <div role="alert" className="error-banner">
            <Icon name="info" size={17} />
            <span>{error}</span>
            <button
              aria-label="Dismiss error"
              className="icon-button"
              onClick={() => studio.setError("")}
            >
              <Icon name="close" size={15} />
            </button>
          </div>
        )}
        {loading ? (
          <div className="initial-loading">
            <div className="assembly-mark" />
            <h1>{error ? "Let’s reconnect." : "Your home, taking shape."}</h1>
            <p>
              {error
                ? "Your saved work will be here when the studio reconnects."
                : "Opening the architectural model and its drawings."}
            </p>
            {error && (
              <button
                className="primary-button"
                onClick={() => void studio.start()}
              >
                Retry connection
              </button>
            )}
          </div>
        ) : (
          <>
            {(view === "3d" || view === "plan" || view === "site") && (
              <div className="model-stage">
                <div className="model-caption">
                  <h1>
                    {view === "3d"
                      ? mode === "building"
                        ? "A different perspective."
                        : mode === "exploded"
                          ? "Every level, connected."
                          : `${currentLevel?.label}. Opened up.`
                      : view === "site"
                        ? "A home beyond its walls."
                        : `${currentLevel?.label} plan.`}
                  </h1>
                  <p>
                    {view === "3d"
                      ? "Explore the architecture. Make it yours."
                      : view === "site"
                        ? "House, yard and garage. One saved design."
                        : "Precise geometry. One coordinated model."}
                  </p>
                </div>
                {!snap.architecture && (
                  <div className="legacy-upgrade">
                    <p>
                      Your saved villa is preserved. Restore its model to
                      continue exploring and editing.
                    </p>
                    <button
                      className="primary-button"
                      disabled={!!busy}
                      onClick={() => void studio.openProject(snap.project_id)}
                    >
                      Restore saved villa
                    </button>
                  </div>
                )}
                {view === "3d" ? (
                  <Villa3D
                    snap={snap}
                    level={level}
                    selected={selected}
                    onSelect={select}
                    onMoveWall={async (id, offset) => {
                      await studio.command(
                        [
                          {
                            type: "move_wall",
                            element_id: id,
                            offset_m: offset,
                          },
                        ],
                        "Moving partition",
                      );
                    }}
                    disabled={!!busy}
                    mode={mode}
                    materialMode={material}
                    replayKey={replay}
                  />
                ) : view === "site" ? (
                  <SitePlan snap={snap} units={units} />
                ) : (
                  <Plan2D
                    snap={snap}
                    level={level}
                    selected={selected}
                    onSelect={select}
                    onMove={(id, dx, dy) =>
                      void studio.command(
                        [
                          {
                            type: "move_space",
                            element_id: id,
                            dx_m: dx,
                            dy_m: dy,
                          },
                        ],
                        "Moving room",
                      )
                    }
                    units={units}
                    busy={!!busy}
                  />
                )}
                {view === "3d" && (
                  <>
                    <div className="render-controls">
                      <button
                        aria-pressed={material === "material"}
                        onClick={() =>
                          setMaterial(
                            material === "material" ? "white" : "material",
                          )
                        }
                        title="Toggle material study"
                      >
                        <Icon name="sun" size={16} />
                        {material === "material" ? "Materials" : "Clay study"}
                      </button>
                      <button
                        onClick={() => setReplay((r) => r + 1)}
                        title="Replay model assembly"
                      >
                        <Icon name="rotate" size={16} />
                        Replay build
                      </button>
                    </div>
                    <div className="camera-hint">
                      <Icon name="move" size={14} />
                      <span>Drag to orbit · Scroll to zoom · Click a room</span>
                    </div>
                    <div className="model-modes" aria-label="Model display">
                      {(["building", "cutaway", "exploded"] as const).map(
                        (m) => (
                          <button
                            key={m}
                            aria-pressed={mode === m}
                            className={mode === m ? "active" : ""}
                            onClick={() => setMode(m)}
                          >
                            {m === "building"
                              ? "Full building"
                              : m === "cutaway"
                                ? "Cutaway"
                                : "Exploded"}
                          </button>
                        ),
                      )}
                    </div>
                  </>
                )}
                {busy && (
                  <div className="model-processing">
                    <span className="status-dot working" />
                    {busy}
                  </div>
                )}
              </div>
            )}
            {(view === "structure" || view === "systems") && (
              <ResultPanel results={results} snap={snap} discipline={view} />
            )}
            {view === "documents" && (
              <div className="documents-view">
                <div className="section-heading">
                  <div>
                    <h1>A design you can take further.</h1>
                    <p>
                      Drawings, calculations, and open questions. Frozen
                      together at revision {snap.revision_number}.
                    </p>
                  </div>
                  <Icon name="file" size={32} />
                </div>
                <div className="package-overview">
                  <div className="sheet-preview">
                    <div className="sheet-mini-brand">NODESNAP</div>
                    <Icon name="plan" size={96} />
                    <h2>
                      Professional
                      <br />
                      review draft
                    </h2>
                    <span>
                      {snap.title} · R
                      {String(snap.revision_number).padStart(2, "0")}
                    </span>
                  </div>
                  <div className="package-copy">
                    <h2>The review package</h2>
                    <p>
                      Architectural plans, relevant quantities, the declared
                      structural scenario, services inventories, and the source
                      and assumption registers.
                    </p>
                    <div className="scope-notice">
                      <Icon name="info" />
                      <p>
                        Demonstration design. Assumptions require professional
                        verification. This package contains unresolved design
                        work.
                      </p>
                    </div>
                    {artifact ? (
                      <div className="download-links">
                        <a
                          className="primary-button"
                          href={`/artifacts/${artifact.artifact_id}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <Icon name="download" />
                          Open review PDF
                        </a>
                        <a href={`/artifacts/${artifact.model_artifact_id}`}>
                          Canonical model JSON
                          <Icon name="chevron" size={13} />
                        </a>
                        <a href={`/artifacts/${artifact.manifest_artifact_id}`}>
                          Revision & file manifest
                          <Icon name="chevron" size={13} />
                        </a>
                        <p className="hash">
                          SHA-256 {artifact.file_sha256?.slice(0, 24)}…
                        </p>
                      </div>
                    ) : (
                      <button
                        className="primary-button"
                        disabled={!!busy}
                        onClick={() => void studio.exportPdf()}
                      >
                        <Icon name="download" />
                        {busy
                          ? "Preparing package…"
                          : "Generate review package"}
                      </button>
                    )}
                  </div>
                </div>
                {artifact && (
                  <iframe
                    className="pdf-preview"
                    title={`Review PDF revision ${artifact.revision_number}`}
                    src={`/artifacts/${artifact.artifact_id}#toolbar=1`}
                  />
                )}
                <section className="coverage-section">
                  <h2>Calculation methods and scope</h2>
                  {studio.methods
                    .filter((m) => !!snap.pool || !m.id.startsWith("pool_"))
                    .map((m) => (
                      <div className="coverage-row" key={m.id}>
                        <div>
                          <strong>{title(m.id)}</strong>
                          <p>{m.purpose}</p>
                          {m.exclusions && (
                            <p className="muted">Open scope: {m.exclusions}</p>
                          )}
                        </div>
                        <span className="outline-tag">
                          {title(m.method_state)}
                        </span>
                      </div>
                    ))}
                </section>
              </div>
            )}
            {(view === "3d" || view === "plan" || view === "site") && (
              <div className="floor-bar">
                {view === "site" ? (
                  <span className="site-context-label">
                    Site overview · assumed context
                  </span>
                ) : (
                  <div className="floor-selector">
                    <Icon name="layers" size={17} />
                    {snap.levels.map((l) => (
                      <button
                        key={l.id}
                        ref={l.name === level ? activeFloorButton : undefined}
                        className={level === l.name ? "active" : ""}
                        aria-pressed={level === l.name}
                        onClick={() => chooseFloor(l.name)}
                      >
                        <span>
                          {l.name === "roof"
                            ? "Roof"
                            : l.label
                                .replace(" floor", "")
                                .replace("Floor", "")}
                        </span>
                        <small>
                          {l.elevation_m >= 0 ? "+" : ""}
                          {l.elevation_m.toFixed(2)} m
                        </small>
                      </button>
                    ))}
                    <button
                      className="add-level-button"
                      aria-label="Add another level"
                      title="Add a floor below the roof using the top floor’s layout"
                      disabled={!!busy}
                      onClick={() =>
                        void studio.command(
                          [{ type: "add_level" }],
                          "Adding a level",
                        )
                      }
                    >
                      <Icon name="plus" size={17} />
                    </button>
                  </div>
                )}
                <label className="unit-picker">
                  <span className="sr-only">Display units</span>
                  <select
                    value={units}
                    onChange={(e) => setUnits(e.target.value as Units)}
                  >
                    <option value="imperial">Feet & inches</option>
                    <option value="metric">Metric</option>
                  </select>
                </label>
              </div>
            )}
          </>
        )}
      </main>
      <aside className="inspector">
        <div className="panel-heading">
          <div className="inspector-tabs">
            <button
              className={inspectorTab === "design" ? "active" : ""}
              onClick={() => setInspectorTab("design")}
            >
              Design details
            </button>
            <button
              className={inspectorTab === "history" ? "active" : ""}
              onClick={() => setInspectorTab("history")}
            >
              History
            </button>
          </div>
          <button
            className="icon-button desktop-only"
            title="Close inspector"
            aria-label="Close inspector"
            onClick={() => setInspectorOpen(false)}
          >
            <Icon name="close" size={15} />
          </button>
        </div>
        <div className="inspector-scroll" ref={inspectorScroll}>
          {snap && inspectorTab === "history" ? (
            <>
              <h2>Your design, evolving.</h2>
              <p className="muted">
                Every saved revision stays intact. Undo and redo create new
                revisions.
              </p>
              <div className="history-list">
                {studio.history.map((r) => (
                  <div key={r.revision_id}>
                    <span className="history-node" />
                    <div>
                      <strong>Revision {r.revision_number}</strong>
                      {r.revision_id === snap.revision_id && (
                        <span className="small-tag">Current</span>
                      )}
                      <p>{new Date(r.created_at).toLocaleString()}</p>
                      <code>{r.revision_id.slice(0, 8)}</code>
                    </div>
                  </div>
                ))}
              </div>
              <button
                className="secondary-button"
                disabled={!!busy || mic.state !== "idle"}
                onClick={() => {
                  studio.setError("");
                  setScreen("new");
                }}
              >
                <Icon name="plus" size={15} />
                Design a new building
              </button>
            </>
          ) : (
            snap && (
              <>
                <div className="inspector-title">
                  <span className="object-symbol">
                    <Icon name={selectedSpace ? "plan" : "cube"} size={28} />
                  </span>
                  <h2>{selectedSpace?.name ?? "Your building at a glance"}</h2>
                  <p>
                    {selectedSpace
                      ? `${currentLevel?.label} · ${title(selectedSpace.use)}`
                      : `${title(snap.brief.use)} · Concept design`}
                  </p>
                </div>
                <div className="properties">
                  {selectedSpace ? (
                    <>
                      <Field
                        label="Clear floor area"
                        value={areaLabel(
                          selectedMetric?.net_area_m2 ??
                            area(selectedSpace.polygon),
                          units,
                        )}
                      />
                      <Field
                        label="Planning zone"
                        value={areaLabel(area(selectedSpace.polygon), units)}
                      />
                      <Field
                        label="Clear width"
                        value={length(
                          selectedMetric?.clear_width_m ??
                            bounds(selectedSpace.polygon).w,
                          units,
                        )}
                      />
                      <Field
                        label="Clear depth"
                        value={length(
                          selectedMetric?.clear_depth_m ??
                            bounds(selectedSpace.polygon).h,
                          units,
                        )}
                      />
                      <Field
                        label="Classification"
                        value={title(selectedSpace.classification)}
                      />
                    </>
                  ) : (
                    <>
                      <Field
                        label="Occupied floors"
                        value={livingLevels.length}
                      />
                      <Field
                        label="Principal rooms"
                        value={
                          snap.spaces.filter(
                            (s) =>
                              s.classification === "principal" &&
                              livingLevels.some((l) => l.id === s.level_id),
                          ).length
                        }
                      />
                      <Field
                        label="Current floor zones"
                        value={areaLabel(
                          spaces.reduce((n, s) => n + area(s.polygon), 0),
                          units,
                        )}
                      />
                      <Field
                        label="Roof terrace"
                        value={areaLabel(snap.roof_terrace_area_m2 ?? 0, units)}
                      />
                      <Field label="Site basis" value="Demonstration" />
                    </>
                  )}
                </div>
                {selectedSpace &&
                  selectedSpace.classification === "principal" &&
                  canReplan && (
                    <div className="edit-block">
                      <h3>Shape this room</h3>
                      <label>
                        Target area (m²)
                        <div className="input-with-action">
                          <input
                            type="number"
                            min="4"
                            max="180"
                            step=".1"
                            value={roomArea}
                            onChange={(e) =>
                              setRoomDraft({
                                id: selected,
                                revision: snap.revision_id,
                                value: e.target.value,
                              })
                            }
                          />
                          <button
                            disabled={
                              !!busy || !roomArea || Number(roomArea) <= 0
                            }
                            onClick={() => void generate()}
                          >
                            Apply
                          </button>
                        </div>
                      </label>
                      <p>
                        Replans this floor to fit the target. Exact clear area
                        accounts for walls.
                      </p>
                    </div>
                  )}
                <SiteControls
                  key={snap.revision_id}
                  snap={snap}
                  units={units}
                  disabled={!!busy || mic.state !== "idle"}
                  error={error}
                  onCommand={(commands, label) =>
                    void studio.command(commands, label)
                  }
                  onPlan={() => {
                    setView("site");
                    setMobileTab("model");
                  }}
                />
                {(currentLevel?.id === snap.pool?.level_id ||
                  view === "site") &&
                  snap.pool && (
                    <div className="edit-block">
                      <h3>
                        {snap.pool.location === "outdoor"
                          ? "Outdoor pool"
                          : "Indoor pool"}{" "}
                        dimensions
                      </h3>
                      <label>
                        Water length (m)
                        <div className="input-with-action">
                          <input
                            aria-label="Pool water length in metres"
                            type="number"
                            min="1"
                            max={snap.building_program ? 50 : 15}
                            step=".1"
                            value={poolLength}
                            onChange={(e) =>
                              setPoolDraft({
                                revision: snap.revision_id,
                                value: e.target.value,
                              })
                            }
                          />
                          <button disabled={!!busy} onClick={applyPool}>
                            Apply
                          </button>
                        </div>
                      </label>
                      <Field
                        label="Width"
                        value={length(snap.pool.water_width_m, units)}
                      />
                      <Field
                        label="Water depth"
                        value={length(snap.pool.water_depth_m, units)}
                      />
                      <p>Flat-bottom basin · demonstration assumption</p>
                    </div>
                  )}
                {aboveLevel && currentLevel && (
                  <div className="edit-block">
                    <h3>Floor-to-floor height</h3>
                    <label>
                      Height (m)
                      <div className="input-with-action">
                        <input
                          aria-label="Floor-to-floor height in metres"
                          type="number"
                          min="2.6"
                          max="4.5"
                          step=".1"
                          value={floorHeight}
                          onChange={(e) =>
                            setLevelHeightDraft({
                              level,
                              revision: snap.revision_id,
                              value: e.target.value,
                            })
                          }
                        />
                        <button
                          disabled={
                            !!busy ||
                            !floorHeight ||
                            Number(floorHeight) < 2.6 ||
                            Number(floorHeight) > 4.5
                          }
                          onClick={() =>
                            void studio.command(
                              [
                                {
                                  type: "set_level_height",
                                  level_id: currentLevel.id,
                                  height_m: Number(floorHeight),
                                },
                              ],
                              "Updating floor heights",
                            )
                          }
                        >
                          Apply
                        </button>
                      </div>
                    </label>
                    <p>
                      Moves all levels above and rebuilds the connecting stairs.
                      Concept range: 2.6–4.5 m.
                    </p>
                  </div>
                )}
                {canReplan && currentLevel && level !== "ground" && (
                  <div className="edit-block">
                    <h3>Building levels</h3>
                    <button
                      className="secondary-button"
                      disabled={!!busy}
                      onClick={() =>
                        void studio.command(
                          [{ type: "remove_level", level_id: currentLevel.id }],
                          "Removing a level",
                        )
                      }
                    >
                      <Icon name="minus" size={16} /> Remove{" "}
                      {currentLevel.label}
                    </button>
                    <p>
                      Removes this floor and its rooms, then lowers the levels
                      above. You can undo this change.
                    </p>
                  </div>
                )}
                {level === "roof" &&
                  (!!snap.roof_terrace_area_m2 || !!snap.building_program) && (
                    <div className="edit-block">
                      <h3>Terrace footprint</h3>
                      <label>
                        Area (m²)
                        <div className="input-with-action">
                          <input
                            aria-label="Terrace area in square metres"
                            type="number"
                            min={terraceMin}
                            max={terraceMax}
                            value={terraceArea}
                            onChange={(e) =>
                              setTerraceDraft({
                                revision: snap.revision_id,
                                value: e.target.value,
                              })
                            }
                          />
                          <button
                            disabled={
                              !!busy ||
                              !terraceArea ||
                              Number(terraceArea) < terraceMin ||
                              Number(terraceArea) > terraceMax
                            }
                            onClick={() =>
                              void studio.command(
                                [
                                  {
                                    type: "set_terrace_area",
                                    area_m2: Number(terraceArea),
                                  },
                                ],
                                "Updating terrace",
                              )
                            }
                          >
                            Apply
                          </button>
                        </div>
                      </label>
                      <p>
                        {snap.building_program
                          ? "Terrace and access space must fit the roof. Set to 0 for an unoccupied roof."
                          : "Connected terrace and access zone. Supported range: 40–130 m²."}
                      </p>
                    </div>
                  )}
                <section className="material-section">
                  <h3>Material story</h3>
                  <div className="material-swatches">
                    <div>
                      <span className="swatch stone" />
                      <span>Stone</span>
                    </div>
                    <div>
                      <span className="swatch timber" />
                      <span>Timber</span>
                    </div>
                    <div>
                      <span className="swatch metal" />
                      <span>Metal</span>
                    </div>
                    <div>
                      <span className="swatch glass" />
                      <span>Glass</span>
                    </div>
                  </div>
                  <label className="palette-picker">
                    Finish palette
                    <select
                      aria-label="Finish palette"
                      value={snap.material_palette ?? "limestone_oak"}
                      disabled={!!busy}
                      onChange={(e) =>
                        void studio.command(
                          [
                            {
                              type: "set_material_palette",
                              palette: e.target.value,
                            },
                          ],
                          "Updating materials",
                        )
                      }
                    >
                      <option value="limestone_oak">Limestone & oak</option>
                      <option value="warm_concrete">Warm concrete</option>
                      <option value="white_stucco">White stucco</option>
                    </select>
                  </label>
                  <p>
                    Visual finishes. Assembly performance requires verification.
                  </p>
                </section>
                <section className="rooms-section">
                  <div className="section-inline">
                    <h3>{currentLevel?.label}</h3>
                    <span>{spaces.length} spaces</span>
                  </div>
                  <div className="room-list">
                    {spaces.map((s, index) => (
                      <button
                        key={s.id}
                        className={s.id === selected ? "selected" : ""}
                        onClick={() => select(s.id)}
                      >
                        <span
                          className={`room-symbol ${s.classification === "principal" ? "principal" : ""}`}
                        />
                        <span>
                          <small className="room-plan-tag">R{index + 1}</small>
                          {s.name}
                        </span>
                        <small>
                          {areaLabel(
                            snap.architecture?.space_metrics.find(
                              (m) => m.space_id === s.id,
                            )?.net_area_m2 ?? area(s.polygon),
                            units,
                          )}
                        </small>
                      </button>
                    ))}
                  </div>
                </section>
                {canReplan && (
                  <button
                    className="secondary-button generate-button"
                    onClick={() => void generate()}
                    disabled={!!busy}
                  >
                    <Icon name="spark" size={15} />
                    Explore another layout
                  </button>
                )}
                {!!snap.building_program?.design_notes.length && (
                  <details className="brief-assumptions">
                    <summary>Design choices and assumptions</summary>
                    <ul>
                      {snap.building_program.design_notes.map((note, i) => (
                        <li key={i}>{note}</li>
                      ))}
                    </ul>
                  </details>
                )}
                <div className="review-note">
                  <Icon name="info" size={16} />
                  <div>
                    <strong>A concept, with a clear basis.</strong>
                    <p>
                      Geometry is coordinated. Engineering scope and assumptions
                      are recorded in the review package.
                    </p>
                    <button onClick={() => setView("documents")}>
                      Review evidence
                      <Icon name="chevron" size={12} />
                    </button>
                  </div>
                </div>
              </>
            )
          )}
        </div>
      </aside>
      <footer className="activity-bar">
        <span>
          <Icon name={busy ? "clock" : "check"} size={13} />
          {busy || studio.activity}
        </span>
        <button
          onClick={() => {
            setView("documents");
            setMobileTab("model");
          }}
        >
          <span className="issue-dot" />
          {issues.length} open review items
        </button>
        <span className="activity-revision">
          {snap
            ? `Revision ${snap.revision_number} · ${snap.content_hash.slice(0, 8)}`
            : "Connecting"}
        </span>
      </footer>
    </div>
  );
}
