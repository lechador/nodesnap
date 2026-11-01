"""Sheet helpers for the review package. Formatting only — every number is
computed by engineering/geometry services and passed in (spec E3)."""
from __future__ import annotations

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from shapely.geometry import Polygon
from shapely.ops import unary_union

from domain.jurisdiction import JurisdictionProfile

MARGIN = inch


def drawing_region(snap, level=None):
    """Gross modeled plate/project projection, independent of the demo dimensions.

    Stair and pool openings remain part of gross plate area; their net material
    areas are accounted for separately in the canonical architecture/services.
    """
    slabs = snap.architecture.slabs if snap.architecture else []
    polygons = [Polygon(slab.polygon) for slab in slabs if level is None or slab.level_id == level.id]
    if not polygons:
        envelope = getattr(snap, "envelope_polygon", None)
        polygons = [Polygon(envelope)] if envelope else [Polygon(space.polygon) for space in snap.spaces]
    return unary_union(polygons)


def fitted_text(c, x, y, text, max_width, font="Helvetica", size=10):
    """Keep user-supplied names inside a bounded drawing column."""
    measured = c.stringWidth(text, font, size)
    c.setFont(font, min(size, size * max_width / measured) if measured else size)
    c.drawString(x, y, text)


def plan_sheets(snap):
    """One plan per actual level, numbered in elevation order for this revision."""
    return [(f"A-{101 + index}", level)
            for index, level in enumerate(sorted(snap.levels, key=lambda level: (level.elevation_m, level.id)))]


def header(c: canvas.Canvas, page_size, sheet: str, title: str, snap):
    w, h = page_size
    if hasattr(c, "set_sheet"):
        c.set_sheet(sheet)
        c.current_sheet_title = title
    fitted_text(c, MARGIN, h - .75 * inch, f"{sheet} — {title}", w-2*MARGIN, "Helvetica-Bold", 18)
    fitted_text(c, MARGIN, h - 1.05 * inch,
                f"NodeSnap · {snap.title} · Revision {snap.revision_number} ({snap.revision_id})", w-2*MARGIN, size=11.5)
    c.setFont("Helvetica", 11.5)
    c.drawString(MARGIN, h - 1.28 * inch,
                 "Professional review draft — Demonstration design, assumptions require professional verification")
    c.setStrokeColorRGB(0.75, 0.45, 0.18)
    c.setLineWidth(2)
    c.line(MARGIN, h - 1.42 * inch, w - MARGIN, h - 1.42 * inch)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)
    return h - 1.75 * inch


def lines(c: canvas.Canvas, page_size, y: float, items: list[str],
          font_size: float = 11.5, leading: float = 0.27, bold_first: bool = False) -> float:
    w, h = page_size
    sheet = getattr(c, "current_sheet", "")
    title = getattr(c, "current_sheet_title", "")
    def draw_line(text, font):
        nonlocal y
        if y < MARGIN:
            c.showPage()
            y = header(c, page_size, sheet, f"{title} (continued)", c.snapshot) if sheet else h - MARGIN
        c.setFont(font, font_size)
        c.drawString(MARGIN, y, text)
        y -= leading * inch

    for i, s in enumerate(items):
        font = "Helvetica-Bold" if (bold_first and i == 0) else "Helvetica"
        # simple word wrap at ~125 chars for this sheet size
        while len(s) > 105:
            cut = s.rfind(" ", 0, 105)
            if cut <= 0:
                cut = 105
            draw_line(s[:cut], font)
            s = "   " + s[cut:].lstrip()
        draw_line(s, font)
    return y


