"""Sheet helpers for the review package. Formatting only — every number is
computed by engineering/geometry services and passed in (spec E3)."""
from __future__ import annotations

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from domain.jurisdiction import JurisdictionProfile

MARGIN = inch


def header(c: canvas.Canvas, page_size, sheet: str, title: str, snap):
    w, h = page_size
    c.setFont("Helvetica-Bold", 15)
    c.drawString(MARGIN, h - 0.75 * inch, f"{sheet} — {title}")
    c.setFont("Helvetica", 9.5)
    c.drawString(MARGIN, h - 1.05 * inch,
                 f"NodeSnap · {snap.title} · Revision {snap.revision_number} ({snap.revision_id})")
    c.drawString(MARGIN, h - 1.28 * inch,
                 "Professional review draft — Demonstration design, assumptions require professional verification")
    c.setStrokeColorRGB(0.75, 0.45, 0.18)
    c.setLineWidth(2)
    c.line(MARGIN, h - 1.42 * inch, w - MARGIN, h - 1.42 * inch)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)
    return h - 1.75 * inch


def lines(c: canvas.Canvas, page_size, y: float, items: list[str],
          font_size: float = 9.5, leading: float = 0.21, bold_first: bool = False) -> float:
    w, h = page_size
    for i, s in enumerate(items):
        c.setFont("Helvetica-Bold" if (bold_first and i == 0) else "Helvetica", font_size)
        # simple word wrap at ~125 chars for this sheet size
        while len(s) > 125:
            cut = s.rfind(" ", 0, 125)
            c.drawString(MARGIN, y, s[:cut]); y -= leading * inch; s = "   " + s[cut + 1:]
            if y < MARGIN:
                c.showPage(); y = h - MARGIN
        c.drawString(MARGIN, y, s)
        y -= leading * inch
        if y < MARGIN:
            c.showPage(); y = h - MARGIN
    return y


def cover_page(c: canvas.Canvas, page_size, snap, results: list[dict]):
    y = header(c, page_size, "COVER", "Project index and design basis", snap)
    prof = JurisdictionProfile()
    items = [
        "Product promise: homeowner intent -> coordinated editable design -> traceable calculations -> professional review package.",
        f"Site mode: {snap.site.mode} — {snap.site.name}; real address: {snap.site.real_address or 'none'}; BBL: {snap.site.bbl or 'none (synthetic demonstration site, 30 x 45 m context)'}",
        f"Jurisdiction: {prof.authority} · profile {prof.profile_version}",
        f"Construction codes: {prof.construction_codes}",
        f"Structural loading basis: {prof.structural_loading}",
        f"Energy: {prof.energy}",
        f"Electrical: {prof.electrical}",
        f"Authority process: {prof.filing}",
        "Sheet index: COVER (this sheet) · C-101 site context · A-101..A-104 floor plans · CALC-101 pool + area schedule · S-101 structure · F-101 foundations · MPE-101 services (M/P/E/EN) · REG-101 registers",
        "Approval fields: DOB job number [ intentionally blank ] · Professional signature/seal [ intentionally blank — never simulated ]",
        "Status vocabulary: method_state / execution_status / check_outcome / freshness / review_status are independent dimensions; a generated sheet never upgrades a check.",
        "",
        "Discipline result summary for this revision:",
    ]
    for r in results:
        items.append(f"  - {r['discipline']}: method={r['method_id']} state={r['method_state']} "
                     f"execution={r['execution_status']} check={r['check_outcome']} review={r['review_status']}")
    y = lines(c, page_size, y, items)
    c.showPage()


def site_page(c: canvas.Canvas, page_size, snap):
    y = header(c, page_size, "C-101", "Site context (synthetic demonstration)", snap)
    w, h = page_size
    # context rectangle 30 x 45 m with building envelope inside
    ox, oy, scale = MARGIN, y - 6.4 * inch, 6.2 * inch / 45.0
    c.setStrokeColorRGB(0.4, 0.4, 0.4)
    c.rect(ox, oy, 30 * scale * (45 / 30) * 0 + 30 * scale, 45 * scale, stroke=1, fill=0)
    c.setFillColorRGB(0.85, 0.88, 0.92)
    ex, ey = ox + 6 * scale, oy + 14 * scale
    c.rect(ex, ey, 18 * scale, 15.5 * scale, stroke=1, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 8.5)
    c.drawString(ox, oy - 16, "Synthetic 30 x 45 m context (scenario parameter, not a surveyed lot). Building envelope 18.0 x 15.5 m.")
    items = [
        "No real address, no BBL, no surveyed boundary, no zoning determination is claimed for this demonstration.",
        "Real-parcel mode (spec D2/D3 adapters: GeoSearch, PLUTO/MapPLUTO, zoning layers, USGS seismic, FEMA/NYC flood screening) remains to be integrated; until then site-specific checks are not evaluated.",
        "Unknowns preserved as unknowns: soil, groundwater, easements, utilities, flood determination, historic/special-district status.",
    ]
    lines(c, page_size, oy - 0.55 * inch, items)
    c.showPage()
