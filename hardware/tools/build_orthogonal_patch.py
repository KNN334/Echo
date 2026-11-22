"""Reconstruct the published 88-channel topology and editable electrode masks.

Planning uses only the Python standard library. Building uses KiCad 10's Python.
The generated layer allocation, fanout and interface are explicitly engineering
choices; they are not represented as the authors' unpublished CAD files.
"""

import argparse
import csv
import json
import math
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'hardware/kicad/orthogonal88'
SIDE = .22  # Assumed contact within the simulated 0.3 mm piezo width; CAD absent.
WIDTH = .03
CLEARANCE = .03
NAMESPACE = uuid.UUID('bbfa8488-2026-5122-8899-012345678901')


def uid(name):
    return str(uuid.uuid5(NAMESPACE, name))


def rotate(u, v):
    return [round((u-v)/math.sqrt(2), 6), round((u+v)/math.sqrt(2), 6)]


def topology():
    channels = []
    # Four routing layers with 13 arm channels and 9 independent center cells each.
    assignments = [('U_NEG', 0, 0, 0), ('V_POS', 1, 0, 1),
                   ('U_POS', 2, 1, 1), ('V_NEG', 3, 1, 0)]
    for arm, layer, qx, qy in assignments:
        group = []
        for k in range(13):
            axis = (-6.2 + k*.4) if arm.endswith('NEG') else (1.4+k*.4)
            coords = [(axis, -1+j*.4) if arm.startswith('U') else (-1+j*.4, axis)
                      for j in range(6)]
            group.append({'name': f'{arm}_{k+1:02}', 'kind': 'arm', 'arm': arm,
                          'arm_index': k+1, 'uv': coords,
                          'sites': [rotate(*p) for p in coords]})
        # Interleave center contacts across layers to leave escape channels.
        # This is an engineering allocation, not a recovered photograph pin map.
        for row in range(qy,6,2):
            for col in range(qx,6,2):
                uv = (-1+col*.4, -1+row*.4)
                group.append({'name': f'C_R{row+1}C{col+1}', 'kind': 'center',
                              'row': row+1, 'column': col+1, 'uv': [uv],
                              'sites': [rotate(*uv)]})
        # Spatial ordering is our fanout choice, not a recovered paper pin order.
        group.sort(key=lambda c: (sum(p[0] for p in c['sites'])/len(c['sites']), c['name']))
        for c in group:
            c['layer'] = layer+1
            c['contact_mm'] = SIDE
            channels.append(c)
    assert len(channels)==88
    assert sum(len(c['sites']) for c in channels)==348
    return channels


def route_layer(channels):
    """Analytic, monotone fanout with two oblique output banks.

    Each mask contains only one arm, so routing perpendicular to that arm
    leaves the other three arms available on the other masks. Center contacts
    use staggered escape lanes. Pin order follows the resulting lane order.
    """
    arm=next(c['arm'] for c in channels if c['kind']=='arm')
    swap=arm.startswith('V')
    sign=1 if arm.endswith('NEG') else -1
    def local(uv):return (uv[1],uv[0]) if swap else tuple(uv)
    def world(a,b):return rotate(b,a) if swap else rotate(a,b)
    routes=[]
    for c in channels:
        pts=[local(p) for p in c['uv']]
        a,b=min(pts,key=lambda p:p[1])
        lane=a
        if c['kind']=='center':
            rank=round((b+1)/.4)//2
            lane=a+sign*[.16,.24,.6][rank]
        c['escape_lane']=lane
        routes.append((lane,c,(a,b)))
    routes.sort(key=lambda item:item[0])
    paths={}
    for i,(lane,c,(a,b)) in enumerate(routes):
        output=-4.2+.4*i+(.1 if c['layer'] in (3,4) else -.1)
        c['terminal']=4*i+c['layer']
        c['tail']=world(output,-12.5)
        c['tail_angle']=45 if swap else -45
        c['tail_corners']=[world(output+x,-12.5+y) for x,y in [(-.06,-.6),(.06,-.6),(.06,.6),(-.06,.6)]]
        pts=[world(a,b)]
        if c['kind']=='center':pts.extend([world(a,b-.2),world(lane,b-.2)])
        pts.extend([world(lane,-6.6),world(output,-11.5),c['tail']])
        paths[c['name']]=list(reversed(pts))
    return paths


