"""Drawing + calculation PDF from canonical coordinates — spec S8/E-Delivery 4.
Vector linework via ReportLab; every page carries the frozen revision."""
from __future__ import annotations

import io
import math

from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from shapely.geometry import box

from domain.models import Level, ProjectSnapshot
from engineering.pool import pool_quantities
from geometry.validate import area_schedule
from .sheets import drawing_region, fitted_text

PAGE = landscape((18 * inch, 12 * inch))  # ARCH B sheet
PLAN_REGISTER_ROWS = 16


def plan_scale_denominator(width_m: float, depth_m: float) -> int:
    """Select a true print scale that fits the measured ARCH B drawing field."""
    minimum = max(width_m*1000*72/25.4/704, depth_m*1000*72/25.4/596)
    return next((value for value in (50, 75, 100, 125, 150, 200, 250, 300, 400, 500, 1000)
                 if value >= minimum), math.ceil(minimum / 100)*100)


class RevisionCanvas(canvas.Canvas):
    """Even automatically paginated register pages carry immutable identity."""
    def __init__(self, *args, snapshot, **kwargs):
        super().__init__(*args, **kwargs)
        self.snapshot = snapshot
        self.page_sheets: list[str] = []
        self.current_sheet = ""
        self.sheet_page_counts: dict[str, int] = {}

    def set_sheet(self, sheet: str, level_name: str | None = None):
        self.current_sheet = f"{sheet} {level_name}" if level_name else sheet

    def showPage(self):
        count = self.sheet_page_counts.get(self.current_sheet, 0) + 1
        self.sheet_page_counts[self.current_sheet] = count
        sheet = self.current_sheet if count == 1 else f"{self.current_sheet} (continued {count})"
        self.page_sheets.append(sheet)
        self.saveState()
        self.setFont("Helvetica", 7)
        self.setFillColorRGB(.2, .28, .23)
        self.setStrokeColorRGB(.6, .65, .62)
        self.setLineWidth(.4)
        self.line(48, 32, PAGE[0] - 48, 32)
        self.drawString(48, 18, f"Professional review draft | Demonstration assumptions | Revision {self.snapshot.revision_number} / {self.snapshot.revision_id}")
        self.drawRightString(PAGE[0] - 48, 18, f"Model {self.snapshot.content_hash[:16]} | {sheet} | Page {self.getPageNumber()}")
        self.restoreState()
        super().showPage()


def _feet(m: float) -> str:
    eighths = round(m / 0.0254 * 8)
    feet, rem = divmod(eighths, 96)
    inches, fraction = divmod(rem, 8)
    frac = '' if not fraction else f" {fraction // math.gcd(fraction, 8)}/{8 // math.gcd(fraction, 8)}"
    return f"{feet}'-{inches}{frac}\""


