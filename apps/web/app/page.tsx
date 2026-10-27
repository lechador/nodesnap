"use client";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

const Plan2D = dynamic(() => import("./Plan2D"), { ssr: false });
const Villa3D = dynamic(() => import("./Villa3D"), { ssr: false });

const LEVELS = ["basement", "ground", "upper", "roof"] as const;

async function api(path: string, opts: RequestInit = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j?.detail ?? `HTTP ${r.status}`);
  return j.data;
}

export default function Home() {
  const [snap, setSnap] = useState<any>(null);
  const [projectId, setProjectId] = useState("");
  const [level, setLevel] = useState<string>("ground");
  const [view, setView] = useState<"plan" | "3d">("plan");
  const [selected, setSelected] = useState<string>("");
  const [results, setResults] = useState<any[]>([]);
  const [coverage, setCoverage] = useState<any[]>([]);
  const [poolLen, setPoolLen] = useState("8");
  const [msg, setMsg] = useState("Starting demo session…");
  const [artifact, setArtifact] = useState<any>(null);
  const [chat, setChat] = useState("");

  async function load(pid: string, rid: string) {
    const s = await api(`/api/v1/projects/${pid}/revisions/${rid}`);
    setSnap(s);
    const a = await api(`/api/v1/projects/${pid}/analyses`, {
      method: "POST", body: JSON.stringify({ revision_id: rid }),
    });
    setResults(a.results);
    const c = await api(`/api/v1/projects/${pid}/coverage?revision_id=${rid}`);
    setCoverage(c.methods);
  }

  async function start() {
    try {
      await api("/api/v1/demo/sessions", { method: "POST" });
      const p = await api("/api/v1/projects", { method: "POST", body: JSON.stringify({ seed: true }) });
      setProjectId(p.project_id);
      await load(p.project_id, p.revision_id);
      setMsg("Seed villa loaded — Demo Villa NYC-01 (synthetic site, no real address).");
    } catch (e: any) { setMsg(`Error: ${e.message}`); }
  }
  useEffect(() => { start(); }, []);

  async function applyPool() {
    try {
      const out = await api(`/api/v1/projects/${projectId}/commands`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "If-Match": `"${snap.revision_id}"` },
        body: JSON.stringify({ base_revision_id: snap.revision_id,
          commands: [{ type: "set_pool_dimensions", water_length_m: Number(poolLen) }] }),
      });
      setArtifact(null);
      await load(projectId, out.revision_id);
      setMsg(`Pool resized → revision ${out.revision_number}. Previous results invalidated and recalculated.`);
    } catch (e: any) { setMsg(`Edit rejected: ${e.message}`); }
  }

  async function moveSpace(id: string, dx: number, dy: number) {
    try {
      const out = await api(`/api/v1/projects/${projectId}/commands`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "If-Match": `"${snap.revision_id}"` },
        body: JSON.stringify({ base_revision_id: snap.revision_id,
          commands: [{ type: "move_space", element_id: id, dx_m: dx, dy_m: dy }] }),
      });
      setArtifact(null);
      await load(projectId, out.revision_id);
      setMsg(`Room moved → revision ${out.revision_number}. Areas recalculated.`);
    } catch (e: any) { setMsg(`Move rejected — geometry restored: ${e.message}`); await load(projectId, snap.revision_id); }
  }

  async function regenerate() {
    if (level !== "ground" && level !== "upper") { setMsg("Generation is supported for Ground and Upper floors."); return; }
    const lvl = snap.levels.find((l: any) => l.name === level);
    const rooms = snap.spaces.filter((s: any) => s.level_id === lvl.id && s.classification === "principal")
      .map((s: any) => ({ name: s.name, use: s.use, target_area_m2: s.target_area_m2 }));
    try {
      const out = await api(`/api/v1/projects/${projectId}/generate`, {
        method: "POST", body: JSON.stringify({ base_revision_id: snap.revision_id, level, rooms }) });
      if (out.execution_status === "blocked") { setMsg(`Solver: ${out.issue.message}`); return; }
      setArtifact(null);
      await load(projectId, out.revision_id);
      setMsg(`CP-SAT layout generated (${out.solver_status}) → revision ${out.revision_number}.`);
    } catch (e: any) { setMsg(`Generation failed: ${e.message}`); }
  }

  async function undo() {
    try {
      const out = await api(`/api/v1/projects/${projectId}/undo`, { method: "POST", body: "{}" });
      setArtifact(null);
      await load(projectId, out.revision_id);
      setMsg(`Undone — restored revision ${out.restored_from_revision_number} as new revision ${out.revision_number}.`);
    } catch (e: any) { setMsg(`Undo: ${e.message}`); }
  }

  async function exportPdf() {
    const m = await api(`/api/v1/projects/${projectId}/exports`, {
      method: "POST", body: JSON.stringify({ revision_id: snap.revision_id }) });
    setArtifact(m);
  }

  async function sendChat() {
    try {
      const r = await api(`/api/v1/projects/${projectId}/conversations`, {
        method: "POST", body: JSON.stringify({ text: chat, base_revision_id: snap.revision_id }) });
      if (r.execution_status === "blocked" || r.execution_status === "error") {
        setMsg(`Meta ${r.execution_status}: ${r.issue?.message ?? "no proposal"}`);
        return;
      }
      if (r.committed_revision_id) {
        setArtifact(null);
        await load(projectId, r.committed_revision_id);
        setMsg(`Meta (${r.model}) → ${r.proposal.intent} committed as revision ${r.committed_revision_number}. ${r.explanation}`);
      } else {
        setMsg(`Meta (${r.model}): ${r.explanation || r.proposal?.intent}`);
      }
    } catch (e: any) { setMsg(`Conversation failed: ${e.message}`); }
  }

  const poolQ = results.find((r) => r.method_id === "pool_quantities")?.quantities;
  const frameQ = results.find((r) => r.method_id === "structural_frame_analysis")?.quantities;
  const bearQ = results.find((r) => r.method_id === "foundation_bearing_review")?.quantities;
  const svcQ = results.find((r) => r.method_id === "services_inventories")?.quantities;
  const sel = snap?.spaces.find((s: any) => s.id === selected);

  return (
    <div style={{ fontFamily: "Georgia, 'Times New Roman', serif", color: "#1c2733", background: "#ece9e2", minHeight: "100vh" }}>
      <header style={{ background: "#20262e", color: "#f2efe8", padding: "14px 22px", display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <span style={{ fontSize: 26, letterSpacing: 0.5 }}>NodeSnap</span>
          <span style={{ marginLeft: 14, opacity: 0.75, fontSize: 13 }}>
            Describe a home → coordinated design, real calculations, professional review package
          </span>
        </div>
        <div style={{ fontSize: 13 }}>
          {snap ? <>Revision {snap.revision_number} · <code>{snap.content_hash.slice(0, 10)}…</code></> : "…"}
          <button onClick={exportPdf} disabled={!snap}
            style={{ marginLeft: 16, background: "#c96f2e", color: "white", border: 0, padding: "8px 14px", cursor: "pointer", fontSize: 14 }}>
            Export review PDF
          </button>
        </div>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr 330px", gap: 0, alignItems: "start" }}>
        <aside style={{ padding: 18, borderRight: "1px solid #cfc9ba" }}>
          <h3 style={{ marginTop: 0 }}>Brief</h3>
          <p style={{ fontSize: 14, lineHeight: 1.5 }}>
            Contemporary luxury villa, NYC demonstration. Two floors, six principal rooms per floor,
            basement indoor pool, occupied roof terrace. Steel frame, timber secondary, concrete basement/pool.
          </p>
          <p style={{ fontSize: 13, background: "#fff8e6", padding: 10, border: "1px solid #e3d29a" }}>
            Site: <b>Demo Villa NYC-01</b> — synthetic 30 × 45 m context. No real address or BBL.
            Quantities below are demonstration assumptions unless labelled derived.
          </p>
          <h4>Conversation</h4>
          <textarea value={chat} onChange={(e) => setChat(e.target.value)} rows={3}
            placeholder="Describe your home, or ask for a change…"
            style={{ width: "100%", boxSizing: "border-box", padding: 8 }} />
          <button onClick={sendChat} disabled={!snap || !chat}
            style={{ marginTop: 8, padding: "7px 12px", cursor: "pointer" }}>Send to Meta</button>
          <p style={{ fontSize: 12.5, lineHeight: 1.5, color: "#5a4632" }}>{msg}</p>

          <h4>Try a real change</h4>
          <label style={{ fontSize: 13 }}>Pool water length (m)
            <input value={poolLen} onChange={(e) => setPoolLen(e.target.value)}
              style={{ width: 70, marginLeft: 8, padding: 5 }} />
          </label>
          <button onClick={applyPool} disabled={!snap}
            style={{ marginLeft: 8, padding: "7px 12px", cursor: "pointer" }}>Apply</button>
          <p style={{ fontSize: 12.5 }}>Commits a typed command, creates a new revision, reruns pool + area calculations.</p>

          <h4>Generate / history</h4>
          <button onClick={regenerate} disabled={!snap} style={{ padding: "7px 12px", cursor: "pointer" }}>
            Regenerate {level} layout (CP-SAT)
          </button>
          <button onClick={undo} disabled={!snap} style={{ marginLeft: 8, padding: "7px 12px", cursor: "pointer" }}>Undo</button>
          <p style={{ fontSize: 12.5 }}>In the plan: click a room to select it, then drag it. Moves snap to 0.1 m;
            overlapping or out-of-plate moves are rejected and the room is restored.</p>

          {artifact && (
            <p style={{ fontSize: 13 }}>
              <a href={`/artifacts/${artifact.artifact_id}`}>Download PDF — revision {artifact.revision_number}</a>
              <br />SHA-256 {artifact.file_sha256.slice(0, 16)}… · {artifact.document_presence} · {artifact.review_status}
              <br />Sheets: {artifact.sheets?.join(" · ")}
              <br /><a href={`/artifacts/${artifact.manifest_artifact_id}`}>Export manifest (JSON)</a>
              {" · "}<a href={`/artifacts/${artifact.model_artifact_id}`}>Canonical model (JSON)</a>
            </p>
          )}
        </aside>

        <main style={{ padding: 18 }}>
          <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
            {LEVELS.map((l) => (
              <button key={l} onClick={() => setLevel(l)}
                style={{ padding: "7px 12px", cursor: "pointer", fontWeight: level === l ? 700 : 400,
                         background: level === l ? "#26303c" : "white", color: level === l ? "white" : "#26303c", border: "1px solid #26303c" }}>
                {l[0].toUpperCase() + l.slice(1)}
              </button>
            ))}
            <span style={{ flex: 1 }} />
            {(["plan", "3d"] as const).map((v) => (
              <button key={v} onClick={() => setView(v)}
                style={{ padding: "7px 12px", cursor: "pointer", fontWeight: view === v ? 700 : 400,
                         background: view === v ? "#c96f2e" : "white", color: view === v ? "white" : "#26303c", border: "1px solid #c96f2e" }}>
                {v === "plan" ? "Plan" : "3D"}
              </button>
            ))}
          </div>
          {snap ? (view === "plan"
            ? <Plan2D snap={snap} level={level} selected={selected} onSelect={setSelected} onMove={moveSpace} />
            : <Villa3D snap={snap} level={level} />)
            : <p>Loading…</p>}
          <p style={{ fontSize: 12.5, color: "#555" }}>
            Plan and 3D are derived views of the same canonical model — neither owns dimensions.
            Click a room to inspect it.
          </p>
        </main>

        <aside style={{ padding: 18, borderLeft: "1px solid #cfc9ba", fontSize: 13.5 }}>
          <h3 style={{ marginTop: 0 }}>Inspector</h3>
          {sel ? (
            <p><b>{sel.name}</b><br />Use: {sel.use} · {sel.classification}<br />
              Level: {snap.levels.find((l: any) => l.id === sel.level_id)?.label}</p>
          ) : <p>Select a space in the plan.</p>}

          <h4>Pool calculation (real, deterministic)</h4>
          {poolQ ? (
            <table cellPadding={3} style={{ borderCollapse: "collapse" }}>
              <tbody>
                <tr><td>Surface</td><td><b>{poolQ.surface_area_m2.toFixed(2)} m²</b></td></tr>
                <tr><td>Volume</td><td><b>{poolQ.volume_m3.toFixed(2)} m³</b></td></tr>
                <tr><td>Water mass</td><td><b>{poolQ.mass_kg.toLocaleString()} kg</b></td></tr>
                <tr><td>Water weight</td><td><b>{poolQ.weight_n.toLocaleString(undefined, { maximumFractionDigits: 0 })} N</b></td></tr>
                <tr><td>Max hydrostatic pressure</td><td><b>{poolQ.max_hydrostatic_pressure_pa.toFixed(0)} Pa</b></td></tr>
              </tbody>
            </table>
          ) : <p>Not calculated yet.</p>}
          <p style={{ color: "#6b5a43" }}>Method <code>pool_quantities</code> — physics only, not pool-shell design.
            Check outcome: <b>not_evaluated</b>. Input basis: demonstration_assumption.</p>

          <h4>Structure — gravity frame (PyNite, fixtures-verified adapter)</h4>
          {frameQ ? (
            <table cellPadding={3} style={{ borderCollapse: "collapse" }}>
              <tbody>
                <tr><td>Total gravity load</td><td><b>{(frameQ.total_applied_load_n / 1000).toLocaleString(undefined, { maximumFractionDigits: 0 })} kN</b></td></tr>
                <tr><td>Base reactions (sum)</td><td><b>{(frameQ.sum_base_reactions_n / 1000).toLocaleString(undefined, { maximumFractionDigits: 0 })} kN</b></td></tr>
                <tr><td>Max beam moment</td><td><b>{(frameQ.max_beam_abs_moment_nm / 1000).toFixed(1)} kN·m</b></td></tr>
                <tr><td>Max beam deflection</td><td><b>{(frameQ.max_floor_deflection_m * 1000).toFixed(1)} mm</b></td></tr>
              </tbody>
            </table>
          ) : <p>Not calculated yet.</p>}
          <p style={{ color: "#6b5a43" }}>Declared gravity scenario with assumed loads/sections.
            Member, connection and lateral checks: <b>not_evaluated</b> (sourced methods still gated).</p>

          {bearQ && (
            <>
              <h4>Foundations — bearing scenario</h4>
              <p>Average pressure <b>{(bearQ.average_pressure_pa / 1000).toFixed(2)} kPa</b> vs assumed allowable{" "}
                <b>{bearQ.assumed_allowable_bearing_pa / 1000} kPa</b> → utilization <b>{bearQ.utilization.toFixed(2)}</b>.
                Uniform-pressure assumption only; no geotechnical evidence — real-project basis remains a missing input.</p>
            </>
          )}

          <h4>Services — inventories &amp; component quantities</h4>
          {svcQ ? (
            <ul style={{ paddingLeft: 18, lineHeight: 1.6 }}>
              <li>Electrical connected load: <b>{(svcQ.electrical.connected_load_w / 1000).toFixed(1)} kW</b>{" "}
                ({svcQ.electrical.current_at_connected_load_a.toFixed(0)} A at declared {svcQ.electrical.declared_voltage_v} V; demand sizing gated)</li>
              <li>Plumbing fixtures: <b>{svcQ.plumbing.fixtures.length}</b>, summed fixture flows{" "}
                <b>{svcQ.plumbing.sum_of_fixture_flows_l_min.toFixed(0)} L/min</b> (fixture-unit sizing gated)</li>
              <li>Envelope conduction (assumed U, ΔT {svcQ.hvac_energy.delta_t_k} K):{" "}
                <b>{(svcQ.hvac_energy.total_conduction_w / 1000).toFixed(2)} kW</b> (ventilation/latent/pool loads gated)</li>
              <li>Roof runoff scenario: <b>{svcQ.drainage.runoff_l_s.toFixed(2)} L/s</b>{" "}
                (C={svcQ.drainage.runoff_coefficient_assumed}, {svcQ.drainage.rainfall_mm_h_assumed} mm/h assumed; hydraulic sizing gated)</li>
            </ul>
          ) : <p>Not calculated yet.</p>}

          <h4>Coverage &amp; honest gaps</h4>
          <ul style={{ paddingLeft: 18, lineHeight: 1.6 }}>
            {coverage.map((m) => (
              <li key={m.id}><code>{m.id}</code> — {m.method_state}
                {m.method_state === "research_required" && <span style={{ color: "#a33" }}> (gap, not a pass)</span>}
              </li>
            ))}
          </ul>
          <p style={{ color: "#6b5a43" }}>Workflow and discipline completion are tracked separately.
            Nothing above claims NYC code compliance, professional review, or DOB approval.</p>
        </aside>
      </div>
    </div>
  );
}
