"""Reference vector reconstruction, layout draft and project workflow.

Hand-built SVG with live text. Thumbnail pixels become palette/run-length paths;
they are display-only vector tracings, not new image or measurement information.
Uses fixed existing validation examples; never trains or evaluates test images.
Run with the project's core dependencies and PyQt5 (the local Anaconda Python).
"""
from collections import Counter, defaultdict
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image
from PyQt5.QtCore import QByteArray, QMarginsF, QPointF, QRectF, QSizeF, Qt
from PyQt5.QtGui import (QColor, QFont, QFontDatabase, QFontMetricsF,
                         QGuiApplication, QImage, QPageLayout, QPageSize,
                         QPainter, QPdfWriter)
from PyQt5.QtSvg import QSvgRenderer

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2]
sys.path.insert(0, str(PROJECT))
spec = importlib.util.spec_from_file_location('workflow_components', OUT.parent / 'build_parts.py')
parts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parts)

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
W, H = 672, 876
WIDTH_MM = 183
HEIGHT_MM = WIDTH_MM * H / W
DPI = 300
FONT, INK, TEAL, RED = 'Microsoft YaHei UI', '#20303e', '#238b80', '#ce645f'
PALETTES = parts.PALETTES
SOURCE = OUT / 'assets/reference.png'


def elem(parent, tag, **attrs):
    return ET.SubElement(parent, '{' + NS + '}' + tag,
                         {k.replace('_', '-'): str(v) for k, v in attrs.items()})


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Figure:
    def __init__(self, name, title, font=FONT):
        self.name, self.font, self.edge = name, font, '#8c9ca3'
        self.root = ET.Element('{' + NS + '}svg', {
            'width': f'{WIDTH_MM}mm', 'height': f'{HEIGHT_MM:.6f}mm',
            'viewBox': f'0 0 {W} {H}', 'version': '1.1',
            'role': 'img', 'aria-label': title})
        elem(self.root, 'title').text = title
        elem(self.root, 'desc').text = (
            'Editable vector reconstruction. Live labels and vector shapes. '
            'Thumbnail paths are quantized tracings, not recovered source data. '
            'Research methods draft; not clinical validation.')
        self.group = self.root
        self.serial = 0
        self.trace_records = []
        self.rect(0, 0, W, H, 'white', 'none', radius=0)

    @contextmanager
    def group_id(self, key, role='component'):
        old = self.group
        self.group = elem(old, 'g', id=key, data_role=role)
        try:
            yield self.group
        finally:
            self.group = old

    def text(self, x, y, text, size=8.6, anchor='middle', bold=False):
        t = elem(self.group, 'text', x=x, y=y, font_family=self.font,
                 font_size=size, text_anchor=anchor, fill=INK,
                 font_weight='700' if bold else '400')
        t.text = text
        return t

    def lines(self, x, y, lines, step=12, **kwargs):
        for i, label in enumerate(lines):
            self.text(x, y + step * i, label, **kwargs)

    def rect(self, x, y, w, h, fill='white', stroke='#8c9ca3', dash=None, radius=3):
        attrs = dict(x=x, y=y, width=w, height=h, rx=radius, fill=fill,
                     stroke=stroke, stroke_width=.65)
        if dash:
            attrs['stroke_dasharray'] = dash
        return elem(self.group, 'rect', **attrs)

    def path(self, d, color=INK, width=.9, fill='none', dash=None):
        attrs = dict(d=d, stroke=color, stroke_width=width, fill=fill,
                     stroke_linejoin='round', stroke_linecap='round')
        if dash:
            attrs['stroke_dasharray'] = dash
        return elem(self.group, 'path', **attrs)

    def line(self, x1, y1, x2, y2, color=INK, width=.9, dash=None):
        return self.path(f'M {x1} {y1} L {x2} {y2}', color, width, dash=dash)

    def arrow(self, key, points, color=INK, dash=None):
        with self.group_id('e-' + key, 'edge'):
            self.path('M ' + ' L '.join(f'{x} {y}' for x, y in points), color, 1.1, dash=dash)
            x, y = points[-1]
            px, py = points[-2]
            a = math.atan2(y - py, x - px)
            vertices = [(x, y)] + [(x + 3.8 * math.cos(a + t), y + 3.8 * math.sin(a + t))
                                   for t in (2.65, -2.65)]
            self.path('M ' + ' L '.join(f'{xx:.3f} {yy:.3f}' for xx, yy in vertices) + ' Z',
                      color, .3, color)

    def circle(self, x, y, r, fill=TEAL):
        return elem(self.group, 'circle', cx=x, cy=y, r=r, fill=fill,
                    stroke='white', stroke_width=.55)

    def box(self, key, x, y, w, h, lines, fill='white', dash=None, size=8.6):
        with self.group_id('n-' + key, 'node'):
            self.rect(x, y, w, h, fill, dash=dash)
            lines = [lines] if isinstance(lines, str) else lines
            for i, label in enumerate(lines):
                self.text(x + w / 2, y + h / 2 + 3 + (i - (len(lines) - 1) / 2) * 12,
                          label, size=size)

    def panel(self, key, x, y, w, h, title, palette, size=9.5):
        tint, paper, edge = PALETTES[palette]
        self.edge = edge
        with self.group_id('c-' + key, 'container'):
            self.rect(x, y + 7, w, h - 7, paper, edge, dash='3.5 2', radius=12)
            # Measure at high precision so physical font rounding cannot size tabs.
            f = QFont(self.font)
            f.setPixelSize(round(size * 100))
            f.setBold(True)
            tw = QFontMetricsF(f).horizontalAdvance(title) / 100
            if tw + 24 > w:
                raise RuntimeError(f'Panel title too wide: {title}')
            self.rect(x + 9, y, tw + 15, 19, tint, 'none', radius=0)
            self.text(x + 16, y + 13.4, title, size=size, anchor='start', bold=True)

    def band(self, key, x, y, w, h, title, palette):
        tint, paper, edge = PALETTES[palette]
        with self.group_id('s-' + key, 'stage'):
            self.rect(x, y, w, h, paper, edge, radius=0)
            self.text(x + 9, y + 16, title, size=12.2, anchor='start', bold=True)

    def image(self, key, image, x, y, w, h, colors=24, max_size=112):
        """Convert a thumbnail to vector run paths; preserve its aspect ratio."""
        image = image.convert('RGB')
        input_size = image.size
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        pal = image.quantize(colors=colors, method=Image.Quantize.MEDIANCUT,
                             dither=Image.Dither.NONE)
        a = np.asarray(pal)
        height, width = a.shape
        scale = min(w / width, h / height)
        ox, oy = x + (w - width * scale) / 2, y + (h - height * scale) / 2
        # Merge identical horizontal runs on adjacent rows into exact rectangles.
        active, rectangles = {}, defaultdict(list)
        for yy in range(height + 1):
            current = set()
            if yy < height:
                row = a[yy]
                starts = np.r_[0, np.where(row[1:] != row[:-1])[0] + 1]
                stops = np.r_[starts[1:], width]
                current = {(int(row[lo]), int(lo), int(hi)) for lo, hi in zip(starts, stops)}
            for run in active.keys() - current:
                color, lo, hi = run
                rectangles[color].append((lo, active[run], hi - lo, yy - active[run]))
            active = {run: active.get(run, yy) for run in current}
        self.serial += 1
        with self.group_id(f'trace-{key}-{self.serial}', 'vector-traced-thumbnail') as g:
            g.set('transform', f'translate({ox:.6f} {oy:.6f}) scale({scale:.9f})')
            elem(g, 'title').text = f'{key}: display-only quantized vector tracing of existing image'
            palette = pal.getpalette()
            for i, rects in sorted(rectangles.items()):
                color = '#%02x%02x%02x' % tuple(palette[i * 3:i * 3 + 3])
                d = ''.join(f'M{xx} {yy}h{ww}v{hh}h-{ww}z' for xx, yy, ww, hh in rects)
                # A tiny same-colour stroke prevents antialias seams between runs.
                # It affects display only, never the masks supplied to geometry.
                elem(g, 'path', d=d, fill=color, stroke=color, stroke_width=.35,
                     shape_rendering='crispEdges')
        self.trace_records.append({'key': key, 'source_size': input_size,
                                   'traced_size': [width, height], 'palette': colors})

    def write(self):
        p = OUT / (self.name + '.svg')
        ET.ElementTree(self.root).write(p, encoding='utf-8', xml_declaration=True)
        return p