def _plan_page(c: canvas.Canvas, snap: ProjectSnapshot, level: Level, sheet: str):
    """A measured vector sheet; the same canonical primitives drive plan + 3D."""
    width, height = PAGE
    c.set_sheet(sheet, level.name)
    spaces = [s for s in snap.spaces if s.level_id == level.id]
    architecture = snap.architecture
    metrics = {m.space_id: m for m in architecture.space_metrics} if architecture else {}
    c.setStrokeColorRGB(.15, .19, .18)
    c.setFillColorRGB(.15, .19, .18)
    fitted_text(c, 48, height-47, f"{sheet}  /  {level.label}", 750, 'Helvetica-Bold', 23)
    c.setFont('Helvetica', 10)
    c.drawRightString(width - 48, height - 40, 'NODESNAP  /  ARCHITECTURE')
    c.drawRightString(width - 48, height - 58, f"REVISION {snap.revision_number:02d}  |  {snap.created_at.strftime('%Y-%m-%d %H:%M UTC')}")
    c.setLineWidth(.6); c.line(48, height-73, width-48, height-73)
    fitted_text(c, 48, height-91, f"{snap.title}   /   {snap.site.name}   /   Level datum {level.elevation_m:+.2f} m", width-96, size=9)
    plate = drawing_region(snap, level)
    minx, miny, maxx, maxy = plate.bounds
    plate_width, plate_depth = maxx-minx, maxy-miny
    denominator = plan_scale_denominator(plate_width, plate_depth)
    scale = (1000 / denominator) * 72 / 25.4
    ox, oy = 106+(704-plate_width*scale)/2, 127+(596-plate_depth*scale)/2
    def point(p):
        return ox + (p[0]-minx)*scale, oy + (p[1]-miny)*scale
    def ring(polygon, fill=False, stroke=True):
        path = c.beginPath()
        for i, p in enumerate(polygon):
            (path.moveTo if i == 0 else path.lineTo)(*point(p))
        path.close(); c.drawPath(path, fill=int(fill), stroke=int(stroke))
    c.setLineWidth(.3)
    c.setStrokeColorRGB(.77,.78,.75)
    c.setFillColorRGB(.985,.98,.965)
    if plate.equals(box(minx,miny,maxx,maxy)):
        c.rect(ox,oy,plate_width*scale,plate_depth*scale,fill=1,stroke=1)
    else:
        for polygon in list(plate.geoms) if plate.geom_type=='MultiPolygon' else [plate]:
            ring(list(polygon.exterior.coords),fill=True)
    for space in spaces:
        polygon = metrics[space.id].clear_polygon if space.id in metrics else space.polygon
        c.setFillColorRGB(*((.92,.94,.92) if space.use in {'circulation','roof_access'} else
                            (.95,.94,.90) if space.classification == 'principal' else (.97,.97,.95)))
        ring(polygon,fill=True,stroke=False)
    walls = [w for w in architecture.walls if w.level_id == level.id] if architecture else []
    for wall in walls:
        c.setStrokeColorRGB(*((.43,.56,.55) if wall.role == 'guard' else (.20,.23,.22)))
        c.setLineCap(0); c.setLineWidth(wall.thickness_m*scale)
        c.line(*point(wall.start), *point(wall.end))
    wall_map = {w.id:w for w in walls}
    for opening in architecture.openings if architecture else []:
        wall = wall_map.get(opening.wall_id)
        if wall is None: continue
        length = math.dist(wall.start,wall.end)
        ux,uy = [(wall.end[i]-wall.start[i])/length for i in (0,1)]
        start = [wall.start[i]+(ux,uy)[i]*opening.offset_m for i in (0,1)]
        end = [start[i]+(ux,uy)[i]*opening.width_m for i in (0,1)]
        a,b = point(start),point(end)
        c.setStrokeColorRGB(1,1,1); c.setLineWidth(wall.thickness_m*scale+.6)
        c.line(*a,*b)
        c.setStrokeColorRGB(.28,.38,.37); c.setLineWidth(.65)
        normal=(-uy,ux)
        if opening.kind == 'window':
            for offset in (-wall.thickness_m*.33,0,wall.thickness_m*.33):
                c.line(a[0]+normal[0]*offset*scale,a[1]+normal[1]*offset*scale,
                       b[0]+normal[0]*offset*scale,b[1]+normal[1]*offset*scale)
            for p in (a,b):
                c.line(p[0]-normal[0]*wall.thickness_m*scale/2,p[1]-normal[1]*wall.thickness_m*scale/2,
                       p[0]+normal[0]*wall.thickness_m*scale/2,p[1]+normal[1]*wall.thickness_m*scale/2)
        elif opening.kind == 'door':
            owner = next((s for s in spaces if s.id in opening.space_ids and s.use not in {'circulation','stairs_service'}),
                         next((s for s in spaces if s.id in opening.space_ids),None))
            cx = sum(p[0] for p in owner.polygon[:-1])/(len(owner.polygon)-1) if owner else start[0]+normal[0]
            cy = sum(p[1] for p in owner.polygon[:-1])/(len(owner.polygon)-1) if owner else start[1]+normal[1]
            sign = 1 if normal[0]*(cx-start[0])+normal[1]*(cy-start[1]) >= 0 else -1
            radius=opening.width_m*scale
            end_hinge=opening.hinge=='end'
            hinge=b if end_hinge else a
            c.line(*hinge,hinge[0]+normal[0]*radius*sign,hinge[1]+normal[1]*radius*sign)
            c.setLineWidth(.4)
            c.arc(hinge[0]-radius,hinge[1]-radius,hinge[0]+radius,hinge[1]+radius,
                  startAng=math.degrees(math.atan2(uy,ux))+(180 if end_hinge else 0),
                  extent=90*sign*(-1 if end_hinge else 1))
    for stair in architecture.stairs if architecture else []:
        if stair.lower_level_id != level.id: continue
        xs,ys=zip(*stair.polygon); x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys)
        c.setStrokeColorRGB(.30,.34,.32); c.setLineWidth(.65)
        ring(stair.polygon)
        count=stair.riser_count//2
        for index in range(count):
            y=y1-index*stair.tread_depth_m
            for x in (x0,x1-stair.width_m):
                c.line(*point([x,y]),*point([x+stair.width_m,y]))
        c.line(*point([x0,y0+stair.landing_depth_m]),*point([x1,y0+stair.landing_depth_m]))
        ax=x0+stair.width_m/2
        c.line(*point([ax,y1-.2]),*point([ax,y0+stair.landing_depth_m+.3]))
        p=point([ax,y0+stair.landing_depth_m+.3])
        c.line(p[0],p[1],p[0]-3,p[1]+6);c.line(p[0],p[1],p[0]+3,p[1]+6)
    if snap.pool and snap.pool.level_id == level.id:
        pool=snap.pool
        c.setStrokeColorRGB(.22,.48,.54); c.setFillColorRGB(.84,.93,.94);c.setLineWidth(1)
        px,py=point([pool.origin_x_m,pool.origin_y_m])
        c.rect(px,py,pool.water_length_m*scale,pool.water_width_m*scale,stroke=1,fill=1)
        c.setFont('Helvetica-Bold',8);c.setFillColorRGB(.18,.37,.42)
        hall_index=next((index for index,space in enumerate(spaces) if space.use=='pool_hall'),None)
        label=f'POOL WATER / R{hall_index+1:02d}' if hall_index is not None else 'POOL WATER'
        label_width=max(4,pool.water_length_m*scale-10)
        c.setFont('Helvetica-Bold',min(8,8*label_width/max(1,c.stringWidth(label,'Helvetica-Bold',8))))
        c.drawCentredString(px+pool.water_length_m*scale/2,py+pool.water_width_m*scale/2+5,label)
        text=f"{_feet(pool.water_length_m)} x {_feet(pool.water_width_m)} / {pool.water_depth_m:.2f} m deep"
        size=min(8,8*(pool.water_length_m*scale-10)/max(1,c.stringWidth(text,'Helvetica',8)))
        c.setFont('Helvetica',size)
        c.drawCentredString(px+pool.water_length_m*scale/2,py+pool.water_width_m*scale/2-9,text)
    # Compact room keys match the adjacent full schedule; labels never claim a
    # target allowance as a measured room dimension.
    for index,space in enumerate(spaces):
        if space.use=='pool_hall' and snap.pool and snap.pool.level_id==level.id:
            continue  # Its key is carried by the water label; avoid centered text collisions.
        if space.use=='stairs_service' and any(stair.lower_level_id==level.id for stair in (architecture.stairs if architecture else [])):
            continue
        metric=metrics.get(space.id)
        polygon=metric.clear_polygon if metric else space.polygon
        xs,ys=zip(*polygon); cx,cy=(min(xs)+max(xs))/2,(min(ys)+max(ys))/2
        px,py=point([cx,cy])
        key=f"R{index+1:02d}"
        label=f"{key} {space.name.strip().upper()}"
        clear_width=(max(xs)-min(xs))*scale
        available=max(4,clear_width-min(12,clear_width*.2))
        words=label.split(); lines=[]; current=''
        for word in words:
            trial=(current+' '+word).strip()
            if c.stringWidth(trial,'Helvetica-Bold',8)>available and current:
                lines.append(current);current=word
            else: current=trial
        if current:lines.append(current)
        available_height=(max(ys)-min(ys))*scale-12
        if len(lines)*10+29>available_height or any(c.stringWidth(line,'Helvetica-Bold',8)>available for line in lines):
            lines=[key]
        text_size=min(8,8*available/max(1,max(c.stringWidth(line,'Helvetica-Bold',8) for line in lines)))
        c.setFillColorRGB(.18,.23,.21);c.setFont('Helvetica-Bold',text_size)
        top=py+(len(lines)-1)*5
        for line in lines:c.drawCentredString(px,top,line);top-=10
        if metric and space.use not in {'circulation','roof_access'} and available_height>=30:
            c.setFont('Helvetica',7.5)
            text=f"{metric.net_area_m2 / .09290304:.0f} SF  /  {metric.net_area_m2:.2f} m2"
            if c.stringWidth(text,'Helvetica',7.5)<=available:
                c.drawCentredString(px,top-2,text)
            if available_height>=43:
                text=f"{_feet(metric.clear_width_m)} x {_feet(metric.clear_depth_m)}"
                text_width=c.stringWidth(text,'Helvetica',7.5)
                if text_width<=available:
                    # A small drafting knockout keeps dimensions legible where
                    # a door swing crosses the room's centered annotation.
                    c.saveState()
                    c.setFillColorRGB(*((.95,.94,.90) if space.classification=='principal' else (.97,.97,.95)))
                    c.rect(px-text_width/2-2,top-15,text_width+4,10,fill=1,stroke=0)
                    c.restoreState()
                    c.drawCentredString(px,top-13,text)
    def dimension(a,b,offset,label):
        ax,ay=point(a);bx,by=point(b)
        c.setStrokeColorRGB(.35,.40,.37);c.setLineWidth(.45);c.setFillColorRGB(.25,.31,.27)
        if a[1]==b[1]:
            y=ay+offset;c.line(ax,ay,ax,y-5);c.line(bx,by,bx,y-5);c.line(ax,y,bx,y)
            for x in (ax,bx):c.line(x-3,y-3,x+3,y+3)
            c.setFont('Helvetica',9);c.drawCentredString((ax+bx)/2,y+5,label)
        else:
            x=ax+offset;c.line(ax,ay,x-5,ay);c.line(bx,by,x-5,by);c.line(x,ay,x,by)
            for y in (ay,by):c.line(x-3,y-3,x+3,y+3)
            c.saveState();c.translate(x-7,(ay+by)/2);c.rotate(90);c.setFont('Helvetica',9);c.drawCentredString(0,0,label);c.restoreState()
    dimension([minx,miny],[maxx,miny],-29,f"{_feet(plate_width)}   /   {plate_width:.3f} m OUTSIDE")
    dimension([minx,miny],[minx,maxy],-34,f"{_feet(plate_depth)}   /   {plate_depth:.3f} m OUTSIDE")
    # Side schedule, readable without zooming into the plan labels.
    tx=845;ty=height-130
    c.setFillColorRGB(.16,.22,.19);c.setFont('Helvetica-Bold',12);c.drawString(tx,ty,'ROOM / AREA REGISTER')
    c.setFont('Helvetica',8);c.drawString(tx,ty-19,'Clear areas inside wall faces. Zones include wall allocation.')
    y=ty-43
    c.setFont('Helvetica-Bold',8);c.drawString(tx,y,'SPACE');c.drawRightString(1160,y,'NET SF');c.drawRightString(1240,y,'NET m2')
    y-=10;c.setLineWidth(.5);c.line(tx,y,1240,y);y-=20
    for index,space in enumerate(spaces[:PLAN_REGISTER_ROWS]):
        metric=metrics.get(space.id)
        label=f"R{index+1:02d}  {space.name}"
        name=label if len(label)<=37 else label[:34]+'...'
        c.setFont('Helvetica',8.5);c.drawString(tx,y,name)
        if metric:
            c.drawRightString(1160,y,f'{metric.net_area_m2/.09290304:,.1f}');c.drawRightString(1240,y,f'{metric.net_area_m2:,.2f}')
        y-=25
    c.setLineWidth(.5);c.line(tx,y+6,1240,y+6)
    c.setFont('Helvetica-Bold',8.5);c.drawString(tx,y-12,'GROSS FLOOR PLATE');c.drawRightString(1240,y-12,f'{plate.area:,.2f} m2 / {plate.area/.09290304:,.1f} SF')
    if level.name=='roof':
        c.setFont('Helvetica',8);c.drawString(tx,y-30,'Roof plate is separate from enclosed floor area.' if spaces else 'Unoccupied roof; no occupied terrace requested.')
    if len(spaces)>PLAN_REGISTER_ROWS:
        c.setFont('Helvetica',8);c.drawString(tx,y-30,f'Room register continues on AR-{sheet.split("-")[1]}.')
    notes=['CONCEPT BASIS','300 mm envelope / 150 mm partitions / 250 mm slabs.',
           'Wall and slab thicknesses are demonstration assumptions.',
           'Door/window sizes are concept geometry, not verified code minima.',
           'Stair treads connect actual level elevations; headroom, guards,',
           'egress, waterproofing and structural design remain open.',
           'North is a drawing convention; site orientation is unverified.',
           'All dimensions derive from this revision. Do not scale screenshots.']
    ny=min(y-65,330)
    for i,note in enumerate(notes):
        c.setFont('Helvetica-Bold' if i==0 else 'Helvetica',9 if i==0 else 8)
        c.drawString(tx,ny,note);ny-=17
    # North, true physical scale bar, and immutable identity.
    c.setLineWidth(1);c.setStrokeColorRGB(.2,.28,.23);c.setFillColorRGB(.2,.28,.23)
    nx,ny=790,749;c.line(nx,ny-24,nx,ny)
    path=c.beginPath();path.moveTo(nx,ny+5);path.lineTo(nx-4,ny-5);path.lineTo(nx+4,ny-5);path.close();c.drawPath(path,fill=1)
    c.setFont('Helvetica-Bold',9);c.drawCentredString(nx,ny+13,'N')
    barx,bary=ox,62
    for i in range(5):
        c.setFillColorRGB(*((.2,.28,.23) if i%2==0 else (1,1,1)))
        c.rect(barx+i*scale,bary,scale,5,stroke=1,fill=1)
    c.setFillColorRGB(.2,.28,.23);c.setFont('Helvetica',8)
    c.drawString(barx,bary-13,'0');c.drawRightString(barx+5*scale,bary-13,'5 m')
    c.drawString(barx+5*scale+18,bary,f'1:{denominator} at ARCH B / print at 100%')
    c.showPage()
    if len(spaces)>PLAN_REGISTER_ROWS:
        _room_register_pages(c,snap,level,sheet,spaces,metrics)


