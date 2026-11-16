"""从单次冻结实验生成患者级结果图；不运行训练、推理或测试集选模。"""
from __future__ import annotations

import csv
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import shutil
from collections import defaultdict

import numpy as np

from ..data.transforms import Transform
from ..utils.io import read_json, write_json, write_csv


BLUE = '#31688e'
ORANGE = '#d98239'
GREY = '#747b83'
GREEN = '#39977d'
REF_GEOMETRY = 'same_geometry_from_expert_ED_ES_contours'
REF_DATASET = 'CAMUS_Info_cfg_EF'


def number(value):
    """CSV 空值与非有限值保留为 NaN，绝不补零。"""
    try:
        result = float(value)
    except (ValueError, TypeError):
        return np.nan
    return result if np.isfinite(result) else np.nan


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def patient_pairs(rows, key, *, method, reference_scope, view=None):
    """严格限定方法和参考来源；每患者先平均配对值，防止重复帧伪增样本。"""
    grouped = defaultdict(list)
    for row in rows:
        if row.get('method') != method or row.get('reference_scope') != reference_scope:
            continue
        if view is not None and row.get('view') != view:
            continue
        pred, ref = number(row.get(key)), number(row.get('ref_' + key))
        if np.isfinite(pred) and np.isfinite(ref):
            grouped[row['patient_id']].append((pred, ref))
    patients = sorted(grouped)
    pairs = np.array([np.mean(grouped[pid], axis=0) for pid in patients], float).reshape(-1, 2)
    return patients, pairs[:, 0], pairs[:, 1]


def agreement(pred, ref, seed=2026, repetitions=2000):
    """患者级 MAE/偏倚/描述性一致性界限；bootstrap 区间是 MAE 的区间。"""
    pred, ref = np.asarray(pred, float), np.asarray(ref, float)
    good = np.isfinite(pred) & np.isfinite(ref)
    errors = pred[good] - ref[good]
    if not len(errors):
        return {'n': 0, 'mae': None, 'bias': None, 'loa_low': None, 'loa_high': None,
                'mae_ci_low': None, 'mae_ci_high': None}
    mae = float(np.mean(np.abs(errors)))
    bias = float(errors.mean())
    sd = float(errors.std(ddof=1)) if len(errors) > 1 else np.nan
    rng = np.random.default_rng(seed)
    boot = np.mean(rng.choice(np.abs(errors), (repetitions, len(errors)), replace=True), axis=1)
    low, high = np.percentile(boot, [2.5, 97.5]) if len(errors) > 1 else (np.nan, np.nan)
    return {'n': len(errors), 'mae': mae, 'bias': bias,
            'loa_low': float(bias - 1.96 * sd) if np.isfinite(sd) else None,
            'loa_high': float(bias + 1.96 * sd) if np.isfinite(sd) else None,
            'mae_ci_low': float(low) if np.isfinite(low) else None,
            'mae_ci_high': float(high) if np.isfinite(high) else None}


def paired_errors(rows, view):
    a = patient_pairs(rows, 'EF', method='single_plane_area_length', reference_scope=REF_GEOMETRY, view=view)
    b = patient_pairs(rows, 'EF', method='single_plane_auto_extrema_' + view,
                      reference_scope=REF_GEOMETRY, view=view)
    first = {pid: abs(p - r) for pid, p, r in zip(*a)}
    second = {pid: abs(p - r) for pid, p, r in zip(*b)}
    common = sorted(first.keys() & second.keys())
    return common, np.array([first[x] for x in common]), np.array([second[x] for x in common]), len(first), len(second)


def _group_means(rows, key):
    groups = defaultdict(list)
    for row in rows:
        value = number(row.get(key))
        if np.isfinite(value):
            groups[row['patient_id']].append(value)
    return {pid: float(np.mean(values)) for pid, values in groups.items()}


def load_bundle(results, training, prepared=None):
    """验证来源、患者隔离、帧计数和摘要；遇到混轮次结果就停止。"""
    results, training = Path(results).resolve(), Path(training).resolve()
    data = {'results': results, 'training': training,
            'prepared': Path(prepared).resolve() if prepared else None}
    data['summary'] = s = read_json(results / 'summary.json')
    data['run'] = run = read_json(training / 'run.json')
    data['history'] = read_csv(training / 'training.csv')
    for name in ('structure', 'function', 'frames'):
        data[name] = read_csv(results / (name + '.csv'))
    if s.get('split') != 'test':
        raise ValueError('结果必须明确属于隔离测试集。')
    best = training / 'best.pt'
    if not best.is_file() or digest(best) != s.get('weights_sha256'):
        raise ValueError('训练权重与测试摘要不匹配，禁止混用不同实验。')
    train, val = set(run.get('train_patients', [])), set(run.get('val_patients', []))
    test = {r['patient_id'] for r in data['frames']}
    if not train or not val or train & val or (train | val) & test:
        raise ValueError('训练/验证/测试患者集合缺失或相互重叠。')
    if len(data['structure']) != s.get('labeled_frames') or len(data['frames']) != s.get('frames'):
        raise ValueError('逐帧表与评估摘要数量不一致。')
    if len(test) != s.get('patients'):
        raise ValueError('测试患者计数与摘要不一致。')
    if not data['history'] or not all(np.isfinite(number(r.get('val_bce'))) for r in data['history']):
        raise ValueError('缺少有效验证损失记录。')
    for name, keys in [('structure', ('case_id', 'frame')), ('frames', ('case_id', 'frame')),
                       ('function', ('patient_id', 'view', 'method'))]:
        identities = [tuple(r[k] for k in keys) for r in data[name]]
        if len(identities) != len(set(identities)):
            raise ValueError(f'{name} 存在重复记录，不能静默计数。')
    reproduced = float(np.mean(list(_group_means(data['structure'], 'dice').values())))
    if not np.isclose(reproduced, s['dice_patient_mean'], atol=1e-10):
        raise ValueError('患者级 Dice 不能复现摘要。')
    data['metadata'] = {}
    data['features'] = {}
    for key in sorted({r['case_id'] for r in data['frames']}):
        path = results / (key + '_features.json')
        feature = read_json(path)
        meta = feature['metadata']
        if meta.get('patient_id') not in test or meta.get('split', 'test') != 'test':
            raise ValueError(f'{key} 的患者或集合身份不匹配。')
        data['metadata'][key], data['features'][key] = meta, feature['frames']
        for row in data['structure']:
            if row['case_id'] == key:
                phases = {int(index): phase for phase, index in meta['phases'].items()}
                row['phase'] = phases.get(int(row['frame']), 'unreported')
                row['image_quality'] = meta.get('config', {}).get('ImageQuality', 'Unknown')
                if row.get('distance_unit') != 'mm':
                    row['assd'], row['hd95'] = '', ''
    if any(r['phase'] == 'unreported' for r in data['structure']):
        raise ValueError('标注帧无法映射回专家 ED/ES 相位。')
    source_files = [results / n for n in ('summary.json', 'frames.csv', 'structure.csv', 'function.csv')]
    source_files += [training / n for n in ('run.json', 'training.csv', 'best.pt')]
    source_files += sorted(results.glob('*_features.json'))
    data['sources'] = {Path(os.path.relpath(p, results.parent.parent)).as_posix(): digest(p) for p in source_files}
    data['test_patients'] = sorted(test)
    data['best_epoch'] = min(data['history'], key=lambda r: number(r['val_bce']))
    return data