def plan():
    OUT.mkdir(parents=True,exist_ok=True)
    channels=topology()
    for layer in range(1,5):
        group=[c for c in channels if c['layer']==layer]
        paths=route_layer(group)
        for c in group:c['route']=paths[c['name']]
        print('Routed electrode layer',layer,'channels',len(group),flush=True)
    plan={'paper':{'pitch_mm':.4,'channels':88,'arm_channels':52,
                   'center_channels':36,'physical_subelements':348,'logical_elements_per_axis':32},
          'reconstruction':{'pad_side_mm':SIDE,'trace_width_mm':WIDTH,'clearance_mm':CLEARANCE,
                            'terminal_pitch_per_layer_mm':.4,'terminal_pad_mm':[.12,1.2],
                            'transducer_outline_side_mm':.3,
                            'routing_assignment':'13 arm plus 9 interleaved center channels per layer; two oblique tail banks; engineering choice',
                            'paper_original_CAD_available':False},'channels':channels}
    (OUT/'geometry.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    with (OUT/'channel_map.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['channel','mask_layer','interface_pad','subelement_count','center_row','center_column'])
        for c in channels:w.writerow([c['name'],c['layer'],c['terminal'],len(c['sites']),c.get('row',''),c.get('column','')])
    u,v=[],[]
    for arm,target in [('U_NEG',u),('U_POS',u),('V_NEG',v),('V_POS',v)]:
        group=sorted([c for c in channels if c.get('arm')==arm],key=lambda c:c['arm_index'])
        vals=[[c['name']] for c in group]
        target.extend(vals)
    for col in range(1,7):u.insert(13+col-1,[f'C_R{r}C{col}' for r in range(1,7)])
    for row in range(1,7):v.insert(13+row-1,[f'C_R{row}C{c}' for c in range(1,7)])
    assert len(u)==len(v)==32
    (OUT/'logical_axis_groups.json').write_text(json.dumps({
        'note':'Center groups are coordinated acquisition groups, not permanent electrical shorts.',
        'U_32_elements':u,'V_32_elements':v},indent=2),encoding='utf-8')


