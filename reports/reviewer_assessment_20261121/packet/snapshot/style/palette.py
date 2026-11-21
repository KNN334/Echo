"""Approved colors, typography, physical dimensions and export policy."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.work/matplotlib'
CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR', str(CACHE))

import matplotlib as mpl
from matplotlib import font_manager, pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from PIL import Image
from cmcrameri import cm


COLORS = {
    'primary': '#0072B2',
    'regularized': '#E69F00',
    'comparison_reserved': '#009E73',
    'expert_contour': '#CC79A7',
    'clinical_label': '#333333',
    'text': '#222222',
    'axis': '#444444',
    'muted': '#6B6B6B',
    'background': '#FFFFFF',
    'image_background': '#000000',
    'image_annotation': '#FFFFFF',
}
METHOD_COLORS = {
    'camus_cuda_progress': COLORS['primary'],
    'camus_regularized': COLORS['regularized'],
}
CMAPS = {'sequential': mpl.colormaps['cividis'], 'diverging': cm.vik,
         'image': mpl.colormaps['gray']}
BODY_PT = 7
PANEL_PT = 8
WIDTH_MM = {'single': 89, 'double': 183}
MAX_HEIGHT_MM = 170
DPI = 600
MM_PER_INCH = 25.4
LINEWIDTH = {'primary': 1.0, 'comparison': 0.7, 'reference': 0.85, 'scale': 1.0}
MARKER_SIZE = {'primary': 3.0, 'reference': 3.5}


def apply_style():
    """Require actual Arial; never silently substitute a different typeface."""
    font_path = font_manager.findfont(font_manager.FontProperties(family=['Arial']),
                                      fallback_to_default=False)
    plt.style.use(Path(__file__).with_name('paper.mplstyle'))
    mpl.rcParams['axes.prop_cycle'] = mpl.cycler(color=[
        COLORS[k] for k in ['primary', 'regularized', 'comparison_reserved', 'expert_contour']])
    return font_path


def figure_size(column='double', height_mm=145):
    if not 0 < height_mm <= MAX_HEIGHT_MM:
        raise ValueError('Figure height must be in (0, 170] mm.')
    return WIDTH_MM[column] / MM_PER_INCH, height_mm / MM_PER_INCH


def symmetric_error_norm(limit):
    """Use one shared, predeclared limit for comparable residual panels."""
    if limit <= 0:
        raise ValueError('An error color scale needs a positive symmetric limit.')
    return TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)


def panel_heading(fig, letter, title, x_mm, y_mm):
    width, height = fig.get_size_inches() * MM_PER_INCH
    fig.text(x_mm / width, y_mm / height, letter, fontsize=PANEL_PT, fontweight='bold',
             va='baseline', color=COLORS['text'])
    fig.text((x_mm + 5) / width, y_mm / height, title, va='baseline')


def export_figure(fig, stem):
    """Save the checked layout at exact size; retain editable PDF text."""
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.canvas.draw()
    fig.savefig(stem.with_suffix('.pdf'), dpi=DPI)
    fig.savefig(stem.with_suffix('.png'), dpi=DPI)
    with Image.open(stem.with_suffix('.png')) as image:
        rgb = image.convert('RGB')
        rgb.save(stem.with_suffix('.png'), dpi=(DPI, DPI))
        rgb.save(stem.with_suffix('.tiff'), compression='tiff_lzw', dpi=(DPI, DPI))
        preview = rgb.copy()
        preview.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        preview.save(stem.with_name(stem.name + '_preview').with_suffix('.png'))