def _style():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'DejaVu Sans'],
        'font.size': 7.5, 'axes.titlesize': 8, 'axes.labelsize': 7.5,
        'xtick.labelsize': 7, 'ytick.labelsize': 7, 'legend.fontsize': 7, 'legend.frameon': False,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.linewidth': .65, 'lines.linewidth': 1.2,
        'pdf.fonttype': 42, 'svg.fonttype': 'none', 'savefig.facecolor': 'white',
        'axes.prop_cycle': matplotlib.cycler(color=[BLUE, ORANGE, GREEN, GREY]),
    })
    return plt


def _grid(plt, rows=1, cols=1, height=92):
    fig, axes = plt.subplots(rows, cols, figsize=(183 / 25.4, height / 25.4), squeeze=False)
    fig.subplots_adjust(left=.09, right=.975, bottom=.17 if rows == 1 else .12,
                        top=.86 if rows == 1 else .91, wspace=.43, hspace=.72)
    return fig, axes


def _letters(axes, x=-.19):
    for i, ax in enumerate(np.ravel(axes)):
        ax.text(x, 1.07, chr(97 + i), transform=ax.transAxes, fontweight='bold', fontsize=9,
                va='bottom', ha='left')


def _export(fig, stem, figures, caption):
    """先测量真实面板区域；可挂接额外严格布局审计，然后导出同一画布。"""
    stem = Path(stem)
    fig.canvas.draw()
    rects = [list(a.get_window_extent().transformed(fig.dpi_scale_trans.inverted()).bounds) for a in fig.axes]
    # 常规矩形网格的绘图区宽高必须相等；所有面板保留同一物理尺寸。
    if len(rects) > 1:
        sizes = np.array([r[2:] for r in rects]) * 72
        if np.ptp(sizes, axis=0).max() > 1.5:
            raise ValueError(f'{stem.name}: 面板绘图区不等宽高。')
    write_json(stem.with_suffix('.alignment.json'), {'rectangles_inch': rects, 'tolerance_pt': 1.5,
                                                    'status': 'passed' if len(rects) > 1 else 'single_panel'})
    alignment_script = os.environ.get('ECHO_FIGURE_ALIGNMENT_SCRIPT')
    if alignment_script:
        spec = importlib.util.spec_from_file_location('echo_alignment_audit', alignment_script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.require_matplotlib_panel_alignment(fig, json_out=str(stem) + '.alignment.json', strict=True)
    for suffix in ('.svg', '.pdf', '.png'):
        fig.savefig(stem.with_suffix(suffix), dpi=300)
    svg = stem.with_suffix('.svg')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n',
                   encoding='utf-8', newline='\n')
    if getattr(figures, 'book', None) is not None:
        figures.book.savefig(fig)
    stem.with_suffix('.caption.md').write_text(caption + '\n', encoding='utf-8')
    figures.append({'stem': stem.name, 'caption': caption})
    import matplotlib.pyplot as plt
    plt.close(fig)


def plot_training(data, plt, output, figures):
    fig, aa = _grid(plt, height=88)
    ax = aa[0, 0]
    history = data['history']
    epoch = np.array([number(r['epoch']) for r in history])
    ax.plot(epoch, [number(r['train_bce']) for r in history], label='Training', color=BLUE)
    ax.plot(epoch, [number(r['val_bce']) for r in history], label='Validation', color=ORANGE)
    best = data['best_epoch']
    e, v = number(best['epoch']), number(best['val_bce'])
    ax.axvline(e, color=GREY, linestyle='--', linewidth=.8)
    ax.scatter([e], [v], color=ORANGE, edgecolor='white', zorder=3, s=32)
    ax.set(xlabel='Epoch', ylabel='Mean binary cross-entropy', xlim=(1, max(epoch)))
    ax.set_title(f'Validation-selected checkpoint: epoch {int(e)}; BCE = {v:.5f}', loc='left', pad=12)
    ax.legend(loc='upper left', bbox_to_anchor=(.54, 1), ncol=2)
    _export(fig, output / '01_training', figures,
            f'图 1｜训练和验证损失。训练集 {len(data["run"]["train_patients"])}、验证集 {len(data["run"]["val_patients"])} 位患者；最小验证 BCE 出现在第 {int(e)} 轮（{v:.5f}）。'
            '虚线和圆点标识验证选模轮次。后期训练损失继续下降而验证损失上升，提示过拟合。'
            '这是单次运行的实测记录，不显示虚构的重复实验区间，也没有使用测试损失选模。')