def schematic(channels):
    root=uid('root')
    for c in channels:c['schematic_subelements']=[]
    # 348 passive two-terminal piezo subelements plus 88 signal and two return contacts.
    def libsym(kind,qualified=False):
        ident=('OrthogonalPatch:' if qualified else '')+kind
        if kind=='Piezo':
            pins='''(pin passive line (at -5.08 0 0) (length 2.54)
              (name "SIG" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))
              (pin passive line (at 5.08 0 180) (length 2.54)
              (name "RETURN" (effects (font (size 1 1)))) (number "2" (effects (font (size 1 1)))))'''
            drawing='''(polyline (pts (xy -1.27 2.54) (xy -1.27 -2.54)) (stroke (width .254) (type default)) (fill (type none)))
              (polyline (pts (xy 1.27 2.54) (xy 1.27 -2.54)) (stroke (width .254) (type default)) (fill (type none)))
              (polyline (pts (xy -2.54 0) (xy -1.27 0)) (stroke (width .254) (type default)) (fill (type none)))
              (polyline (pts (xy 1.27 0) (xy 2.54 0)) (stroke (width .254) (type default)) (fill (type none)))'''
            ref='Y'
        else:
            pins='''(pin passive line (at -5.08 0 0) (length 2.54)
              (name "CONTACT" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))'''
            drawing='''(rectangle (start -2.54 1.27) (end 0 -1.27)
              (stroke (width .254) (type default)) (fill (type background)))''';ref='J'
        return f'''(symbol "{ident}" (pin_names (offset 1.016) (hide yes))
          (exclude_from_sim no) (in_bom yes) (on_board no)
          (property "Reference" "{ref}" (at 0 5.08 0) (effects (font (size 1.27 1.27))))
          (property "Value" "{kind}" (at 0 -5.08 0) (effects (font (size 1.27 1.27))))
          (symbol "{kind}_0_1" {drawing}) (symbol "{kind}_1_1" {pins}))'''
    lib=' '.join(libsym(k,True) for k in ['Piezo','Port'])
    (OUT/'OrthogonalPatch.kicad_sym').write_text('(kicad_symbol_lib (version 20250114) (generator "kicad_symbol_editor") '
        +' '.join(libsym(k) for k in ['Piezo','Port'])+')\n',encoding='utf-8')
    def header(sheet,title):
        return [f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid "{sheet}")
          (paper "A3") (title_block (title "{title}") (date "2026-11-22")
          (comment 1 "Published topology reconstruction; piezo properties unspecified")) (lib_symbols {lib})''']
    def symbol(parts,kind,ref,x,y,path):
        parts.append(f'''(symbol (lib_id "OrthogonalPatch:{kind}") (at {x:g} {y:g} 0) (unit 1)
          (exclude_from_sim no) (in_bom yes) (on_board no) (dnp no) (uuid "{uid(ref)}")
          (property "Reference" "{ref}" (at {x:g} {y-5.08:g} 0) (effects (font (size 1.016 1.016))))
          (property "Value" "{kind}" (at {x:g} {y+5.08:g} 0) (effects (font (size 1.016 1.016)) (hide yes)))
          (pin "1" (uuid "{uid(ref+'p1')}"))'''
          +(f'(pin "2" (uuid "{uid(ref+"p2")}"))' if kind=='Piezo' else '')
          +f'''(instances (project "orthogonal88" (path "{path}" (reference "{ref}") (unit 1)))))''')
    def label(parts,name,x,y,key,left=False):
        parts.append(f'''(global_label "{name}" (shape passive) (at {x:g} {y:g} {180 if left else 0})
          (effects (font (size .762 .762)) (justify {'right' if left else 'left'})) (uuid "{uid(key)}")
          (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x:g} {y:g} 0)
            (effects (font (size 1 1)) (hide yes))))''')
    main=header(root,'Orthogonal patch / 88 physical channels')
    for layer in range(1,5):
        group=[c for c in channels if c['layer']==layer]
        for j,c in enumerate(group):
            x=40.64+(layer-1)*95.25;y=30.48+j*10.16
            symbol(main,'Port',f'J{c["terminal"]:03}',x,y,f'/{root}')
            label(main,c['name'],x-5.08,y,'port'+c['name'],True)
    for n in [89,90]:
        x=63.5+(n-89)*76.2;y=264.16
        symbol(main,'Port',f'J{n:03}',x,y,f'/{root}');label(main,'RETURN',x-5.08,y,'ret'+str(n),True)
    yref=0
    for armnum,arm in enumerate(['U_NEG','U_POS','V_NEG','V_POS','CENTER']):
        sid=uid('sheet_'+arm)
        group=([c for c in channels if c['kind']=='center'] if arm=='CENTER'
               else sorted([c for c in channels if c.get('arm')==arm],key=lambda c:c['arm_index']))
        p=header(sid,arm+' / independent physical piezo subelements')
        for i,c in enumerate(group):
            for sub in range(len(c['sites'])):
                if arm=='CENTER':x=33.02+(i%6)*58.42;y=43.18+(i//6)*33.02
                else:x=27.94+i*27.94;y=43.18+sub*30.48
                yref+=1;ref=f'Y{yref:03}'
                symbol(p,'Piezo',ref,x,y,f'/{root}/{sid}')
                label(p,c['name'],x-5.08,y,ref+'sig',True)
                label(p,'RETURN',x+5.08,y,ref+'ret')
                c.setdefault('schematic_subelements',[]).append(ref)
        p.append('(embedded_fonts no))')
        (OUT/(arm+'.kicad_sch')).write_text('\n'.join(p),encoding='utf-8')
        sx=330.2;sy=243.84+armnum*7.62
        main.append(f'''(sheet (at {sx:g} {sy:g}) (size 60.96 5.08)
          (stroke (width .1524) (type default)) (fill (color 0 0 0 0)) (uuid "{sid}")
          (property "Sheetname" "{arm}" (at {sx:g} {sy-1.27:g} 0) (effects (font (size .762 .762)) (justify left bottom)))
          (property "Sheetfile" "{arm}.kicad_sch" (at {sx:g} {sy+6.35:g} 0) (effects (font (size .762 .762)) (hide yes)))
          (instances (project "orthogonal88" (path "/{root}" (page "{armnum+2}")))))''')
    main.append('(embedded_fonts no))')
    (OUT/'orthogonal88.kicad_sch').write_text('\n'.join(main),encoding='utf-8')
    (OUT/'sym-lib-table').write_text('''(sym_lib_table (version 7)
      (lib (name "OrthogonalPatch") (type "KiCad") (uri "${KIPRJMOD}/OrthogonalPatch.kicad_sym") (options "") (descr "Source-grounded topology")))\n''',encoding='utf-8')
    assert yref==348


def build():
    import pcbnew as k
    from copy import deepcopy
    data=json.loads((OUT/'geometry.json').read_text(encoding='utf-8'))
    channels=data['channels']
    center=(100,100)
    def vec(p):return k.VECTOR2I(k.FromMM(p[0]+center[0]),k.FromMM(p[1]+center[1]))
    def makeboard(name,multi=False):
        b=k.BOARD();b.SetCopperLayerCount(6 if multi else 2)
        b.GetTitleBlock().SetTitle(name+' / RECONSTRUCTION, NOT FABRICATION RELEASE')
        b.GetTitleBlock().SetDate('2026-11-22')
        corners=[(-14,-18),(14,-18),(14,14),(-14,14)]
        for a,z in zip(corners,corners[1:]+corners[:1]):
            s=k.PCB_SHAPE(b);s.SetShape(k.SHAPE_T_SEGMENT);s.SetStart(vec(a));s.SetEnd(vec(z))
            s.SetWidth(k.FromMM(.05));s.SetLayer(k.Edge_Cuts);b.Add(s)
        return b
    def net(b,name):
        n=k.NETINFO_ITEM(b,name);b.Add(n);return n
    def track(b,pts,n,layer,width=WIDTH):
        for a,z in zip(pts,pts[1:]):
            if math.dist(a,z)<1e-7:continue
            t=k.PCB_TRACK(b);t.SetStart(vec(a));t.SetEnd(vec(z));t.SetWidth(k.FromMM(width))
            t.SetLayer(layer);t.SetNet(n);b.Add(t)
    def copper_zone(b,points,n,layer):
        z=k.ZONE(b);z.SetLayer(layer);z.SetNet(n);z.SetLocalClearance(k.FromMM(CLEARANCE))
        z.SetMinThickness(k.FromMM(.005));z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_NEVER)
        z.Outline().NewOutline()
        for pt in points:
            v=vec(pt);z.Outline().Append(v.x,v.y)
        b.Add(z);return z
    def square(p,side=SIDE):
        h=side/2
        offsets=[rotate(-h,-h),rotate(h,-h),rotate(h,h),rotate(-h,h)]
        return [[p[0]+x,p[1]+y] for x,y in offsets]
    def rect(p,w,h):return [[p[0]+x,p[1]+y] for x,y in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]]
    def note(b,s,p,layer=k.Cmts_User,size=.8):
        t=k.PCB_TEXT(b);t.SetText(s);t.SetPosition(vec(p));t.SetTextSize(k.VECTOR2I(k.FromMM(size),k.FromMM(size)))
        t.SetTextThickness(k.FromMM(.1));t.SetLayer(layer);b.Add(t)
    def pad(b,fp,p,num,n,size=(SIDE,SIDE),angle=45):
        t=k.PAD(fp);t.SetNumber(str(num));t.SetAttribute(k.PAD_ATTRIB_CONN);t.SetShape(k.PAD_SHAPE_RECT)
        t.SetSize(k.VECTOR2I(k.FromMM(size[0]),k.FromMM(size[1])));t.SetPosition(vec(p))
        t.SetOrientation(k.EDA_ANGLE(angle,k.DEGREES_T));ls=k.LSET();ls.AddLayer(k.F_Cu);t.SetLayerSet(ls)
        t.SetNet(n);fp.Add(t)
    def save(b,path):
        print('Saving',path.name,flush=True)
        b.BuildConnectivity()
        k.SaveBoard(str(path),b)
        # CLI performs zone fill with the project's explicit rules loaded.
    main=makeboard('Orthogonal 88 / six electrode masks',True)
    layers=[k.F_Cu,k.In1_Cu,k.In2_Cu,k.In3_Cu]
    # Keep standard layer identifiers for export; user-visible names record semantics.
    for layer,label in zip(layers,['LM_E1','LM_E2','LM_E3','LM_E4']):main.SetLayerName(layer,label)
    main.SetLayerName(k.In4_Cu,'LM_SHIELD');main.SetLayerName(k.B_Cu,'LM_RETURN')
    maskdir=OUT/'masks';maskdir.mkdir(exist_ok=True)
    for layer in range(1,5):
        b=makeboard('Electrode mask E'+str(layer))
        for c in [c for c in channels if c['layer']==layer]:
            n=net(b,c['name']);nm=net(main,c['name']);cl=layers[layer-1]
            f=k.FOOTPRINT(b);f.SetReference('P'+str(c['terminal']));f.SetValue(c['name'])
            f.SetAttributes(k.FP_SMD);f.Reference().SetVisible(False);f.Value().SetVisible(False);b.Add(f)
            for p in c['sites']:
                pad(b,f,p,1,n);copper_zone(main,square(p),nm,cl)
            pad(b,f,c['tail'],2,n,(.12,1.2),c['tail_angle'])
            copper_zone(main,c['tail_corners'],nm,cl)
            if len(c['sites'])>1:
                track(b,c['sites'],n,k.F_Cu);track(main,c['sites'],nm,cl)
            track(b,c['route'],n,k.F_Cu);track(main,c['route'],nm,cl)
            note(main,f'{c["terminal"]:02}',[c['tail'][0],c['tail'][1]-.7],k.User_1,.16)
        note(b,'E'+str(layer)+' / 22 channels / engineering fanout',(0,10.5))
        note(b,'Use F.Cu as one liquid-metal mask; no conventional vias',(0,11.8),size=.65)
        save(b,maskdir/f'E{layer}.kicad_pcb')
    g=net(main,'RETURN')
    for layer in [k.In4_Cu,k.B_Cu]:copper_zone(main,rect((0,-2),21,27),g,layer)
    for name in ['RETURN','SHIELD']:
        b=makeboard('Common '+name+' mask');gn=net(b,'RETURN')
        copper_zone(b,rect((0,-2),21,27),gn,k.F_Cu)
        f=k.FOOTPRINT(b);f.SetReference('G1');f.SetValue(name+'_BOND');f.SetAttributes(k.FP_SMD)
        f.Reference().SetVisible(False);f.Value().SetVisible(False);b.Add(f)
        pad(b,f,(0,-14.5),1,gn,(.8,1.2),0)
        note(b,name+' / outline assumed, not photo metrology',(0,12),size=.65)
        save(b,maskdir/(name+'.kicad_pcb'))
    # User.2 shows the transducer footprint independently of active mask visibility.
    for c in channels:
        for p in c['sites']:
            pts=square(p,.3)
            for a,z in zip(pts,pts[1:]+pts[:1]):
                s=k.PCB_SHAPE(main);s.SetShape(k.SHAPE_T_SEGMENT);s.SetStart(vec(a));s.SetEnd(vec(z))
                s.SetLayer(k.User_2);s.SetWidth(k.FromMM(.012));main.Add(s)
    note(main,'ORTHOGONAL 88 / 348 SUBELEMENTS',(0,9.4),size=.9)
    note(main,'Pitch 0.4 mm; four arms x 13 + center 6 x 6',(0,10.7),size=.65)
    note(main,'Four signal masks + RETURN + SHIELD',(0,11.8),size=.65)
    save(main,OUT/'orthogonal88.kicad_pcb')
    pro={'meta':{'filename':'orthogonal88.kicad_pro','version':3},
         'board':{'design_settings':{'rules':{'min_clearance':CLEARANCE,'min_track_width':WIDTH,
            'min_copper_edge_clearance':.2},'track_widths':[0,WIDTH]}},
         'net_settings':{'meta':{'version':3},'classes':[{'name':'Default','clearance':CLEARANCE,
            'track_width':WIDTH,'via_diameter':.15,'via_drill':.07,
            'microvia_diameter':.1,'microvia_drill':.05}],
            'netclass_patterns':[],'netclass_assignments':None,'net_colors':None}}
    (OUT/'orthogonal88.kicad_pro').write_text(json.dumps(pro,indent=2),encoding='utf-8')
    for name in ['E1','E2','E3','E4','RETURN','SHIELD']:
        p=deepcopy(pro);p['meta']['filename']=name+'.kicad_pro'
        (maskdir/(name+'.kicad_pro')).write_text(json.dumps(p,indent=2),encoding='utf-8')
    schematic(channels)
    (OUT/'geometry.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print('Built 6-layer mask model, 6 single-mask boards and 348-piezo schematic')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['plan','build'])
    args=parser.parse_args()
    plan() if args.action=='plan' else build()
