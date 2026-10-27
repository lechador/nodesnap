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
    c.setFont("Helvetica-Bold", 16)
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
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(cx, cy, s.name)
    if snap.pool and level_name == "basement":
        pl = snap.pool
        c.setStrokeColorRGB(0.1, 0.35, 0.8)
        c.setLineWidth(2)
        c.rect(ox + pl.origin_x_m * scale, oy + pl.origin_y_m * scale,
               pl.water_length_m * scale, pl.water_width_m * scale, stroke=1, fill=0)
        c.setFont("Helvetica", 7)
        c.drawString(ox + pl.origin_x_m * scale, oy + (pl.origin_y_m + pl.water_width_m) * scale + 4,
                     f"POOL WATER {pl.water_length_m} x {pl.water_width_m} m")
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)
    c.setFont("Helvetica", 8)
    c.drawString(ox, oy - 18, f"Scale: drawing fitted to page; envelope 18.0 x 15.5 m. Units: m (SI canonical). North: +Y.")
    c.showPage()


def build_review_pdf(snap: ProjectSnapshot) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=PAGE)
    c.setTitle(f"NodeSnap review draft — revision {snap.revision_number}")
    for lvl in ("basement", "ground", "upper", "roof"):
        _plan_page(c, snap, lvl)
    # calculation + schedule page
    w, h = PAGE
    c.setFont("Helvetica-Bold", 16)
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
            c.drawString(inch, y, ln); y -= 0.22 * inch
    y -= 0.2 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(inch, y, "Area schedule (actual from canonical geometry vs program target)")
    y -= 0.25 * inch
    c.setFont("Helvetica", 8)
    for r in area_schedule(snap):
        tgt = f"{r['target_area_m2']:.2f}" if r['target_area_m2'] is not None else "—"
        delta = f"{r['delta_m2']:+.2f}" if r['delta_m2'] is not None else "—"
        c.drawString(inch, y, f"{r['level']:<16} {r['name']:<28} actual {r['actual_area_m2']:>8.2f} m2   target {tgt:>8}   delta {delta:>8}")
        y -= 0.16 * inch
        if y < inch:
            c.showPage(); y = h - inch; c.setFont("Helvetica", 8)
    c.showPage()
    c.save()
    return buf.getvalue()