def _distribution(ax, groups, colors, labels, *, jitter_seed=2026):
    rng = np.random.default_rng(jitter_seed)
    safe = [np.asarray(g, float)[np.isfinite(g)] for g in groups]
    populated = [(i, g) for i, g in enumerate(safe) if len(g)]
    if populated:
        artists = ax.boxplot([g for _, g in populated], positions=[i for i, _ in populated], widths=.44,
                             patch_artist=True, showfliers=False, manage_ticks=False,
                             medianprops={'color': '#252b30', 'linewidth': 1.1},
                             whiskerprops={'linewidth': .75}, capprops={'linewidth': .75})
        for patch, (i, _) in zip(artists['boxes'], populated):
            patch.set(facecolor=colors[i], alpha=.2, edgecolor=colors[i])
        for i, g in populated:
            ax.scatter(i + rng.uniform(-.16, .16, len(g)), g, s=7, color=colors[i], alpha=.48,
                       linewidths=0, rasterized=True, zorder=2)
    ax.set_xticks(range(len(groups)), labels)
    ax.set_xlim(-.55, len(groups) - .45)
    ax.grid(axis='y', alpha=.18, linewidth=.5)


def plot_segmentation(data, plt, output, figures):
    fig, aa = _grid(plt, cols=3, height=91)
    _letters(aa)
    strata = [(v, p) for v in ('2CH', '4CH') for p in ('ED', 'ES')]
    for ax, (key, label) in zip(aa[0], [('dice', 'Dice'), ('assd', 'ASSD (mm)'), ('hd95', 'HD95 (mm)')]):
        groups = [np.array(list(_group_means([r for r in data['structure'] if r['view'] == v and r['phase'] == p], key).values())) for v, p in strata]
        labels = [f'{v}\n{p}\nn={len(g)}' for (v, p), g in zip(strata, groups)]
        _distribution(ax, groups, [BLUE, ORANGE, BLUE, ORANGE], labels)
        ax.set_ylabel(label)
        ax.set_title({'dice': 'Overlap', 'assd': 'Average boundary error', 'hd95': 'Tail boundary error'}[key], pad=15)
        if key == 'dice':
            ax.set_ylim(min(.5, min(min(g) for g in groups) - .04), 1.015)
        else:
            ax.set_ylim(bottom=0)
    _export(fig, output / '02_segmentation', figures,
            '图 2｜切面和相位分层的左室分割性能。每组最多 82 位患者，每个点是一位患者在该切面/相位上的一张标注帧。'
            '全部有效观测均显示；箱体为四分位范围，横线为中位数，须延伸至 1.5×IQR 范围内的最远点。'
            'ASSD 和 HD95 在原始坐标、原始像素间距下计算，单位 mm；非毫米或不可定义的边界距离不混入。'
            '四组来自相同患者，不是四个独立队列。')


def _scatter(ax, pred, ref, key, unit):
    if not len(pred):
        ax.set_title('No paired reference')
        return
    lo, hi = min(pred.min(), ref.min()), max(pred.max(), ref.max())
    margin = max((hi - lo) * .1, 1)
    ax.plot([lo - margin, hi + margin], [lo - margin, hi + margin], color=GREY, linestyle='--', linewidth=.8)
    ax.scatter(ref, pred, color=BLUE, s=16, alpha=.7, edgecolor='white', linewidth=.3)
    ax.set(xlabel=f'Reference {key} ({unit})', ylabel=f'Predicted {key} ({unit})',
           xlim=(lo - margin, hi + margin), ylim=(lo - margin, hi + margin))


def _bland_altman(ax, pred, ref, unit, stat, difference_unit=None):
    if not len(pred):
        return
    ax.scatter((pred + ref) / 2, pred - ref, s=16, color=BLUE, alpha=.7,
               edgecolor='white', linewidth=.3)
    ax.axhline(0, color='#d2d6d8', linewidth=.7)
    ax.axhline(stat['bias'], color=ORANGE)
    for k in ('loa_low', 'loa_high'):
        if stat[k] is not None:
            ax.axhline(stat[k], color=ORANGE, linestyle='--', linewidth=.9)
    ax.set(xlabel=f'Pair mean ({unit})', ylabel=f'Prediction - reference ({difference_unit or unit})')
    ax.margins(y=.18)


