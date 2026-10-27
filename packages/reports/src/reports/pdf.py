"""Drawing + calculation PDF from canonical coordinates — spec S8/E-Delivery 4.
Vector linework via ReportLab; every page carries the frozen revision."""
from __future__ import annotations

import io

from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from domain.models import ProjectSnapshot
from engineering.pool import pool_quantities
from geometry.validate import area_schedule

PAGE = landscape((18 * inch, 12 * inch))  # ARCH B sheet


def _plan_page(c: canvas.Canvas, snap: ProjectSnapshot, level_name: str):
    w, h = PAGE
    c.setFont("Helvetica-Bold", 19)
    c.drawString(inch, h - 0.8 * inch, f"NodeSnap — {snap.title}")
    c.setFont("Helvetica", 10)
    c.drawString(inch, h - 1.15 * inch,
                 f"Level: {level_name}   Revision: {snap.revision_number} ({snap.revision_id})")
    c.drawString(inch, h - 1.4 * inch,
                 "Professional review draft — Demonstration design, assumptions require professional verification")
    level = next(l for l in snap.levels if l.name == level_name)
    spaces = [s for s in snap.spaces if s.level_id == level.id]
    # fit 18 x 15.5 m envelope into drawing area
    ox, oy, dw, dh = inch, 1.2 * inch, w - 2 * inch, h - 3.0 * inch
    scale = min(dw / 18.0, dh / 15.5)
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    for s in spaces:
        pts = s.polygon
        p = c.beginPath()
        for i, (x, y) in enumerate(pts):
            px, py = ox + x * scale, oy + y * scale
            (p.moveTo if i == 0 else p.lineTo)(px, py)
        p.close()
        c.setFillColorRGB(0.92, 0.95, 0.98) if s.classification == "principal" \
            else c.setFillColorRGB(0.97, 0.94, 0.88)
        c.drawPath(p, stroke=1, fill=1)
        cx = ox + sum(pt[0] for pt in pts[:-1]) / (len(pts) - 1) * scale
        cy = oy + sum(pt[1] for pt in pts[:-1]) / (len(pts) - 1) * scale
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 9.5)
        c.drawCentredString(cx, cy, s.name)
    if snap.pool and level_name == "basement":
        pl = snap.pool
        c.setStrokeColorRGB(0.1, 0.35, 0.8)
        c.setLineWidth(2)
        c.rect(ox + pl.origin_x_m * scale, oy + pl.origin_y_m * scale,
               pl.water_length_m * scale, pl.water_width_m * scale, stroke=1, fill=0)
        c.setFont("Helvetica", 9.5)
        c.drawString(ox + pl.origin_x_m * scale, oy + (pl.origin_y_m + pl.water_width_m) * scale + 4,
                     f"POOL WATER {pl.water_length_m} x {pl.water_width_m} m")
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)
    c.setFont("Helvetica", 10)
    c.drawString(ox, oy - 18, f"Scale: drawing fitted to page; envelope 18.0 x 15.5 m. Units: m (SI canonical). North: +Y.")
    c.showPage()


