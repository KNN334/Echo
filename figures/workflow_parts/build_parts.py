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
WIDTH, HEIGHT = 46 / 25.4 * 72, 54 / 25.4 * 72
FONT, DPI = 'Microsoft YaHei UI', 600
PATIENT = 'patient0008'


def element(parent, tag, **attrs):
    return ET.SubElement(parent, '{' + NS + '}' + tag,
                         {k.replace('_', '-'): str(v) for k, v in attrs.items()})


class Part:
    def __init__(self, name, title):
        self.name, self.title = name, title
        self.root = ET.Element('{' + NS + '}svg', {
            'width': '46mm', 'height': '54mm', 'viewBox': f'0 0 {WIDTH} {HEIGHT}',
            'version': '1.1', 'role': 'img', 'aria-label': title})
        self.group = self.root
        element(self.root, 'rect', x=0, y=0, width=WIDTH, height=HEIGHT, fill='white')
        self.rect(3, 3, WIDTH - 6, 17, PEACH, stroke='none')
        self.text(WIDTH / 2, 14.5, title, size=7.6, bold=True)

    def text(self, x, y, text, size=6.5, anchor='middle', bold=False):
        item = element(self.group, 'text', x=x, y=y, font_family=FONT, font_size=size,
                       text_anchor=anchor, fill=INK, font_weight='700' if bold else '400')
        item.text = text
        return item

    def rect(self, x, y, w, h, fill=LIGHT, stroke=GREY, dash=None):
        attrs = dict(x=x, y=y, width=w, height=h, rx=2, fill=fill, stroke=stroke, stroke_width=.55)
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


def geometry(part, sample, x, y, w, h, labels=False):
    clean, _ = main_component(sample['original'])
    boundary = clean & ~ndimage.binary_erosion(clean)
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
    for i, diameter in enumerate(f['diameters_mm']):
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


