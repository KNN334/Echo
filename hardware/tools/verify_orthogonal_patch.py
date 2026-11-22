"""Audit the exported KiCad netlist and electrode access geometry independently.

Run after build and KiCad CLI ERC/DRC + XML netlist exports. Standard library only.
This checks electrical topology and nominal 2D geometry, not fabrication validity.
"""

from collections import Counter
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


OUT = Path(__file__).resolve().parents[2] / 'hardware/kicad/orthogonal88'


def point_segment(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    t = max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.dist(p, (a[0]+t*dx, a[1]+t*dy))


def cross(a, b, p):
    return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])


def segment_distance(a, b, c, d):
    if cross(a,b,c)*cross(a,b,d)<=0 and cross(c,d,a)*cross(c,d,b)<=0:
        if max(min(a[0],b[0]),min(c[0],d[0]))<=min(max(a[0],b[0]),max(c[0],d[0]))+1e-10 and max(min(a[1],b[1]),min(c[1],d[1]))<=min(max(a[1],b[1]),max(c[1],d[1]))+1e-10:
            return 0
    return min(point_segment(a,c,d),point_segment(b,c,d),point_segment(c,a,b),point_segment(d,a,b))


def rectangle_distance(a, b, center, side):
    x,y=center;h=side/2
    corners=[(x-h,y-h),(x+h,y-h),(x+h,y+h),(x-h,y+h)]
    if any(abs(p[0]-x)<=h and abs(p[1]-y)<=h for p in [a,b]):return 0
    return min(segment_distance(a,b,c,d) for c,d in zip(corners,corners[1:]+corners[:1]))


def audit():
    data=json.loads((OUT/'geometry.json').read_text(encoding='utf-8'))
    channels=data['channels']
    assert len(channels)==88
    assert Counter(c['kind'] for c in channels)=={'arm':52,'center':36}
    assert Counter(c['layer'] for c in channels)=={1:22,2:22,3:22,4:22}
    assert {c['terminal'] for c in channels}==set(range(1,89))
    assert sum(len(c['sites']) for c in channels)==348
    assert all(len(c['sites'])==(6 if c['kind']=='arm' else 1) for c in channels)
    root=ET.parse(OUT/'exports/orthogonal88.xml').getroot()
    components={c.attrib['ref'] for c in root.findall('components/comp')}
    piezos={f'Y{i:03}' for i in range(1,349)}
    assert components==piezos|{f'J{i:03}' for i in range(1,91)}
    nets={n.attrib['name']:{(p.attrib['ref'],p.attrib['pin']) for p in n.findall('node')} for n in root.findall('nets/net')}
    assert set(nets)=={c['name'] for c in channels}|{'RETURN'}
    for c in channels:
        expected={(y,'1') for y in c['schematic_subelements']}|{(f'J{c["terminal"]:03}','1')}
        assert nets[c['name']]==expected, c['name']
    assert nets['RETURN']=={(y,'2') for y in piezos}|{('J089','1'),('J090','1')}
    groups=json.loads((OUT/'logical_axis_groups.json').read_text(encoding='utf-8'))
    for key in ['U_32_elements','V_32_elements']:
        assert len(groups[key])==32
        assert Counter(len(g) for g in groups[key])=={1:26,6:6}
        center=[name for g in groups[key] for name in g if name.startswith('C_')]
        assert len(center)==len(set(center))==36
    # Reserve every foreign contact's opening across ALL four masks, including
    # sites assigned to other layers. This does not model access depth/materials.
    def inverse(p):return ((p[0]+p[1])/math.sqrt(2),(p[1]-p[0])/math.sqrt(2))
    side=data['reconstruction']['pad_side_mm'];width=data['reconstruction']['trace_width_mm']
    clearance=data['reconstruction']['clearance_mm'];minimum=float('inf')
    for c in channels:
        paths=[list(map(inverse,c['route']))]
        if c['kind']=='arm':paths.append(c['uv'])
        for other in channels:
            if other['name']==c['name']:continue
            for center in other['uv']:
                for path in paths:
                    for a,b in zip(path,path[1:]):
                        d=rectangle_distance(a,b,center,side)-width/2
                        minimum=min(minimum,d)
                        assert d>=clearance-2e-6,(c['name'],other['name'],d)
    reports={}
    for name in ['E1','E2','E3','E4','RETURN','SHIELD','main']:
        d=json.loads((OUT/f'exports/{name}_drc.json').read_text(encoding='utf-8'))
        assert not d['unconnected_items']
        counts=Counter(v['type'] for v in d['violations'])
        if name=='main':
            assert set(counts)<= {'isolated_copper'}
            assert all(v['severity']=='warning' for v in d['violations'])
        else:assert not counts,(name,counts)
        reports[name]={'errors':sum(v['severity']=='error' for v in d['violations']),
                       'warnings':sum(v['severity']=='warning' for v in d['violations']),
                       'unconnected':len(d['unconnected_items']),'violation_types':dict(counts)}
    erc=json.loads((OUT/'exports/erc.json').read_text(encoding='utf-8'))
    assert not [v for s in erc['sheets'] for v in s['violations']]
    result={'physical_channels':88,'subelements':348,'schematic_components':438,'electrical_nets':89,
            'common_return_nodes':350,'logical_elements_per_axis':32,'erc_violations':0,
            'minimum_track_to_foreign_access_contact_clearance_mm':round(minimum,6),
            'drc':reports,'schematic_pcb_parity':'Not applicable: multilayer mask abstraction; not a conventional PCB assembly.',
            'fabrication_validation':False,'vertical_access_depths_and_material_stack_verified':False}
    (OUT/'exports/validation_summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':audit()
