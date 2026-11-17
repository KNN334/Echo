"""仅从冻结的实际训练记录重绘过拟合对照，不训练模型或读取测试图像。"""
import csv
import importlib.util
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
BLUE, ORANGE, GREY = '#31688e', '#d98239', '#747b83'


def main():
    matplotlib.rcParams.update({
        'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'DejaVu Sans'],
        'font.size': 7.5, 'axes.titlesize': 8, 'axes.labelsize': 7.5,
        'xtick.labelsize': 7, 'ytick.labelsize': 7, 'legend.fontsize': 7.5,
        'legend.frameon': False, 'axes.spines.top': False, 'axes.spines.right': False,
        'axes.linewidth': .65, 'lines.linewidth': 1.3,
        'pdf.fonttype': 42, 'svg.fonttype': 'none', 'savefig.facecolor': 'white',
    })
    fig, axes = plt.subplots(1, 2, figsize=(183 / 25.4, 88 / 25.4), sharex=True, sharey=True)
    fig.subplots_adjust(left=.10, right=.98, bottom=.22, top=.78, wspace=.22)
    statistics = {}
    for ax, label, title in zip(axes, ('baseline', 'regularized'),
                                ('Original training', 'Augmentation + weight decay + early stopping')):
        with (ROOT / 'source_data' / (label + '_training.csv')).open(encoding='utf-8-sig') as stream:
            history = list(csv.DictReader(stream))
        epoch = np.array([int(row['epoch']) for row in history])
        training = np.array([float(row['train_bce']) for row in history])
        validation = np.array([float(row['val_bce']) for row in history])
        assert np.array_equal(epoch, np.arange(1, len(epoch) + 1))
        assert np.all(np.isfinite(training)) and np.all(np.isfinite(validation))
        best = int(np.argmin(validation))
        ax.plot(epoch, training, color=BLUE, linestyle='--', label='Training')
        ax.plot(epoch, validation, color=ORANGE, label='Validation')
        ax.axvline(epoch[best], color=GREY, linestyle=':', linewidth=.8)
        ax.scatter(epoch[best], validation[best], color=ORANGE, edgecolor='white', s=28, zorder=3)
        ax.set(xlabel='Epoch', xlim=(1, 30), ylim=(.015, .05),
               xticks=[1, 5, 10, 15, 20, 25, 30], yticks=[.02, .03, .04, .05])
        ax.set_title(title, pad=27)
        end = f'; stopped at {epoch[-1]}' if label == 'regularized' else ''
        ax.text(0, 1.04, f'Best: epoch {epoch[best]}; val BCE {validation[best]:.5f}{end}',
                transform=ax.transAxes, fontsize=7, va='bottom')
        ax.text(-.15, 1.24, 'a' if label == 'baseline' else 'b', transform=ax.transAxes,
                fontweight='bold', fontsize=9, va='bottom')
        ax.grid(axis='y', color='#e7e9eb', linewidth=.5)
        statistics[label] = {'best_epoch': int(epoch[best]), 'epochs_completed': len(epoch),
                             'best_val_bce': float(validation[best]),
                             'train_bce_at_best_epoch': float(training[best]),
                             'last_train_bce': float(training[-1]), 'last_val_bce': float(validation[-1])}
    axes[0].set_ylabel('Binary cross-entropy (BCE)')
    fig.legend(*axes[0].get_legend_handles_labels(), loc='lower center', bbox_to_anchor=(.54, .085),
               ncol=2, handlelength=2.5)
    fig.text(.10, .035, 'Seed 2026; 347 train / 71 validation patients. Training in b uses augmentation.', fontsize=7)
    fig.canvas.draw()
    auditor = os.environ.get('ECHO_FIGURE_ALIGNMENT_SCRIPT')
    alignment = ROOT / 'training_comparison.alignment.json'
    if auditor:
        spec = importlib.util.spec_from_file_location('figure_alignment', auditor)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.require_matplotlib_panel_alignment(fig, json_out=alignment, strict=True)
    else:
        rects = [ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted()).bounds for ax in axes]
        assert np.ptp(np.array(rects)[:, 2:], axis=0).max() * 72 <= 1.5
        alignment.write_text(json.dumps({'status': 'equal_plot_area_sizes_only', 'rectangles_inch': rects,
                                         'tolerance_pt': 1.5}, indent=2) + '\n', encoding='utf-8')
    fig.savefig(ROOT / 'training_comparison.pdf')
    fig.savefig(ROOT / 'training_comparison.svg')
    fig.savefig(ROOT / 'training_comparison.png', dpi=300)
    svg = ROOT / 'training_comparison.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n',
                   encoding='utf-8', newline='\n')
    plt.close(fig)
    statistics['relative_best_val_bce_reduction'] = (
        1 - statistics['regularized']['best_val_bce'] / statistics['baseline']['best_val_bce'])
    (ROOT / 'source_data' / 'training_statistics.json').write_text(
        json.dumps(statistics, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
