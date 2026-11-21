"""Export the editable SVG with vector shapes and searchable PDF text.

Requires PyQt5. No patient data are accessed and no measurements are plotted.
Run from any directory: python figures/render_method_flow.py
"""
from copy import deepcopy
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from PyQt5.QtCore import QByteArray, QMarginsF, QPointF, QRectF, QSizeF, Qt
from PyQt5.QtGui import (QColor, QFont, QFontDatabase, QFontMetricsF,
                         QGuiApplication, QImage, QPageLayout, QPageSize,
                         QPainter, QPdfWriter)
from PyQt5.QtSvg import QSvgRenderer


DIRECTORY = Path(__file__).resolve().parent
SVG = DIRECTORY / 'camus_method_flow.svg'
DPI = 300
NS = {'svg': 'http://www.w3.org/2000/svg'}


def main():
    app = QGuiApplication.instance() or QGuiApplication([])
    if 'Microsoft YaHei UI' not in QFontDatabase().families():
        raise RuntimeError('Install Microsoft YaHei UI before exporting this figure.')
    source = ET.parse(SVG).getroot()
    width_mm = float(source.attrib['width'].removesuffix('mm'))
    height_mm = float(source.attrib['height'].removesuffix('mm'))
    view = list(map(float, source.attrib['viewBox'].split()))
    # Qt 5 SVG outlines text in PDFs. Render shapes separately, then paint
    # the original SVG text as native text so it remains searchable.
    shapes = deepcopy(source)
    for parent in shapes.iter():
        for child in list(parent):
            if child.tag.endswith('}text'):
                parent.remove(child)
    renderer = QSvgRenderer(QByteArray(ET.tostring(shapes)))
    if not renderer.isValid():
        raise RuntimeError('SVG could not be parsed by the renderer.')
    labels = list(source.findall('.//svg:text', NS))
    owners = {}
    for group in source.findall('svg:g', NS):
        rect = group.find('svg:rect', NS)
        if rect is not None:
            for label in group.findall('svg:text', NS):
                owners[id(label)] = (group.attrib['id'], QRectF(
                    float(rect.attrib['x']), float(rect.attrib['y']),
                    float(rect.attrib['width']), float(rect.attrib['height'])))

    def paint(device, area):
        painter = QPainter(device)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        painter.translate(area.x(), area.y())
        painter.scale(area.width() / view[2], area.height() / view[3])
        renderer.render(painter, QRectF(*view))
        records = []
        for label in labels:
            if 'transform' in label.attrib:
                raise RuntimeError('Transformed text needs an explicit export handler.')
            text = ''.join(label.itertext())
            family = label.attrib['font-family'].split(',')[0].strip()
            font = QFont(family)
            font.setPointSizeF(float(label.attrib['font-size']) * 72 / device.logicalDpiY())
            font.setBold(label.get('font-weight') == '700')
            font.setHintingPreference(QFont.PreferNoHinting)
            metrics = QFontMetricsF(font, device)
            x, y = float(label.attrib['x']), float(label.attrib['y'])
            if label.get('text-anchor') == 'middle':
                x -= metrics.horizontalAdvance(text) / 2
            painter.setFont(font)
            painter.setPen(QColor(label.get('fill', '#172F31')))
            painter.drawText(QPointF(x, y), text)
            bounds = metrics.tightBoundingRect(text).translated(x, y)
            owner = owners.get(id(label))
            if owner and not owner[1].adjusted(1, 1, -1, -1).contains(bounds):
                raise RuntimeError(f'Text exceeds box padding: {owner[0]}: {text}')
            if not QRectF(*view).contains(bounds):
                raise RuntimeError(f'Text extends beyond canvas: {text}')
            records.append({'text': text, 'bounds': [round(bounds.x(), 3),
                            round(bounds.y(), 3), round(bounds.width(), 3),
                            round(bounds.height(), 3)]})
        painter.end()
        for i, first in enumerate(records):
            a = QRectF(*first['bounds'])
            for second in records[i + 1:]:
                overlap = a.intersected(QRectF(*second['bounds']))
                if overlap.width() > 0.3 and overlap.height() > 0.3:
                    raise RuntimeError(f'Overlapping text: {first["text"]} / {second["text"]}')
        return records

    image = QImage(round(width_mm / 25.4 * DPI), round(height_mm / 25.4 * DPI),
                   QImage.Format_ARGB32_Premultiplied)
    image.setDotsPerMeterX(round(DPI / .0254))
    image.setDotsPerMeterY(round(DPI / .0254))
    image.fill(Qt.white)
    paint(image, QRectF(0, 0, image.width(), image.height()))
    if not image.save(str(DIRECTORY / 'camus_method_flow.png'), 'PNG'):
        raise RuntimeError('PNG export failed.')
    pdf = QPdfWriter(str(DIRECTORY / 'camus_method_flow.pdf'))
    pdf.setResolution(DPI)
    page = QPageSize(QSizeF(width_mm, height_mm), QPageSize.Millimeter, 'CAMUS workflow')
    layout = QPageLayout(page, QPageLayout.Portrait, QMarginsF(0, 0, 0, 0),
                        QPageLayout.Millimeter)
    if not pdf.setPageLayout(layout):
        raise RuntimeError('PDF page layout could not be set.')
    pdf.setTitle('CAMUS LV segmentation and functional parameter workflow')
    pdf.setCreator('Editable SVG workflow export')
    records = paint(pdf, QRectF(pdf.pageLayout().paintRectPixels(DPI)))
    report = {
        'scope': 'Schematic export and geometry checks; not clinical validation',
        'width_mm': width_mm, 'height_mm': height_mm, 'dpi': DPI,
        'png_pixels': [image.width(), image.height()],
        'text_elements': len(records), 'text_box_padding': 'PASS',
        'text_overlap': 'PASS', 'text_bounds': records,
    }
    (DIRECTORY / 'method_flow_export_check.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Exported SVG to PNG/PDF with {len(records)} native text labels.')
    return app


if __name__ == '__main__':
    main()