def cover_page(c: canvas.Canvas, page_size, snap, results: list[dict]):
    y = header(c, page_size, "COVER", "Project index and design basis", snap)
    prof = JurisdictionProfile()
    plans = " · ".join(f"{sheet} {level.label}" for sheet, level in plan_sheets(snap))
    layout = getattr(snap, "site_layout", None)
    if layout:
        x0, y0, x1, y1 = Polygon(layout.context_polygon).bounds
        context = f"coordinated concept extent {x1-x0:g} x {y1-y0:g} m (not a survey)"
    else:
        context = f"declared context {snap.site.context_width_m:g} x {snap.site.context_depth_m:g} m (not a survey)"
    items = [
        "Product promise: homeowner intent -> coordinated editable design -> traceable calculations -> professional review package.",
        f"Site mode: {snap.site.mode} — {snap.site.name}; real address: {snap.site.real_address or 'none'}; BBL: {snap.site.bbl or 'none'}; {context}",
        f"Jurisdiction: {prof.authority} · profile {prof.profile_version}",
        f"Construction codes: {prof.construction_codes}",
        f"Structural loading basis: {prof.structural_loading}",
        f"Energy: {prof.energy}",
        f"Electrical: {prof.electrical}",
        f"Authority process: {prof.filing}",
        "Sheet index: COVER (this sheet) · C-101 " + ("house, yard and outbuildings" if layout else "site context"),
        f"Architectural plans: {plans}",
        f"CALC-101 {'pool + ' if snap.pool else ''}area schedule (continuations as needed) · S-101 structure · F-101 foundations · MPE-101 services (M/P/E/EN) · REG-101 registers",
        "Approval fields: DOB job number [ intentionally blank ] · Professional signature/seal [ intentionally blank — never simulated ]",
        "Status vocabulary: method_state / execution_status / check_outcome / freshness / review_status are independent dimensions; a generated sheet never upgrades a check.",
        "",
        "Discipline result summary for this revision:",
    ]
    from .pdf import PLAN_REGISTER_ROWS
    extra_registers = [f'AR-{sheet.split("-")[1]} {level.label}' for sheet, level in plan_sheets(snap)
                       if sum(space.level_id==level.id for space in snap.spaces)>PLAN_REGISTER_ROWS]
    if extra_registers:
        items.insert(11, 'Architectural room-register continuations: '+" · ".join(extra_registers))
    for r in results:
        items.append(f"  - {r['discipline']}: method={r['method_id']} state={r['method_state']} "
                     f"execution={r['execution_status']} check={r['check_outcome']} review={r['review_status']}")
    y = lines(c, page_size, y, items)
    c.showPage()


def site_page(c: canvas.Canvas, page_size, snap):
    if getattr(snap, "site_layout", None) is not None:
        from .site import site_plan_page
        return site_plan_page(c, page_size, snap)
    y = header(c, page_size, "C-101", "Site context (synthetic demonstration)", snap)
    w, h = page_size
    region = drawing_region(snap)
    minx, miny, maxx, maxy = region.bounds
    building_width, building_depth = maxx-minx, maxy-miny
    context_width, context_depth = snap.site.context_width_m, snap.site.context_depth_m
    # Center the modeled projection within the explicitly synthetic context.
    # This presentation offset is not a setback, orientation or site measurement.
    dx, dy = (context_width-building_width)/2-minx, (context_depth-building_depth)/2-miny
    extent_width, extent_depth = max(context_width, building_width), max(context_depth, building_depth)
    scale = min(8*inch/extent_width, 6.2*inch/extent_depth)
    ox, oy = MARGIN + max(0, (building_width-context_width)/2)*scale, y - 6.4*inch
    c.setStrokeColorRGB(0.4, 0.4, 0.4)
    c.rect(ox, oy, context_width*scale, context_depth*scale, stroke=1, fill=0)
    c.setFillColorRGB(0.85, 0.88, 0.92)
    polygons = list(region.geoms) if region.geom_type == "MultiPolygon" else [region]
    for polygon in polygons:
        path = c.beginPath()
        for index, (x, yy) in enumerate(polygon.exterior.coords):
            (path.moveTo if index == 0 else path.lineTo)(ox+(x+dx)*scale, oy+(yy+dy)*scale)
        path.close()
        c.drawPath(path, stroke=1, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 10.5)
    fitted_text(c, MARGIN, oy-16,
                f"Declared context {context_width:g} x {context_depth:g} m (not a surveyed lot). Building projection {building_width:g} x {building_depth:g} m.", w-2*MARGIN, size=10.5)
    items = [
        "Building placement is centered for this schematic; it does not establish setbacks, surveyed boundaries, site orientation or zoning compliance.",
        "Real-parcel mode (spec D2/D3 adapters: GeoSearch, PLUTO/MapPLUTO, zoning layers, USGS seismic, FEMA/NYC flood screening) remains to be integrated; until then site-specific checks are not evaluated.",
        "Unknowns preserved as unknowns: soil, groundwater, easements, utilities, flood determination, historic/special-district status.",
    ]
    lines(c, page_size, oy - 0.55 * inch, items)
    c.showPage()
