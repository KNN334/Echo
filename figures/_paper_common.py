"""Shared source handling and calibrated display; no analysis-model fitting."""
import csv
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path

import numpy as np
from matplotlib.patches import Rectangle

from style.palette import CMAPS, COLORS, LINEWIDTH, MM_PER_INCH
from src.data.transforms import Transform

ROOT = Path(__file__).resolve().parents[1]
PREPARED = ROOT / 'data/processed/camus'
RUN = ROOT / 'runs/camus_cuda_progress'
FROZEN = ROOT / 'reports/result_analysis/camus_cuda_progress'


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_csv(path, rows):
    with Path(path).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def provenance(out, sources, **details):
    """Recheck every used source that belongs to the pre-existing freeze."""
    frozen = read_json(FROZEN / 'analysis_manifest.json')
    sources = [*sources, FROZEN / 'analysis_manifest.json',
               ROOT / 'style/palette.py', ROOT / 'style/paper.mplstyle', Path(__file__)]
    hashes = {Path(p).relative_to(ROOT).as_posix(): digest(p) for p in sources}
    checked = []
    for name, value in hashes.items():
        if name in frozen['sources_sha256']:
            assert value == frozen['sources_sha256'][name], f'Frozen source changed: {name}'
            checked.append(name)
    write_json(out / 'provenance.json', {
        'experiment': 'camus_cuda_progress', 'new_training_or_inference': False,
        'test_feedback_used_for_model_selection': False,
        'sources_sha256': hashes, 'existing_frozen_sources_rechecked': checked,
        'versions': {name: importlib.metadata.version(name)
                     for name in ['matplotlib', 'numpy', 'Pillow', 'cmcrameri']},
        **details})


class Canvas:
    """Position final-size elements in millimetres, without tight export crops."""
    def __init__(self, fig):
        self.fig = fig
        self.width, self.height = fig.get_size_inches() * MM_PER_INCH

    def axes(self, x, y, width, height):
        return self.fig.add_axes([x/self.width, y/self.height, width/self.width, height/self.height])

    def text(self, x, y, text, **kwargs):
        return self.fig.text(x/self.width, y/self.height, text, **kwargs)

    def card(self, x, y, width, height, title, lines, color='axis'):
        ax = self.axes(x, y, width, height)
        ax.set_axis_off()
        ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                               facecolor=COLORS['background'], edgecolor=COLORS[color],
                               linewidth=LINEWIDTH['comparison'], clip_on=False))
        self.text(x+2, y+height-5, title, fontweight='bold', color=COLORS[color])
        for index, line in enumerate(lines):
            self.text(x+2, y+height-10-index*4.5, line)
        return ax


def load_case(case):
    meta_path = PREPARED / (case + '.json')
    cache_path = PREPARED / (case + '.npz')
    pred_path = RUN / (case + '_pred.npz')
    meta = read_json(meta_path)
    with np.load(cache_path, allow_pickle=False) as cache:
        arrays = {name: cache[name] for name in ['frames', 'original_gt', 'original_gt_indices', 'labeled']}
    with np.load(pred_path, allow_pickle=False) as pred:
        arrays['prediction'] = pred['masks']
    assert arrays['frames'].shape == arrays['prediction'].shape
    assert arrays['frames'].shape[1:] == (112, 112)
    assert set(arrays['original_gt_indices']) == set(meta['phases'].values())
    assert meta['sequence_type'] == 'half_sequence' and meta['split'] == 'test'
    return meta, arrays, [meta_path, cache_path, pred_path]