def title(p):
    p.text(12, 22, '基于贴片式超声探头的心脏功能参数连续监测与分析',
           size=14.5, anchor='start', bold=True)
    p.text(12, 38, 'CAMUS 可复现基线  ·  EchoNet 分割迁移  ·  贴片连续监测扩展',
           size=8.6, anchor='start')


def stages(p):
    p.band('data', 4, 48, 664, 142, '步骤 1   数据准备与患者级隔离', 'A')
    p.band('segmentation', 4, 198, 664, 204, '步骤 2   EchoNet 权重迁移与左室分割', 'B')
    p.band('geometry', 4, 410, 664, 182, '步骤 3   从预测掩膜到几何容积', 'C')
    p.band('evaluation', 4, 600, 417, 222, '步骤 4   心功能参数与分层评价', 'D')
    p.band('patch', 429, 600, 239, 222, '步骤 5   贴片连续监测扩展', 'E')


def footer(p):
    p.text(12, 840, '轮廓派生点为候选；半周期不拼接。HR / CO 需可靠时间与完整周期，或有来源的参考 HR。',
           anchor='start', size=7.8)
    p.text(12, 854, 'CAMUS：Leclerc et al., 2019 · CC BY-NC-SA 4.0。贴片扩展待接入、待外部验证。',
           anchor='start', size=7.8)
    p.text(12, 868, '方法与研究计划示意稿 · 不表示已完成临床验证 · 灰度缩略图为已有验证影像的矢量描摹',
           anchor='start', size=7.8)


def build_layout():
    p = Figure('02_project_layout', '项目总图布局规划')
    title(p)
    stages(p)
    for key, x, w, lines in [
        ('input', 15, 189, ['CAMUS 两切面序列', '专家 ED / ES 标注', '外部公开数据']),
        ('preprocess', 219, 230, ['处理后数据核验与坐标审计', '原标注、空间 / 时间标定', '正反坐标变换']),
        ('split', 464, 193, ['固定患者级划分', '训练 / 验证 / 测试互斥', '参数学习 / 选模 / 最终评价']),
    ]:
        p.box(key, x, 86, w, 88, lines, fill='#f7e5d7')
    p.arrow('input-preprocess', [(205, 132), (217, 132)])
    p.arrow('preprocess-split', [(450, 132), (462, 132)])
    p.box('network', 15, 235, 642, 65,
          ['EchoNet 初始化 → ResNet-50 → ASPP → 分割头 → 左室掩膜',
           '网络结构主视觉；使用张量、分支和真实验证帧'], fill='#edf3e5')
    p.box('supervised', 15, 320, 380, 65,
          ['专家标签 → BCE；影像 → 网络 → BCE', '训练更新；验证选模与早停'], fill='#edf3e5')
    p.box('inference', 410, 320, 247, 65,
          ['最佳权重逐帧推理', '固定阈值；恢复原图坐标'], fill='#edf3e5')
    p.arrow('selected-inference', [(397, 352), (408, 352)])
    p.box('contour', 15, 449, 273, 125,
          ['原坐标掩膜 → 轮廓清理', 'PCA 候选点；面积 / 长轴 / 20 盘径',
           '图形化展示长轴与截面'], fill='#e9eff7')
    p.box('volumes', 303, 449, 354, 125,
          ['单平面面积–长度 / 双平面 20 椭圆盘', '同患者、同 ED / ES 相位配对',
           '空间标定 → 绝对容积'], fill='#e9eff7')
    p.arrow('geometry-volume', [(290, 512), (301, 512)])
    p.box('function', 15, 640, 395, 65,
          ['EDV / ESV → SV / EF', '参数公式与共同尺度的 ED / ES 轮廓'], fill='#fbf3d9')
    p.box('evaluation', 15, 720, 395, 85,
          ['分割一致性；同法轮廓参考；数据集报告 EF', '患者级误差 / 一致性 / 置信区间 / 覆盖率',
           '独立参考缺失：null + 原因'], fill='#fbf3d9')
    p.box('conditional', 441, 640, 215, 165,
          ['贴片连续采集（待接入）', '空间 / 时间标定', '完整周期或有来源参考 HR',
           '跨设备验证与独立参考', '条件满足后评价 HR / CO'], fill='#f3eaf5')
    footer(p)
    return p


def people(p, x, y, color, count=3, scale=.75):
    for i in range(count):
        parts.person(p, x + i * 15 * scale, y, color, scale=scale)


def tensor(p, key, x, y, w, h, color, layers=3):
    parts.tensor(p, key, x, y, w, h, color, layers)