def plot_agreement(data, plt, output, figures, stats_rows, pair_rows, *, keys, name, scope):
    method = '20_disks_shorter_axis' if scope == REF_GEOMETRY else 'biplane_vs_CAMUS_reported_EF'
    fig, aa = _grid(plt, rows=len(keys), cols=2, height=87 if len(keys) == 1 else 151)
    _letters(aa)
    for i, key in enumerate(keys):
        ids, pred, ref = patient_pairs(data['function'], key, method=method, reference_scope=scope)
        stat = agreement(pred, ref)
        stats_rows.append({'method': method, 'reference_scope': scope, 'metric': key, **stat})
        pair_rows.extend({'patient_id': pid, 'method': method, 'reference_scope': scope,
                          'metric': key, 'prediction': p, 'reference': r, 'difference': p - r}
                         for pid, p, r in zip(ids, pred, ref))
        archived = data['summary']['function'][method][key]
        if len(ids) != archived['n_patients'] or not np.isclose(stat['mae'], archived['mae'], atol=1e-9):
            raise ValueError(f'{method}/{key}: 图件统计与本轮摘要不一致。')
        unit = '%' if key == 'EF' else 'mL'
        errunit = 'pp' if key == 'EF' else 'mL'
        _scatter(aa[i, 0], pred, ref, key, unit)
        _bland_altman(aa[i, 1], pred, ref, unit, stat, difference_unit=errunit)
        aa[i, 0].set_title(f'{key}: n={len(ids)}; MAE {stat["mae"]:.2f} {errunit}', loc='left', pad=12)
        aa[i, 1].set_title(f'Bias {stat["bias"]:.2f}; LoA [{stat["loa_low"]:.2f}, {stat["loa_high"]:.2f}]',
                           loc='left', pad=12)
    reference = ('专家 ED/ES 轮廓经过相同双平面几何法计算的参考值；它不是独立临床容积真值'
                 if scope == REF_GEOMETRY else 'CAMUS Info.cfg 记录的 EF；它与同法轮廓参考分开评价，不称为独立前瞻临床金标准')
    _export(fig, output / name, figures,
            f'图 {int(name.split("_")[0])}｜{"、".join(keys)} 的患者级一致性。参考为{reference}。'
            '每点一位患者；左侧虚线为恒等线。右侧为 Bland–Altman：横轴为预测/参考均值，纵轴为预测减参考，'
            '橙实线为偏倚，橙虚线为偏倚±1.96×患者差值样本标准差。EF 的误差单位为百分点 pp，'
            'EF 水平单位为 %；这些描述性界限不是预先定义的临床等效界值，也不是逐搏重复测量界限。'
            'MAE 的患者 bootstrap 95% 区间、n 和全部配对数据见 source_data。')


def plot_phase_comparison(data, plt, output, figures, exports):
    fig, aa = _grid(plt, cols=2, height=92)
    _letters(aa)
    for ax, view in zip(aa[0], ('2CH', '4CH')):
        ids, first, second, n_first, n_second = paired_errors(data['function'], view)
        for x, y in zip(first, second):
            ax.plot([0, 1], [x, y], color='#b9bec2', alpha=.5, linewidth=.6, zorder=1)
        _distribution(ax, [first, second], [BLUE, ORANGE], ['Expert phases', 'Automatic extrema'])
        ax.set(ylabel='Absolute EF error (pp)', ylim=(0, None))
        ax.set_title(f'{view}: paired n={len(ids)}; expert {n_first}, auto {n_second}', loc='left', pad=14)
        exports.extend({'patient_id': pid, 'view': view, 'expert_phase_abs_error_pp': a,
                        'auto_extrema_abs_error_pp': b, 'paired_error_change_pp': b - a}
                       for pid, a, b in zip(ids, first, second))
    _export(fig, output / '06_phase_selection', figures,
            '图 6｜专家相位与自动极值选相位的 EF 误差配对比较。灰线连接同一患者；参考均为该切面专家 ED/ES 轮廓'
            '经单平面面积–长度法计算的 EF。仅在两种方法都有效的患者上比较，完整可用数和配对数写在标题。'
            '因此有意排除不能成对的患者，并在 source_data/coverage.csv 保留方法总覆盖数。'
            '自动相位只在现有半序列内寻找 ED 后的 ES，不能解释为完整周期识别。未进行显著性检验。')


def coverage_rows(data):
    s = data['summary']
    values = [('Segmentation', len({r['patient_id'] for r in data['structure']}), 'available'),
              ('Biplane geometry', s['function']['20_disks_shorter_axis']['EF']['n_patients'], 'available'),
              ('CAMUS reported EF', s['function']['biplane_vs_CAMUS_reported_EF']['EF']['n_patients'], 'available')]
    for view in ('2CH', '4CH'):
        values.append((f'Auto extrema {view}', s['function']['single_plane_auto_extrema_' + view]['EF']['n_patients'], 'available'))
    manual = len({r['patient_id'] for r in data['structure'] if np.isfinite(number(r.get('manual_keypoint_error')))})
    co = len({r['patient_id'] for r in data['function'] if np.isfinite(number(r.get('ref_CO')))})
    clinical = len({r['patient_id'] for r in data['function']
                    if r.get('reference_scope') == 'external_reference_sidecar'
                    and np.isfinite(number(r.get('ref_EDV'))) and np.isfinite(number(r.get('ref_ESV')))})
    values += [('Independent EDV / ESV', clinical, 'missing_clinical_volumes' if not clinical else 'available'),
               ('Manual landmarks', manual, 'missing_manual_labels' if not manual else 'available'),
               ('Independent CO', co, 'missing_independent_reference' if not co else 'available')]
    total = s.get('patients_attempted', len(data['test_patients']))
    return [{'analysis': label, 'valid_patients': n, 'attempted_patients': total,
             'coverage': n / total, 'status': status} for label, n, status in values]


def plot_coverage(data, plt, output, figures):
    rows = coverage_rows(data)
    fig, aa = _grid(plt, height=96)
    fig.subplots_adjust(left=.29, right=.95, bottom=.15)
    ax = aa[0, 0]
    for i, row in enumerate(rows):
        ax.barh(i, 100, color='#edf0f2', height=.56)
        ax.barh(i, 100 * row['coverage'], color=BLUE, height=.56)
        label = f'{row["valid_patients"]}/{row["attempted_patients"]}'
        if not row['valid_patients']:
            label += '  reference unavailable'
        ax.text(2, i, label, va='center', color='white' if row['coverage'] > .5 else GREY, fontsize=7)
    ax.set(yticks=range(len(rows)), yticklabels=[r['analysis'] for r in rows],
           xlabel='Patients with evaluable results (%)', xlim=(0, 101))
    ax.invert_yaxis()
    ax.set_title('Evaluation coverage and unavailable references', loc='left', pad=12)
    _export(fig, output / '07_coverage', figures,
            '图 7｜有效评价覆盖率。分母为全部尝试测试患者；条内标注有效数/尝试数。'
            '独立临床容积、人工关键点和独立 CO 的零覆盖意味着没有参考标签，不代表零误差或测量准确。'
            '几何可计算率不等于经人工确认的临床有效覆盖率。')
    return rows