def create_parts(samples):
    parts = []
    p = Part('A1_camus_input', 'A1｜CAMUS 数据输入')
    for col, view in enumerate(('2CH', '4CH')):
        sample = samples[view]
        x = 12 + col * 60
        p.text(x + 23, 31, view)
        for row, phase in enumerate(('ED', 'ES')):
            i = sample['meta']['phases'][phase]
            p.image(view + phase, echo_image(sample['arrays']['frames'][i], sample['arrays']['masks'][i]), x, 35 + row * 49, 46, 40)
            p.text(x + 23, 83 + row * 49, phase)
    p.text(WIDTH / 2, 146, '专家轮廓仅位于 ED / ES')
    parts.append(p)

    p = Part('A2_preprocessing', 'A2｜预处理与坐标审计')
    for key, y, lines in [('metadata', 29, ['声窗与元数据核查', '空间 / 时间信息']),
                          ('resize', 65, ['裁剪与尺寸变换', '112 × 112']),
                          ('audit', 101, ['保留原始 ED/ES 标签', '保存正反坐标变换'])]:
        p.box(key, 16, y, 98, 26, lines, fill=PALE)
    p.arrow('to-resize', [(65, 55), (65, 64)])
    p.arrow('to-audit', [(65, 91), (65, 100)])
    p.text(WIDTH / 2, 143, '日常入口核验已有缓存')
    parts.append(p)

    p = Part('A3_patient_split', 'A3｜固定患者级划分')
    for key, y, label, number, count in [('train', 29, '训练集', 347, 1388), ('val', 66, '验证集', 71, 284), ('test', 103, '测试集', 82, 328)]:
        p.box(key, 12, y, 106, 29, [f'{label}：{number} 位患者', f'{count} 张 ED/ES 标注帧'], fill=PALE if key == 'train' else LIGHT)
    p.text(WIDTH / 2, 146, '同患者两切面归属同一集合')
    parts.append(p)

    p = Part('B1_segmentation_network', 'B1｜左室分割网络')
    for key, y, label, fill in [('input', 28, '输入：3 × 112 × 112', LIGHT), ('backbone', 53, 'ResNet-50', LIGHT),
                               ('aspp', 78, 'ASPP 多尺度特征', PALE), ('head', 103, '单通道分割头 + 上采样', LIGHT)]:
        p.box(key, 13, y, 104, 18, label, fill=fill)
        if y < 103:
            p.arrow('after-' + key, [(65, y + 18), (65, y + 24)])
    p.text(WIDTH / 2, 134, 'p = sigmoid(z)')
    p.text(WIDTH / 2, 146, 'EchoNet 官方权重初始化')
    parts.append(p)

    p = Part('B2_supervised_finetuning', 'B2｜正则化监督微调')
    p.box('image', 12, 29, 48, 18, 'ED/ES 影像')
    p.box('label', 70, 29, 48, 18, '专家标签 y')
    p.box('augmentation', 20, 58, 90, 20, '同步几何增广', fill=PALE)
    p.arrow('image-augmentation', [(36, 47), (36, 57)])
    p.arrow('label-augmentation', [(94, 47), (94, 57)])
    p.box('prediction', 12, 90, 48, 18, '预测 logit z')
    p.box('bce', 70, 90, 48, 18, 'BCE 损失', fill=PALE)
    p.arrow('aug-prediction', [(36, 78), (36, 89)])
    p.arrow('aug-bce', [(94, 78), (94, 89)])
    p.arrow('pred-bce', [(60, 99), (69, 99)])
    p.path('M 94 108 C 94 117 6 117 6 99 L 11 99', color=TEAL, dash='1 2')
    p.arrow('optimizer-return', [(6, 99), (11, 99)], dash='1 2')
    p.text(65, 124, 'AdamW：lr / WD = 1e-4')
    p.text(65, 134, '验证 BCE 选模 · 早停 6 轮')
    p.text(65, 146, '仅训练帧更新参数与统计量')
    parts.append(p)

    sample = samples['2CH']
    ed = sample['meta']['phases']['ED']
    p = Part('B3_frame_inference', 'B3｜逐帧推理与掩膜')
    p.image('frame', echo_image(sample['arrays']['frames'][ed]), 12, 30, 43, 43)
    p.image('prediction', mask_image(sample['prediction'][ed]), 76, 30, 43, 43)
    p.arrow('frame-mask', [(57, 51), (73, 51)])
    p.text(65, 85, 'M = 1[p ≥ 0.5]')
    restored_w = 40 * sample['original'].shape[1] / sample['original'].shape[0]
    restored_x = (WIDTH - restored_w) / 2
    p.image('restored', mask_image(sample['original']), restored_x, 99, restored_w, 40)
    p.rect(restored_x, 99, restored_w, 40, fill='none', stroke=GREY)
    p.arrow('restore', [(65, 88), (65, 97)])
    p.text(65, 150, '还原至原图坐标后测量')
    parts.append(p)

    p = Part('C1_contour_geometry', 'C1｜轮廓几何特征')
    p.text(65, 31, '最大连通域 + 填洞')
    geometry(p, sample, 35, 39, 60, 82, labels=True)
    p.text(65, 140, '面积 A · 长轴 L · 20 个盘径')
    p.text(65, 151, '点位为轮廓派生候选，需复核')
    parts.append(p)

    p = Part('C2_volume_methods', 'C2｜几何容积估算')
    p.text(35, 31, '2CH')
    p.text(96, 31, '4CH')
    geometry(p, samples['2CH'], 17, 38, 36, 58)
    geometry(p, samples['4CH'], 78, 38, 36, 58)
    p.text(65, 110, '同患者、同 ED/ES 相位配对')
    p.text(65, 124, 'V1 = 8A² / (3πL) / 1000')
    p.text(65, 136, 'V2 = Σπd2i d4i L / (80×1000)')
    p.text(65, 149, 'L = min(L2,L4)，容积单位 mL')
    parts.append(p)

    p = Part('D1_functional_parameters', 'D1｜心功能参数计算')
    p.box('edv', 12, 29, 48, 24, ['EDV', '舒张末容积'])
    p.box('esv', 70, 29, 48, 24, ['ESV', '收缩末容积'])
    p.box('sv', 14, 66, 102, 18, 'SV = EDV − ESV', fill=PALE)
    p.arrow('edv-sv', [(36, 53), (36, 65)])
    p.arrow('esv-sv', [(94, 53), (94, 65)])
    p.box('ef', 14, 92, 102, 18, 'EF = 100 × SV / EDV', fill=PALE)
    p.box('co', 14, 122, 102, 22, ['可靠 HR 时', 'CO = SV × HR / 1000'], fill='white', dash='3 2')
    parts.append(p)

    p = Part('D2_reference_evaluation', 'D2｜参考分层与评价')
    p.box('pred', 8, 29, 53, 24, ['预测掩膜', '原图坐标'])
    p.box('gt', 69, 29, 53, 24, ['原始专家掩膜', '仅 ED/ES'])
    p.box('segmetrics', 8, 63, 114, 18, 'Dice / ASSD / HD95', fill=PALE)
    p.arrow('pred-metrics', [(35, 53), (35, 62)])
    p.arrow('gt-metrics', [(95, 53), (95, 62)])
    p.box('same-geometry-ref', 8, 93, 53, 24, ['同法轮廓参考', 'EDV / ESV / EF'])
    p.box('camus-ef', 69, 93, 53, 24, ['CAMUS 报告', 'EF'])
    p.text(65, 133, '患者级误差、一致性与覆盖率')
    p.text(65, 146, '独立临床参考缺失时保留 null')
    parts.append(p)

    p = Part('E1_patch_extension', 'E1｜贴片连续监测扩展')
    p.box('patch', 14, 29, 102, 22, '贴片探头连续采集', fill='white', dash='3 2')
    p.box('calibration', 14, 62, 102, 22, '格式适配 + 空间/时间标定', fill='white', dash='3 2')
    p.box('validation', 14, 95, 102, 22, '跨设备验证 + 独立参考', fill='white', dash='3 2')
    p.arrow('patch-calibration', [(65, 51), (65, 61)], dash='3 2')
    p.arrow('calibration-validation', [(65, 84), (65, 94)], dash='3 2')
    p.text(65, 133, '完整周期与可靠时间 → HR / CO')
    p.text(65, 146, '后续扩展 · 待采集与验证')
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
    image = QImage(round(46 / 25.4 * DPI), round(54 / 25.4 * DPI), QImage.Format_ARGB32_Premultiplied)
    image.setDotsPerMeterX(round(DPI / .0254))
    image.setDotsPerMeterY(round(DPI / .0254))
    image.fill(Qt.white)
    paint(image)
    image.save(str(OUTPUT / 'png' / (part.name + '.png')))
    writer = QPdfWriter(str(OUTPUT / 'pdf' / (part.name + '.pdf')))
    writer.setResolution(DPI)
    writer.setPageLayout(QPageLayout(QPageSize(QSizeF(46, 54), QPageSize.Millimeter),
                                    QPageLayout.Portrait, QMarginsF(0, 0, 0, 0), QPageLayout.Millimeter))
    writer.setTitle(part.title)
    return paint(writer)