def _extra_pages(c, snap, results):
    from .sheets import header, lines
    by_id = {r["method_id"]: r for r in (results or [])}
    # S-101 structure
    fr = (by_id.get("structural_frame_analysis") or {}).get("quantities") or {}
    y = header(c, PAGE, "S-101", "Structure — baseline gravity frame", snap)
    items = [
        f"Idealization: {fr.get('idealization', 'not calculated')}",
        f"Total gravity load applied: {fr.get('total_applied_load_n', 0):,.0f} N; sum of base reactions: {fr.get('sum_base_reactions_n', 0):,.0f} N; equilibrium residual: {fr.get('equilibrium_relative_residual', 0):.2e}",
        f"Maximum beam moment (magnitude): {fr.get('max_beam_abs_moment_nm', 0):,.0f} N-m; maximum beam deflection: {fr.get('max_floor_deflection_m', 0) * 1000:.1f} mm",
        "Loads and section properties are explicit demonstration assumptions (see REG-101). Self-weight excluded in this scenario and not double counted.",
        "Checks NOT evaluated: steel/timber member design, connections, diaphragm, lateral/seismic system, serviceability limits — sourced methods still gated. This sheet reports elastic responses only.",
        "Base reactions by column (N):",
    ]
    for k, v in (fr.get("base_reactions_n") or {}).items():
        items.append(f"   {k}: {v:,.0f}")
    lines(c, PAGE, y, items)
    c.showPage()
    # F-101 foundations
    be = (by_id.get("foundation_bearing_review") or {}).get("quantities") or {}
    y = header(c, PAGE, "F-101", "Foundations — bearing scenario", snap)
    lines(c, PAGE, y, [
        f"Pressure assumption: {be.get('pressure_assumption', 'not calculated')}",
        f"Average pressure: {be.get('average_pressure_pa', 0):,.1f} Pa vs assumed allowable {be.get('assumed_allowable_bearing_pa', 0):,.0f} Pa -> utilization {be.get('utilization', 0):.3f}",
        "Missing input: project geotechnical basis (MISSING_INPUT). NYC BC 1803.2 requires a geotechnical investigation for a real structure; this scenario cannot satisfy it.",
        f"Not evaluated: {be.get('exclusions', '')}",
    ])
    c.showPage()
    # MPE-101 services
    sv = (by_id.get("services_inventories") or {}).get("quantities") or {}
    y = header(c, PAGE, "MPE-101", "Services — mechanical / plumbing / electrical / energy / drainage", snap)
    el, pl, hv, dr = sv.get("electrical", {}), sv.get("plumbing", {}), sv.get("hvac_energy", {}), sv.get("drainage", {})
    items = [
        f"Electrical: connected load {el.get('connected_load_w', 0):,.0f} W; current at declared {el.get('declared_voltage_v', 0)} V = {el.get('current_at_connected_load_a', 0):.1f} A. {el.get('note', '')}",
        f"Plumbing: {len(pl.get('fixtures', []))} fixtures; summed fixture flows {pl.get('sum_of_fixture_flows_l_min', 0):,.0f} L/min. {pl.get('note', '')}",
        f"Energy/HVAC envelope conduction at dT={hv.get('delta_t_k', 0)} K: total {hv.get('total_conduction_w', 0):,.0f} W (assumed U-values; component only).",
    ]
    for e in hv.get("envelope_conduction", []):
        items.append(f"   {e['element']}: A={e['area_m2']} m2, U={e['u_w_m2k']} W/m2K, Q={e['heat_loss_w']:,.0f} W")
    items += [
        f"Drainage: roof runoff scenario {dr.get('runoff_l_s', 0):.2f} L/s (C={dr.get('runoff_coefficient_assumed')}, rainfall {dr.get('rainfall_mm_h_assumed')} mm/h, both assumed). {dr.get('note', '')}",
        "Pool environment/evaporation, ventilation rates, equipment selection, demand factors, ampacity, panel schedules, NYCECC pathway and hydraulic sizing: research_required — no values invented for this sheet.",
    ]
    lines(c, PAGE, y, items)
    c.showPage()
    # REG-101 registers
    y = header(c, PAGE, "REG-101", "Registers — assumptions, methods, open issues", snap)
    items = ["Assumptions (all demonstration_assumption unless stated):"]
    for a in snap.assumptions:
        items.append(f"   - {a.field} = {a.value} — {a.rationale}")
    items.append("Methods and coverage:")
    for r in results or []:
        items.append(f"   - {r['method_id']}: state={r['method_state']}, execution={r['execution_status']}, check={r['check_outcome']}")
        for iss in r.get("issues", []):
            items.append(f"       OPEN [{iss['code']}] {iss.get('field','')}: {iss['message']}")
    items.append("Professional review: unreviewed. Authority process: not_submitted. Signature/seal/job-number fields are intentionally blank.")
    lines(c, PAGE, y, items)
    c.showPage()


def build_review_pdf(snap: ProjectSnapshot, results: list[dict] | None = None) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=PAGE)
    c.setTitle(f"NodeSnap review draft — revision {snap.revision_number}")
    from .sheets import cover_page, site_page
    cover_page(c, PAGE, snap, results or [])
    site_page(c, PAGE, snap)
    for lvl in ("basement", "ground", "upper", "roof"):
        _plan_page(c, snap, lvl)
    # calculation + schedule page
    w, h = PAGE
    c.setFont("Helvetica-Bold", 19)
    c.drawString(inch, h - 0.8 * inch, "Calculation & schedule — pool quantities and areas")
    c.setFont("Helvetica", 10)
    y = h - 1.3 * inch
    c.drawString(inch, y, f"Revision {snap.revision_number} ({snap.revision_id})  content_hash={snap.content_hash[:16]}…")
    y -= 0.35 * inch
    if snap.pool:
        q = pool_quantities(snap.pool.water_length_m, snap.pool.water_width_m, snap.pool.water_depth_m)
        lines = [
            f"Pool water: {q['inputs']['water_length_m']} x {q['inputs']['water_width_m']} x {q['inputs']['water_depth_m']} m (flat-bottom declared basin)",
            f"Surface area = {q['surface_area_m2']:.4f} m2",
            f"Volume = {q['volume_m3']:.4f} m3",
            f"Mass = {q['mass_kg']:.2f} kg  (rho = {q['inputs']['rho_water_kg_m3']} kg/m3)",
            f"Weight = {q['weight_n']:.2f} N  (g = {q['inputs']['g_m_s2']} m/s2)",
            f"Max hydrostatic pressure = {q['max_hydrostatic_pressure_pa']:.2f} Pa",
            "Method: pool_quantities (implemented; physics only — not pool-shell design). Input basis: demonstration_assumption.",
        ]
        for ln in lines:
            c.drawString(inch, y, ln); y -= 0.27 * inch
    y -= 0.2 * inch
    c.setFont("Helvetica-Bold", 13)
    c.drawString(inch, y, "Area schedule (actual from canonical geometry vs program target)")
    y -= 0.25 * inch
    c.setFont("Helvetica", 10)
    for r in area_schedule(snap):
        tgt = f"{r['target_area_m2']:.2f}" if r['target_area_m2'] is not None else "—"
        delta = f"{r['delta_m2']:+.2f}" if r['delta_m2'] is not None else "—"
        c.drawString(inch, y, f"{r['level']:<16} {r['name']:<28} actual {r['actual_area_m2']:>8.2f} m2   target {tgt:>8}   delta {delta:>8}")
        y -= 0.20 * inch
        if y < inch:
            c.showPage(); y = h - inch; c.setFont("Helvetica", 10)
    c.showPage()
    _extra_pages(c, snap, results or [])
    c.save()
    return buf.getvalue()