def _room_register_pages(c,snap,level,sheet,spaces,metrics):
    """Keep dense programs readable instead of running beyond the plan sheet."""
    from .sheets import header
    for offset in range(PLAN_REGISTER_ROWS,len(spaces),18):
        y=header(c,PAGE,f'AR-{sheet.split("-")[1]}',f'{level.label} — room register',snap)
        c.setFont('Helvetica',10)
        c.drawString(inch,y,f'Room keys refer to {sheet}; measured net areas, not program targets.')
        y-=30
        for index,space in enumerate(spaces[offset:offset+18],start=offset):
            metric=metrics.get(space.id)
            fitted_text(c,inch,y,f'R{index+1:02d}  {space.name}',760,size=10)
            if metric:
                c.setFont('Helvetica',10)
                c.drawRightString(1100,y,f'{metric.net_area_m2/.09290304:,.1f} SF')
                c.drawRightString(1224,y,f'{metric.net_area_m2:,.2f} m2')
            y-=30
        c.showPage()

def _extra_pages(c, snap, results):
    from .sheets import header, lines
    by_id = {r["method_id"]: r for r in (results or [])}
    def quantity(data, key, precision=1, factor=1):
        value = data.get(key)
        return "not calculated" if value is None else f"{value * factor:,.{precision}f}"
    # S-101 structure
    fr = (by_id.get("structural_frame_analysis") or {}).get("quantities") or {}
    y = header(c, PAGE, "S-101", "Structure — baseline gravity frame", snap)
    items = [
        "Independent fixed-frame scenario, not the structural model of this architectural revision. Added floors and architectural edits do not change its loads or members. No capacity for an added level is established.",
        f"Idealization: {fr.get('idealization', 'not calculated')}",
        f"Total gravity load applied: {quantity(fr, 'total_applied_load_n', 0)} N; sum of base reactions: {quantity(fr, 'sum_base_reactions_n', 0)} N; equilibrium residual: {fr.get('equilibrium_relative_residual', 'not calculated')}",
        f"Maximum beam moment (magnitude): {quantity(fr, 'max_beam_abs_moment_nm', 0)} N-m; maximum beam deflection: {quantity(fr, 'max_floor_deflection_m', 1, 1000)} mm",
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
        "This bearing scenario uses the independent fixed-frame reactions; it does not include loads from added floors or establish the foundation capacity of this revision.",
        f"Pressure assumption: {be.get('pressure_assumption', 'not calculated')}",
        f"Average pressure: {quantity(be, 'average_pressure_pa')} Pa vs assumed allowable {quantity(be, 'assumed_allowable_bearing_pa', 0)} Pa -> utilization {quantity(be, 'utilization', 3)}",
        "Missing input: project geotechnical basis (MISSING_INPUT). NYC BC 1803.2 requires a geotechnical investigation for a real structure; this scenario cannot satisfy it.",
        f"Not evaluated: {be.get('exclusions', '')}",
    ])
    c.showPage()
    # MPE-101 services
    sv = (by_id.get("services_inventories") or {}).get("quantities") or {}
    y = header(c, PAGE, "MPE-101", "Services — mechanical / plumbing / electrical / energy / drainage", snap)
    el, pl, hv, dr = sv.get("electrical", {}), sv.get("plumbing", {}), sv.get("hvac_energy", {}), sv.get("drainage", {})
    items = [
        f"Electrical: connected load {quantity(el, 'connected_load_w', 0)} W; current at declared {quantity(el, 'declared_voltage_v', 0)} V = {quantity(el, 'current_at_connected_load_a')} A. {el.get('note', '')}",
        f"Plumbing: {len(pl['fixtures']) if 'fixtures' in pl else 'not calculated'} fixtures; summed fixture flows {quantity(pl, 'sum_of_fixture_flows_l_min', 0)} L/min. {pl.get('note', '')}",
        f"Energy/HVAC envelope conduction at dT={quantity(hv, 'delta_t_k')} K: total {quantity(hv, 'total_conduction_w', 0)} W (assumed U-values; component only).",
    ]
    for e in hv.get("envelope_conduction", []):
        items.append(f"   {e['element']}: A={e['area_m2']:.2f} m2, U={e['u_w_m2k']:.2f} W/m2K, Q={e['heat_loss_w']:,.0f} W")
    items += [
        f"Drainage: roof runoff scenario {quantity(dr, 'runoff_l_s', 2)} L/s (C={dr.get('runoff_coefficient_assumed')}, rainfall {dr.get('rainfall_mm_h_assumed')} mm/h, both assumed). {dr.get('note', '')}",
        ("Pool environment/evaporation, " if snap.pool else "No pool is modeled. ") + "Ventilation rates, equipment selection, demand factors, ampacity, panel schedules, NYCECC pathway and hydraulic sizing: research_required — no values invented for this sheet.",
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


def build_review_package(snap: ProjectSnapshot, results: list[dict] | None = None) -> tuple[bytes, list[str]]:
    """Render once and return an index of the pages actually emitted."""
    buf = io.BytesIO()
    c = RevisionCanvas(buf, pagesize=PAGE, snapshot=snap)
    c.setTitle(f"NodeSnap review draft — revision {snap.revision_number}")
    from .sheets import cover_page, plan_sheets, site_page
    cover_page(c, PAGE, snap, results or [])
    site_page(c, PAGE, snap)
    for sheet, level in plan_sheets(snap):
        _plan_page(c, snap, level, sheet)
    # calculation + schedule page
    w, h = PAGE
    c.set_sheet("CALC-101")
    c.setFont("Helvetica-Bold", 19)
    c.drawString(inch, h - 0.8 * inch, "CALC-101 / Calculation & schedule - " + ("pool quantities and areas" if snap.pool else "areas"))
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
            f"Method: pool_quantities (implemented; physics only — not pool-shell design). Input basis: {snap.pool.input_basis.value}.",
        ]
        for ln in lines:
            c.drawString(inch, y, ln); y -= 0.27 * inch
    else:
        c.drawString(inch, y, "No pool is modeled in this revision; pool water quantities are not applicable.")
        y -= .27 * inch
    y -= 0.2 * inch
    c.setFont("Helvetica-Bold", 13)
    c.drawString(inch, y, "Area schedule (clear net actual vs planning-zone target)" if snap.building_program else "Area schedule (actual from canonical geometry vs program target)")
    y -= 0.25 * inch
    c.setFont("Helvetica", 10)
    for r in area_schedule(snap):
        if y < inch:
            c.showPage()
            c.setFont("Helvetica-Bold", 19)
            c.drawString(inch, h - 0.8 * inch, "CALC-101 / Area schedule (continued)")
            c.setFont("Helvetica", 10)
            y = h - 1.3 * inch
            c.drawString(inch, y, f"Revision {snap.revision_number} ({snap.revision_id})  content_hash={snap.content_hash[:16]}...")
            y -= 0.4 * inch
        tgt = f"{r['target_area_m2']:.2f}" if r['target_area_m2'] is not None else "—"
        delta = f"{r['delta_m2']:+.2f}" if r['delta_m2'] is not None else "—"
        fitted_text(c, inch, y, f"{r['level']:<16} {r['name']:<28} actual {r['actual_area_m2']:>8.2f} m2   target {tgt:>8}   delta {delta:>8}", w-2*inch, size=10)
        y -= 0.20 * inch
    c.showPage()
    _extra_pages(c, snap, results or [])
    c.save()
    return buf.getvalue(), c.page_sheets


def build_review_pdf(snap: ProjectSnapshot, results: list[dict] | None = None) -> bytes:
    return build_review_package(snap, results)[0]