def calibrated_overlay(ax, meta, arrays, phase, field_mm=None, contours=True, scale=True):
    """112-cache image; original expert and restored prediction in physical mm.

    A shared field_mm adds black padding only. It never crops or stretches an
    image. Original pixel centres and half-pixel resize edges are respected.
    """
    index = meta['phases'][phase]
    tr = meta['audit']['transform']
    sx, sy = meta['audit']['spacing_xy_mm']
    x0, y0, x1, y1 = tr['crop_xyxy']
    extent = [(x0-.5)*sx, (x1-.5)*sx, (y1-.5)*sy, (y0-.5)*sy]
    ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                           facecolor=COLORS['image_background'], edgecolor='none', zorder=-10))
    ax.imshow(arrays['frames'][index], cmap=CMAPS['image'], vmin=0, vmax=255,
              extent=extent, origin='upper', interpolation='none', aspect='equal')
    if contours:
        slot = list(arrays['original_gt_indices']).index(index)
        truth = arrays['original_gt'][slot]
        transform = Transform(tuple(tr['original_hw']), tuple(tr['crop_xyxy']), tuple(tr['output_hw']))
        prediction = transform.restore_mask(arrays['prediction'][index])
        h, w = truth.shape
        assert prediction.shape == truth.shape == tuple(tr['original_hw'])
        x, y = np.arange(w)*sx, np.arange(h)*sy
        ax.contour(x, y, truth, levels=[.5], colors=[COLORS['expert_contour']],
                   linestyles='--', linewidths=LINEWIDTH['reference'])
        ax.contour(x, y, prediction, levels=[.5], colors=[COLORS['primary']],
                   linewidths=LINEWIDTH['primary'])
    cx, cy = np.mean(extent[:2]), np.mean(extent[2:])
    fw, fh = field_mm if field_mm is not None else (extent[1]-extent[0], extent[2]-extent[3])
    assert fw+1e-6 >= extent[1]-extent[0] and fh+1e-6 >= extent[2]-extent[3], 'Display would crop data'
    ax.set(xlim=(cx-fw/2, cx+fw/2), ylim=(cy+fh/2, cy-fh/2))
    ax.set_axis_off()
    if scale:
        right, bottom = cx+fw/2, cy+fh/2
        ax.plot([right-50, right-30], [bottom-12, bottom-12],
                 color=COLORS['image_annotation'], linewidth=LINEWIDTH['scale'])
        ax.text(right-40, bottom-20, '20 mm', ha='center', color=COLORS['image_annotation'])
    return {'case_id': meta['patient_id']+'_'+meta['view'], 'phase': phase, 'frame': index,
            'source_image_hw': [112, 112], 'original_hw': tr['original_hw'],
            'original_spacing_xy_mm': [sx, sy],
            'processed_spacing_xy_mm': tr['processed_spacing_xy_mm'],
            'image_extent_mm': extent, 'display_field_mm': [fw, fh],
            'extra_crop': None, 'interpolation': 'none', 'image_limits': [0, 255],
            'brightness_contrast_gamma': 'unchanged', 'roi_reviewed': meta['audit']['roi_reviewed'],
            'contours': 'original expert and original-coordinate restored prediction' if contours else None}


def alignment(fig, out, stem, axes, ids, rows, columns, auditor=None):
    """Always measure physical boxes; optionally run the full external gate."""
    fig.canvas.draw()
    bounds = {name: list(np.array(ax.get_position().bounds)*[fig.get_figwidth()*72,
              fig.get_figheight()*72, fig.get_figwidth()*72, fig.get_figheight()*72])
              for name, ax in zip(ids, axes)}
    for groups, components in [(rows, [1, 2, 3]), (columns, [0, 2, 3])]:
        for group in groups:
            # Column groups used here are equal-span repeated panels.
            for component in components:
                values = [bounds[name][component] for name in group]
                assert np.ptp(values) <= 1.5, (group, component, values)
    write_json(out / (stem+'.plot_rectangles.json'), {'bounds_xywh_pt': bounds, 'tolerance_pt': 1.5,
               'row_groups': rows, 'column_groups': columns})
    if auditor is not None:
        spec = importlib.util.spec_from_file_location('paper_alignment_audit', auditor)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.require_matplotlib_panel_alignment(fig, axes=axes, panel_ids=ids,
             row_groups=rows, column_groups=columns, json_out=out/(stem+'.alignment.json'), strict=True)
