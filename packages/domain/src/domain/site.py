"""Deterministic concept siting, independent of the enclosed-house floor plan.

These are local-coordinate design assumptions, never a parcel survey or a
setback/zoning/access approval. All footprints and openings persist in SI.
"""
from __future__ import annotations

from .architecture import rect, stable_id
from .models import Assumption, GarageGeometry, GarageProgram, SiteLayout, SiteSurface, YardProgram

UNCHANGED = object()


def ring_bounds(ring):
    return min(p[0] for p in ring), min(p[1] for p in ring), max(p[0] for p in ring), max(p[1] for p in ring)


def yard_program(snapshot):
    if snapshot.building_program and snapshot.building_program.yard:
        return snapshot.building_program.yard.model_copy(deep=True)
    if snapshot.site_layout and snapshot.site_layout.yard:
        x0,y0,x1,y1 = ring_bounds(snapshot.site_layout.yard.polygon)
        return YardProgram(width_m=x1-x0, depth_m=y1-y0)
    return None


def garage_program(snapshot):
    if snapshot.building_program and snapshot.building_program.garage:
        return snapshot.building_program.garage.model_copy(deep=True)
    if snapshot.site_layout and snapshot.site_layout.garage:
        garage = snapshot.site_layout.garage
        x0,y0,x1,y1 = ring_bounds(garage.polygon)
        return GarageProgram(width_m=x1-x0,depth_m=y1-y0,height_m=garage.height_m,
                             side=garage.side,vehicle_door_width_m=garage.vehicle_door_width_m)
    return None