def select_examples(data):
    scores = defaultdict(list)
    for row in data['structure']:
        if np.isfinite(number(row['dice'])):
            scores[row['case_id']].append(number(row['dice']))
    ranked = sorted((float(np.mean(v)), k) for k, v in scores.items())
    positions = [0, round((len(ranked) - 1) * .25), round((len(ranked) - 1) * .5), round((len(ranked) - 1) * .75)]
    result, seen = [], set()
    for label, pos in zip(['Lowest', 'Q1', 'Median', 'Q3'], positions):
        score, key = ranked[pos]
        if key not in seen:
            result.append({'selection': label, 'rank': pos + 1, 'of_cases': len(ranked),
                           'case_id': key, 'mean_dice': score})
            seen.add(key)
    return result


def _example_arrays(data, example):
    key = example['case_id']
    root = data['prepared']
    if root is None:
        return None
    with np.load(root / (key + '.npz'), allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in archive.files}
    with np.load(data['results'] / (key + '_pred.npz'), allow_pickle=False) as archive:
        masks = archive['masks']
    meta = data['metadata'][key]
    tr = meta['audit']['transform']
    transform = Transform(tuple(tr['original_hw']), tuple(tr['crop_xyxy']), tuple(tr['output_hw']))
    gt = dict(zip(arrays['original_gt_indices'], arrays['original_gt']))
    if len(masks) != len(arrays['frames']) or masks.shape != arrays['frames'].shape:
        raise ValueError(f'{key} 缓存帧数/尺寸不一致。')
    # 比较原始标签上的 Dice，防止把其他轮次或失配缓存画入定性图。
    for phase, i in meta['phases'].items():
        pred = transform.restore_mask(masks[i]).astype(bool)
        truth = gt[i].astype(bool)
        denominator = pred.sum() + truth.sum()
        dice = 2 * (pred & truth).sum() / denominator if denominator else np.nan
        archived = next(r for r in data['structure'] if r['case_id'] == key and int(r['frame']) == i)
        if not np.isclose(dice, number(archived['dice']), atol=1e-10, equal_nan=True):
            raise ValueError(f'{key}/{phase} 的缓存不能复现已记录 Dice。')
    for path in (root / (key + '.npz'), data['results'] / (key + '_pred.npz')):
        data['sources'][Path(os.path.relpath(path, data['results'].parent.parent)).as_posix()] = digest(path)
    return arrays, masks, meta, transform, gt


def plot_examples(data, plt, output, figures, examples):
    if data['prepared'] is None:
        return ['08_examples: prepared cache not supplied', '09_half_sequences: prepared cache not supplied']
    from PIL import Image
    from matplotlib.lines import Line2D
    fig, aa = _grid(plt, rows=2, cols=len(examples), height=122)
    fig.subplots_adjust(left=.04, right=.98, bottom=.1, top=.86, wspace=.1, hspace=.34)
    _letters(aa, x=-.08)
    for col, example in enumerate(examples):
        arrays, masks, meta, transform, gt = _example_arrays(data, example)
        key = example['case_id']
        for row, phase in enumerate(('ED', 'ES')):
            ax = aa[row, col]
            index = meta['phases'][phase]
            h, w = transform.original_hw
            sx, sy = meta['audit']['spacing_xy_mm']
            restored = transform.restore_mask(masks[index])
            x0, y0, x1, y1 = transform.crop_xyxy
            background = np.zeros((h, w), np.uint8)
            background[y0:y1, x0:x1] = np.array(Image.fromarray(arrays['frames'][index]).resize(
                (x1 - x0, y1 - y0), Image.Resampling.BILINEAR))
            extent = (0, w * sx, h * sy, 0)
            ax.imshow(background, cmap='gray', vmin=0, vmax=255, extent=extent, aspect='equal')
            x, y = (np.arange(w) + .5) * sx, (np.arange(h) + .5) * sy
            ax.contour(x, y, gt[index], levels=[.5], colors=[ORANGE], linewidths=.85)
            ax.contour(x, y, restored, levels=[.5], colors=[GREEN], linewidths=.85, linestyles='--')
            span = max(w * sx, h * sy)
            ax.set(xlim=(w * sx / 2 - span / 2, w * sx / 2 + span / 2),
                   ylim=(h * sy / 2 + span / 2, h * sy / 2 - span / 2))
            ax.set_xticks([]); ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            record = next(r for r in data['structure'] if r['case_id'] == key and int(r['frame']) == index)
            ax.set_title(f'{example["selection"]}: {key.replace("patient", "P")}\n{phase}; Dice {number(record["dice"]):.3f}', fontsize=7, pad=5)
    fig.legend(handles=[Line2D([], [], color=ORANGE, label='Expert contour'),
                        Line2D([], [], color=GREEN, linestyle='--', label='Prediction')],
               loc='lower center', ncol=2, bbox_to_anchor=(.5, .005), frameon=False)
    _export(fig, output / '08_examples', figures,
            '图 8｜预先声明排名规则选择的失败与典型病例。对全部测试切面按 ED/ES 平均 Dice 排序，选择最差、'
            '25%、50%、75% 位置（排序稳定，见 example_selection.csv）；并非随机抽样或独立成功率证据。'
            '上排 ED，下排 ES；橙实线为原始专家轮廓，绿虚线为本轮预测掩膜恢复后的轮廓。'
            '图像为已有 112×112 处理帧重采样至原始显示坐标，不是恢复出原始图像细节；原始专家标签没有缩放后再充当真值。'
            '显示范围按物理空间补至方形，保留横纵比例；图中所有 Dice 均在原始标签上重新核对。')
    fig, aa = _grid(plt, rows=2, cols=2, height=141)
    _letters(aa)
    for ax, example in zip(aa.flat, examples):
        key = example['case_id']
        rows = sorted([r for r in data['frames'] if r['case_id'] == key], key=lambda r: int(r['frame']))
        time = np.array([number(r.get('time_s')) for r in rows])
        valid = np.array([r.get('valid') in ('True', 'true', '1') for r in rows])
        volumes = np.array([number(r['volume_ml']) for r in rows])
        use_time = np.isfinite(time).all() and np.all(np.diff(time) > 0)
        x = time if use_time else np.array([int(r['frame']) for r in rows])
        ax.plot(x, np.where(valid, volumes, np.nan), marker='.', markersize=3, color=BLUE, label='Prediction')
        meta = data['metadata'][key]
        frow = next(r for r in data['function'] if r['method'] == 'single_plane_area_length'
                    and r['patient_id'] == meta['patient_id'] and r['view'] == meta['view'])
        for phase, column in [('ED', 'ref_EDV'), ('ES', 'ref_ESV')]:
            index = meta['phases'][phase]
            ax.scatter([x[index]], [number(frow[column])], color=ORANGE, s=28, zorder=4)
        ax.set(xlabel='Time from first frame (s)' if use_time else 'Original frame index',
               ylabel='Single-plane volume (mL)')
        ax.set_title(key.replace('patient', 'P') + f'; {len(rows)} frames; half-sequence', loc='left', fontsize=7.5, pad=12)
        ax.grid(alpha=.18, linewidth=.5)
    fig.legend(handles=[Line2D([], [], color=BLUE, label='Predicted volume'),
                        Line2D([], [], color=ORANGE, marker='o', linestyle='None', label='Expert-derived ED / ES only')],
               loc='upper center', bbox_to_anchor=(.53, .997), ncol=2, frameon=False)
    _export(fig, output / '09_half_sequences', figures,
            '图 9｜与图 8 相同病例的原始半周期单平面容积预测。横轴在元数据支持时使用由 Info.cfg 帧率推导的时间，'
            '并非设备原始采集时间戳。蓝线为本轮逐帧预测，断点保留无效/缺失帧；橙点仅在专家 ED/ES 帧上，'
            '由专家轮廓经相同单平面公式计算，不连接或插值成中间真值。保留原始帧序，不反转、反射或拼接成完整心搏。'
            '不同病例独立，不连接成长期趋势；不推导 HR/CO。')
    return []


