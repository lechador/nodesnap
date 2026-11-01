"""Measured concept-site sheet from the same revision as the house drawings.

The dashed context extent is synthetic, not a surveyed parcel. Coordinates and
surface quantities are canonical; this sheet makes no setback or safety claim.
"""
from __future__ import annotations

import math

from reportlab.lib.units import inch
from shapely.geometry import Polygon, box

from engineering.services import site_surface_quantities
from .sheets import drawing_region, fitted_text, header


def site_scale_denominator(width_m: float, depth_m: float) -> int:
    """Choose a physical ARCH B print scale inside a 660 x 500 point field."""
    minimum = max(width_m * 1000 * 72 / 25.4 / 660,
                  depth_m * 1000 * 72 / 25.4 / 500)
    return next((value for value in (50, 75, 100, 125, 150, 200, 250, 300, 400, 500, 1000)
                 if value >= minimum), math.ceil(minimum / 100) * 100)


def site_plan_page(c, page_size, snap):
    layout = snap.site_layout
    quantities = site_surface_quantities(snap)
    header(c, page_size, "C-101", "House, yard and outbuildings — concept site plan", snap)
    context = Polygon(layout.context_polygon)
    minx, miny, maxx, maxy = context.bounds
    width_m, depth_m = maxx - minx, maxy - miny
    denominator = site_scale_denominator(width_m, depth_m)
    scale = 1000 / denominator * 72 / 25.4
    ox, oy = 106 + (660 - width_m * scale) / 2, 174 + (500 - depth_m * scale) / 2

    def point(p):
        return ox + (p[0] - minx) * scale, oy + (p[1] - miny) * scale

    def region(polygon, fill=True, stroke=True):
        path = c.beginPath()
        for ring in [polygon.exterior, *polygon.interiors]:
            for index, p in enumerate(ring.coords):
                (path.moveTo if index == 0 else path.lineTo)(*point(p))
            path.close()
        c.drawPath(path, fill=int(fill), stroke=int(stroke), fillMode=0)

    def badge(polygon, text):
        p = polygon.representative_point()
        x, y = point([p.x, p.y])
        c.setFont("Helvetica-Bold", 9)
        text_width = c.stringWidth(text, "Helvetica-Bold", 9)
        c.setFillColorRGB(.99, .99, .97)
        c.rect(x-text_width/2-4, y-5, text_width+8, 15, fill=1, stroke=0)
        c.setFillColorRGB(.18, .26, .20)
        c.drawCentredString(x, y, text)

    def dimension(a, b, offset, text):
        ax, ay = point(a)
        bx, by = point(b)
        c.setStrokeColorRGB(.32, .39, .34)
        c.setFillColorRGB(.22, .30, .25)
        c.setLineWidth(.45)
        c.setFont("Helvetica", 8)
        if a[1] == b[1]:
            yy = ay + offset
            c.line(ax, ay, ax, yy-4)
            c.line(bx, by, bx, yy-4)
            c.line(ax, yy, bx, yy)
            for xx in (ax, bx):
                c.line(xx-3, yy-3, xx+3, yy+3)
            c.drawCentredString((ax+bx)/2, yy+4, text)
        else:
            xx = ax + offset
            c.line(ax, ay, xx-4, ay)
            c.line(bx, by, xx-4, by)
            c.line(xx, ay, xx, by)
            for yy in (ay, by):
                c.line(xx-3, yy-3, xx+3, yy+3)
            c.saveState()
            c.translate(xx-7, (ay+by)/2)
            c.rotate(90)
            c.drawCentredString(0, 0, text)
            c.restoreState()

    # A dashed boundary distinguishes the layout's drawing extent from a lot line.
    c.setStrokeColorRGB(.55, .61, .55)
    c.setFillColorRGB(.98, .98, .96)
    c.setLineWidth(.65)
    c.setDash(5, 4)
    region(context)
    c.setDash()
    if layout.yard:
        c.setFillColorRGB(.85, .91, .80)
        c.setStrokeColorRGB(.41, .55, .36)
        region(Polygon(layout.yard.polygon, holes=layout.yard.holes))
    if layout.driveway:
        c.setFillColorRGB(.88, .88, .85)
        c.setStrokeColorRGB(.55, .57, .52)
        region(Polygon(layout.driveway.polygon, holes=layout.driveway.holes))
    if layout.pool_deck:
        c.setFillColorRGB(.93, .89, .81)
        c.setStrokeColorRGB(.60, .55, .45)
        region(Polygon(layout.pool_deck.polygon, holes=layout.pool_deck.holes))

    house = drawing_region(snap)
    c.setStrokeColorRGB(.23, .28, .25)
    c.setFillColorRGB(.93, .93, .90)
    c.setLineWidth(1)
    for polygon in list(house.geoms) if house.geom_type == "MultiPolygon" else [house]:
        region(polygon)
    badge(house, "H1")
    if layout.yard:
        badge(Polygon(layout.yard.polygon, holes=layout.yard.holes), "Y1")
    if layout.driveway:
        badge(Polygon(layout.driveway.polygon, holes=layout.driveway.holes), "D1")
    if layout.pool_deck:
        badge(Polygon(layout.pool_deck.polygon, holes=layout.pool_deck.holes), "P2")

    garage = layout.garage
    if garage:
        outer = Polygon(garage.polygon)
        inner = outer.buffer(-garage.wall_thickness_m, join_style=2)
        x0, y0, x1, y1 = outer.bounds
        start, end = garage.vehicle_door_start, garage.vehicle_door_end
        opening = box(min(start[0], end[0]), y0-.1,
                      max(start[0], end[0]), y0+garage.wall_thickness_m+.01)
        wall_region = outer.difference(inner).difference(opening)
        c.setFillColorRGB(.96, .95, .92)
        c.setStrokeColorRGB(.25, .28, .25)
        region(outer)
        c.setFillColorRGB(.29, .33, .29)
        for polygon in list(wall_region.geoms) if wall_region.geom_type == "MultiPolygon" else [wall_region]:
            region(polygon, stroke=False)
        # Parallel lines mark a vehicle-door opening, not a pedestrian swing.
        c.setStrokeColorRGB(.41, .37, .30)
        c.setLineWidth(.65)
        for offset in (garage.wall_thickness_m*.25, garage.wall_thickness_m*.65):
            c.line(*point([start[0], start[1]+offset]), *point([end[0], end[1]+offset]))
        badge(inner, "G1")

    pool = snap.pool if snap.pool and getattr(snap.pool, "location", "indoor") == "outdoor" else None
    if pool:
        c.setStrokeColorRGB(.25, .49, .54)
        c.setFillColorRGB(.76, .90, .92)
        c.setLineWidth(.9)
        px, py = point([pool.origin_x_m, pool.origin_y_m])
        c.rect(px, py, pool.water_length_m*scale, pool.water_width_m*scale, fill=1, stroke=1)
        badge(box(pool.origin_x_m, pool.origin_y_m,
                  pool.origin_x_m+pool.water_length_m, pool.origin_y_m+pool.water_width_m), "P1")

    # Outside-face dimensions describe measured geometry, never legal setbacks.
    dimension([minx, miny], [maxx, miny], -25, f"{width_m:.3f} m CONCEPT EXTENT")
    dimension([minx, miny], [minx, maxy], -30, f"{depth_m:.3f} m CONCEPT EXTENT")
    hx0, hy0, hx1, hy1 = house.bounds
    dimension([hx0, hy0], [hx1, hy0], -15, f"HOUSE {hx1-hx0:.3f} m")
    dimension([hx0, hy0], [hx0, hy1], -16, f"HOUSE {hy1-hy0:.3f} m")

    tx, y = 835, 711
    c.setFillColorRGB(.18, .26, .20)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(tx, y, "SITE / AREA REGISTER")
    y -= 23
    c.setFont("Helvetica", 8.5)
    c.drawString(tx, y, "Coordinates and surfaces derive from this revision.")
    y -= 29

    def row(key, title, detail, area=None, extra=None):
        nonlocal y
        c.setFillColorRGB(.18, .26, .20)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(tx, y, f"{key}  {title}")
        y -= 16
        fitted_text(c, tx, y, detail, 390, size=8.5)
        y -= 16
        if area is not None:
            c.setFont("Helvetica", 8.5)
            c.drawString(tx, y, f"{area:,.2f} m2 / {area/.09290304:,.1f} SF")
            y -= 16
        if extra:
            fitted_text(c, tx, y, extra, 390, size=8.5)
            y -= 16
        y -= 12

    row("H1", "MAIN HOUSE PROJECTION", f"{hx1-hx0:.3f} x {hy1-hy0:.3f} m outside faces", house.area,
        "Enclosed floor areas are scheduled on the floor plans.")
    if layout.yard:
        x0, y0, x1, y1 = Polygon(layout.yard.polygon).bounds
        row("Y1", "YARD / OPEN AIR", f"{x1-x0:.3f} x {y1-y0:.3f} m gross reservation",
            quantities["yard_gross_area_m2"], f"Net grass {quantities['yard_grass_area_m2']:,.2f} m2; pool/deck excluded from grass.")
    if garage:
        x0, y0, x1, y1 = Polygon(garage.polygon).bounds
        row("G1", "DETACHED GARAGE / UNCONDITIONED", f"{x1-x0:.3f} x {y1-y0:.3f} m outside; {garage.height_m:.3f} m wall height",
            quantities["garage_gross_floor_area_m2"],
            f"Clear {quantities['garage_clear_floor_area_m2']:,.2f} m2; vehicle door {garage.vehicle_door_width_m:.3f} x {garage.vehicle_door_height_m:.3f} m.")
    if layout.driveway:
        row("D1", "DRIVEWAY / OPEN AIR", "Vehicle approach to garage; road connection unverified.", quantities["driveway_area_m2"])
    if pool:
        row("P1", "OUTDOOR POOL WATER", f"{pool.water_length_m:.3f} x {pool.water_width_m:.3f} x {pool.water_depth_m:.3f} m deep",
            quantities["outdoor_pool_water_area_m2"])
    if layout.pool_deck:
        row("P2", "POOL DECK / OPEN AIR", "Net paved deck excludes the water opening.", quantities["pool_deck_area_m2"])

    # Keep concise scope notes below the drawing and schedule; detailed unknowns
    # remain in the revision's assumption and method registers.
    c.setFillColorRGB(.30, .36, .31)
    notes = [
        "Dashed context is synthetic, not a surveyed lot. Placement does not establish property lines, setbacks or parcel fit.",
        "Garage is separate unconditioned enclosed area. Yard, driveway, deck and water are outdoor surfaces, not enclosed floor area.",
        "Site grade/orientation, road connection, garage structure/fire separation/ventilation, pool barriers and drainage remain unverified.",
    ]
    for index, note in enumerate(notes):
        fitted_text(c, 72, 121-index*14, note, page_size[0]-144, size=8)
    c.setStrokeColorRGB(.20, .28, .23)
    for index in range(5):
        c.setFillColorRGB(*((.20, .28, .23) if index % 2 == 0 else (1, 1, 1)))
        c.rect(106+index*scale, 60, scale, 5, fill=1, stroke=1)
    c.setFillColorRGB(.20, .28, .23)
    c.setFont("Helvetica", 8)
    c.drawString(106, 47, "0")
    c.drawRightString(106+5*scale, 47, "5 m")
    c.drawString(106+5*scale+18, 60, f"1:{denominator} at ARCH B / print at 100%")
    c.drawRightString(page_size[0]-72, 60, "LOCAL XY / METRES  |  +Y UP THE DRAWING")
    c.showPage()
