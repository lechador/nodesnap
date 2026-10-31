"""Whole-building concept synthesis from a typed program, without a seed model.

A bounded orthogonal planning family connects every requested rectangular room
through central/side circulation. Targets are zone areas, never claimed clear
net areas. Explicit areas are preserved; inferred targets may absorb a bounded
small remainder, with achieved quantities reported separately. Assemblies, stair reserves and synthetic site context are assumptions.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math

from .architecture import bounds, enrich_snapshot, rect, stable_id
from .models import (Assumption, Brief, BuildingProgram, FloorProgram, Level,
                     PoolProgram, PoolSystem, ProjectSnapshot, RoomProgram,
                     SiteContext, Space, new_id)


class BuildingGenerationError(ValueError):
    pass


def envelope_bounds(snapshot):
    ring = snapshot.envelope_polygon or rect(0, 0, 18, 15.5)
    return min(p[0] for p in ring), min(p[1] for p in ring), max(p[0] for p in ring), max(p[1] for p in ring)


def planning_dimensions(width: float, depth: float):
    corridor_depth = 1.6
    corridor_y = max(4.2, (depth - corridor_depth) / 2)
    return corridor_y, corridor_depth, 3.0, 4.2


def _expanded(rooms):
    return [room.model_copy(update={"name": room.name if room.count == 1 else f"{room.name} {i + 1}", "count": 1})
            for room in rooms for i in range(room.count)]


def _assign(rooms, bins, pool):
    # Deterministic bounded beam search over connected rectangular room bands.
    # Keep distinct capacity ledgers; no generated code or external solver input.
    ordered = sorted(enumerate(rooms), key=lambda item: (-item[1].target_area_m2, item[0]))
    states = [((0.0,) * len(bins), {})]
    capacities = [b["width"] * b["depth"] for b in bins]
    for index, room in ordered:
        candidates = {}
        for used, assigned in states:
            for slot, band in enumerate(bins):
                area = room.target_area_m2
                width = band["width"] if band["vertical"] else area / band["depth"]
                depth = area / band["width"] if band["vertical"] else band["depth"]
                minimum = 1.5 if room.classification == "principal" else 1.2
                if (min(width, depth) < minimum - 1e-8 or max(width,depth)/min(width,depth) > 4+1e-8
                        or used[slot] + area > capacities[slot] + 1e-8):
                    continue
                if room.use == "pool_hall" and pool and (width < pool.water_length_m + .6 or depth < pool.water_width_m + .6):
                    continue
                ledger = tuple(round(value + area if n == slot else value, 8) for n, value in enumerate(used))
                if ledger not in candidates:
                    candidates[ledger] = (ledger, {**assigned, index: slot})
        if not candidates:
            return None
        # Balance occupied fractions while preferring compact placements.
        states = sorted(candidates.values(), key=lambda state: (
            max(state[0][i] / capacities[i] for i in range(len(bins))) - min(state[0][i] / capacities[i] for i in range(len(bins))),
            state[0], tuple(state[1].values())))[:768]
    valid = []
    for used, assigned in states:
        def valid_remainder(i,capacity):
            remainder=capacity-used[i]
            if remainder < 1e-6 or bins[i].get("merge_remainder"):
                return True
            dimension=remainder/(bins[i]["width"] if bins[i]["vertical"] else bins[i]["depth"])
            if dimension >= 1.2-1e-8:
                return True
            indices=[index for index,slot in assigned.items() if slot==i]
            if not indices:
                return False
            room=rooms[max(indices)]
            placed_area=room.target_area_m2+remainder
            fixed=bins[i]["width"] if bins[i]["vertical"] else bins[i]["depth"]
            varied=placed_area/fixed
            return (room.area_basis != "user_supplied" and remainder <= room.target_area_m2*.15+1e-8
                    and max(fixed,varied)/min(fixed,varied)<=4+1e-8)
        if all(valid_remainder(i,capacity) for i,capacity in enumerate(capacities)):
            valid.append((used, assigned))
    if not valid:
        return None
    return min(valid, key=lambda state: (max(state[0][i]/capacities[i] for i in range(len(bins)))-min(state[0][i]/capacities[i] for i in range(len(bins))),state[0]))[1]


def _floor_spaces(project_id, namespace, level, program, width, depth, pool=None, existing=None):
    sy, ch, cw, sh = planning_dimensions(width, depth)
    rooms = _expanded(program.rooms)
    if pool and not any(room.use == "pool_hall" for room in rooms):
        if len(rooms) >= 20:
            raise BuildingGenerationError("The pool needs a pool hall, but this floor already has the maximum 20 requested rooms.")
        rooms.append(RoomProgram(name="Indoor pool hall", use="pool_hall", classification="support",
                                 target_area_m2=(pool.water_length_m + 1.2) * max(sy, depth - sy - ch)))
    if pool and sum(room.use == "pool_hall" for room in rooms) != 1:
        raise BuildingGenerationError("A pool floor needs exactly one pool hall.")
    base = [dict(x=0., y=0., width=width-cw, depth=sy, vertical=False),
            dict(x=0., y=sy+ch, width=width, depth=depth-sy-ch, vertical=False)]
    families = [("central_corridor",base,[])]
    service_widths={1.6,2.,2.4,3.,3.6,4.,4.2}
    # A fitted support column preserves explicitly requested small bathroom /
    # utility areas without leaving a thin unused cell at the end of its run.
    support_area=sum(room.target_area_m2 for room in rooms if room.classification=="support" and room.use!="pool_hall")
    fitted_width=support_area/(depth-sy-ch)
    if 1.2<=fitted_width<=4.2:
        service_widths.add(fitted_width)
    for service_width in sorted(service_widths):
        side = [base[0], dict(x=0., y=sy+ch, width=width-service_width-1.4, depth=depth-sy-ch,
                              vertical=False, merge_remainder=True),
                dict(x=width-service_width, y=sy+ch, width=service_width, depth=depth-sy-ch, vertical=True)]
        families.append((f"central_with_service_branch_{service_width:g}m",side,[]))
    # Deeper footprints use short room bands connected to a side spine. This
    # keeps offices/bedrooms proportionate instead of stretching small targets
    # across half the entire building depth.
    for rows_per_side in (2,3):
        bands,crossings = [],[]
        for y,region_depth in ((0.,sy),(sy+ch,depth-sy-ch)):
            room_depth=(region_depth-(rows_per_side-1)*1.4)/rows_per_side
            if room_depth < 1.2:
                break
            for n in range(rows_per_side):
                row_y=y+n*(room_depth+1.4)
                bands.append(dict(x=0.,y=row_y,width=width-cw-1.4,depth=room_depth,vertical=False,merge_remainder=True,spine=True))
                if n<rows_per_side-1:
                    crossings.append(rect(0,row_y+room_depth,width-cw,1.4))
        else:
            families.append((f"connected_grid_{rows_per_side*2}_bands",bands,crossings))
    feasible=[]
    for family,bins,crossings in families:
        assignment=_assign(rooms,bins,pool)
        if assignment is None:
            continue
        ratios=[]
        for index,room in enumerate(rooms):
            band=bins[assignment[index]]
            a,b=(band["width"],room.target_area_m2/band["width"]) if band["vertical"] else (room.target_area_m2/band["depth"],band["depth"])
            ratios.append(max(a,b)/min(a,b))
        feasible.append((max(ratios)+len(crossings)*.04,sum(ratios),family,bins,assignment,crossings))
    chosen = min(feasible,key=lambda candidate:candidate[:3]) if feasible else None
    if chosen is None:
        requested = sum(r.target_area_m2 for r in rooms)
        available = (width-cw) * sy + width * (depth-sy-ch)
        constraints=[]
        for room in rooms:
            minimum_dimension=1.5 if room.classification=="principal" else 1.2
            ranges=[]
            for _,candidate_bins,_ in families:
                for band in candidate_bins:
                    fixed=band["width"] if band["vertical"] else band["depth"]
                    if fixed < minimum_dimension:
                        continue
                    minimum=max(minimum_dimension*fixed,fixed*fixed/4)
                    maximum=min(band["width"]*band["depth"],4*fixed*fixed)
                    if room.use=="pool_hall" and pool:
                        if band["vertical"]:
                            if band["width"] < pool.water_length_m+.6:
                                continue
                            minimum=max(minimum,(pool.water_width_m+.6)*fixed)
                        else:
                            if band["depth"] < pool.water_width_m+.6:
                                continue
                            minimum=max(minimum,(pool.water_length_m+.6)*fixed)
                    if minimum<=maximum:
                        ranges.append((minimum,maximum))
            if ranges and room.target_area_m2 < min(value[0] for value in ranges)-1e-8:
                constraints.append(f"{room.name}: target {room.target_area_m2:g} m² is too small; increase it to at least {min(value[0] for value in ranges):.2f} m² for usable room dimensions")
            elif not ranges or not any(lo-1e-8<=room.target_area_m2<=hi+1e-8 for lo,hi in ranges):
                constraints.append(f"{room.name}: target {room.target_area_m2:g} m² does not fit an available room band with the 4:1 aspect-ratio limit")
        detail="; ".join(constraints) if constraints else "The combined room areas do not pack into the connected bands; redistribute inferred room areas or change the footprint. Small support rooms may need larger areas, not further reductions"
        raise BuildingGenerationError(
            f"{program.label}: {len(rooms)} rooms totaling {requested:.1f} m² cannot fit this {width:g} × {depth:g} m "
            f"planning envelope ({available:.1f} m² available before additional branch circulation). {detail}. "
            "Preserve explicit user requirements; only inferred choices may be adjusted. No rooms were dropped.")
    _,_,family,bins,assignment,crossings = chosen
    spaces = []
    def make(name, use, classification, polygon, target=None, key=None):
        original = next((s for s in existing or [] if s.name == name and s.use == use and s.classification == classification),None)
        identity = original.id if original else stable_id(project_id, f"{namespace}:space:{level.id}:{key or 'room:'+name+':'+use}")
        space = Space(id=identity, level_id=level.id, name=name, use=use, classification=classification,
                      polygon=polygon, target_area_m2=target)
        spaces.append(space)
        return space
    side_gap = 0.
    spine_rows = []
    for slot, band in enumerate(bins):
        cursor = 0.
        indices=[index for index in range(len(rooms)) if assignment[index]==slot]
        remainder_area=band["width"]*band["depth"]-sum(rooms[index].target_area_m2 for index in indices)
        remainder_dimension=remainder_area/(band["width"] if band["vertical"] else band["depth"])
        extra = remainder_area if indices and not band.get("merge_remainder") and 1e-6 < remainder_dimension < 1.2 else 0.
        for index, room in enumerate(rooms):
            if assignment[index] != slot:
                continue
            placed_area = room.target_area_m2 + (extra if index == indices[-1] else 0.)
            room_width = band["width"] if band["vertical"] else placed_area / band["depth"]
            room_depth = placed_area / band["width"] if band["vertical"] else band["depth"]
            x = band["x"] if band["vertical"] else band["x"] + cursor
            y = band["y"] + cursor if band["vertical"] else band["y"]
            make(room.name, room.use, room.classification, rect(x,y,room_width,room_depth), room.target_area_m2)
            cursor += room_depth if band["vertical"] else room_width
        remain = (band["depth"] if band["vertical"] else band["width"]) - cursor
        if band.get("merge_remainder") and remain < 1.2:
            if not band.get("spine"):
                side_gap = remain
        elif remain > 1e-6:
            polygon = rect(band["x"], band["y"]+cursor, band["width"], remain) if band["vertical"] else rect(band["x"]+cursor, band["y"], remain, band["depth"])
            make(f"Unassigned space {slot+1}", "unassigned", "support", polygon, key=f"reserve:{slot}")
        if band.get("spine"):
            gap=remain if remain<1.2 else 0
            spine_rows.append(rect(width-cw-1.4-gap,band["y"],1.4+gap,band["depth"]))
    make("Main circulation", "circulation", "support", rect(0,sy,width,ch), key="circulation")
    make("Stair / service reserve", "stairs_service", "support", rect(width-cw,sy-sh,cw,sh), key="core")
    if sy-sh > 1e-6:
        make("Service circulation", "circulation", "support", rect(width-cw,0,cw,sy-sh), key="core-reserve")
    if family.startswith("central_with_service_branch"):
        make("Side circulation", "circulation", "support", rect(bins[2]["x"]-1.4-side_gap,sy+ch,1.4+side_gap,depth-sy-ch), key="side-circulation")
    if spine_rows:
        for index,polygon in enumerate(spine_rows):
            make(f"Side circulation {index+1}","circulation","support",polygon,key=f"spine:{index}")
        for index,polygon in enumerate(crossings):
            make(f"Cross circulation {index+1}","circulation","support",polygon,key=f"cross:{index}")
        make("Unassigned support zone","unassigned","support",rect(width-cw,sy+ch,cw,depth-sy-ch),key="upper-support")
    return spaces, family


def _roof_spaces(project_id, namespace, roof, width, depth, terrace_area):
    if terrace_area <= 0:
        return []
    sy, ch, cw, sh = planning_dimensions(width, depth)
    max_width = width-cw
    # Choose a rectangle that meets the full corridor band and stays clear of
    # the stair enclosure; use full width when the requested area is small.
    terrace_depth = max(sy+ch, terrace_area/max_width)
    if terrace_depth > depth + 1e-8:
        raise BuildingGenerationError("The roof terrace cannot fit beside the stair enclosure; reduce its area or enlarge the footprint.")
    terrace_width = terrace_area/terrace_depth
    if terrace_width < 1.2:
        raise BuildingGenerationError(f"The requested terrace is too narrow to connect; use at least {1.2*terrace_depth:.1f} m² or omit it.")
    records = [("Roof terrace", "roof_terrace", rect(0,0,terrace_width,terrace_depth), terrace_area),
               ("Terrace access", "roof_access", rect(terrace_width,sy,width-terrace_width,ch), None),
               ("Roof stair enclosure", "stairs_service", rect(width-cw,sy-sh,cw,sh), None)]
    return [Space(id=stable_id(project_id,f"{namespace}:space:{roof.id}:{use}"), level_id=roof.id,
                  name=name,use=use,classification="support",polygon=polygon,target_area_m2=target)
            for name,use,polygon,target in records]


def build_building(project_id: str, program: BuildingProgram | dict, *, namespace: str = "building") -> ProjectSnapshot:
    program = BuildingProgram.model_validate(program).model_copy(deep=True)
    width, depth = program.width_m, program.depth_m
    floors = []
    if program.basement:
        floors.append(("basement", program.basement, -program.basement.height_m))
    elevation = 0.
    for index, floor in enumerate(program.floors):
        floors.append(("ground" if index == 0 else "upper" if index == 1 else f"level_{index+1}", floor, elevation))
        elevation += floor.height_m
    levels = [Level(id=stable_id(project_id,f"{namespace}:level:{name}"),name=name,label=floor.label,elevation_m=z)
              for name,floor,z in floors]
    roof = Level(id=stable_id(project_id,f"{namespace}:level:roof"),name="roof",label="Roof / terrace" if program.roof_terrace_area_m2 else "Roof",elevation_m=elevation)
    spaces, families = [], {}
    for level, (_, floor, _) in zip(levels, floors):
        host_pool = program.pool if program.pool and program.pool.level == level.name else None
        generated,family = _floor_spaces(project_id,namespace,level,floor,width,depth,host_pool)
        spaces.extend(generated); families[level.name] = family
    levels.append(roof)
    spaces.extend(_roof_spaces(project_id,namespace,roof,width,depth,program.roof_terrace_area_m2))
    pool = None
    if program.pool:
        level = next(l for l in levels if l.name == program.pool.level)
        hall = next(s for s in spaces if s.level_id == level.id and s.use == "pool_hall")
        x0,y0,x1,y1 = bounds(hall)
        pool = PoolSystem(id=stable_id(project_id,f"{namespace}:pool"),level_id=level.id,
                          water_length_m=program.pool.water_length_m,water_width_m=program.pool.water_width_m,
                          water_depth_m=program.pool.water_depth_m,
                          origin_x_m=(x0+x1-program.pool.water_length_m)/2,
                          origin_y_m=(y0+y1-program.pool.water_width_m)/2)
    notes = [Assumption(field="building_program",value=program.model_dump(mode="json"),
                        rationale="The homeowner brief is interpreted as a concept program. Dimensions, room targets and omitted details may be inferred; notes identify those choices. No site survey, zoning envelope or engineering approval is established."),
             Assumption(field="layout_generation",value={"family_by_level":families,"target_basis":"wall_centerline_zone","maximum_inferred_zone_target_tolerance":.15,"maximum_requested_room_aspect_ratio":4,"envelope_m":[width,depth]},
                        rationale="Deterministic rectangular room packing with reserved circulation and aligned stair/service zones. All requested room instances are retained. A final room with an inferred target may expand by at most 15% of its zone target to avoid an unusable remnant; actual zone areas and clear areas are reported separately. Clear areas deduct concept wall thickness."),
             Assumption(field="architecture.assemblies_m",value={"exterior":.30,"partition":.15,"slab":.25},
                        rationale="Concept assembly dimensions; structural, thermal, fire, accessibility and acoustic performance require project-specific design."),
             Assumption(field="architecture.stair_reserve",value={"width_m":3.0,"depth_m":4.2},
                        rationale="An aligned stair/service reserve remains on occupied floors, including a single-floor concept, to support later expansion. A bare unoccupied roof has no fabricated stair route or headhouse. Actual stair/headroom/egress design is unverified."),
             Assumption(field="site.context_m",value=[width+20,depth+20],rationale="Synthetic display context with 10 m margin around the footprint; not a site measurement or permitted setback.")]
    notes.extend(Assumption(field=f"design_notes.{i}",value=note,rationale="Declared concept choice or unresolved preference from brief interpretation.") for i,note in enumerate(program.design_notes))
    snap = ProjectSnapshot(project_id=project_id,title=program.title,
        brief=Brief(use=program.building_use,floors_above_ground=len(program.floors),principal_rooms_per_floor=0,
                    target_floor_area_m2=width*depth,basement_area_m2=width*depth if program.basement else 0,
                    roof_terrace_target_m2=program.roof_terrace_area_m2,pool=bool(pool),terrace=program.roof_terrace_area_m2>0,
                    materials="Concept assemblies; structural system and material performance are not selected."),
        site=SiteContext(name="Synthetic design context",context_width_m=width+20,context_depth_m=depth+20),
        levels=levels,spaces=spaces,pool=pool,roof_terrace_area_m2=program.roof_terrace_area_m2,
        material_palette=program.material_palette,building_program=program,envelope_polygon=rect(0,0,width,depth),assumptions=notes)
    return enrich_snapshot(snap).with_hash()


def redesign_building(snapshot, program):
    candidate = build_building(snapshot.project_id,program,namespace=f"redesign:{snapshot.revision_id}")
    candidate.parent_revision_id = snapshot.revision_id
    candidate.revision_id = new_id()
    candidate.revision_number = snapshot.revision_number+1
    candidate.created_at = datetime.now(timezone.utc)
    return enrich_snapshot(candidate).with_hash()


def regenerate_program_floor(snapshot, level_name, rooms):
    level = next((l for l in snapshot.levels if l.name == level_name),None)
    if level is None or level.name == "roof":
        return {"spaces":None,"solver_status":"MODEL_INVALID"}
    existing = [s for s in snapshot.spaces if s.level_id == level.id]
    supports = [RoomProgram(name=s.name,use=s.use,target_area_m2=s.target_area_m2,classification="support",
                            area_basis=_room_basis(snapshot,s.name,s.use,s.target_area_m2,level.id))
                for s in existing if s.classification == "support" and s.target_area_m2 is not None and s.use not in {"stairs_service","circulation","roof_access","roof_terrace"}]
    try:
        floor = FloorProgram(label=level.label,rooms=[RoomProgram(**room,classification="principal",
                     area_basis=_room_basis(snapshot,room["name"],room["use"],room["target_area_m2"],level.id,
                                            new_basis="user_supplied")) for room in rooms]+supports)
        x0,y0,x1,y1 = envelope_bounds(snapshot)
        pool = snapshot.pool.model_copy(deep=True) if snapshot.pool and snapshot.pool.level_id == level.id else None
        generated,family = _floor_spaces(snapshot.project_id,"building",level,floor,x1-x0,y1-y0,pool,existing)
        output = {"spaces":[s.model_copy(deep=True) for s in snapshot.spaces if s.level_id != level.id]+generated,
                  "solver_status":"FEASIBLE","settings":{"family":family,"method":"deterministic_bounded_packing","target_area_basis":"wall_centerline_zone"}}
        if pool:
            hall = next(s for s in generated if s.use == "pool_hall")
            hx0,hy0,hx1,hy1 = bounds(hall)
            pool.origin_x_m=(hx0+hx1-pool.water_length_m)/2;pool.origin_y_m=(hy0+hy1-pool.water_width_m)/2
            output["pool"]=pool
        candidate=snapshot.model_copy(deep=True)
        candidate.spaces=output["spaces"]
        if pool:
            candidate.pool=pool
        if level.name=="basement":
            candidate.building_program.basement=floor
        else:
            above_ground=sorted((l for l in candidate.levels if l.name not in {"roof","basement"}),key=lambda l:l.elevation_m)
            candidate.building_program.floors[next(i for i,l in enumerate(above_ground) if l.id==level.id)]=floor
        output["building_program"]=synchronize_program(candidate)
        return output
    except (ValueError,TypeError) as exc:
        return {"spaces":None,"solver_status":"INFEASIBLE","issue":str(exc)}


def _room_basis(snapshot,name,use,target,level_id=None,*,new_basis="demonstration_assumption"):
    program=snapshot.building_program
    source_floors=([program.basement] if program and program.basement else [])+(program.floors if program else [])
    if program and level_id:
        level=next((l for l in snapshot.levels if l.id==level_id),None)
        if level and level.name=="basement" and program.basement:
            source_floors=[program.basement]
        elif level:
            above_ground=sorted((l for l in snapshot.levels if l.name not in {"roof","basement"}),key=lambda l:l.elevation_m)
            index=next((i for i,l in enumerate(above_ground) if l.id==level_id),len(program.floors))
            if index<len(program.floors):
                source_floors=[program.floors[index]]
    candidates=[]
    for floor in source_floors:
        for room in _expanded(floor.rooms):
            if room.name==name and room.use==use:
                candidates.append(room)
    matching=[room for room in candidates if math.isclose(room.target_area_m2,target,abs_tol=1e-8)]
    if matching:
        return "user_supplied" if any(room.area_basis=="user_supplied" for room in matching) else "demonstration_assumption"
    return "user_supplied" if candidates else new_basis


def synchronize_program(snapshot):
    """Keep the editable brief synchronized with accepted canonical edits."""
    if snapshot.building_program is None:
        return None
    ordered = sorted(snapshot.levels,key=lambda l:l.elevation_m)
    floors, basement = [], None
    for index,level in enumerate(ordered[:-1]):
        requested = [RoomProgram(name=s.name,use=s.use,target_area_m2=s.target_area_m2,
                                 classification=s.classification,area_basis=_room_basis(snapshot,s.name,s.use,s.target_area_m2,level.id))
                     for s in snapshot.spaces if s.level_id == level.id and s.target_area_m2 is not None
                     and s.use not in {"circulation","stairs_service","roof_access","roof_terrace"}]
        if not requested:
            continue
        floor=FloorProgram(label=level.label,height_m=ordered[index+1].elevation_m-level.elevation_m,rooms=requested)
        if level.name == "basement":
            basement=floor
        else:
            floors.append(floor)
    program=snapshot.building_program.model_copy(deep=True)
    program.title=snapshot.title
    program.floors=floors
    program.basement=basement
    program.material_palette=snapshot.material_palette
    program.roof_terrace_area_m2=snapshot.roof_terrace_area_m2 or 0
    if snapshot.pool:
        name=next(l.name for l in snapshot.levels if l.id==snapshot.pool.level_id)
        program.pool=PoolProgram(level=name,water_length_m=snapshot.pool.water_length_m,
                                 water_width_m=snapshot.pool.water_width_m,water_depth_m=snapshot.pool.water_depth_m)
    else:
        program.pool=None
    snapshot.building_program=BuildingProgram.model_validate(program.model_dump())
    return snapshot.building_program