def plot_associations(data, plt, output, figures, exports):
    score = _group_means(data['structure'], 'dice')
    ids, pred, ref = patient_pairs(data['function'], 'EF', method='biplane_vs_CAMUS_reported_EF', reference_scope=REF_DATASET)
    quality_order = {'Good': 0, 'Medium': 1, 'Poor': 2, 'Unknown': 3}
    quality = defaultdict(list)
    for meta in data['metadata'].values():
        quality[meta['patient_id']].append(meta.get('config', {}).get('ImageQuality', 'Unknown'))
    for pid, p, r in zip(ids, pred, ref):
        q = max(quality[pid], key=lambda x: quality_order.get(x, 3))
        exports.append({'patient_id': pid, 'worst_view_quality': q,
                        'mean_dice': score.get(pid, np.nan), 'reported_ef_abs_error_pp': abs(p - r)})
    labels = [q for q in ('Good', 'Medium', 'Poor', 'Unknown') if any(r['worst_view_quality'] == q for r in exports)]
    fig, aa = _grid(plt, cols=3, height=97)
    _letters(aa)
    groups = [[r for r in exports if r['worst_view_quality'] == q] for q in labels]
    for ax, key, ylabel in zip(aa[0, :2], ['mean_dice', 'reported_ef_abs_error_pp'], ['Patient mean Dice', 'Absolute EF error (pp)']):
        _distribution(ax, [np.array([r[key] for r in group]) for group in groups],
                      [BLUE, ORANGE, GREY, GREEN][:len(groups)], [q + f'\nn={len(g)}' for q, g in zip(labels, groups)])
        ax.set_ylabel(ylabel)
        ax.set_title('Worst-view image quality', loc='left', fontsize=7.5, pad=15)
    aa[0, 0].set_ylim(bottom=min(.5, min(score.values()) - .03), top=1.01)
    aa[0, 1].set_ylim(bottom=0)
    ax = aa[0, 2]
    ax.scatter([r['mean_dice'] for r in exports], [r['reported_ef_abs_error_pp'] for r in exports],
               color=BLUE, alpha=.7, s=14, edgecolor='white', linewidth=.3)
    ax.set(xlabel='Patient mean Dice', ylabel='Absolute EF error (pp)')
    ax.set_title('Segmentation vs function', loc='left', fontsize=7.5, pad=15)
    _export(fig, output / '10_error_associations', figures,
            '图 10｜患者级探索性误差关联。每位患者的图像质量按其两个切面中较差等级汇总（Good<Medium<Poor），'
            'Dice 为该患者全部标注帧的平均，EF 误差对 CAMUS Info.cfg EF 计算。各患者仅计一次。'
            '箱线图定义同图 2；右图用于检查分割重叠和功能误差是否一致变化，不进行因果推断或显著性筛选。'
            '质量等级不平衡和几何假设都可能影响结果；高 Dice 不能自动证明 EF 准确。')


