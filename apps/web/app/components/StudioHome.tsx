"use client";
import Icon from "./Icon";
import type { ProjectSummary } from "../lib/types";

type Props = {
  ready: boolean;
  busy: string;
  error: string;
  projects: ProjectSummary[];
  onNew: () => void;
  onOpen: (id: string) => void;
  onDemo: () => void;
  onRetry: () => void;
};

export default function StudioHome({
  ready,
  busy,
  error,
  projects,
  onNew,
  onOpen,
  onDemo,
  onRetry,
}: Props) {
  const disabled = !ready || !!busy;
  return (
    <div className="new-design-shell">
      <header className="new-design-header">
        <div className="new-design-brand">
          <Icon name="cube" size={25} />
          <span>nodesnap.</span>
        </div>
        <span>Architectural design studio</span>
      </header>
      <main className="studio-home-main">
        <div className="studio-home-intro">
          <h1 data-screen-heading tabIndex={-1}>
            Make space for
            <br />
            what’s next.
          </h1>
          <p>
            Start a house from your own ideas, or pick up a design you’ve
            already begun.
          </p>
        </div>
        {error && (
          <div role="alert" className="brief-error home-error">
            <Icon name="info" size={17} />
            <span>{error}</span>
            <button onClick={onRetry} disabled={!!busy}>
              Retry connection
            </button>
          </div>
        )}
        <div className="home-paths">
          <section className="home-new" aria-labelledby="home-new-title">
            <h2 id="home-new-title">
              A new house.
              <br />
              Your starting point.
            </h2>
            <p>
              Describe your rooms, floors and dimensions. Shape the design
              through a conversation, with the model and plans beside you.
            </p>
            <button
              className="primary-button"
              onClick={onNew}
              disabled={disabled}
            >
              Build a new house <Icon name="arrow" size={18} />
            </button>
            <span className="home-new-note">Start with text or voice.</span>
          </section>
          <section
            className="home-existing"
            aria-labelledby="home-existing-title"
          >
            <h2 id="home-existing-title">Open an existing house</h2>
            <p>Choose a saved building to continue designing.</p>
            {busy ? (
              <p className="home-loading" role="status">
                <span className="status-dot working" /> {busy}…
              </p>
            ) : !error && ready && projects.length === 0 ? (
              <p className="home-empty">
                Your saved buildings will appear here. You can also explore the
                example below.
              </p>
            ) : null}
            {projects.length > 0 && (
              <ul className="home-projects" aria-label="Saved buildings">
                {projects.map((project) => (
                  <li key={project.project_id}>
                    <button
                      disabled={disabled}
                      onClick={() => onOpen(project.project_id)}
                    >
                      <Icon name="cube" size={20} />
                      <span>
                        <strong>{project.title}</strong>
                        <small>Revision {project.revision_number}</small>
                      </span>
                      <Icon name="chevron" size={16} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <button
              className="home-example"
              onClick={onDemo}
              disabled={disabled}
            >
              <Icon name="plan" size={20} />
              <span>
                <strong>Explore the example villa</strong>
                <small>Two floors · indoor pool · roof terrace</small>
              </span>
              <Icon name="chevron" size={16} />
            </button>
          </section>
        </div>
        <footer className="home-footer">
          Your ideas, in perspective.{" "}
          <span>3D models · Floor plans · Review packages</span>
        </footer>
      </main>
    </div>
  );
}
