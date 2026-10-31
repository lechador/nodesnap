"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Icon from "./Icon";
import { useMicrophone } from "../lib/useMicrophone";
import type { BriefTurn, DesignResponse, ProjectSummary } from "../lib/types";

const examples = [
  {
    title: "A compact family home",
    detail: "One floor · two bedrooms · 12 × 10 m",
    text: "Design a single-storey house, 12 by 10 metres, with 2 bedrooms, a living/dining room, kitchen, bathroom and utility room. No basement, pool or roof terrace.",
  },
  {
    title: "A place to work",
    detail: "Two floors · studio and offices · 14 × 12 m",
    text: "Create a two-storey office building, 14 by 12 metres. Ground floor: reception, an open studio for eight people, a meeting room, kitchenette and toilets. Upper floor: four private offices, a meeting room and toilets. No basement, pool or occupied roof terrace.",
  },
  {
    title: "A home with a pool",
    detail: "Two floors · four bedrooms · basement pool",
    text: "Design a two-storey home, 18 by 16 metres, with four bedrooms, a living room, kitchen, dining room and study. Include bathrooms, a basement with an 8 by 3.5 metre pool, and a 60 square metre roof terrace. Use limestone and oak finishes.",
  },
];
type Props = {
  busy: string;
  ready: boolean;
  error: string;
  projects: ProjectSummary[];
  onCreate: (text: string, history: BriefTurn[]) => Promise<DesignResponse>;
  onOpen: (id: string) => void;
  onDemo: () => void;
  onRetry: () => void;
  onError: (message: string) => void;
  onCancel?: () => void;
};

