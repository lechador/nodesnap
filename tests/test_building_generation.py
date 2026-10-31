"""Independent whole-building program, geometry, editing and history evidence."""
import hashlib
import json
from copy import deepcopy

import pytest
from pydantic import ValidationError
from shapely.geometry import Polygon
from shapely.ops import unary_union

from domain.architecture import bounds, enrich_snapshot
from domain.building import BuildingGenerationError, build_building, redesign_building
from domain.commands import CommandError, apply_commands
from domain.models import BuildingProgram, ProjectSnapshot, new_id
from domain.seed import build_seed
from geometry.generate import generate_floor
from geometry.validate import validate_snapshot


def room(name,use,area,count=1,classification='principal',basis='demonstration_assumption'):
    return dict(name=name,use=use,target_area_m2=area,count=count,classification=classification,area_basis=basis)


def small_program():
    return dict(title='A new two-bedroom home',width_m=12,depth_m=10,footprint_basis='user_supplied',
        floors=[dict(label='Garden floor',height_m=3.1,rooms=[room('Living','living',24),room('Kitchen','kitchen',12),
        room('Bedroom','bedroom',14,2),room('Bathroom','bathroom',6,classification='support'),
        room('Utility','service',6,classification='support')])],design_notes=['The dimensions are the requested concept envelope, not a surveyed site.'])


def complex_program():
    return dict(title='A three-storey studio house',width_m=22,depth_m=18,material_palette='warm_concrete',
        floors=[dict(label='Day floor',height_m=3.4,rooms=[room('Living','living',48),room('Kitchen','kitchen',24),room('Dining','dining',26),room('Guest','bedroom',24),room('WC','bathroom',8,classification='support')]),
                dict(label='Sleeping floor',height_m=3.0,rooms=[room('Bedroom','bedroom',30,3),room('Study','study',20),room('Lounge','family',40),room('Bathroom','bathroom',8,2,'support')]),
                dict(label='Studios',height_m=3.8,rooms=[room('Studio','studio',45,4),room('WC','bathroom',8,2,'support')])],
        basement=dict(label='Pool basement',height_m=3.2,rooms=[room('Pool hall','pool_hall',100),room('Fitness','fitness',40),room('Changing','changing',8,classification='support'),room('Plant','plant',8,classification='support')]),
        pool=dict(water_length_m=8,water_width_m=3,water_depth_m=1.5,level='basement'),roof_terrace_area_m2=60)


def assert_geometry(snapshot):
    assert validate_snapshot(snapshot)==[]
    assert snapshot.architecture.revision_id==snapshot.revision_id
    assert snapshot.content_hash==snapshot.compute_hash()
    envelope=Polygon(snapshot.envelope_polygon)
    for level in snapshot.levels:
        assert all(Polygon(s.polygon).within(envelope.buffer(1e-8)) for s in snapshot.spaces if s.level_id==level.id)
        if level.name!='roof':
            shapes=[Polygon(s.polygon) for s in snapshot.spaces if s.level_id==level.id]
            assert sum(shape.area for shape in shapes)==pytest.approx(envelope.area)
            assert unary_union(shapes).area==pytest.approx(envelope.area)
    by_id={level.id:level for level in snapshot.levels}
    for stair in snapshot.architecture.stairs:
        assert stair.riser_count*stair.riser_height_m==pytest.approx(by_id[stair.upper_level_id].elevation_m-by_id[stair.lower_level_id].elevation_m)


def test_small_house_is_new_geometry_without_seed_features_or_room_program():
    source=small_program();before=deepcopy(source)
    snapshot=build_building(new_id(),source)
    assert source==before
    assert_geometry(snapshot)
    assert snapshot.title==source['title']
    assert [(l.name,l.elevation_m) for l in snapshot.levels]==[('ground',0),('roof',3.1)]
    assert snapshot.pool is None and snapshot.roof_terrace_area_m2==0
    assert not snapshot.architecture.stairs
    assert len(snapshot.architecture.slabs)==2
    assert sum(s.use=='bedroom' for s in snapshot.spaces)==2
    assert sum(s.classification=='principal' for s in snapshot.spaces)==4
    assert not any(s.level_id==snapshot.levels[-1].id for s in snapshot.spaces)
    assert Polygon(snapshot.architecture.slabs[0].polygon).area==120
    for space in snapshot.spaces:
        if space.target_area_m2:
            assert space.target_area_m2-1e-8<=Polygon(space.polygon).area<=space.target_area_m2*1.15+1e-8


