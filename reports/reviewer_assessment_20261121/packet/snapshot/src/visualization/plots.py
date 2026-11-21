"""容积曲线 SVG；无效帧保留断点，不补造连续心搏。"""
import numpy as np


def volume_curve_svg(records):
    """将 frames.csv 的病例记录绘成可嵌入离线 HTML 的双曲线。"""
    values = [float(row['volume_ml']) for row in records if row.get('volume_ml') not in ('', None)]
    values = [value for value in values if np.isfinite(value)]
    if not values:
        return '<p>缺少有效空间标定或分割，暂无绝对容积曲线。</p>'
    low, high = min(values), max(values)
    span = max(high - low, 1.)
    width, height = 900, 220
    parts = [f'<svg viewBox="0 0 {width} {height + 35}" role="img" aria-label="容积曲线，单位毫升">',
             f'<line x1="50" y1="{height}" x2="880" y2="{height}" stroke="#bbb"/>']
    for field, color in [('volume_ml', '#9a9a9a'), ('analysis_volume_ml', '#12648c')]:
        segment = []

        def emit():
            if segment:
                parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(segment)}"/>')

        for index, row in enumerate(records):
            value = row.get(field)
            valid = field == 'volume_ml' or row.get('valid') in (True, 'True')
            if value not in ('', None) and np.isfinite(float(value)) and valid:
                x = 50 + index / max(1, len(records) - 1) * 830
                y = height - 15 - (float(value) - low) / span * (height - 35)
                segment.append(f'{x:.1f},{y:.1f}')
            else:
                emit()
                segment = []
        emit()
    parts.append(f'<text x="3" y="25">{high:.1f}</text><text x="3" y="{height - 10}">{low:.1f}</text>'
                 f'<text x="4" y="{height + 20}">mL</text><text x="400" y="{height + 25}">Frame index</text></svg>')
    return '\n'.join(parts)