def mask_shape(p, key, mask, x, y, w, h, color=RED):
    p.image(key, parts.mask_image(mask, tuple(bytes.fromhex(color.lstrip('#')))),
            x, y, w, h, colors=2, max_size=max(mask.shape))


def project_samples(samples):
    s = samples['2CH']
    ed, es = (s['meta']['phases'][k] for k in ('ED', 'ES'))
    return s, ed, es, s['arrays']['frames'][ed], s['prediction'][ed]


def build_project(samples, manifest):
    p = Figure('03_project_workflow', 'CAMUS 左室分割、几何心功能估算与贴片扩展总图')
    s, ed, es, frame, pred = project_samples(samples)
    title(p)
    stages(p)

    # Step 1: observed input, audited transforms, patient-level separation.
    p.panel('cohort', 14, 76, 190, 103, 'CAMUS 数据与专家标注', 'A')
    people(p, 31, 110, '#ead4be', count=3, scale=.8)
    p.text(43, 145, '500 位患者')
    p.text(43, 160, '1000 条序列', size=7.8)
    for view, x in [('2CH', 91), ('4CH', 148)]:
        v = samples[view]
        i = v['meta']['phases']['ED']
        p.image('cohort-' + view, parts.overlay(v['arrays']['frames'][i], v['arrays']['masks'][i],
                                               (63, 146, 132)), x, 105, 43, 43)
        p.text(x + 21.5, 160, view, size=7.8)
    p.text(109, 173, '仅 ED / ES 有专家标签', size=7.8)
    p.panel('audit', 218, 76, 232, 103, '处理后数据核验与坐标审计', 'A')
    original_mask = s['arrays']['original_gt'][list(s['arrays']['original_gt_indices']).index(ed)]
    mask_shape(p, 'original-expert-mask', original_mask, 229, 106, 49, 49, TEAL)
    p.arrow('audit-transform', [(281, 129), (300, 129)])
    p.image('processed-example', parts.echo_image(frame), 305, 105, 49, 49)
    parts.document(p, 369, 107, '#f7e5d7', lines=3)
    p.text(419, 119, '原标注', size=7.8)
    p.text(419, 133, '标定', size=7.8)
    p.text(419, 147, '坐标', size=7.8)
    p.text(250, 168, '原坐标', size=7.8)
    p.text(331, 168, '112 × 112', size=7.8)
    p.text(405, 168, '保留审计', size=7.8)
    p.path('M 327 155 C 327 164 292 164 284 153', TEAL, 1.1)
    p.arrow('inverse-transform', [(284, 153), (281, 148)], TEAL)
    p.panel('patient-split', 464, 76, 194, 103, '固定患者级划分', 'A')
    for yy, label, number, note, fill in [
        (110, '训练', 347, '学习', '#e5edd7'),
        (132, '验证', 71, '选模', '#e0ebf6'),
        (154, '测试', 82, '终评', '#faf0c8'),
    ]:
        people(p, 479, yy - 3, fill, count=2, scale=.48)
        p.text(505, yy + 4, label, anchor='start')
        p.text(561, yy + 4, str(number), bold=True)
        p.text(629, yy + 4, note)
    p.text(561, 173, '同患者全部帧与两切面同属一集', size=7.8)
    p.arrow('cohort-audit', [(205, 129), (216, 129)])
    p.arrow('audit-split', [(452, 129), (462, 129)])

    # Step 2: explicit backbone, parallel ASPP, labels-to-loss and best-model inference.
    p.panel('network', 14, 225, 644, 90, 'DeepLabV3–ResNet50', 'B')
    p.image('network-input', parts.echo_image(frame), 28, 252, 42, 42)
    p.text(49, 307, '灰度复制 3 通道', size=7.8)
    p.arrow('image-backbone', [(74, 273), (92, 273)])
    p.rect(98, 250, 184, 47, '#f0f4f8', '#a0b0bb', radius=5)
    p.text(207, 246, 'EchoNet 分割权重初始化', size=8.6)
    for i, (height, repeat, fill) in enumerate([
        (28, 3, '#d8e5f2'), (25, 4, '#e6dfe9'),
        (22, 6, '#e2ebd5'), (19, 3, '#f2e9cf'),
    ]):
        x = 110 + i * 43
        tensor(p, 'resnet-layer-' + str(i + 1), x, 259 + (28 - height) / 2, 16, height, fill)
        p.text(x + 10, 307, f'L{i + 1} ×{repeat}', size=7.8)
        if i < 3:
            p.arrow('resnet-' + str(i), [(x + 23, 274), (x + 38, 274)])
    p.arrow('backbone-aspp', [(286, 273), (303, 273)])
    p.text(348, 246, 'ASPP 多尺度分支')
    p.line(305, 254, 305, 294)
    p.line(395, 254, 395, 294)
    # Group rate branches without falsely implying one sequential atrous stack.
    for i, (label, fill) in enumerate([
        ('1 × 1', '#e2eaf4'), ('3×3 · r=12/24/36', '#eee3e9'), ('全局池化', '#f5edcf'),
    ]):
        yy = 252 + i * 17
        p.box('aspp-branch-' + str(i), 315, yy, 71, 14, label, fill=fill, size=7.8)
        p.arrow('aspp-in-' + str(i), [(305, yy + 7), (313, yy + 7)])
        p.line(386, yy + 7, 395, yy + 7)
    p.arrow('aspp-head', [(395, 273), (419, 273)])
    tensor(p, 'segmentation-head', 430, 258, 17, 32, '#eee0e7')
    p.text(442, 307, '拼接与分割头', size=7.8)
    p.arrow('head-output', [(459, 273), (540, 273)])
    p.text(501, 258, '上采样')
    p.text(501, 294, 'sigmoid', size=7.8)
    mask_shape(p, 'network-mask', pred, 550, 251, 45, 45)
    p.lines(621, 262, ['左室', '掩膜'], step=13)
    p.text(581, 307, '固定阈值 0.5', size=7.8)

    p.panel('finetune', 14, 325, 381, 66, '仅 ED / ES 标签监督微调', 'B', size=9.1)
    p.text(37, 354, '影像', size=7.8)
    p.arrow('training-image', [(54, 351), (70, 351)])
    p.box('train-model', 75, 341, 59, 24, '分割网络', '#edf3e5')
    p.arrow('train-logit', [(137, 353), (151, 353)])
    p.box('train-bce', 157, 341, 42, 24, 'BCE', '#f7edcb')
    p.text(230, 350, '专家标签', size=7.8)
    p.arrow('labels-loss', [(212, 356), (201, 356)], color='#7b9c8b')
    p.path('M 177 367 C 177 381 104 381 104 367', TEAL, 1.1)
    p.arrow('parameter-update', [(104, 367), (104, 365)], TEAL)
    p.text(295, 370, '配对增广 · AdamW', size=7.8)
    p.text(295, 384, '归一化仅取训练集', size=7.8)
    p.line(259, 344, 259, 359, '#8b9e73', .6)
    p.text(320, 352, '验证 BCE 选模 / 早停', size=7.8)

    p.panel('frame-inference', 409, 325, 249, 66, '最佳权重逐帧推理', 'B', size=9.1)
    p.image('inference-frame', parts.echo_image(frame), 422, 347, 31, 31)
    p.arrow('frame-best', [(458, 363), (471, 363)])
    tensor(p, 'best-model', 477, 352, 12, 24, '#d8e5f2', layers=2)
    p.arrow('best-mask', [(495, 363), (512, 363)])
    mask_shape(p, 'inference-mask', pred, 519, 347, 31, 31)
    p.arrow('mask-overlay', [(555, 363), (570, 363)])
    p.image('inference-overlay', parts.overlay(frame, pred), 579, 347, 31, 31)
    p.text(629, 365, '逐帧', size=7.8)
    p.text(531, 387, '所有帧可预测；中间帧不新增监督标签', size=7.8)
    p.arrow('best-weights-inference', [(398, 363), (407, 363)])

    # Step 3: restore first, then geometry cleaning, contour-derived candidates.
    p.panel('contour-features', 14, 438, 274, 142, '原坐标恢复与轮廓几何', 'C')
    p.image('geometry-prediction', parts.overlay(frame, pred), 27, 477, 52, 52)
    p.text(53, 466, '逐帧预测', size=7.8)
    p.lines(53, 544, ['分割叠加', '处理后坐标'], size=7.8, step=12)
    p.arrow('prediction-geometry', [(84, 502), (106, 502)])
    parts.geometry(p, s, 115, 478, 55, 78, labels=False, disks=True)
    p.text(157, 466, '原图坐标与 20 盘径', size=7.8)
    p.lines(228, 478, ['A  面积', 'L  长轴', 'di  盘径'], step=24)
    p.text(153, 573, '坐标恢复 / 清理 → PCA 候选点（需复核）', size=7.8)
    p.panel('volume-estimation', 302, 438, 356, 142, '空间标定后的单 / 双平面容积估算', 'C')
    for view, x in [('2CH', 315), ('4CH', 366)]:
        parts.geometry(p, samples[view], x, 481, 35, 60, labels=False, disks=True)
        p.text(x + 18, 472, view, size=7.8)
    p.arrow('paired-geometries-disks', [(405, 505), (417, 505)])
    # The disk width uses saved diameters, scaled together, not fabricated 3-D.
    d = np.sqrt(np.array(samples['2CH']['features']['diameters_mm']) *
                np.array(samples['4CH']['features']['diameters_mm']))
    for i, width in enumerate(d / d.max() * 41):
        elem(p.group, 'ellipse', cx=449, cy=472 + i * 3.15, rx=width / 2,
             ry=3.7, fill='#ecd4ad' if i == 10 else '#e2e9ce',
             stroke='#8b9874', stroke_width=.5)
    p.text(449, 552, '20 盘示意', size=7.8)
    p.box('single-volume', 483, 468, 162, 33,
          ['单平面面积–长度', 'V = 8A² / (3πL) / 1000'], '#eef3e6', size=8.2)
    p.box('biplane-volume', 483, 510, 162, 45,
          ['双平面椭圆盘', 'V = Σ[π d2i d4i / 4] × ΔL / 1000',
           'ΔL = min(L2,L4) / 20'], '#e9eff7', size=8.2)
    p.text(362, 570, '同患者、同 ED / ES 配对', size=7.8)
    p.text(566, 570, 'A：mm²；L / d：mm；V：mL', size=7.8)
    p.arrow('contour-to-volumes', [(290, 511), (300, 511)])

    # Step 4: functional parameters plus reference tiers, without invented results.
    p.panel('sv-ef', 14, 629, 397, 80, '由有效 EDV / ESV 计算 SV / EF', 'D')
    from src.data.transforms import Transform
    from src.geometry.mask_features import main_component
    tr = s['meta']['audit']['transform']
    transform = Transform(tuple(tr['original_hw']), tuple(tr['crop_xyxy']), tuple(tr['output_hw']))
    masks = [main_component(transform.restore_mask(s['prediction'][i]))[0] for i in (ed, es)]
    yy, xx = np.where(masks[0] | masks[1])
    for i, mask in enumerate(masks):
        crop = mask[yy.min():yy.max() + 1, xx.min():xx.max() + 1]
        mask_shape(p, 'function-phase-' + str(i), crop, 26 + i * 46, 653, 33, 37)
        p.text(42 + i * 46, 702, 'EDV' if i == 0 else 'ESV', size=7.8)
    p.arrow('phases-sv', [(114, 673), (139, 673)])
    p.box('stroke-volume', 146, 652, 109, 47,
          ['每搏量 SV', 'EDV − ESV', 'mL'], '#fbf3d9')
    p.arrow('sv-ef', [(260, 673), (274, 673)])
    p.box('ejection-fraction', 282, 652, 117, 47,
          ['射血分数 EF', '100 × SV / EDV', '%'], '#f4e8d3')
    p.panel('reference-tiers', 14, 719, 397, 92, '结构评价与功能参考分层', 'D')
    p.image('evaluation-prediction', parts.overlay(frame, pred), 25, 745, 34, 29)
    p.image('evaluation-expert', parts.overlay(frame, s['arrays']['masks'][ed], (63, 146, 132)),
            69, 745, 34, 29)
    p.text(42, 783, '预测', size=7.8)
    p.text(86, 783, '专家', size=7.8)
    p.text(65, 796, 'Dice / ASSD / HD95', size=7.8)
    p.text(65, 807, '原始掩膜 · 原图坐标', size=7.8)
    p.line(119, 740, 119, 801, '#b7ad73', .7)
    p.box('contour-reference', 130, 742, 133, 28,
          ['同法轮廓参考', 'EDV / ESV / SV / EF'], '#edf1e3', size=7.8)
    p.box('reported-reference', 273, 742, 125, 28,
          ['CAMUS 报告 EF', 'Info.cfg · 单独报告'], '#e9eff7', size=7.8)
    p.text(264, 786, '患者级误差 / 一致性 / CI / 覆盖率', size=7.8)
    p.text(264, 803, '人工点 / 独立临床参考缺失：null + 原因', size=7.8)

    # Step 5 is a clearly conditional extension rather than completed hardware.
    p.panel('patch-extension', 440, 629, 216, 182, '待接入与待外部验证', 'E')
    elem(p.group, 'circle', cx=475, cy=663, r=8, fill='#f7eee7',
         stroke='#b69e91', stroke_width=.7)
    p.path('M 454 709 L 456 685 Q 457 678 466 677 L 485 677 Q 494 678 495 686 L 497 709 Z',
           '#b69e91', .8, '#f8f1eb')
    p.path('M 474 692 C 466 683 459 694 474 704 C 489 694 482 683 474 692 Z',
           '#ca8f89', .7, '#eed7d5')
    p.rect(480, 681, 22, 8, '#b8c9dc', '#7e94ac', radius=2)
    p.text(477, 724, '贴片采集示意', size=7.8)
    p.arrow('patch-calibration', [(507, 689), (533, 689)], dash='1 2')
    elem(p.group, 'circle', cx=568, cy=680, r=17, fill='#f5edf6',
         stroke='#a48cab', stroke_width=.8)
    p.line(568, 680, 568, 668, '#a48cab', 1)
    p.line(568, 680, 577, 686, '#a48cab', 1)
    p.rect(542, 704, 52, 7, '#e8e1ef', '#a48cab', radius=0)
    for i in range(9):
        p.line(545 + i * 5.5, 704, 545 + i * 5.5, 708, '#a48cab', .5)
    p.text(573, 724, '空间 / 时间标定', size=7.8)
    p.arrow('calibration-validation', [(573, 729), (573, 736)], dash='1 2')
    p.box('external-validation', 452, 738, 190, 31,
          ['跨设备验证 + 有来源的独立参考', '接入既有推理 / 几何流程'], '#f3eaf5', size=7.8)
    p.text(548, 784, '完整周期或可靠参考 HR 后评价', size=7.8)
    p.text(548, 802, 'CO = SV × HR / 1000   (L/min)', size=8.6)
    footer(p)
    return p