def catalog(parts):
    # Inventory only: no cross-component arrows and no final workflow assembly.
    cell_w, cell_h = 430, 525
    sheet = Image.new('RGB', (3 * cell_w + 40, 4 * cell_h + 150), '#f1f3f5')
    draw = ImageDraw.Draw(sheet)
    from PIL import ImageFont
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 30)
    small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 20)
    draw.text((30, 22), '项目流程图零件｜审阅稿', font=font, fill=INK)
    draw.text((30, 69), '当前 CAMUS 主体 + 贴片扩展；完整总图待讨论后组装', font=small, fill=INK)
    links = []
    for i, part in enumerate(parts):
        image = Image.open(OUTPUT / 'png' / (part.name + '.png')).convert('RGB')
        image.thumbnail((400, 475), Image.Resampling.LANCZOS)
        x, y = 20 + (i % 3) * cell_w, 125 + (i // 3) * cell_h
        sheet.paste(image, (x + (cell_w - image.width) // 2, y))
        links.append(f'<article><img src="png/{part.name}.png" alt="{html.escape(part.title)}">'
                     f'<p>{html.escape(part.title)}</p><a href="svg/{part.name}.svg">SVG</a> · '
                     f'<a href="pdf/{part.name}.pdf">PDF</a> · <a href="png/{part.name}.png">PNG</a></article>')
    sheet.save(OUTPUT / 'parts_catalog.png')
    (OUTPUT / 'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<title>流程图零件审阅</title><style>body{font:16px "Microsoft YaHei",sans-serif;color:#20303e;'
        'max-width:1200px;margin:32px auto;background:#f4f5f6}main{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}'
        'article{background:white;padding:16px;text-align:center}img{width:100%;height:auto}a{color:#187969}'
        '@media(max-width:760px){main{grid-template-columns:1fr}}</style><h1>流程图零件｜审阅稿</h1>'
        '<p>11 个独立零件；完整总图将在讨论后绘制。<a href="PLAN.md">规划方案</a> · '
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
    parts = create_parts(samples)
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
    for view in ('2CH', '4CH'):
        key = PATIENT + '_' + view
        sources += ['data/processed/camus/' + key + ext for ext in ('.npz', '.json')]
        sources += ['runs/validation_camus_regularized/' + key + '_pred.npz']
    audit = {'scope': 'independent_workflow_components_not_final_assembled_figure',
             'example_patient': PATIENT, 'example_split': 'val', 'selection': 'fixed_example_no_metric_based_selection',
             'image_scope': 'processed_frames_and_saved_predictions_not_raw_acquisition_images',
             'prediction_weights_sha256': read_json(PROJECT / 'runs/validation_camus_regularized/summary.json')['weights_sha256'],
             'parts': [{'name': p.name, 'title': p.title} for p in parts],
             'checks': checks, 'physical_part_size_mm': [46, 54], 'png_dpi': DPI,
             'sources_sha256': {s: hashlib.sha256((PROJECT / s).read_bytes()).hexdigest() for s in sources}}
    (OUTPUT / 'qa/export_check.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n',
                                               encoding='utf-8', newline='\n')
    print(f'Exported {len(parts)} independent components; final workflow not assembled.')
    return app


if __name__ == '__main__':
    main()