def test_different_program_has_own_counts_heights_features_and_pool():
    snapshot=build_building(new_id(),complex_program())
    assert_geometry(snapshot)
    assert [l.elevation_m for l in snapshot.levels]==pytest.approx([-3.2,0,3.4,6.4,10.2])
    assert sum(s.use=='bedroom' for s in snapshot.spaces)==4
    assert len(snapshot.architecture.stairs)==4
    assert snapshot.pool.water_length_m==8 and snapshot.pool.water_width_m==3
    assert snapshot.pool.water_depth_m==1.5
    assert snapshot.roof_terrace_area_m2==60
    assert all(Polygon(s.polygon).area==pytest.approx(396) for s in snapshot.architecture.slabs if s.elevation_m is None)


def test_dense_rooms_use_shorter_connected_bands_with_bounded_aspect_ratio():
    program=dict(title='Many studios',width_m=40,depth_m=30,floors=[dict(label='Work floor',rooms=[room('Office','office',30,10),room('Studio','studio',30,8),room('WC','bathroom',8,2,'support')])])
    snapshot=build_building(new_id(),program)
    assert_geometry(snapshot)
    assert len([s for s in snapshot.spaces if s.target_area_m2 is not None])==20
    assert snapshot.assumptions[1].value['family_by_level']['ground'].startswith('connected_grid_')
    for space in snapshot.spaces:
        if space.target_area_m2 is not None:
            x0,y0,x1,y1=bounds(space)
            assert max(x1-x0,y1-y0)/min(x1-x0,y1-y0)<=4+1e-8
    assert any(s.use=='unassigned' for s in snapshot.spaces)


def test_explicit_room_area_is_never_expanded_into_a_remainder():
    program=small_program()
    program['floors'][0]['rooms'][0]['area_basis']='user_supplied'
    snapshot=build_building(new_id(),program)
    living=next(s for s in snapshot.spaces if s.name=='Living')
    assert Polygon(living.polygon).area==pytest.approx(24)
    assert snapshot.building_program.floors[0].rooms[0].area_basis=='user_supplied'


def test_geometry_and_entity_ids_are_reproducible_for_the_same_program():
    a=build_building('reproducible',small_program());b=build_building('reproducible',small_program())
    assert [(s.id,s.polygon) for s in a.spaces]==[(s.id,s.polygon) for s in b.spaces]
    assert [w.model_dump() for w in a.architecture.walls]==[w.model_dump() for w in b.architecture.walls]


def test_new_building_command_keeps_existing_project_history_untouched():
    old=build_seed(new_id());before=old.model_dump_json()
    new=apply_commands(old,[dict(type='design_building',program=small_program())])
    assert old.model_dump_json()==before
    assert new.project_id==old.project_id and new.parent_revision_id==old.revision_id
    assert new.revision_number==old.revision_number+1
    assert {s.id for s in old.spaces}.isdisjoint(s.id for s in new.spaces)
    assert_geometry(new)
    direct=redesign_building(old,small_program())
    assert direct.parent_revision_id==old.revision_id and direct.revision_number==2
    assert_geometry(direct)


def test_single_floor_without_roof_access_can_add_and_remove_a_floor():
    old=build_building(new_id(),small_program())
    added=apply_commands(old,[dict(type='add_level')])
    assert_geometry(added)
    assert len(added.architecture.stairs)==1
    assert len(added.building_program.floors)==2
    assert {s.id for s in old.spaces}<={s.id for s in added.spaces}
    removed=apply_commands(added,[dict(type='remove_level')])
    assert_geometry(removed)
    assert len(removed.building_program.floors)==1
    assert not removed.architecture.stairs
    assert [s.model_dump() for s in old.spaces]==[s.model_dump() for s in removed.spaces]


def test_normal_edits_keep_program_options_and_height_current():
    snapshot=build_building(new_id(),complex_program())
    level=next(l for l in snapshot.levels if l.name=='ground')
    edited=apply_commands(snapshot,[dict(type='set_level_height',level_id=level.id,height_m=4),dict(type='set_material_palette',palette='white_stucco'),dict(type='set_pool_dimensions',water_depth_m=1.2),dict(type='set_terrace_area',area_m2=80)])
    assert_geometry(edited)
    p=edited.building_program
    assert p.floors[0].height_m==4 and p.material_palette=='white_stucco'
    assert p.pool.water_depth_m==1.2 and p.roof_terrace_area_m2==80
    without=apply_commands(edited,[dict(type='set_terrace_area',area_m2=0)])
    assert_geometry(without)
    assert not without.brief.terrace and not without.building_program.roof_terrace_area_m2
    assert len(without.architecture.stairs)==3


def test_arbitrary_room_count_can_regenerate_without_reviving_seed():
    snapshot=build_building(new_id(),small_program())
    level=snapshot.levels[0]
    rooms=[dict(name=s.name,use=s.use,target_area_m2=22 if s.name=='Living' else s.target_area_m2) for s in snapshot.spaces if s.classification=='principal']
    solved=generate_floor(snapshot,level.name,rooms)
    assert solved['spaces'] is not None
    candidate=snapshot.model_copy(deep=True);candidate.spaces=solved['spaces'];candidate.building_program=solved['building_program']
    candidate=enrich_snapshot(candidate).with_hash()
    assert_geometry(candidate)
    old={s.id for s in snapshot.spaces if s.target_area_m2 is not None}
    assert old=={s.id for s in candidate.spaces if s.target_area_m2 is not None}
    living=next(r for r in candidate.building_program.floors[0].rooms if r.name=='Living')
    assert living.target_area_m2==22 and living.area_basis=='user_supplied'