def hospital(p, x, y, color, scale=1):
    p.rect(x, y, 12 * scale, 17 * scale, 'white', color, radius=0)
    p.line(x + 4 * scale, y + 4 * scale, x + 8 * scale, y + 4 * scale, color, .8)
    p.line(x + 6 * scale, y + 2 * scale, x + 6 * scale, y + 6 * scale, color, .8)
    for i in range(3):
        p.line(x + 3 * scale, y + (9 + i * 3) * scale,
               x + 9 * scale, y + (9 + i * 3) * scale, color, .5)


def mlp(p, key, x, y, w=43, h=46):
    p.rect(x - 6, y - 5, w + 12, h + 10, '#eef2f7', '#9eaebb', radius=5)
    columns = [[(x + j * w / 2, y + i * h / (n - 1)) for i in range(n)]
               for j, n in enumerate([3, 4, 3])]
    with p.group_id('n-' + key, 'network-schematic'):
        for left, right in zip(columns, columns[1:]):
            for a in left:
                for b in right:
                    p.line(*a, *b, '#75848a', .4)
        for col in columns:
            for xx, yy in col:
                elem(p.group, 'circle', cx=xx, cy=yy, r=3.6,
                     fill='#ead8e2', stroke='#9eaebb', stroke_width=.5)


