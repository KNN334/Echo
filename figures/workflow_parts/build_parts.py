"""Build independent method components from code and saved validation examples.

This script never assembles the final workflow, trains a model or evaluates test
images. SVG keeps live text; Qt exports native PDF text and PNG previews.
Requires the project's core dependencies and PyQt5.
"""
from copy import deepcopy
import base64
import hashlib
import html
from io import BytesIO
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from PyQt5.QtCore import QByteArray, QMarginsF, QPointF, QRectF, QSizeF, Qt
from PyQt5.QtGui import (QColor, QFont, QFontDatabase, QFontMetricsF,
                         QGuiApplication, QImage, QPageLayout, QPageSize,
                         QPainter, QPdfWriter)
from PyQt5.QtSvg import QSvgRenderer

PROJECT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))
from src.data.transforms import Transform
from src.geometry.mask_features import mask_features, main_component

NS = 'http://www.w3.org/2000/svg'
XLINK = 'http://www.w3.org/1999/xlink'
ET.register_namespace('', NS)
ET.register_namespace('xlink', XLINK)
INK, TEAL, PEACH = '#20303e', '#238b80', '#feccab'
PALE, LIGHT, GREY = '#eaf5f2', '#f4f5f6', '#65747c'
SIZE_MM = (180, 70)
WIDTH, HEIGHT = [v / 25.4 * 72 for v in SIZE_MM]
FONT, DPI = 'Microsoft YaHei UI', 600
PATIENT = 'patient0008'
RED = '#ce645f'
PALETTES = {
    'A': ('#f7e5d7', '#fffcf8', '#b59c7d'),
    'B': ('#e5edd7', '#fbfdf8', '#8b9e73'),
    'C': ('#e0ebf6', '#f9fcff', '#839db6'),
    'D': ('#faf0c8', '#fffef7', '#b7ad73'),
    'E': ('#eee1f1', '#fdfaff', '#a48cab'),
}


def element(parent, tag, **attrs):
    return ET.SubElement(parent, '{' + NS + '}' + tag,
                         {k.replace('_', '-'): str(v) for k, v in attrs.items()})