def coordinate_site(snapshot, *, yard=UNCHANGED, garage=UNCHANGED):
    """Coordinate requested features on a mutable candidate without moving rooms.

    Overrides are applied together, so removing an outdoor pool then its yard,
    or growing a yard and a pool in one batch, validates the final arrangement.
    """
    old = snapshot.site_layout
    explicitly_remove_yard = yard is None
    yard = yard_program(snapshot) if yard is UNCHANGED else yard
    garage = garage_program(snapshot) if garage is UNCHANGED else garage
    outside_pool = snapshot.pool if snapshot.pool and snapshot.pool.location == "outdoor" else None
    x0,y0,x1,y1 = ring_bounds(snapshot.envelope_polygon or rect(0,0,18,15.5))
    ground = next((l for l in snapshot.levels if l.name == "ground"),None)
    if ground is None and (yard or garage or outside_pool):
        raise ValueError("Site features need a ground-floor datum.")
    grade = ground.elevation_m if ground else 0
    if outside_pool:
        outside_pool.level_id = ground.id
        if yard is None:
            if explicitly_remove_yard:
                raise ValueError("Remove the outdoor pool before removing its hosting yard.")
            yard = YardProgram(width_m=max(x1-x0,outside_pool.water_length_m+2),
                               depth_m=max(8,outside_pool.water_width_m+2))
    if not yard and not garage and not outside_pool:
        snapshot.site_layout = None
        if snapshot.building_program:
            snapshot.building_program.yard = None
            snapshot.building_program.garage = None
        if old:
            snapshot.assumptions = [a for a in snapshot.assumptions if a.field != "site.layout"]
        return snapshot

    sid = lambda role: stable_id(snapshot.project_id, f"site:{role}")
    yard_surface, garage_geometry, driveway, pool_deck = None,None,None,None
    if yard:
        yard = YardProgram.model_validate(yard)
        width = yard.width_m if yard.width_m is not None else x1-x0
        yx0, yy0 = (x0+x1-width)/2, y1+1
        yard_surface = SiteSurface(id=sid("yard"),name="Rear yard",polygon=rect(yx0,yy0,width,yard.depth_m),
                                   elevation_m=grade,material="grass")
        if outside_pool:
            if (outside_pool.water_length_m+2 > width+1e-8
                    or outside_pool.water_width_m+2 > yard.depth_m+1e-8):
                raise ValueError("The outdoor pool needs a yard at least 2 m wider and deeper than its water rectangle for the concept deck and surrounding strip. Enlarge the yard or reduce the pool.")
            outside_pool.origin_x_m = yx0+(width-outside_pool.water_length_m)/2
            outside_pool.origin_y_m = yy0+(yard.depth_m-outside_pool.water_width_m)/2
            water = rect(outside_pool.origin_x_m,outside_pool.origin_y_m,outside_pool.water_length_m,outside_pool.water_width_m)
            deck = rect(outside_pool.origin_x_m-.6,outside_pool.origin_y_m-.6,
                        outside_pool.water_length_m+1.2,outside_pool.water_width_m+1.2)
            pool_deck = SiteSurface(id=sid("pool_deck"),name="Outdoor pool deck",polygon=deck,holes=[water],
                                   elevation_m=grade,material="paving")
            yard_surface.holes = [deck]
    if garage:
        garage = GarageProgram.model_validate(garage)
        yard_bounds = ring_bounds(yard_surface.polygon) if yard_surface else (x0,y0,x1,y1)
        # Keep the garage clear even if a large yard extends beyond the house.
        gx = max(x1,yard_bounds[2])+1.5 if garage.side == "right" else min(x0,yard_bounds[0])-1.5-garage.width_m
        opening_x = gx+(garage.width_m-garage.vehicle_door_width_m)/2
        garage_geometry = GarageGeometry(id=sid("garage"),polygon=rect(gx,y0,garage.width_m,garage.depth_m),
            elevation_m=grade,height_m=garage.height_m,side=garage.side,
            vehicle_door_width_m=garage.vehicle_door_width_m,
            vehicle_door_start=[opening_x,y0],vehicle_door_end=[opening_x+garage.vehicle_door_width_m,y0])
        driveway = SiteSurface(id=sid("driveway"),name="Garage approach",polygon=rect(gx,y0-6,garage.width_m,6),
                               elevation_m=grade,material="paving")
    rings = [snapshot.envelope_polygon or rect(0,0,18,15.5)]
    rings.extend(feature.polygon for feature in (yard_surface,garage_geometry,driveway) if feature)
    all_points = [point for ring in rings for point in ring]
    minx,miny,maxx,maxy = ring_bounds(all_points)
    context = rect(minx-3,miny-3,maxx-minx+6,maxy-miny+6)
    snapshot.site_layout = SiteLayout(revision_id=snapshot.revision_id,yard=yard_surface,garage=garage_geometry,
                                      driveway=driveway,pool_deck=pool_deck,context_polygon=context)
    if snapshot.site.mode == "synthetic_demo":
        snapshot.site.context_width_m = maxx-minx+6
        snapshot.site.context_depth_m = maxy-miny+6
        context_note = next((a for a in snapshot.assumptions if a.field == "site.context_m"),None)
        if context_note:
            context_note.value = [snapshot.site.context_width_m,snapshot.site.context_depth_m]
            context_note.rationale = "Synthetic display/study extent coordinated around the house and current site features, with a 3 m display margin. It is not a parcel measurement or permitted setback."
    if snapshot.building_program:
        snapshot.building_program.yard = yard
        snapshot.building_program.garage = garage
    value = dict(yard=yard.model_dump(mode="json") if yard else None,
                 garage=garage.model_dump(mode="json") if garage else None,
                 pool_location=snapshot.pool.location if snapshot.pool else None,
                 garage_assembly_m={"wall":.20,"slab":.16,"roof":.18,"vehicle_door_height":2.2},
                 siting_m={"rear_yard_gap":1,"detached_garage_gap":1.5,"approach_depth":6,"pool_deck_width":.6},
                 context_basis="synthetic_study_extent_not_parcel_boundary")
    assumption = Assumption(id=sid("assumptions"),field="site.layout",value=value,
        rationale="Concept rear yard, detached unconditioned garage and vehicle approach are coordinated in local metres. Yard area is separate from enclosed floor area; its pool/deck holes are not lawn. Garage dimensions are exterior faces, wall height is to roof soffit, and slab top is the ground datum. Siting gaps, assemblies, door, deck and approach dimensions are design assumptions, not minimum legal clearances. The context extent is not a surveyed property boundary. Parcel fit, legal curb access, setbacks, drainage, pool barriers, garage fire separation and all engineering/permit requirements remain unverified.")
    prior = next((i for i,a in enumerate(snapshot.assumptions) if a.field == "site.layout"),None)
    if prior is None:
        snapshot.assumptions.append(assumption)
    else:
        snapshot.assumptions[prior] = assumption
    return snapshot
