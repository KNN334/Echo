"""Rebuild the explicit teaching geometry with the Python shipped with KiCad 10.

Run from the repository root. Existing lesson files are replaced; keep exercises
in a separate project. No paper-derived fabrication dimensions are assumed.
"""

import json
import uuid
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "hardware/kicad/electrode8"
OUT.mkdir(parents=True, exist_ok=True)
LIB = OUT / "PatchLesson.pretty"
LIB.mkdir(exist_ok=True)
PROJECT = "electrode8"
NAMESPACE = uuid.UUID("a435f723-0b93-4d86-8dd6-202611220001")


def uid(name):
    return str(uuid.uuid5(NAMESPACE, name))


def xy(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def text(board, value, x, y, size=0.75, layer=pcbnew.F_SilkS):
    item = pcbnew.PCB_TEXT(board)
    item.SetText(value)
    item.SetPosition(xy(x, y))
    item.SetTextSize(xy(size, size))
    item.SetTextThickness(pcbnew.FromMM(0.12))
    item.SetLayer(layer)
    board.Add(item)


def footprint(name, reference, coords, size):
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID("PatchLesson", name))
    fp.SetReference(reference)
    fp.SetValue(name)
    fp.SetAttributes(pcbnew.FP_SMD)
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    for i, (x, y) in enumerate(coords, 1):
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(i))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        pad.SetSize(xy(*size))
        pad.SetPosition(xy(x, y))
        layers = pcbnew.LSET()
        layers.AddLayer(pcbnew.F_Cu)
        layers.AddLayer(pcbnew.F_Mask)
        pad.SetLayerSet(layers)
        pad.SetLocalSolderMaskMargin(pcbnew.FromMM(0.05))
        fp.Add(pad)
    # Simple explicit courtyard around the contact row.
    left = min(x for x, _ in coords) - size[0] / 2 - 0.25
    right = max(x for x, _ in coords) + size[0] / 2 + 0.25
    top, bottom = -size[1] / 2 - 0.25, size[1] / 2 + 0.25
    points = [(left, top), (right, top), (right, bottom), (left, bottom)]
    for a, b in zip(points, points[1:] + points[:1]):
        edge = pcbnew.PCB_SHAPE(fp)
        edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
        edge.SetStart(xy(*a))
        edge.SetEnd(xy(*b))
        edge.SetWidth(pcbnew.FromMM(0.05))
        edge.SetLayer(pcbnew.F_CrtYd)
        fp.Add(edge)
    pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(LIB), fp)
    return fp


board = pcbnew.BOARD()
nets = {}
for name in [f"CH{i}" for i in range(1, 9)] + ["RET"]:
    net = pcbnew.NETINFO_ITEM(board, "/" + name)
    board.Add(net)
    nets[name] = net

contacts = [(-4.2 + 1.2 * i, 0) for i in range(8)]
connector = [(-8 + 2 * i, 0) for i in range(9)]
specs = [
    ("Array_8_P1.20", "J2", contacts, (0.8, 3), (100, 84)),
    ("Tail_9_P2.00", "J1", connector, (1.2, 3), (100, 100)),
    ("Return_Contact", "J3", [(0, 0)], (1.5, 3), (109.5, 84)),
]
for name, ref, coords, size, pos in specs:
    fp = footprint(name, ref, coords, size)
    board.Add(fp)
    fp.SetPosition(xy(*pos))
    fp.SetValue(f"Contact_{len(coords)}")
    # Link PCB footprint to the embedded schematic instance.
    fp.SetPath(pcbnew.KIID_PATH(f"/{uid('sheet')}/{uid(ref)}"))
    for pad in fp.Pads():
        n = int(pad.GetNumber())
        netname = "RET" if ref == "J3" or n == 9 else f"CH{n}"
        pad.SetNet(nets[netname])

paths = []
for i in range(8):
    startx = round(95.8 + 1.2 * i, 4)
    endx = 92 + 2 * i
    pts = [(startx, 84), (startx, 88), (endx, 88 + abs(startx - endx)), (endx, 100)]
    paths.append((f"CH{i + 1}", pts))
