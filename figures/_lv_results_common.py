"""Calibrated, observed-frame data for descriptive LV results figures.

This module does not run inference, smooth measurements or estimate new phases.
"""
from pathlib import Path

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from style.palette import COLORS, CMAPS, LINEWIDTH, MARKER_SIZE
from src.data.transforms import Transform
from src.geometry.mask_features import mask_features
from _paper_common import FROZEN, ROOT, RUN, load_case, read_csv, read_json

FIELD_MM = (200, 170)


def fixed_examples():
    path = FROZEN / 'source_data/example_selection.csv'
    original = read_csv(path)
    chosen = [next(r for r in original if r['selection'] == label)
              for label in ['Median', 'Lowest']]
    assert [r['case_id'] for r in chosen] == ['patient0327_2CH', 'patient0229_2CH']
    assert [int(r['rank']) for r in chosen] == [83, 1]
    assert all(int(r['of_cases']) == 164 for r in chosen)
    return chosen, path


def geometry_case(case, verify_all=False):
    meta, arrays, sources = load_case(case)
    feature_path = RUN / (case + '_features.json')
    features = read_json(feature_path)['frames']
    n = meta['audit']['n_frames']
    assert meta['phases'] == {'ED': 0, 'ES': n - 1}
    assert sorted(map(int, features)) == list(range(n))
    time = np.asarray(meta['audit']['timestamps_s'], float)
    assert meta['audit']['timestamp_source'] == 'derived_from_fps'
    assert np.allclose(time, np.arange(n) / meta['fps'])
    tr = meta['audit']['transform']
    transform = Transform(tuple(tr['original_hw']), tuple(tr['crop_xyxy']), tuple(tr['output_hw']))
    indices = range(n) if verify_all else meta['phases'].values()
    for index in indices:
        frozen = features[str(index)]
        measured = mask_features(transform.restore_mask(arrays['prediction'][index]),
                                 meta['audit']['spacing_xy_mm'])
        assert measured['valid'] == frozen['valid']
        if frozen['valid']:
            for key in ['area_mm2', 'long_axis_mm', 'volume_ml', 'diameters_mm']:
                assert np.allclose(measured[key], frozen[key], rtol=1e-12, atol=1e-12), (case, index, key)
    return meta, arrays, features, time, [*sources, feature_path]


def expert_features(meta, arrays, phase):
    index = meta['phases'][phase]
    slot = list(arrays['original_gt_indices']).index(index)
    value = mask_features(arrays['original_gt'][slot], meta['audit']['spacing_xy_mm'])
    assert value['valid']
    return value


def observed_overlay(ax, meta, arrays, index, scale=False, label=None):
    """One real cache frame; physical aspect, unchanged gray window, no crop."""
    tr = meta['audit']['transform']
    sx, sy = meta['audit']['spacing_xy_mm']
    x0, y0, x1, y1 = tr['crop_xyxy']
    extent = [(x0-.5)*sx, (x1-.5)*sx, (y1-.5)*sy, (y0-.5)*sy]
    ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                          facecolor=COLORS['image_background'], edgecolor='none', zorder=-10))
    ax.imshow(arrays['frames'][index], cmap=CMAPS['image'], vmin=0, vmax=255,
              extent=extent, origin='upper', interpolation='none', aspect='equal')
    transform = Transform(tuple(tr['original_hw']), tuple(tr['crop_xyxy']), tuple(tr['output_hw']))
    prediction = transform.restore_mask(arrays['prediction'][index])
    h, w = prediction.shape
    x, y = np.arange(w)*sx, np.arange(h)*sy
    expert_available = index in arrays['original_gt_indices']
    if expert_available:
        slot = list(arrays['original_gt_indices']).index(index)
        ax.contour(x, y, arrays['original_gt'][slot], levels=[.5],
                   colors=[COLORS['expert_contour']], linestyles='--',
                   linewidths=LINEWIDTH['reference'])
    ax.contour(x, y, prediction, levels=[.5], colors=[COLORS['primary']],
               linewidths=LINEWIDTH['primary'])
    cx, cy = np.mean(extent[:2]), np.mean(extent[2:])
    fw, fh = FIELD_MM
    assert fw >= extent[1]-extent[0] and fh >= extent[2]-extent[3], 'No image crop allowed'
    ax.set(xlim=(cx-fw/2, cx+fw/2), ylim=(cy+fh/2, cy-fh/2))
    ax.set_axis_off()
    if label:
        ax.text(.04, .96, label, transform=ax.transAxes, ha='left', va='top',
                color=COLORS['image_annotation'])
    if scale:
        right, bottom = cx+fw/2, cy+fh/2
        ax.plot([right-35, right-15], [bottom-9, bottom-9],
                color=COLORS['image_annotation'], linewidth=LINEWIDTH['scale'])
        ax.text(right-25, bottom-17, '20 mm', ha='center', color=COLORS['image_annotation'])
    return {'case_id': meta['patient_id']+'_'+meta['view'], 'frame': int(index),
            'phase': next((p for p, i in meta['phases'].items() if i == index), 'intermediate'),
            'time_s': meta['audit']['timestamps_s'][index], 'expert_available': bool(expert_available),
            'source_image_hw': [112, 112], 'original_hw': tr['original_hw'],
            'original_spacing_xy_mm': [sx, sy],
            'processed_spacing_xy_mm': tr['processed_spacing_xy_mm'],
            'image_extent_mm': extent, 'display_field_mm': list(FIELD_MM),
            'interpolation': 'none', 'image_limits': [0, 255], 'extra_crop': None,
            'brightness_contrast_gamma': 'unchanged', 'roi_reviewed': meta['audit']['roi_reviewed']}


def contour_legend():
    return [Line2D([], [], color=COLORS['primary'], linewidth=LINEWIDTH['primary'],
                   label='Predicted LV contour'),
            Line2D([], [], color=COLORS['expert_contour'], linestyle='--',
                   linewidth=LINEWIDTH['reference'], label='Expert contour · ED/ES only')]


def time_edges(time):
    """Voronoi display cells, truncated exactly at the first/last observation."""
    time = np.asarray(time)
    assert len(time) > 1 and np.all(np.diff(time) > 0)
    return np.r_[time[0], (time[:-1]+time[1:])/2, time[-1]]


def source_dependencies():
    return [Path(__file__), ROOT/'src/geometry/mask_features.py', ROOT/'src/geometry/volume.py',
            ROOT/'src/data/transforms.py']