export default function NewDesign({
  busy,
  ready,
  error,
  projects,
  onCreate,
  onOpen,
  onDemo,
  onRetry,
  onError,
  onCancel,
}: Props) {
  const [text, setText] = useState("");
  const [turns, setTurns] = useState<BriefTurn[]>([]);
  const [lastRequest, setLastRequest] = useState<{
    text: string;
    history: BriefTurn[];
  } | null>(null);
  const [retry, setRetry] = useState(false);
  const input = useRef<HTMLTextAreaElement>(null),
    dialogue = useRef<HTMLDivElement>(null),
    pending = useRef(false);
  const briefLimitReached = turns.length >= 12;
  useEffect(() => {
    if (dialogue.current)
      dialogue.current.scrollTop = dialogue.current.scrollHeight;
  }, [turns]);
  const mic = useMicrophone(undefined, setText, onError);
  async function submit(request = { text: text.trim(), history: turns }) {
    if (
      !request.text ||
      busy ||
      !ready ||
      pending.current ||
      request.history.length >= 12
    )
      return;
    pending.current = true;
    setRetry(false);
    setLastRequest(request);
    setTurns([...request.history, { role: "user", text: request.text }]);
    setText("");
    try {
      const result = await onCreate(request.text, request.history);
      if (!result.project_id) {
        const message =
          result.explanation ??
          result.issue?.message ??
          "Please describe the building you have in mind.";
        setTurns([
          ...request.history,
          { role: "user", text: request.text },
          { role: "assistant", text: message },
        ]);
        setRetry(result.execution_status === "error");
        input.current?.focus();
      }
    } finally {
      pending.current = false;
    }
  }
  return (
    <div className="new-design-shell">
      <header className="new-design-header">
        <Link
          href="/"
          className="new-design-brand"
          aria-label="NodeSnap studio"
        >
          <Icon name="cube" size={25} />
          <span>nodesnap.</span>
        </Link>
        <span>Architectural design studio</span>
        {onCancel && (
          <button disabled={!!busy || mic.state !== "idle"} onClick={onCancel}>
            <Icon name="chevron" size={14} />
            <span>Back to your building</span>
          </button>
        )}
      </header>
      <main className="new-design-main">
        <section className="new-brief" aria-label="New building brief">
          <div className="new-brief-heading">
            <h1>
              What would you
              <br />
              like to build?
            </h1>
            <p>
              Start with the building you have in mind. Describe its size,
              floors and spaces. Your model and plans will take shape from that
              brief.
            </p>
          </div>
          {turns.length > 0 && (
            <div ref={dialogue} className="brief-dialogue" aria-live="polite">
              {turns.map((turn, i) => (
                <div className={`brief-turn ${turn.role}`} key={i}>
                  <span>
                    {turn.role === "user" ? "Your brief" : "NodeSnap"}
                  </span>
                  <p>{turn.text}</p>
                </div>
              ))}
            </div>
          )}
          <form
            className={`new-brief-composer ${busy ? "is-building" : ""}`}
            onSubmit={(e) => {
              e.preventDefault();
              void submit();
            }}
          >
            <label htmlFor="building-brief">
              {turns.length
                ? "Continue your brief"
                : "Describe your new building"}
            </label>
            <textarea
              ref={input}
              id="building-brief"
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={8000}
              placeholder="A two-storey home with three bedrooms, a sunny living room and a roof terrace. About 14 × 12 metres…"
              rows={5}
              disabled={
                !ready ||
                !!busy ||
                mic.state === "transcribing" ||
                mic.state === "requesting"
              }
            />
            <div className="new-brief-actions">
              <button
                type="button"
                className={`brief-voice ${mic.state === "recording" ? "recording" : ""}`}
                aria-label={
                  mic.state === "recording"
                    ? "Stop recording building brief"
                    : "Record building brief"
                }
                disabled={
                  !ready ||
                  !!busy ||
                  mic.state === "transcribing" ||
                  mic.state === "requesting"
                }
                onClick={() =>
                  mic.state === "recording" ? mic.stop() : void mic.start()
                }
              >
                <Icon
                  name={mic.state === "recording" ? "stop" : "mic"}
                  size={17}
                />
                <span>
                  {mic.state === "recording"
                    ? `${mic.seconds}s · Stop`
                    : mic.state === "transcribing"
                      ? "Transcribing…"
                      : mic.state === "requesting"
                        ? "Opening microphone…"
                        : "Speak your brief"}
                </span>
              </button>
              <button
                className="primary-button"
                type="submit"
                disabled={
                  !ready ||
                  !!busy ||
                  !text.trim() ||
                  mic.state !== "idle" ||
                  briefLimitReached
                }
              >
                <span>
                  {busy
                    ? "Designing…"
                    : turns.length
                      ? "Continue design"
                      : "Create building"}
                </span>
                <Icon name="arrow" size={16} />
              </button>
            </div>
          </form>
          {busy && (
            <div role="status" className="brief-status">
              <span className="status-dot working" />
              {busy}…
            </div>
          )}
          {error && (
            <div role="alert" className="brief-error">
              <Icon name="info" size={16} />
              <span>{error}</span>
              {!ready && (
                <button onClick={onRetry} disabled={!!busy}>
                  Reconnect
                </button>
              )}
            </div>
          )}
          {retry && lastRequest && (
            <button
              className="secondary-button"
              disabled={!!busy}
              onClick={() => void submit(lastRequest)}
            >
              Retry this brief
            </button>
          )}
          {turns.length > 0 && (
            <div className="brief-restart">
              {briefLimitReached && (
                <p>
                  Let’s bring the size, floors and rooms together in a fresh
                  brief.
                </p>
              )}
              <button
                type="button"
                disabled={!!busy || mic.state !== "idle"}
                onClick={() => {
                  setTurns([]);
                  setRetry(false);
                  setLastRequest(null);
                  input.current?.focus();
                }}
              >
                Start a fresh brief
              </button>
            </div>
          )}
          <p className="brief-basis">
            Rooms and dimensions come from your brief. Any assumptions are
            recorded with the design.
          </p>
          {!turns.length && (
            <section className="brief-examples">
              <h2>Try a starting idea</h2>
              {examples.map((example) => (
                <button
                  key={example.title}
                  disabled={!!busy || !ready || mic.state !== "idle"}
                  onClick={() => {
                    setText(example.text);
                    input.current?.focus();
                  }}
                >
                  <span>
                    <strong>{example.title}</strong>
                    <small>{example.detail}</small>
                  </span>
                  <Icon name="arrow" size={17} />
                </button>
              ))}
            </section>
          )}
          <div className="example-link">
            <span>Want to explore first?</span>
            <button
              disabled={!!busy || !ready || mic.state !== "idle"}
              onClick={onDemo}
            >
              Open the example villa <Icon name="chevron" size={13} />
            </button>
          </div>
        </section>
        <aside
          className="new-design-stage"
          aria-label="Building preview and saved projects"
        >
          <div className={`blank-drawing ${busy ? "is-building" : ""}`}>
            <div className="blank-sheet-meta">
              <Icon name="plan" size={17} />
              <span>New building / Design brief</span>
            </div>
            <svg
              viewBox="0 0 540 390"
              aria-hidden="true"
              className="drafting-guides"
            >
              <defs>
                <pattern
                  id="draft-grid"
                  width="24"
                  height="24"
                  patternUnits="userSpaceOnUse"
                >
                  <path
                    d="M24 0H0V24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth=".5"
                  />
                </pattern>
              </defs>
              <rect
                x="40"
                y="30"
                width="460"
                height="310"
                fill="url(#draft-grid)"
                opacity=".32"
              />
              <path
                d="M40 70V30h40M460 30h40v40M500 300v40h-40M80 340H40v-40"
                fill="none"
                stroke="currentColor"
              />
              <path
                className="draft-scan"
                d="M40 185H500"
                fill="none"
                stroke="currentColor"
              />
              <path
                d="M270 173v24m-12-12h24"
                fill="none"
                stroke="currentColor"
              />
            </svg>
            <div className="blank-sheet-caption">
              <h2>
                {busy ? "Giving your idea a plan." : "A fresh starting point."}
              </h2>
              <p>
                {busy
                  ? "Your brief is being interpreted before the model is built."
                  : "Your own building, from the ground up. The 3D model and dimensioned plans will appear here."}
              </p>
            </div>
            <div className="blank-sheet-footer">
              <span>{busy ? "Brief in progress" : "Awaiting your brief"}</span>
              <span>Model · Plans · Review</span>
            </div>
          </div>
          {projects.length > 0 && (
            <section className="saved-buildings">
              <h2>Your saved buildings</h2>
              <div>
                {projects.slice(0, 6).map((project) => (
                  <button
                    key={project.project_id}
                    disabled={!!busy || mic.state !== "idle"}
                    onClick={() => onOpen(project.project_id)}
                  >
                    <Icon name="cube" size={18} />
                    <span>
                      <strong>{project.title}</strong>
                      <small>Revision {project.revision_number}</small>
                    </span>
                    <Icon name="chevron" size={15} />
                  </button>
                ))}
              </div>
            </section>
          )}
        </aside>
      </main>
    </div>
  );
}