paths.append(("RET", [(109.5, 84), (109.5, 92), (108, 93.5), (108, 100)]))
for name, pts in paths:
    for a, b in zip(pts, pts[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(xy(*a))
        track.SetEnd(xy(*b))
        track.SetWidth(pcbnew.FromMM(0.25))
        track.SetLayer(pcbnew.F_Cu)
        track.SetNet(nets[name])
        board.Add(track)

corners = [(88, 77), (112, 77), (112, 107), (88, 107)]
for a, b in zip(corners, corners[1:] + corners[:1]):
    edge = pcbnew.PCB_SHAPE(board)
    edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
    edge.SetStart(xy(*a))
    edge.SetEnd(xy(*b))
    edge.SetWidth(pcbnew.FromMM(0.05))
    edge.SetLayer(pcbnew.Edge_Cuts)
    board.Add(edge)

text(board, "ELECTRODE8 LESSON", 100, 79, 0.9)
for i in range(8):
    text(board, str(i + 1), 95.8 + 1.2 * i, 81.5, 0.8)
for i in range(9):
    text(board, str(i + 1), 92 + 2 * i, 103.2, 0.8)
text(board, "RET", 109.5, 81.5, 0.8)
text(board, "COPPER ROUTING PRACTICE", 100, 95.5, 0.8)
text(board, "24 x 30 mm / F.Cu", 100, 105.5, 0.8)
title = board.GetTitleBlock()
title.SetTitle("8-channel contact and routing lesson")
title.SetDate("2026-11-22")
title.SetComment(0, "Teaching dimensions; not a paper reproduction or a transducer stack")
pcbnew.SaveBoard(str(OUT / f"{PROJECT}.kicad_pcb"), board)

template = Path(pcbnew.__file__).parents[3] / "share/kicad/template/kicad.kicad_pro"
# The normal Windows install keeps bin/Lib/site-packages/pcbnew.py.
if not template.exists():
    template = Path(pcbnew.__file__).parents[3].parent / "share/kicad/template/kicad.kicad_pro"
pro = json.loads(template.read_text(encoding="utf-8")) if template.exists() else {}
pro["meta"] = {"filename": "electrode8.kicad_pro", "version": 3}
pro.setdefault("board", {}).setdefault("design_settings", {}).setdefault("rules", {}).update({
    "min_clearance": 0.2,
    "min_track_width": 0.25,
    "min_copper_edge_clearance": 0.5,
})
pro["board"]["design_settings"]["track_widths"] = [0, 0.25]
pro["net_settings"] = {
    "classes": [{"name": "Default", "description": "Lesson only", "clearance": 0.2,
                 "track_width": 0.25, "via_diameter": 0.8, "via_drill": 0.4,
                 "microvia_diameter": 0.3, "microvia_drill": 0.1,
                 "diff_pair_width": 0.25, "diff_pair_gap": 0.2, "diff_pair_via_gap": 0.25,
                 "bus_width": 12, "wire_width": 6, "line_style": 0,
                 "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}],
    "meta": {"version": 3}, "netclass_assignments": None,
    "netclass_patterns": [], "net_colors": None,
}
(OUT / "electrode8.kicad_pro").write_text(json.dumps(pro, indent=2), encoding="utf-8")

# Self-contained passive connector symbols: no external library resolution needed.
def libsymbol(n, qualified=False):
    name = f"Contact_{n}"
    ident = f"PatchLesson:{name}" if qualified else name
    pins = []
    for i in range(n):
        pins.append(f'''(pin passive line (at 5.08 {-2.54*i:g} 180) (length 2.54)
          (name "{i+1}" (effects (font (size 1 1))))
          (number "{i+1}" (effects (font (size 1 1)))))''')
    return f'''(symbol "{ident}" (pin_names (offset 1.016) (hide yes))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "J" (at 0 5.08 0) (effects (font (size 1.27 1.27))))
      (property "Value" "{name}" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
      (symbol "{name}_0_1"
        (rectangle (start -2.54 2.54) (end 2.54 {-2.54*n:g})
          (stroke (width 0.254) (type default)) (fill (type background))))
      (symbol "{name}_1_1" {' '.join(pins)}))'''


(OUT / "PatchLesson.kicad_sym").write_text(
    '(kicad_symbol_lib (version 20250114) (generator "kicad_symbol_editor") '
    + "\n".join(libsymbol(n) for n in [1, 8, 9]) + ")\n", encoding="utf-8")
parts = [f'''(kicad_sch (version 20250114) (generator "eeschema")
  (uuid "{uid('sheet')}") (paper "A4")
  (title_block (title "8-channel contact routing lesson") (date "2026-11-22")
    (comment 1 "Teaching dimensions. RET is a return contact, not protective earth."))
  (lib_symbols {' '.join(libsymbol(n, True) for n in [1, 8, 9])})''']
for ref, n, x, y, fpname in [
    ("J2", 8, 63.5, 50.8, "Array_8_P1.20"),
    ("J1", 9, 139.7, 50.8, "Tail_9_P2.00"),
    ("J3", 1, 63.5, 95.25, "Return_Contact"),
]:
    instances = f'''(instances (project "electrode8"
      (path "/{uid('sheet')}" (reference "{ref}") (unit 1))))'''
    pins = " ".join(f'(pin "{i}" (uuid "{uid(ref+str(i))}"))' for i in range(1, n+1))
    parts.append(f'''(symbol (lib_id "PatchLesson:Contact_{n}")
      (at {x} {y} 0) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (dnp no) (uuid "{uid(ref)}")
      (property "Reference" "{ref}" (at {x} {y-7.62:g} 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Contact_{n}" (at {x} {y-5.08:g} 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "PatchLesson:{fpname}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))
      {pins} {instances})''')
    for i in range(n):
        name = "RET" if ref == "J3" or i == 8 else f"CH{i+1}"
        yy = y + 2.54*i
        parts.append(f'''(wire (pts (xy {x+5.08:g} {yy:g}) (xy {x+15.24:g} {yy:g}))
          (stroke (width 0) (type default)) (uuid "{uid('wire'+ref+str(i))}"))''')
        parts.append(f'''(label "{name}" (at {x+15.24:g} {yy:g} 0)
          (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{uid('label'+ref+str(i))}"))''')
parts.append(f'''(text "J2: eight individual contacts\\nJ3: common return contact\\nJ1: nine output contacts\\n\\nNo transmitter, receiver or piezoelectric stack is modelled."
  (at 75 125 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid('note')}"))
  (embedded_fonts no))''')
(OUT / "electrode8.kicad_sch").write_text("\n".join(parts), encoding="utf-8")
(OUT / "fp-lib-table").write_text('''(fp_lib_table (version 7)
  (lib (name "PatchLesson") (type "KiCad") (uri "${KIPRJMOD}/PatchLesson.pretty") (options "") (descr "Teaching contact footprints")))
''', encoding="utf-8")
(OUT / "sym-lib-table").write_text('''(sym_lib_table (version 7)
  (lib (name "PatchLesson") (type "KiCad") (uri "${KIPRJMOD}/PatchLesson.kicad_sym") (options "") (descr "Teaching passive contacts")))
''', encoding="utf-8")

parameters = {
    "purpose": "teaching_only_not_paper_fabrication",
    "board_mm": {"left": 88, "top": 77, "width": 24, "height": 30},
    "array": {"reference": "J2", "center_mm": [100, 84], "count": 8,
              "pitch_mm": 1.2, "pad_mm": [0.8, 3]},
    "tail": {"reference": "J1", "center_mm": [100, 100], "count": 9,
             "pitch_mm": 2.0, "pad_mm": [1.2, 3]},
    "return": {"reference": "J3", "center_mm": [109.5, 84], "pad_mm": [1.5, 3]},
    "track_width_mm": 0.25, "clearance_mm": 0.2,
    "copper_layers_used": ["F.Cu"], "solder_paste_openings": False,
    "net_paths_mm": {name: pts for name, pts in paths},
}
(OUT / "lesson_parameters.json").write_text(json.dumps(parameters, indent=2), encoding="utf-8")
print(f"Created {OUT}: 3 footprints, 18 pads, 9 nets, 27 track segments")