@pytest.mark.parametrize('fault',['rooms_too_large','too_many_rooms','no_principal','pool_without_basement','unknown_field','bad_dimension'])
def test_impossible_or_malformed_program_never_mutates_input(fault):
    p=small_program()
    if fault=='rooms_too_large':p['floors'][0]['rooms'][0]['target_area_m2']=1000
    elif fault=='too_many_rooms':p['floors'][0]['rooms'][0]['count']=12;p['floors'][0]['rooms'][1]['count']=12
    elif fault=='no_principal':
        for r in p['floors'][0]['rooms']:r['classification']='support'
    elif fault=='pool_without_basement':p['pool']=dict(water_length_m=8,water_width_m=3)
    elif fault=='unknown_field':p['script']='not executable'
    elif fault=='bad_dimension':p['width_m']=float('nan')
    before=deepcopy(p)
    with pytest.raises((BuildingGenerationError,ValidationError)):
        build_building(new_id(),p)
    assert repr(p)==repr(before)


def test_existing_02_hash_survives_new_optional_program_fields():
    snapshot=build_seed(new_id());raw=snapshot.model_dump(mode='json')
    assert 'building_program' not in raw and 'envelope_polygon' not in raw
    expected=hashlib.sha256(json.dumps({k:v for k,v in raw.items() if k not in {'content_hash','created_at'}},sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    loaded=ProjectSnapshot.model_validate(raw)
    assert loaded.compute_hash()==snapshot.content_hash==expected


def test_small_support_rooms_use_a_narrower_branch_without_changing_explicit_areas():
    program=small_program()
    for r in program['floors'][0]['rooms']:
        r['area_basis']='user_supplied'
        if r['use']=='bathroom':r['target_area_m2']=4
        elif r['use']=='service':r['target_area_m2']=2
    snapshot=build_building(new_id(),program)
    assert_geometry(snapshot)
    assert len([s for s in snapshot.spaces if s.target_area_m2 is not None])==6
    assert Polygon(next(s.polygon for s in snapshot.spaces if s.use=='bathroom')).area==pytest.approx(4)
    assert Polygon(next(s.polygon for s in snapshot.spaces if s.use=='service')).area==pytest.approx(2)


def test_program_basis_tracks_same_name_rooms_on_their_own_floor_after_regeneration_and_removal():
    program=small_program()
    for index,area in enumerate((24,22,20)):
        floor=deepcopy(program['floors'][0])
        floor['label']=f'Floor {index+1}'
        floor['rooms'][0]['target_area_m2']=area
        floor['rooms'][0]['area_basis']='user_supplied' if index==2 else 'demonstration_assumption'
        if index==0:program['floors'][0]=floor
        else:program['floors'].append(floor)
    snapshot=build_building(new_id(),program)
    middle=next(l for l in snapshot.levels if l.name=='upper')
    requests=[dict(name=s.name,use=s.use,target_area_m2=24 if s.name=='Living' else s.target_area_m2)
              for s in snapshot.spaces if s.level_id==middle.id and s.classification=='principal']
    generated=generate_floor(snapshot,'upper',requests)
    assert generated['spaces'] is not None
    assert generated['building_program'].floors[1].rooms[0].area_basis=='user_supplied'
    removed=apply_commands(snapshot,[dict(type='remove_level',level_id=middle.id)])
    assert_geometry(removed)
    assert len(removed.building_program.floors)==2
    assert removed.building_program.floors[1].rooms[0].name=='Living'
    assert removed.building_program.floors[1].rooms[0].target_area_m2==20
    assert removed.building_program.floors[1].rooms[0].area_basis=='user_supplied'


def test_added_floor_over_ground_pool_reserves_dry_space_and_keeps_one_pool():
    program=complex_program()
    program['floors']=[program['basement']]
    program.pop('basement')
    program['pool']['level']='ground'
    program['roof_terrace_area_m2']=0
    snapshot=build_building(new_id(),program)
    added=apply_commands(snapshot,[dict(type='add_level')])
    assert_geometry(added)
    assert added.pool==snapshot.pool
    assert sum(s.use=='pool_hall' for s in added.spaces)==1
    assert sum(s.use=='flexible' for s in added.spaces)==1
    assert len(added.building_program.floors)==2
    assert not any(r.use=='pool_hall' for r in added.building_program.floors[1].rooms)
    assert any('dry flexible room' in a.rationale for a in added.assumptions)