def build_reference():
    p = Figure('01_reference_vector', '用户参考图的可编辑矢量结构重建', font='Arial')
    reference = Image.open(SOURCE).convert('RGB')

    def crop(key, box, x, y, w, h):
        p.image('reference-' + key, reference.crop(box), x, y, w, h, colors=40, max_size=190)

    # Source-specific labels are retained here only, never transplanted to project.
    p.band('reference-data', 5, 7, 662, 163,
           'Step 1. Data collection and tumor segmentation', 'A')
    p.panel('ici-cohort', 13, 30, 219, 135, 'ICI cohort', 'A', size=10)
    for i, color in enumerate(['#d6afb3', '#d8b9a6', '#c9c6a0']):
        hospital(p, 36 + i * 13, 60 + (i % 2) * 3, color)
    p.text(53, 102, 'WHUH+HCH+APH', size=8.2)
    p.arrow('ref-randomization', [(73, 77), (119, 77)])
    p.text(98, 69, 'Random ratio', size=7.8)
    p.text(101, 88, '7:3', size=7.8)
    p.path('M 129 55 L 121 55 L 121 101 L 129 101', INK, 1)
    p.box('ref-train', 132, 47, 91, 17, 'Training set (n=456)', '#f7e5d7', size=8.2)
    p.box('ref-internal', 132, 86, 91, 27,
          ['Internal validation', 'set (n=196)'], '#f7e5d7', size=8.2)
    for i, color in enumerate(['#c4d2b1', '#b5cbd9', '#ccc1d5', '#d4d6c5']):
        hospital(p, 43 + i % 2 * 18, 119 + i // 2 * 12, color, scale=.7)
    p.text(68, 158, 'XYH+HBCH+SAHMU+TFCH', size=7.8)
    p.arrow('ref-external', [(100, 136), (122, 136)])
    p.box('ref-external-set', 132, 124, 91, 27,
          ['External test set', '(n=180)'], '#f7e5d7', size=8.2)
    p.panel('biological-cohorts', 240, 30, 194, 135,
            'Biological interpretation cohorts', 'A', size=9.4)
    for i, (short, lines, color) in enumerate([
        ('TCGA-LIHC', ['TCGA-LIHC cohort', '(n=39)'], '#91b7ca'),
        ('TCGA-LIHC+', ['WSI cohort (n=396)'], '#b5c5af'),
        ('WHUH', ['scRNA-seq cohort', '(n=6)'], '#d5b3bf'),
    ]):
        yy = 51 + i * 41
        hospital(p, 274, yy, color)
        p.text(283, yy + 27, short, size=7.8)
        if i == 1:
            p.text(283, yy + 37, 'APH+SRRSH', size=7.8)
        p.arrow('ref-cohort-' + str(i), [(303, yy + 9), (326, yy + 9)])
        p.box('ref-bio-' + str(i), 331, yy - 2, 94, 29, lines, '#f7e5d7', size=8.2)
    p.panel('tumor', 443, 30, 217, 135, 'Tumor segmentation', 'A', size=10)
    crop('ct-before', (907, 84, 1078, 215), 454, 45, 84, 65)
    crop('ct-after', (1088, 197, 1265, 328), 546, 101, 87, 62)
    crop('tumor-mask', (1213, 91, 1290, 167), 609, 48, 37, 37)
    p.path('M 493 114 C 486 137 507 142 522 139', '#c69867', 2)
    p.arrow('ref-tumor-net', [(522, 139), (528, 137)], '#c69867')
    p.text(489, 150, 'nnU-Net', size=8.2)
    p.line(541, 97, 602, 71, '#b59c7d', .8, dash='1 2')

    p.band('reference-features', 5, 173, 662, 157,
           'Step 2. Feature extraction and selection', 'B')
    p.panel('habitats', 13, 195, 286, 129, 'Habitat features', 'B', size=10)
    crop('habitat-maps', (40, 418, 252, 518), 22, 210, 104, 49)
    crop('habitat-ct', (123, 523, 268, 642), 62, 263, 72, 58)
    p.path('M 30 259 C 10 283 20 302 54 303', '#8fa767', 4)
    p.arrow('ref-habitat-ct', [(54, 303), (61, 301)], '#8fa767')
    p.arrow('ref-habitat-shape', [(138, 270), (160, 270)])
    p.rect(164, 210, 68, 111, '#edf3df', '#9eb185', radius=10)
    for i, label in enumerate(['Shape', 'First order', 'Texture']):
        p.box('ref-feature-' + str(i), 172, 214 + i * 25, 52, 22, label,
              'white', size=8.2)
    p.lines(198, 295, ['GLCM  GLRLM', 'GLSZM  GLDM', 'NGTDM'], step=9, size=7.8)
    p.arrow('ref-feature-select', [(236, 269), (269, 269)])
    p.text(254, 284, 'Selection', size=7.8)
    tensor(p, 'ref-feature-vector', 279, 237, 9, 38, '#e5edd7', layers=2)
    p.panel('deep-features', 306, 195, 354, 129, '2.5D deep learning features', 'B', size=10)
    crop('2point5d-input', (620, 418, 791, 484), 314, 210, 84, 32)
    crop('2point5d-stack', (715, 496, 838, 616), 353, 252, 62, 59)
    p.arrow('ref-stack', [(323, 245), (323, 275), (350, 275)])
    p.text(426, 226, 'ImageNet', size=8.2)
    p.arrow('ref-imagenet', [(451, 224), (483, 224)])
    p.text(503, 241, 'DenseNet121', size=8.2)
    p.text(585, 230, 'Transfer learning', size=8.2)
    crop('densenet', (864, 490, 1246, 617), 433, 251, 184, 61)
    p.arrow('ref-stack-net', [(417, 275), (430, 275)])
    p.arrow('ref-net-features', [(621, 276), (639, 276)])
    tensor(p, 'ref-deep-vector', 643, 222, 9, 38, '#d8e5f2', layers=2)
    p.text(525, 320, 'Pretrained DenseNet121', size=8.2)

    p.band('reference-model', 5, 334, 662, 194,
           'Step 3. ECOS-Net and model construction', 'C')
    p.panel('ecos-net', 13, 353, 503, 170, 'ECOS-Net', 'C', size=10)
    p.panel('clinical', 526, 353, 134, 170, 'Clinical models', 'C', size=10)
    for i, yy in enumerate((385, 463)):
        tensor(p, 'ref-input-' + str(i), 60, yy, 8, 34,
               '#e5edd7' if i == 0 else '#d8e5f2', layers=2)
        p.text(61, yy - 9, 'Habitat' if i == 0 else '2.5D features', size=7.8)
        p.arrow('ref-encoder-in-' + str(i), [(75, yy + 18), (96, yy + 18)])
        mlp(p, 'ref-encoder-' + str(i), 107, yy - 1, w=37, h=36)
        p.text(124, yy + 47, 'MLP Encoder', size=7.8)
    p.box('ref-concat', 164, 374, 51, 70, ['Concat', 'Feature', 'fusion'], '#eff4e8', size=8.2)
    p.arrow('ref-upper-fusion', [(153, 404), (162, 404)])
    p.arrow('ref-lower-fusion', [(153, 482), (160, 482), (160, 422), (162, 422)])
    p.box('ref-transformer', 228, 374, 110, 70,
          ['Multi-head attention', 'Add & Norm', 'FFN + Add & Norm', 'Transformer'],
          '#fbf1d8', size=8.2)
    p.arrow('ref-fusion-transformer', [(217, 409), (226, 409)])
    p.box('ref-attention', 169, 452, 90, 62,
          ['Multi-head attention', 'Q / K / V', 'Scaled dot product', 'Concat + Linear'],
          '#e5edd7', size=7.8)
    p.box('ref-layernorm', 270, 452, 67, 62,
          ['LayerNorm', 'Z', 'Feature axes'], '#fbeddc', size=7.8)
    tensor(p, 'ref-output-tensor', 354, 379, 24, 58, '#e5edd7', layers=5)
    p.text(391, 378, 'GAP', size=8.2)
    p.arrow('ref-transformer-gap', [(339, 409), (350, 409)])
    p.box('ref-ffn', 348, 452, 65, 62, ['FFN', 'Projection'], '#f8f0cc', size=8.2)
    for i, yy in enumerate((382, 464)):
        mlp(p, 'ref-head-' + str(i), 438, yy, w=22, h=35)
        p.arrow('ref-head-link-' + str(i), [(466, yy + 18), (480, yy + 18)])
        p.rect(485, yy + 5, 11, 25, '#e5edd7' if i == 0 else '#d8e5f2', '#8c9ca3', radius=0)
        p.text(473, yy + 49, 'Classification' if i == 0 else 'Prognostic', size=7.8)
        p.text(474, yy + 59, 'Head', size=7.8)
    p.arrow('ref-gap-heads', [(389, 408), (425, 408)])
    parts.document(p, 540, 420, '#e7e7e7')
    p.text(558, 474, 'Clinical data', size=8.2)
    p.arrow('ref-clinical-branch', [(578, 440), (589, 440)])
    crop('clinical-class', (1201, 754, 1295, 849), 598, 380, 48, 48)
    crop('clinical-survival', (1204, 888, 1303, 991), 598, 456, 48, 48)
    p.text(619, 442, 'Clinical-DC', size=8.2)
    p.text(619, 518, 'Clinical-OS', size=8.2)

    p.band('reference-evaluation', 5, 532, 392, 315,
           'Step 4. Model evaluation and stratified analysis', 'D')
    p.panel('performance', 12, 552, 378, 191, 'Performance metrics', 'D', size=10)
    for key, box, x, y, w, h, label in [
        ('roc', (43, 1131, 225, 1290), 22, 572, 88, 77, 'ROC curve'),
        ('radar', (232, 1131, 403, 1290), 119, 572, 83, 77, 'Radar'),
        ('calibration', (432, 1131, 592, 1290), 213, 572, 78, 77, 'Calibration'),
        ('dca', (620, 1132, 773, 1290), 303, 572, 75, 77, 'DCA curve'),
        ('cindex', (155, 1317, 363, 1457), 77, 664, 104, 69, 'C-index'),
        ('timeauc', (479, 1317, 687, 1457), 240, 664, 104, 69, 'Time-dependent AUC'),
    ]:
        crop(key, box, x, y, w, h)
        p.text(x + w / 2, y + h + 10, label, size=8.2)
    p.panel('stratification', 12, 752, 378, 91, 'Stratified analysis', 'D', size=10)
    crop('tumor-response', (44, 1527, 186, 1660), 22, 770, 70, 64)
    p.box('ref-high-prob', 109, 771, 85, 25, 'Higher probability', '#fffaf0', size=7.8)
    p.box('ref-low-prob', 109, 807, 85, 25, 'Lower probability', '#fffaf0', size=7.8)
    people(p, 215, 785, '#f1df93', count=2, scale=1.2)
    p.box('ref-high-risk', 250, 771, 55, 25, 'Higher risk', '#fffaf0', size=7.8)
    p.box('ref-low-risk', 250, 807, 55, 25, 'Lower risk', '#fffaf0', size=7.8)
    crop('survival', (628, 1529, 774, 1662), 314, 770, 67, 62)
    p.text(57, 843, 'Tumor response', size=7.8)
    p.text(342, 843, 'Kaplan-Meier', size=7.8)

    p.band('reference-interpretation', 402, 532, 265, 315,
           'Step 5. Biological interpretation', 'E')
    p.panel('multiomics', 409, 552, 251, 94, 'Multi-omics analysis', 'E', size=10)
    crop('enrichment', (836, 1142, 1049, 1269), 419, 575, 102, 60)
    crop('genomic', (1095, 1143, 1310, 1270), 548, 575, 102, 60)
    p.text(470, 643, 'Gene enrichment', size=8.2)
    p.text(599, 643, 'Genomic landscape', size=8.2)
    p.panel('pathology', 409, 657, 251, 95, 'Digital pathology quantitative analysis', 'E', size=10)
    crop('wsi', (829, 1335, 1034, 1466), 420, 680, 98, 61)
    crop('cells', (1093, 1334, 1305, 1464), 550, 680, 99, 61)
    p.arrow('ref-cellvit', [(523, 709), (547, 709)])
    p.text(536, 728, 'CellViT', size=7.8)
    p.text(468, 749, 'Whole-slide image', size=8.2)
    p.text(600, 749, 'Cell segmentation', size=8.2)
    p.panel('scrna', 409, 763, 251, 80, 'scRNA-seq analysis', 'E', size=10)
    crop('celltype', (829, 1540, 1041, 1658), 420, 784, 98, 53)
    crop('pathways', (1091, 1540, 1303, 1662), 550, 784, 98, 53)
    p.text(469, 845, 'Cell type annotation', size=8.2)
    p.text(599, 845, 'Pathway analysis', size=8.2)
    p.text(10, 861, '用户参考图的矢量结构重建；影像、图表及细部为量化描摹，不恢复原始医学或曲线数据。',
           size=8.2, anchor='start')
    p.text(10, 873, '仅供版式研究。原图来源与再发布许可未提供；主标签可编辑，缩略图内部小字为路径。',
           size=8.2, anchor='start')
    # The footer is Chinese; use the project font for those two labels.
    for t in list(p.root.iter('{' + NS + '}text'))[-2:]:
        t.set('font-family', FONT)
    return p


def export(p):
    """Paint shapes then native text; validate measured text instead of guesses."""
    root = p.root
    shapes = deepcopy(root)
    for parent in shapes.iter():
        for child in list(parent):
            if child.tag == '{' + NS + '}text':
                parent.remove(child)
    renderer = QSvgRenderer(QByteArray(ET.tostring(shapes)))
    if not renderer.isValid():
        raise RuntimeError('SVG renderer rejected ' + p.name)
    labels = list(root.iter('{' + NS + '}text'))
    owners = {}
    for group in root.iter('{' + NS + '}g'):
        if group.get('data-role') == 'node':
            rect = group.find('{' + NS + '}rect')
            if rect is not None:
                bounds = QRectF(*[float(rect.get(k)) for k in ('x', 'y', 'width', 'height')])
                owners.update({id(t): (group.get('id'), bounds) for t in group.findall('{' + NS + '}text')})

    def paint(device, area):
        painter = QPainter(device)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        painter.translate(area.x(), area.y())
        painter.scale(area.width() / W, area.height() / H)
        renderer.render(painter, QRectF(0, 0, W, H))
        records, defects = [], []
        for label in labels:
            precision = 100
            font = QFont(label.get('font-family'))
            font.setPixelSize(round(float(label.get('font-size')) * precision))
            font.setBold(label.get('font-weight') == '700')
            font.setHintingPreference(QFont.PreferNoHinting)
            metrics = QFontMetricsF(font, device)
            text = label.text or ''
            missing = [c for c in text if not c.isspace() and not metrics.inFontUcs4(ord(c))]
            if missing:
                defects.append(f'missing glyphs: {missing}')
            x, y = float(label.get('x')), float(label.get('y'))
            text_width = metrics.horizontalAdvance(text) / precision
            if label.get('text-anchor') == 'middle':
                x -= text_width / 2
            elif label.get('text-anchor') == 'end':
                x -= text_width
            b = metrics.tightBoundingRect(text)
            bounds = QRectF(b.x() / precision + x, b.y() / precision + y,
                            b.width() / precision, b.height() / precision)
            painter.save()
            painter.scale(1 / precision, 1 / precision)
            painter.setFont(font)
            painter.setPen(QColor(label.get('fill', INK)))
            painter.drawText(QPointF(x * precision, y * precision), text)
            painter.restore()
            if not QRectF(0, 0, W, H).contains(bounds):
                defects.append('outside canvas: ' + text)
            if id(label) in owners:
                key, owner = owners[id(label)]
                if not owner.adjusted(1.2, 1.2, -1.2, -1.2).contains(bounds):
                    defects.append(f'outside node {key}: {text}')
            records.append({'text': text, 'bounds': [bounds.x(), bounds.y(), bounds.width(), bounds.height()]})
        painter.end()
        for i, first in enumerate(records):
            a = QRectF(*first['bounds'])
            for second in records[i + 1:]:
                overlap = a.intersected(QRectF(*second['bounds']))
                if overlap.width() > .4 and overlap.height() > .4:
                    defects.append(f'text overlap: {first["text"]} / {second["text"]}')
        return records, sorted(set(defects))

    png = QImage(round(WIDTH_MM / 25.4 * DPI), round(HEIGHT_MM / 25.4 * DPI),
                 QImage.Format_ARGB32_Premultiplied)
    png.fill(Qt.white)
    png.setDotsPerMeterX(round(DPI / .0254))
    png.setDotsPerMeterY(round(DPI / .0254))
    records, defects = paint(png, QRectF(0, 0, png.width(), png.height()))
    png.save(str(OUT / (p.name + '.png')), 'PNG')
    if p.name == '03_project_workflow':
        with Image.open(OUT / (p.name + '.png')) as preview:
            preview.resize((1080, round(1080 * H / W)), Image.Resampling.LANCZOS).save(
                OUT / (p.name + '.preview.png'))
            for key, bounds in {
                'data_detail': (0, 48, 672, 190),
                'network_detail': (0, 218, 672, 402),
                'geometry_detail': (0, 410, 672, 592),
                'function_extension_detail': (0, 600, 672, 822),
            }.items():
                crop = tuple(round(v * preview.width / W) for v in bounds)
                preview.crop(crop).save(OUT / 'qa' / (key + '.png'))
    pdf = QPdfWriter(str(OUT / (p.name + '.pdf')))
    pdf.setResolution(DPI)
    page = QPageSize(QSizeF(WIDTH_MM, HEIGHT_MM), QPageSize.Millimeter, p.name)
    if not pdf.setPageLayout(QPageLayout(page, QPageLayout.Portrait, QMarginsF(0, 0, 0, 0),
                                         QPageLayout.Millimeter)):
        raise RuntimeError('Could not set PDF page size')
    pdf.setTitle(p.root.get('aria-label'))
    pdf.setCreator('Editable SVG workflow export')
    _, pdf_defects = paint(pdf, QRectF(pdf.pageLayout().paintRectPixels(DPI)))
    defects = sorted(set(defects + pdf_defects))
    ids = [e.get('id') for e in root.iter() if e.get('id')]
    duplicate_ids = [key for key, count in Counter(ids).items() if count > 1]
    if duplicate_ids:
        defects.append('duplicate ids: ' + str(duplicate_ids))
    raster_count = sum(e.tag == '{' + NS + '}image' for e in root.iter())
    report = {'name': p.name, 'size_mm': [WIDTH_MM, HEIGHT_MM],
              'png_pixels': [png.width(), png.height()], 'dpi': DPI,
              'native_text_elements': len(labels), 'raster_image_elements': raster_count,
              'live_text': True, 'quantized_traces': p.trace_records,
              'checks': 'PASS' if not defects else 'FIX REQUIRED',
              'defects': defects, 'text_bounds': records}
    (OUT / 'qa' / (p.name + '.export.json')).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(p.name + ': ' + report['checks'] + ', ' + str(len(labels)) + ' live labels')
    for defect in defects:
        print('  ' + defect)
    return report


def main():
    app = QGuiApplication.instance() or QGuiApplication([])
    for family in [FONT, 'Arial']:
        if family not in QFontDatabase().families():
            raise RuntimeError('Required font unavailable: ' + family)
    (OUT / 'qa').mkdir(exist_ok=True)
    samples, manifest = parts.load_examples()
    patient_counts = Counter({})
    for split in ('train', 'val', 'test'):
        patient_counts[split] = len({r['patient_id'] for r in manifest['cases'] if r['split'] == split})
    assert dict(patient_counts) == {'train': 347, 'val': 71, 'test': 82}, patient_counts
    assert len(manifest['cases']) == 1000
    assert sum(r['labeled_frames'] for r in manifest['cases']) == 2000
    builds = [('reference', build_reference), ('layout', build_layout),
              ('project', lambda: build_project(samples, manifest))]
    reports = []
    for phase, build in builds:
        figure = build()
        figure.write()
        reports.append(export(figure))
    provenance_paths = [SOURCE, PROJECT / 'configs/camus_splits.json',
                        PROJECT / 'configs/experiment.yaml', PROJECT / 'configs/train/baseline.yaml',
                        PROJECT / 'data/processed/camus/manifest.json']
    for view in ('2CH', '4CH'):
        provenance_paths.extend([PROJECT / f'data/processed/camus/patient0008_{view}.npz',
                                 PROJECT / f'data/processed/camus/patient0008_{view}.json',
                                 PROJECT / f'runs/validation_camus_regularized/patient0008_{view}_pred.npz'])
    provenance = {
        'date': '2026-11-17', 'scope': 'vector_workflow_artifacts_only_not_new_experiments',
        'reference_reuse': 'traced_only_in_01_reference_vector_style_only_in_project_figure',
        'reference_source': 'user_supplied_image_original_publication_and_license_not_provided',
        'project_examples': {'patient': 'patient0008', 'split': 'val',
                             'selection': 'fixed_previous_example_not_selected_by_test_metrics'},
        'patient_counts': dict(patient_counts), 'sequences': len(manifest['cases']),
        'labeled_frames': sum(r['labeled_frames'] for r in manifest['cases']),
        'thumbnail_transformation': 'display_quantization_and_run_length_vector_paths_not_measurement_input',
        'clinical_validation': False, 'author_scientific_review': 'pending',
        'input_sha256': {str(path.relative_to(PROJECT)).replace('\\', '/'): digest(path)
                         for path in provenance_paths},
        'exports': {r['name']: {'checks': r['checks'], 'native_text_elements': r['native_text_elements'],
                               'raster_image_elements': r['raster_image_elements']}
                    for r in reports},
    }
    (OUT / 'qa/provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n',
                                           encoding='utf-8')
    if any(r['defects'] for r in reports):
        raise SystemExit('Fix the reported layout defects, then rebuild.')
    return app


if __name__ == '__main__':
    main()