class Part:
    def __init__(self, name, title):
        self.name, self.title = name, title
        self.root = ET.Element('{' + NS + '}svg', {
            'width': f'{SIZE_MM[0]}mm', 'height': f'{SIZE_MM[1]}mm', 'viewBox': f'0 0 {WIDTH} {HEIGHT}',
            'version': '1.1', 'role': 'img', 'aria-label': title})
        self.group = self.root
        element(self.root, 'rect', x=0, y=0, width=WIDTH, height=HEIGHT, fill='white')
        self.tint, self.paper, self.edge = PALETTES[name[0]]
        self.rect(6, 19, WIDTH - 12, HEIGHT - 26, self.paper, self.edge, dash='3 2', radius=10)
        tab_width = 18 + sum(8.8 if ord(c) > 255 else 5.0 for c in title)
        self.rect(17, 7, tab_width, 23, self.tint, stroke='none', radius=0)
        self.text(25, 22.5, title, size=8.8, anchor='start', bold=True)
        self.text(WIDTH - 17, 14, 'CAMUS  /  METHOD COMPONENT', size=5.8, anchor='end')

    def text(self, x, y, text, size=6.5, anchor='middle', bold=False):
        item = element(self.group, 'text', x=x, y=y, font_family=FONT, font_size=size,
                       text_anchor=anchor, fill=INK, font_weight='700' if bold else '400')
        item.text = text
        return item

    def rect(self, x, y, w, h, fill=LIGHT, stroke=GREY, dash=None, radius=2):
        attrs = dict(x=x, y=y, width=w, height=h, rx=radius, fill=fill, stroke=stroke, stroke_width=.55)
        if dash:
            attrs['stroke_dasharray'] = dash
        return element(self.group, 'rect', **attrs)

    def box(self, key, x, y, w, h, lines, fill=LIGHT, dash=None, size=6.5):
        before = self.group
        self.group = element(before, 'g', id='n-' + key, data_role='node')
        self.rect(x, y, w, h, fill=fill, dash=dash)
        lines = [lines] if isinstance(lines, str) else lines
        for i, text in enumerate(lines):
            self.text(x + w / 2, y + h / 2 + 2.2 + (i - (len(lines) - 1) / 2) * 9, text, size=size)
        self.group = before

    def path(self, d, color=INK, width=.75, fill='none', dash=None):
        attrs = dict(d=d, fill=fill, stroke=color, stroke_width=width,
                     stroke_linejoin='round', stroke_linecap='round')
        if dash:
            attrs['stroke_dasharray'] = dash
        return element(self.group, 'path', **attrs)

    def line(self, x1, y1, x2, y2, color=INK, width=.75, dash=None):
        return self.path(f'M {x1} {y1} L {x2} {y2}', color, width, dash=dash)

    def arrow(self, key, points, color=TEAL, dash=None):
        before = self.group
        self.group = element(before, 'g', id='e-' + key, data_role='edge')
        self.path('M ' + ' L '.join(f'{x} {y}' for x, y in points), color, 1.05, dash=dash)
        x, y = points[-1]
        px, py = points[-2]
        angle = math.atan2(y - py, x - px)
        a, b = angle + 2.65, angle - 2.65
        self.path(f'M {x} {y} L {x + 3.2 * math.cos(a)} {y + 3.2 * math.sin(a)} '
                  f'L {x + 3.2 * math.cos(b)} {y + 3.2 * math.sin(b)} Z', color, .4, color)
        self.group = before

    def image(self, key, image, x, y, w, h):
        stream = BytesIO()
        image.save(stream, format='PNG')
        # Fit explicitly because some SVG renderers ignore image aspect-ratio hints.
        scale = min(w / image.width, h / image.height)
        iw, ih = image.width * scale, image.height * scale
        x, y = x + (w - iw) / 2, y + (h - ih) / 2
        item = element(self.group, 'image', id='i-' + key, x=x, y=y, width=iw, height=ih,
                       preserveAspectRatio='xMidYMid meet')
        item.set('{' + XLINK + '}href', 'data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode())
        return item

    def circle(self, x, y, r, fill=TEAL):
        element(self.group, 'circle', cx=x, cy=y, r=r, fill=fill, stroke='white', stroke_width=.4)

    def write(self):
        (OUTPUT / 'svg' / (self.name + '.svg')).write_bytes(ET.tostring(self.root, encoding='utf-8', xml_declaration=True))


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def load_examples():
    samples = {}
    for view in ('2CH', '4CH'):
        key = PATIENT + '_' + view
        source = PROJECT / 'data/processed/camus'
        meta = read_json(source / (key + '.json'))
        with np.load(source / (key + '.npz'), allow_pickle=False) as z:
            arrays = {k: z[k].copy() for k in z.files}
        with np.load(PROJECT / 'runs/validation_camus_regularized' / (key + '_pred.npz')) as z:
            prediction = z['masks'].copy()
        transform = meta['audit']['transform']
        tr = Transform(tuple(transform['original_hw']), tuple(transform['crop_xyxy']), tuple(transform['output_hw']))
        ed = meta['phases']['ED']
        original = tr.restore_mask(prediction[ed])
        features = mask_features(original, meta['audit']['spacing_xy_mm'])
        assert arrays['labeled'][ed] and meta['patient_id'] == PATIENT
        samples[view] = dict(meta=meta, arrays=arrays, prediction=prediction,
                             original=original, features=features)
    manifest = read_json(PROJECT / 'data/processed/camus/manifest.json')
    assert {r['split'] for r in manifest['cases'] if r['patient_id'] == PATIENT} == {'val'}
    return samples, manifest


def echo_image(frame, contour=None):
    rgb = np.repeat(frame[..., None], 3, axis=2).copy()
    if contour is not None:
        mask = np.asarray(contour, bool)
        boundary = mask & ~ndimage.binary_erosion(mask)
        rgb[boundary] = [66, 218, 183]
    return Image.fromarray(rgb)


def mask_image(mask, color=(35, 139, 128), white=True):
    rgb = np.full(mask.shape + (3,), 255 if white else 0, dtype=np.uint8)
    rgb[np.asarray(mask, bool)] = color
    return Image.fromarray(rgb)


def geometry(part, sample, x, y, w, h, labels=False, disks=True):
    clean, _ = main_component(sample['original'])
    yy, xx = np.where(clean)
    minxy, maxxy = np.array([xx.min(), yy.min()]), np.array([xx.max(), yy.max()])
    factor = min(w / (maxxy - minxy)[0], h / (maxxy - minxy)[1])
    offset = np.array([x, y]) + (np.array([w, h]) - (maxxy - minxy) * factor) / 2
    mapped = lambda p: (np.asarray(p) - minxy) * factor + offset
    # This raster is the saved prediction's cleaned silhouette, not a fabricated anatomy.
    crop = clean[yy.min():yy.max() + 1, xx.min():xx.max() + 1]
    dest = (maxxy - minxy) * factor
    part.image('clean-contour-' + str(x), mask_image(crop, (221, 241, 235)), *offset, *dest)
    f = sample['features']
    landmarks = f['landmarks_xy']
    apex = np.array(landmarks['apex'])
    base_l, base_r = np.array(landmarks['base_left']), np.array(landmarks['base_right'])
    base = (base_l + base_r) / 2
    spacing = np.array(sample['meta']['audit']['spacing_xy_mm'])
    axis = (base - apex) * spacing
    axis /= np.linalg.norm(axis)
    side = np.array([axis[1], -axis[0]])
    for i, diameter in enumerate(f['diameters_mm'] if disks else []):
        center = apex * spacing + (i + .5) * f['long_axis_mm'] / 20 * axis
        start, stop = (center - diameter / 2 * side) / spacing, (center + diameter / 2 * side) / spacing
        p1, p2 = mapped(start), mapped(stop)
        part.line(*p1, *p2, color=TEAL, width=.45)
    a, b = mapped(apex), mapped(base)
    part.line(*a, *b, color='#c77439', width=1.0)
    for name, point in [('A', apex), ('BL', base_l), ('BR', base_r)]:
        px, py = mapped(point)
        part.circle(px, py, 1.7)
        if labels:
            dx, dy = (5, -2) if name == 'A' else ((-6, 9) if name == 'BL' else (6, 9))
            part.text(px + dx, py + dy, name)


def overlay(frame, mask, color=(206, 100, 95)):
    rgb = np.asarray(echo_image(frame)).copy()
    foreground = np.asarray(mask, bool)
    rgb[foreground] = .58 * rgb[foreground] + .42 * np.array(color)
    boundary = foreground & ~ndimage.binary_erosion(foreground)
    rgb[boundary] = color
    return Image.fromarray(rgb)


def person(p, x, y, color, scale=1):
    element(p.group, 'circle', cx=x, cy=y, r=3.1 * scale, fill=color, stroke=p.edge, stroke_width=.45)
    p.path(f'M {x-5*scale} {y+15*scale} L {x-5*scale} {y+8*scale} '
           f'Q {x} {y+2*scale} {x+5*scale} {y+8*scale} L {x+5*scale} {y+15*scale} Z',
           color=p.edge, width=.45, fill=color)


def people(p, x, y, color, count=6):
    for i in range(count):
        person(p, x + (i % 3) * 15, y + (i // 3) * 25, color)


def tensor(p, key, x, y, w, h, color, layers=3):
    group = element(p.group, 'g', id='n-' + key, data_role='schematic-tensor')
    previous, p.group = p.group, group
    for i in range(layers - 1, -1, -1):
        p.rect(x + i * 2.7, y - i * 2.7, w, h, color, stroke=p.edge, radius=0)
    for i in range(1, 4):
        p.line(x, y + h * i / 4, x + w, y + h * i / 4, color=p.edge, width=.25)
    p.group = previous


def document(p, x, y, color, lines=4):
    p.rect(x+3, y-3, 31, 40, fill='white', stroke=p.edge, radius=1)
    p.rect(x, y, 31, 40, fill=color, stroke=p.edge, radius=1)
    for i in range(lines):
        p.line(x+6, y+9+i*7, x+25, y+9+i*7, color=p.edge, width=.65)


def stack(p, key, images, x, y, size=52, step=6):
    for i, image in reversed(list(enumerate(images))):
        p.rect(x+i*step-1, y-i*step-1, size+2, size+2, 'white', p.edge, radius=0)
        p.image(key+str(i), image, x+i*step, y-i*step, size, size)


def mini_model(p, x, y):
    for i, (h, color) in enumerate([(36, '#dce8f4'), (28, '#ecdfe9'), (22, '#e5edd7')]):
        tensor(p, f'model-{x}-{i}', x+i*20, y+(36-h)/2, 11, h, color, 2)
        if i < 2:
            p.arrow(f'model-link-{x}-{i}', [(x+i*20+14, y+18), (x+i*20+19, y+18)], color=INK)


def disks_volume(p, samples, cx, y):
    d2 = np.asarray(samples['2CH']['features']['diameters_mm'])
    d4 = np.asarray(samples['4CH']['features']['diameters_mm'])
    widths = np.sqrt(d2*d4)
    widths = widths / max(widths) * 70
    for i, width in enumerate(widths):
        yy = y + i * 4.0
        fill = '#ecd4ad' if i == 10 else '#e2e9ce'
        left, right = cx-width/2, cx+width/2
        p.path(f'M {left} {yy} L {left} {yy+3.8} C {left} {yy+9.8} {right} {yy+9.8} '
               f'{right} {yy+3.8} L {right} {yy} Z', color='#8b9874', width=.45, fill=fill)
        element(p.group, 'ellipse', cx=cx, cy=yy, rx=width/2, ry=min(5.5, width/5),
                fill=fill, stroke='#8b9874', stroke_width=.45)


def training_example(manifest):
    record = next(r for r in manifest['cases'] if r['split'] == 'train' and r['view'] == '2CH')
    name = record['case_id']
    source = PROJECT / 'data/processed/camus'
    meta = read_json(source / (name + '.json'))
    with np.load(source / (name + '.npz'), allow_pickle=False) as z:
        i = meta['phases']['ED']
        return name, z['frames'][i].copy(), z['masks'][i].copy()


def create_parts(samples, train):
    parts = []
    sample = samples['2CH']
    ed, es = [sample['meta']['phases'][phase] for phase in ('ED', 'ES')]
    frame, pred = sample['arrays']['frames'][ed], sample['prediction'][ed]

    p = Part('A1_camus_input', 'A1  数据队列与专家标注')
    people(p, 39, 64, '#ead4be')
    p.text(54, 133, '500', size=12)
    p.text(54, 148, '位 CAMUS 患者')
    p.arrow('cohort-clips', [(98, 105), (121, 105)], color=INK)
    for row, view in enumerate(('2CH', '4CH')):
        s = samples[view]
        ee, ss = [s['meta']['phases'][phase] for phase in ('ED', 'ES')]
        indices = np.linspace(ee, ss, 4).round().astype(int)
        yy = 55 + row*62
        p.text(146, yy+19, view, anchor='end')
        p.rect(153, yy-4, 154, 44, '#26323a', stroke='none', radius=1)
        for col, index in enumerate(indices):
            p.image(view+str(index), echo_image(s['arrays']['frames'][index]), 158+col*37, yy, 34, 34)
            for dx in (0, 14, 28):
                p.rect(160+col*37+dx, yy-2.7, 3, 1, '#f7f7f4', stroke='none', radius=0)
        for col, phase in enumerate(('ED', 'ES')):
            index = s['meta']['phases'][phase]
            p.image(view+phase, overlay(s['arrays']['frames'][index], s['arrays']['masks'][index],(63,146,132)),
                    368+col*56, yy, 39, 39)
    p.arrow('clips-labels', [(317, 105), (347, 105)], color=INK)
    p.text(229, 45, '两切面超声序列')
    p.text(387, 45, 'ED')
    p.text(443, 45, 'ES')
    p.text(416, 172, '专家标注仅位于 ED / ES')
    p.text(224, 182, '1000 条序列 · 2000 张专家标注帧')
    parts.append(p)

    p = Part('A2_preprocessing', 'A2  预处理与坐标保留')
    transform = sample['meta']['audit']['transform']
    tr = Transform(tuple(transform['original_hw']), tuple(transform['crop_xyxy']), tuple(transform['output_hw']))
    original_gt = tr.restore_mask(sample['arrays']['masks'][ed])
    p.text(81, 48, '原始标签坐标')
    p.image('original-label', mask_image(original_gt, (63,146,132)), 30, 57, 94, 93)
    ow = 93*original_gt.shape[1]/original_gt.shape[0]
    ox = 30+(94-ow)/2
    p.rect(ox, 57, ow, 93, 'none', p.edge, radius=0)
    x0,y0,x1,y1 = transform['crop_xyxy']
    scale = 93/original_gt.shape[0]
    p.rect(ox+x0*scale, 57+y0*scale, (x1-x0)*scale, (y1-y0)*scale,
           'none', RED, dash='1 2', radius=0)
    p.text(81, 166, '空间 / 时间元数据')
    p.arrow('original-cache', [(133,103), (173,103)], color=INK)
    p.text(153, 83, '裁剪')
    p.text(153, 130, '缩放')
    p.image('processed-label', overlay(frame, sample['arrays']['masks'][ed],(63,146,132)), 185,61,86,86)
    p.text(228, 48, '处理后影像与标签')
    p.text(228, 166, '112 × 112')
    p.path('M 182 150 C 150 175 124 171 124 145', color=TEAL, width=1.4)
    p.arrow('inverse-map', [(124,145),(124,137)], color=TEAL)
    p.text(153, 184, '正反坐标变换')
    p.arrow('cache-audit', [(284,103), (320,103)], color=INK)
    document(p, 350,70, '#f7e5d7')
    p.text(414, 82, 'ED / ES 原标注', anchor='start')
    p.text(414, 104, '像素间距', anchor='start')
    p.text(414, 126, '坐标记录', anchor='start')
    p.text(391, 165, '缓存与元数据审计')
    parts.append(p)

    p = Part('A3_patient_split', 'A3  固定患者级划分')
    people(p, 36,64,'#ead4be')
    p.text(52,137,'500 位患者')
    p.text(52,152,'2CH + 4CH')
    p.arrow('patient-split',[(96,102),(127,102)],color=INK)
    p.path('M 128 102 L 128 49 L 446 49',color=INK)
    for x, name, number, count, color, note in [
        (205,'训练集',347,1388,'#e4edd4','参数学习'),
        (321,'验证集',71,284,'#dce7f3','选模与早停'),
        (437,'测试集',82,328,'#f3e7c3','最终评价')]:
        p.arrow('split-'+name,[(x,49),(x,65)],color=INK)
        people(p,x-15,78,color)
        p.text(x,137,f'{name}  n={number}',size=7.3)
        p.text(x,152,f'{count} 张标注帧')
        p.text(x,168,note)
    p.text(270,184,'同一患者的全部帧与两切面始终属于同一集合')
    parts.append(p)

    p = Part('B1_segmentation_network', 'B1  DeepLabV3–ResNet50 分割网络')
    p.box('weights',94,40,125,18,'EchoNet 分割预训练权重',fill='#edf1e3')
    p.path('M 157 59 C 157 67 142 66 142 73',color=TEAL,width=1.2)
    p.arrow('initialization',[(142,73),(142,77)])
    stack(p,'input',[echo_image(frame)]*3,23,100,40,3)
    p.text(46,157,'3 × 112 × 112')
    p.arrow('input-backbone',[(77,119),(90,119)],color=INK)
    p.rect(92,78,151,76,fill='#f0f4f8',stroke='#a0b0bb',radius=5)
    p.text(167,91,'ResNet-50')
    tensor(p,'stem',101,108,8,25,'#dce8f4',2)
    for i,(height,repeat,color) in enumerate([(33,3,'#d8e5f2'),(29,4,'#e6dfe9'),(25,6,'#e2ebd5'),(22,3,'#f2e9cf')]):
        x=128+i*27
        tensor(p,'layer'+str(i+1),x,107+(33-height)/2,11,height,color,3)
        p.text(x+6,150,f'L{i+1} ×{repeat}',size=5.8)
        if i<3:p.arrow('layer-edge'+str(i),[(x+17,122),(x+25,122)],color=INK)
    p.arrow('backbone-aspp',[(244,120),(260,120)],color=INK)
    p.text(300,48,'ASPP 多尺度分支',size=7.3)
    p.path('M 263 65 L 263 145',color=INK)
    p.path('M 335 65 L 335 145',color=INK)
    for i,label in enumerate(['1 × 1','3 × 3 · r=12','3 × 3 · r=24','3 × 3 · r=36','全局池化']):
        yy=60+i*20
        p.box('aspp-'+str(i),272,yy,55,13,label,fill=['#e2eaf4','#e6eddc','#f5e5dc','#ece3ef','#f5edcf'][i],size=5.8)
        p.arrow('aspp-in-'+str(i),[(263,yy+6.5),(270,yy+6.5)],color=INK)
        p.line(327,yy+6.5,335,yy+6.5,color=INK)
    p.arrow('aspp-head',[(335,110),(358,110)],color=INK)
    tensor(p,'head',365,91,14,42,'#eee0e7',3)
    p.text(374,157,'分割头')
    p.arrow('head-mask',[(391,111),(437,111)],color=INK)
    p.text(415,84,'上采样',size=5.8)
    p.text(415,142,'sigmoid',size=5.8)
    p.image('mask-output',mask_image(pred,(206,100,95)),445,87,48,48)
    p.text(469,157,'左室掩膜')
    p.text(261,182,'骨干特征 → 多尺度上下文 → 单通道分割；掩膜由固定阈值生成')
    parts.append(p)

    p=Part('B2_supervised_finetuning','B2  专家监督与正则化微调')
    _,train_frame,train_mask=train
    p.image('train-label',mask_image(train_mask,(63,146,132)),29,58,44,44)
    p.image('train-frame',echo_image(train_frame),29,118,44,44)
    p.text(51,48,'专家标签 y')
    p.text(51,175,'ED / ES 影像')
    p.text(127,107,'同步几何增广')
    p.text(127,119,'仅训练集')
    p.arrow('label-loss',[(80,80),(337,80),(337,103)],color='#7b9c8b')
    p.arrow('image-model',[(80,140),(181,140),(181,123),(190,123)],color=INK)
    mini_model(p,195,105)
    p.text(223,96,'分割网络')
    p.arrow('model-loss',[(255,123),(307,123)],color=INK)
    p.text(280,112,'logit z',size=5.8)
    p.box('loss',313,105,53,37,['BCE','损失'],fill='#f6edcb',size=7.3)
    p.path('M 339 143 C 339 176 224 176 224 149',color=TEAL,width=1.5)
    p.arrow('update',[(224,149),(224,143)],color=TEAL)
    p.text(305,177,'AdamW 反向更新')
    p.line(392,49,392,172,color=p.edge,width=.6)
    p.text(434,48,'验证集 ED / ES')
    p.arrow('validation-selection',[(434,55),(434,65)],color=INK)
    document(p,418,73,'#e1ead6')
    p.text(434,134,'验证 BCE')
    p.text(434,149,'选模与早停')
    p.text(434,164,'保存最佳权重')
    p.text(261,186,'lr / WD = 1e-4 · 冻结 BN 统计 · 早停耐心 6 轮')
    parts.append(p)

    p=Part('B3_frame_inference','B3  序列逐帧推理与分割叠加')
    indices=[ed,(ed+es)//2,es]
    frames=[echo_image(sample['arrays']['frames'][i]) for i in indices]
    masks=[mask_image(sample['prediction'][i],(206,100,95)) for i in indices]
    overlays=[overlay(sample['arrays']['frames'][i],sample['prediction'][i]) for i in indices]
    stack(p,'input-sequence',frames,27,86,59,7)
    p.text(66,49,'超声序列')
    p.text(66,163,'ED → 中间帧 → ES')
    p.arrow('sequence-model',[(111,111),(148,111)],color=INK)
    mini_model(p,160,94)
    p.text(187,49,'冻结最佳模型')
    p.text(187,163,'逐帧推理')
    p.arrow('model-masks',[(221,111),(265,111)],color=INK)
    stack(p,'masks',masks,279,86,59,7)
    p.text(318,49,'左室二值掩膜')
    p.text(318,163,'M = 1[p ≥ 0.5]')
    p.arrow('masks-overlay',[(361,111),(398,111)],color=INK)
    stack(p,'overlay',overlays,410,86,59,7)
    p.text(450,49,'分割叠加')
    p.text(450,163,'预测轮廓')
    p.text(255,184,'所有帧可预测；几何测量前恢复原图坐标')
    parts.append(p)

    p=Part('C1_contour_geometry','C1  轮廓清理与几何特征提取')
    p.image('predicted-overlay',overlay(frame,pred),30,62,87,87)
    p.text(73,48,'预测左室轮廓')
    p.arrow('mask-clean',[(129,105),(163,105)],color=INK)
    geometry(p,sample,187,57,76,100,labels=True,disks=False)
    p.text(226,48,'轮廓派生候选点')
    p.text(225,181,'PCA / 基底宽度启发式')
    p.arrow('landmarks-geometry',[(280,105),(311,105)],color=INK)
    geometry(p,sample,334,56,75,101,disks=True)
    p.text(372,48,'长轴与 20 个截面')
    p.text(73,169,'最大连通域 + 填洞')
    p.text(447,83,'A  面积',anchor='start')
    p.text(447,107,'L  长轴',anchor='start')
    p.text(447,131,'di  盘径',anchor='start')
    p.text(408,181,'候选关键点需复核')
    parts.append(p)

    p=Part('C2_volume_methods','C2  双切面几何与容积估算')
    for view,x in [('2CH',34),('4CH',112)]:
        geometry(p,samples[view],x,60,48,91)
        p.text(x+24,48,view,size=7.3)
    p.text(96,171,'同患者 · 同 ED / ES 相位')
    p.arrow('diameters-disks',[(174,106),(201,106)],color=INK)
    disks_volume(p,samples,249,62)
    p.text(249,171,'20 盘几何示意')
    p.rect(309,51,184,45,'#eef3e6',stroke='none',radius=3)
    p.text(401,65,'单平面面积–长度法',size=7.3)
    p.text(401,84,'V = 8A² / (3πL) / 1000')
    p.rect(309,109,184,49,'#e9eff7',stroke='none',radius=3)
    p.text(401,123,'双平面椭圆盘法',size=7.3)
    p.text(401,138,'V = Σ[π d2i d4i / 4] × ΔL / 1000')
    p.text(401,152,'ΔL = min(L2,L4) / 20')
    p.text(351,184,'A：mm²；L / d：mm；V：mL')
    parts.append(p)

    p=Part('D1_functional_parameters','D1  EDV / ESV 与心功能参数')
    restored=[]
    for i in (ed,es):restored.append(main_component(tr.restore_mask(sample['prediction'][i]))[0])
    yy,xx=np.where(restored[0]|restored[1])
    for i,(mask,label) in enumerate(zip(restored,('EDV','ESV'))):
        crop=mask[yy.min():yy.max()+1,xx.min():xx.max()+1]
        p.image('phase-'+label,mask_image(crop,(206,100,95)),35+i*87,62,57,83)
        p.text(63+i*87,48,'ED' if i==0 else 'ES',size=7.3)
        p.text(63+i*87,162,label,size=7.3)
    p.arrow('edv-esv-parameters',[(185,105),(219,105)],color=INK)
    p.rect(231,67,113,72,'#fbf3d9',stroke='none',radius=4)
    p.text(287,84,'每搏量 SV',size=7.3)
    p.text(287,107,'EDV − ESV',size=8.8)
    p.text(287,127,'mL')
    p.arrow('sv-ef',[(349,105),(373,105)],color=INK)
    p.rect(382,67,111,72,'#f4e8d3',stroke='none',radius=4)
    p.text(437,84,'射血分数 EF',size=7.3)
    p.text(437,107,'100 × SV / EDV',size=7.3)
    p.text(437,127,'%')
    p.path('M 288 143 L 288 167 L 378 167',color=p.edge,dash='1 2')
    p.text(431,170,'可靠 HR 时计算 CO')
    p.text(350,185,'CO = SV × HR / 1000   (L/min)')
    parts.append(p)

    p=Part('D2_reference_evaluation','D2  分割评价与功能参考分层')
    p.text(136,48,'结构一致性',size=7.3)
    p.image('prediction',overlay(frame,pred),31,61,69,69)
    p.image('expert',overlay(frame,sample['arrays']['masks'][ed],(63,146,132)),151,61,69,69)
    p.text(65,143,'模型预测')
    p.text(185,143,'专家 ED / ES')
    p.text(125,98,'vs',size=7.3)
    for i,text in enumerate(['Dice','ASSD','HD95']):
        p.box('metric-'+text,25+i*77,155,68,19,text,fill='#f9efcb')
    p.line(263,49,263,173,color=p.edge,width=.6)
    p.text(384,48,'功能参数一致性',size=7.3)
    document(p,306,68,'#e8eedb')
    document(p,431,68,'#e4eaf5')
    p.text(322,124,'同法轮廓参考')
    p.text(447,124,'CAMUS 报告')
    p.text(322,138,'EDV / ESV / EF')
    p.text(447,138,'Info.cfg EF')
    p.text(383,160,'患者级误差 · 一致性 · 覆盖率')
    p.text(383,182,'独立临床参考缺失时保留空值')
    parts.append(p)

    p=Part('E1_patch_extension','E1  贴片连续监测扩展（待验证）')
    element(p.group,'circle',cx=68,cy=61,r=11,fill='#f7eee7',stroke='#b69e91',stroke_width=.8)
    p.path('M 37 145 L 39 94 Q 41 82 55 80 L 81 80 Q 95 82 98 94 L 100 145 Z',
           color='#b69e91',width=.8,fill='#f8f1eb')
    p.path('M 66 112 C 55 99 46 113 66 126 C 86 113 77 99 66 112 Z',
           color='#ca8f89',fill='#eed7d5')
    p.rect(73,94,29,11,'#b8c9dc',stroke='#7e94ac',radius=3)
    p.text(69,165,'贴片采集概念示意')
    p.arrow('collection-calibration',[(115,109),(159,109)],color=INK,dash='1 2')
    element(p.group,'circle',cx=222,cy=92,r=26,fill='#f5edf6',stroke=p.edge,stroke_width=.8)
    p.line(222,92,222,74,color=p.edge,width=1.1)
    p.line(222,92,237,101,color=p.edge,width=1.1)
    p.rect(188,130,70,12,'#e8e1ef',stroke=p.edge,radius=1)
    for i in range(11):p.line(191+i*6,130,191+i*6,136 if i%2 else 140,color=p.edge,width=.6)
    p.text(222,165,'空间 / 时间标定')
    p.arrow('calibration-validation',[(272,109),(314,109)],color=INK,dash='1 2')
    document(p,344,73,'#eee1f1')
    p.path('M 350 102 L 357 109 L 372 89',color='#849674',width=2)
    mini_model(p,410,84)
    p.text(408,145,'跨设备验证 + 独立参考')
    p.text(404,165,'接入既有推理与几何流程')
    p.text(257,184,'可靠时间与完整周期满足后，再评价连续 HR / CO')
    parts.append(p)
    return parts


def export(part, device=None):
    source = part.root
    shapes = deepcopy(source)
    for parent in shapes.iter():
        for child in list(parent):
            if child.tag.endswith('}text'):
                parent.remove(child)
    renderer = QSvgRenderer(QByteArray(ET.tostring(shapes)))
    if not renderer.isValid():
        raise RuntimeError('Invalid SVG: ' + part.name)
    labels = list(source.iter('{' + NS + '}text'))
    owners = {}
    for group in source.iter('{' + NS + '}g'):
        if group.get('data-role') == 'node':
            rect = group.find('{' + NS + '}rect')
            bounds = QRectF(*[float(rect.get(k)) for k in ('x', 'y', 'width', 'height')])
            owners.update({id(t): bounds for t in group.findall('{' + NS + '}text')})

    def paint(target):
        painter = QPainter(target)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        painter.scale(target.width() / WIDTH, target.height() / HEIGHT)
        renderer.render(painter, QRectF(0, 0, WIDTH, HEIGHT))
        records = []
        for label in labels:
            font = QFont(FONT)
            # Measure large logical glyphs then scale down to avoid Qt rounding
            # a 6.5-unit font to 7 units before the high-resolution export.
            precision = 100
            font.setPixelSize(round(float(label.get('font-size')) * precision))
            font.setBold(label.get('font-weight') == '700')
            font.setHintingPreference(QFont.PreferNoHinting)
            metrics = QFontMetricsF(font, target)
            missing = [c for c in label.text if not c.isspace() and not metrics.inFontUcs4(ord(c))]
            if missing:
                raise RuntimeError(f'{part.name}: missing font glyphs: {missing}')
            x, y = float(label.get('x')), float(label.get('y'))
            if label.get('text-anchor') == 'middle':
                x -= metrics.horizontalAdvance(label.text) / (2 * precision)
            elif label.get('text-anchor') == 'end':
                x -= metrics.horizontalAdvance(label.text) / precision
            measured = metrics.tightBoundingRect(label.text)
            bounds = QRectF(measured.x() / precision, measured.y() / precision,
                            measured.width() / precision, measured.height() / precision).translated(x, y)
            painter.save()
            painter.scale(1 / precision, 1 / precision)
            painter.setFont(font)
            painter.setPen(QColor(INK))
            painter.drawText(QPointF(x * precision, y * precision), label.text)
            painter.restore()
            if not QRectF(0, 0, WIDTH, HEIGHT).contains(bounds):
                raise RuntimeError(f'{part.name}: text outside canvas: {label.text}')
            if id(label) in owners and not owners[id(label)].adjusted(1, 1, -1, -1).contains(bounds):
                raise RuntimeError(f'{part.name}: text exceeds box: {label.text}')
            records.append((label.text, bounds))
        painter.end()
        for i, (a, ba) in enumerate(records):
            for b, bb in records[i + 1:]:
                intersection = ba.intersected(bb)
                if intersection.width() > .3 and intersection.height() > .3:
                    raise RuntimeError(f'{part.name}: text overlaps: {a} / {b}')
        return {'text_elements': len(records), 'bounds_and_text_overlap': 'PASS'}

    if device is not None:
        return paint(device)
    image = QImage(*[round(v / 25.4 * DPI) for v in SIZE_MM], QImage.Format_ARGB32_Premultiplied)
    image.setDotsPerMeterX(round(DPI / .0254))
    image.setDotsPerMeterY(round(DPI / .0254))
    image.fill(Qt.white)
    paint(image)
    image.save(str(OUTPUT / 'png' / (part.name + '.png')))
    writer = QPdfWriter(str(OUTPUT / 'pdf' / (part.name + '.pdf')))
    writer.setResolution(DPI)
    writer.setPageLayout(QPageLayout(QPageSize(QSizeF(*SIZE_MM), QPageSize.Millimeter),
                                    QPageLayout.Portrait, QMarginsF(0, 0, 0, 0), QPageLayout.Millimeter))
    writer.setTitle(part.title)
    return paint(writer)


def catalog(parts):
    # Inventory only: no cross-component arrows and no final workflow assembly.
    cell_w, cell_h = 910, 375
    sheet = Image.new('RGB', (2 * cell_w + 40, 6 * cell_h + 150), '#f4f4ef')
    draw = ImageDraw.Draw(sheet)
    from PIL import ImageFont
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 30)
    small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 20)
    draw.text((30, 22), 'CAMUS 方法零件｜参考图风格重绘', font=font, fill=INK)
    draw.text((30, 69), '浅色分区 · 影像叠加 · 网络结构 · 几何示意   /   各模块独立，总图待讨论', font=small, fill=INK)
    links = []
    for i, part in enumerate(parts):
        image = Image.open(OUTPUT / 'png' / (part.name + '.png')).convert('RGB')
        image.thumbnail((890, 350), Image.Resampling.LANCZOS)
        x, y = 20 + (i % 2) * cell_w, 125 + (i // 2) * cell_h
        sheet.paste(image, (x + (cell_w - image.width) // 2, y))
        links.append(f'<article><img src="png/{part.name}.png" alt="{html.escape(part.title)}">'
                     f'<p>{html.escape(part.title)}</p><a href="svg/{part.name}.svg">SVG</a> · '
                     f'<a href="pdf/{part.name}.pdf">PDF</a> · <a href="png/{part.name}.png">PNG</a></article>')
    sheet.save(OUTPUT / 'parts_catalog.png')
    selected = ['B1_segmentation_network', 'C1_contour_geometry', 'C2_volume_methods']
    preview = Image.new('RGB', (1500, 3*605+120), '#f4f4ef')
    preview_draw = ImageDraw.Draw(preview)
    preview_draw.text((28,20), '重点零件｜网络结构与几何容积', font=font, fill=INK)
    preview_draw.text((28,66), '参照新提供的论文图重绘；这三幅是独立零件，尚未连接为总图', font=small, fill=INK)
    for i, name in enumerate(selected):
        im = Image.open(OUTPUT/'png'/(name+'.png')).convert('RGB')
        im.thumbnail((1460,580),Image.Resampling.LANCZOS)
        preview.paste(im,((1500-im.width)//2,120+i*605))
    preview.save(OUTPUT/'style_preview.png')
    (OUTPUT / 'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<title>流程图零件审阅</title><style>body{font:16px "Microsoft YaHei",sans-serif;color:#20303e;'
        'max-width:1600px;margin:32px auto;background:#f4f4ef}main{display:grid;grid-template-columns:repeat(2,1fr);gap:20px}'
        'article{background:white;padding:12px;text-align:center}img{width:100%;height:auto}a{color:#187969}'
        '@media(max-width:1000px){main{grid-template-columns:1fr}}</style><h1>参考图风格｜流程图独立零件</h1>'
        '<p>11 个横向图形模块；完整总图将在讨论后绘制。<a href="PLAN.md">规划方案</a> · '
        '<a href="CAPTIONS.md">零件说明</a></p><main>' + ''.join(links) + '</main></html>',
        encoding='utf-8', newline='\n')


def main():
    app = QGuiApplication.instance() or QGuiApplication([])
    # Qt's offscreen platform may start with an empty system font database.
    for filename in ('msyh.ttc', 'msyhbd.ttc', 'arial.ttf'):
        font_path = Path('C:/Windows/Fonts') / filename
        if font_path.is_file():
            QFontDatabase.addApplicationFont(str(font_path))
    if FONT not in QFontDatabase().families():
        raise RuntimeError('Missing font: ' + FONT)
    for directory in ('svg', 'pdf', 'png', 'qa'):
        (OUTPUT / directory).mkdir(exist_ok=True)
    samples, manifest = load_examples()
    train = training_example(manifest)
    parts = create_parts(samples, train)
    checks = {}
    for part in parts:
        part.write()
        checks[part.name] = export(part)
    catalog(parts)
    sources = ['configs/experiment.yaml', 'configs/train/baseline.yaml', 'configs/camus_splits.json',
               'src/engine/trainer.py', 'src/engine/evaluator.py', 'src/data/base.py',
               'src/data/camus/prepare.py', 'src/geometry/mask_features.py', 'src/geometry/volume.py',
               'src/geometry/functional.py', 'src/models/deeplabv3.py', 'src/models/build.py',
               'data/processed/camus/manifest.json', 'runs/validation_camus_regularized/summary.json']
    sources += ['src/data/transforms.py', 'docs/data_sources/echonet_weights.json']
    sources += ['data/processed/camus/'+train[0]+ext for ext in ('.npz','.json')]
    for view in ('2CH', '4CH'):
        key = PATIENT + '_' + view
        sources += ['data/processed/camus/' + key + ext for ext in ('.npz', '.json')]
        sources += ['runs/validation_camus_regularized/' + key + '_pred.npz']
    audit = {'scope': 'independent_workflow_components_not_final_assembled_figure',
             'example_patient': PATIENT, 'example_split': 'val', 'selection': 'fixed_example_no_metric_based_selection',
             'image_scope': 'processed_frames_and_saved_predictions_not_raw_acquisition_images',
             'prediction_weights_sha256': read_json(PROJECT / 'runs/validation_camus_regularized/summary.json')['weights_sha256'],
             'training_diagram_example': train[0], 'training_example_split': 'train',
             'style': 'user_reference_pastel_groups_illustrated_landscape_modules',
             'style_reference_sha256': 'f6a51d1add21fd4279bfae869b14ac61523d4e2f7fcdafd31402481a594e6472',
             'style_reference_reuse': 'style_only_no_source_raster_elements_reused',
             'feature_tensors': 'architecture_schematic_not_measured_activations',
             'volume_disks': 'geometric_illustration_from_saved_predicted_diameters_not_acquired_3D',
             'parts': [{'name': p.name, 'title': p.title} for p in parts],
             'checks': checks, 'physical_part_size_mm': list(SIZE_MM), 'png_dpi': DPI,
             'sources_sha256': {s: hashlib.sha256((PROJECT / s).read_bytes()).hexdigest() for s in sources}}
    (OUTPUT / 'qa/export_check.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n',
                                               encoding='utf-8', newline='\n')
    print(f'Exported {len(parts)} independent components; final workflow not assembled.')
    return app


if __name__ == '__main__':
    main()