def _write_reports(data, output, figures, stats, selection, omissions):
    s = data['summary']
    best = data['best_epoch']
    ef = next(r for r in stats if r['reference_scope'] == REF_DATASET)
    text = f'''# CAMUS 结果分析与图件解读

## 固定实验与主要结果

本报告只使用 `{data['results'].name}` 及匹配训练记录。测试权重 SHA256：`{s['weights_sha256']}`。没有重跑训练、调节测试阈值或混入历史 full_baseline 结果。测试 {s['patients']} 位患者、{s['cases_attempted']} 个切面、{s['labeled_frames']} 张专家标注帧，失败切面 {s['cases_failed']}。

- 验证 BCE 最低轮次：{int(number(best['epoch']))}，值 {number(best['val_bce']):.5f}。训练后期出现训练/验证损失分离，应使用验证选择的检查点。
- 患者平均 Dice：{s['dice_patient_mean']:.4f}；ASSD：{s['assd_mm']:.3f} mm；HD95：{s['hd95_mm']:.3f} mm。
- 双平面 EF 对 CAMUS 报告 EF 的 MAE：{ef['mae']:.3f} 个百分点，患者 bootstrap 95% 区间 [{ef['mae_ci_low']:.3f}, {ef['mae_ci_high']:.3f}]；偏倚 {ef['bias']:.3f} 个百分点；描述性一致性界限 [{ef['loa_low']:.3f}, {ef['loa_high']:.3f}]。
- 这同时说明分割重叠较高与功能误差仍然明显可以共存。需要检查基底/心尖、长轴、几何假设与选相位，不能只用 Dice 评价整条链。
- 完整心搏数：{s['beats']}；人工点和独立 CO 参考仍缺失。没有据此绘制 HR、CO、数分钟连续曲线或声称临床等效。

'''
    text += '## 关键结果如何解读\n\n'
    text += '| 参考来源 | 指标 | 患者数 | MAE | 偏倚：预测减参考 | 描述性一致性界限 |\n|---|---|---:|---:|---:|---|\n'
    for row in stats:
        scope = '专家轮廓经同法计算' if row['reference_scope'] == REF_GEOMETRY else 'CAMUS 报告 EF'
        unit = 'pp' if row['metric'] == 'EF' else 'mL'
        text += (f'| {scope} | {row["metric"]} | {row["n"]} | {row["mae"]:.2f} {unit} | '
                 f'{row["bias"]:.2f} {unit} | [{row["loa_low"]:.2f}, {row["loa_high"]:.2f}] {unit} |\n')
    text += ('\n图 3–5 显示，接近零的平均偏倚可以与较宽的个体差值分布同时存在。'
             '两种 EF 参考对应的偏倚不同，说明参考定义会影响结论，不能交换命名。'
             '图 1 的验证损失最低点已用于选模，之后的训练/验证分离不能由继续训练的低训练损失抵消。\n\n')
    for view in ('2CH', '4CH'):
        ids, first, second, _, _ = paired_errors(data['function'], view)
        text += (f'图 6 的 {view} 共同有效患者 n={len(ids)}：专家相位与自动极值的平均绝对 EF 误差分别为 '
                 f'{first.mean():.2f}、{second.mean():.2f} 个百分点；配对平均变化为 {(second-first).mean():+.2f} 个百分点。'
                 '这是当前半周期内的探索性比较，不等同于完整心搏定位或经过独立验证的自动相位识别。\n\n')
    text += ('图 8–9 应联合阅读：最差切面的 ES 轮廓明显失配；另有较高 Dice 的切面仍显示很大的单平面容积与参考差值。'
             '这些数值是当前算法输出，不能解释为患者真实心室容积或疾病诊断。面积–长度法含面积平方及长轴分母，'
             '而双平面法依赖长轴与盘径；PCA 轮廓关键点尚无人工点验证，共享几何参考也可能共享系统误差。'
             '应在新训练/验证研究中复核空间标定、长轴与心尖/基底定位，当前图集保留异常值。\n\n'
             '图 10 的质量分层和 Dice–EF 误差关系仅作探索。质量组数不同、样本较少，也没有混杂校正，'
             '不能据散点或箱体重叠作因果、显著性或质量无影响的结论。图 7 的 100% 可计算率也不等于临床合格率。\n\n'
             '## 全部图件及可直接使用的中文图注\n\n')
    for item in figures:
        text += f'### {item["stem"]}\n\n![{item["stem"]}]({item["stem"]}.png)\n\n{item["caption"]}\n\n'
    text += '## 排除、缺失与统计说明\n\n'
    text += ('\n'.join('- ' + x for x in omissions) + '\n\n') if omissions else '定量图未按美观删去极端值。定性图只显示按公开排名规则选出的示例；这不影响总体统计。\n\n'
    text += ('每图统计源于同一实验。箱线图保留全部有限点，不把缺失值补零。MAE 区间用 2,000 次患者 bootstrap、固定种子 2026；'
             '与历史摘要的 1,000 次 bootstrap 次数不同，点估计和患者数逐项核对，不能要求随机区间末位完全一致。'
             'Bland–Altman 用患者差值的样本标准差，不把连续帧当独立样本；界限未附临床合格阈值。'
             '所有关联均为探索性，不反馈为测试集模型选择。图像质量来源于 CAMUS 元数据，不是新训练的质量分类器。\n\n'
             '原始数据完整下载未在本次重新验证；预处理全量状态来自既有记录，实际绘图仅核查使用到的病例缓存。'
             '训练完成状态、测试计数、权重一致性和绘图输入 SHA256 分别保存在 analysis_manifest.json。'
             '该记录不表示已经在当前重构后的代码上重新跑完模型实验。\n\n'
             '## 署名与许可\n\n'
             '图中超声图像源自 CAMUS。S. Leclerc et al., Deep Learning for Segmentation Using an Open Large-Scale Dataset in 2D Echocardiography, '
             'IEEE TMI 38, 2198–2210 (2019), DOI: 10.1109/TMI.2019.2900516。CAMUS 为 CC BY-NC-SA 4.0；含该数据图像的派生图件应保留署名、非商业与相同方式共享条件。'
             '官方 EchoNet 代码采用 MIT；不将该代码许可误写为 CAMUS 数据许可。\n')
    (output / 'RESULTS_ANALYSIS.md').write_text(text, encoding='utf-8')
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
             '<title>CAMUS 结果分析图集</title><style>body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:0 24px;color:#203342;line-height:1.7}img{width:100%;height:auto}section{margin:42px 0;border-top:1px solid #dbe2e7;padding-top:20px}a{color:#31688e}.note{padding:16px;background:#f2f6f8}nav{display:flex;gap:12px;flex-wrap:wrap}</style>',
             '<h1>CAMUS 左室分割与心功能结果分析</h1>',
             f'<p class="note">固定实验：{html.escape(data["results"].name)} · {s["patients"]} 位测试患者 · Dice {s["dice_patient_mean"]:.4f} · 报告 EF MAE {ef["mae"]:.2f} 个百分点。半周期研究基线；无独立 CO 和人工关键点验证。</p>',
             '<p><a href="RESULTS_ANALYSIS.md">完整中文解读</a> · <a href="all_figures.pdf">全部图件 PDF</a> · <a href="../../visualization_literature.md">文献与参考图分析</a> · <a href="source_data/agreement_statistics.csv">统计与置信区间</a> · <a href="analysis_manifest.json">数据与权重审计</a></p>', '<nav>']
    parts += [f'<a href="#{item["stem"]}">{item["stem"].split("_")[0]}</a>' for item in figures]
    parts.append('</nav>')
    for item in figures:
        name = html.escape(item['stem'])
        title = html.escape(item['caption'].split('。')[0])
        parts.append(f'<section id="{name}"><h2>{title}</h2><img src="{name}.png" alt="{name}"><p>{html.escape(item["caption"])}</p><a href="{name}.pdf">PDF 矢量版</a> · <a href="{name}.svg">SVG 可编辑版</a></section>')
    parts.append('<p>CAMUS: Leclerc et al., IEEE TMI (2019), DOI 10.1109/TMI.2019.2900516 · CC BY-NC-SA 4.0。图件分析不替代临床验证。</p></html>')
    (output / 'index.html').write_text('\n'.join(parts), encoding='utf-8')


def build_analysis(results, training, prepared, output):
    """生成完整图集与可追溯数据；未提供缓存时跳过依赖图像的图。"""
    data = load_bundle(results, training, prepared)
    output = Path(output).resolve()
    forbidden = [data['results'], data['training']]
    if data['prepared'] is not None:
        forbidden.append(data['prepared'])
    if any(output == p or output in p.parents or p in output.parents for p in forbidden):
        raise ValueError('绘图输出必须与源结果、训练权重和数据缓存目录分离。')
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / 'analysis_manifest.json'
    if manifest_path.exists() and read_json(manifest_path)['weights_sha256'] != data['summary']['weights_sha256']:
        raise ValueError('输出目录已包含另一轮实验，请使用新目录。')
    source = output / 'source_data'
    source.mkdir(exist_ok=True)
    for name in ('structure', 'function', 'frames'):
        write_csv(source / (name + '.csv'), data[name])
    shutil.copyfile(data['training'] / 'training.csv', source / 'training.csv')
    from matplotlib.backends.backend_pdf import PdfPages
    class FigureList(list):
        book = None
    figures = FigureList()
    stats, pairs, phases, associations = [], [], [], []
    plt = _style()
    with PdfPages(output / 'all_figures.pdf') as book:
        figures.book = book
        plot_training(data, plt, output, figures)
        plot_segmentation(data, plt, output, figures)
        for keys, name, scope in [(['EDV', 'ESV'], '03_volume_agreement', REF_GEOMETRY),
                                  (['SV', 'EF'], '04_function_agreement', REF_GEOMETRY),
                                  (['EF'], '05_reported_ef', REF_DATASET)]:
            plot_agreement(data, plt, output, figures, stats, pairs, keys=keys, name=name, scope=scope)
        plot_phase_comparison(data, plt, output, figures, phases)
        coverage = plot_coverage(data, plt, output, figures)
        selection = select_examples(data)
        omissions = plot_examples(data, plt, output, figures, selection)
        plot_associations(data, plt, output, figures, associations)
    for name, rows in [('agreement_statistics', stats), ('agreement_pairs', pairs), ('paired_phase_errors', phases),
                       ('coverage', coverage), ('example_selection', selection), ('error_associations', associations)]:
        write_csv(source / (name + '.csv'), rows)
    summary = data['summary']
    write_json(manifest_path, {
        'schema_version': 1, 'experiment': data['results'].name, 'weights_sha256': summary['weights_sha256'],
        'evaluation_git_commit': summary.get('git_commit'),
        'evaluation_working_tree_dirty': summary.get('working_tree_dirty'),
        'plotting_source_sha256': digest(Path(__file__)),
        'sources_sha256': data['sources'], 'figures': figures, 'omissions': omissions,
        'best_epoch_by_validation': int(number(data['best_epoch']['epoch'])),
        'test_patients': data['test_patients'], 'bootstrap': {'unit': 'patient', 'repetitions': 2000, 'seed': 2026},
        'checkpoint_digest_verified': True, 'patient_disjointness_verified': True,
        'source_summary_point_estimates_verified': True,
        'raw_data_complete_download': 'not_reverified', 'prepared_dataset_full_audit': 'not_repeated',
        'prepared_local_figure_cache_cases_verified': len(selection) if data['prepared'] else 0,
        'model_experiment': 'existing_completed_run_not_rerun',
        'reference_scopes': [REF_GEOMETRY, REF_DATASET],
        'clinical_validation': False, 'semi_supervised_training': False,
    })
    _write_reports(data, output, figures, stats, selection, omissions)
    return {'output': str(output), 'figures': len(figures), 'patients': summary['patients'],
            'dice': summary['dice_patient_mean'], 'best_epoch': int(number(data['best_epoch']['epoch']))}
