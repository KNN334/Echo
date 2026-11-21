"""Rebuild Fig.S3 from two historical training runs and paired validation data."""
import argparse
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from style.palette import (COLORS, LINEWIDTH, MARKER_SIZE, METHOD_COLORS, apply_style,
                           export_figure, figure_size, panel_heading)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import torch

from _paper_common import (Canvas, alignment, digest, provenance, read_csv, read_json,
                           write_csv, write_json)

STEM = 'fig_s03_training_comparison'
OUT = ROOT/'figures'/STEM
RUNS = ['camus_cuda_progress', 'camus_regularized']
LABELS = ['Baseline', 'Regularized']
MARKERS = ['o', '^']
LINES = ['-', '--']


def describe(values):
    values = np.asarray(values, dtype=float)
    assert len(values) > 1 and np.isfinite(values).all()
    return {'n': len(values), 'mean': float(values.mean()),
            'sample_sd': float(values.std(ddof=1)), 'median': float(np.median(values)),
            'minimum': float(values.min()), 'maximum': float(values.max())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True, exist_ok=True)
    split_path = ROOT/'configs/camus_splits.json'
    split = read_json(split_path)['patients']
    expected = {p for p, s in split.items() if s == 'val'}
    assert len(expected) == 71
    sources = [split_path, Path(__file__), OUT/'figure_contract.md']
    histories, metadata, patient_dice, patient_ef = {}, {}, {}, {}
    epoch_rows, configs, full_ef, all_valid_stats = [], [], [], []
    for index, run_id in enumerate(RUNS):
        checkpoint = ROOT/'checkpoints'/run_id
        evaluated = ROOT/'runs'/('validation_'+run_id)
        paths = [checkpoint/name for name in ['training.csv', 'run.json', 'completed.json',
                                             'experiment.json', 'best.pt']]
        paths += [evaluated/name for name in ['structure.csv', 'function.csv', 'summary.json']]
        sources.extend(paths)
        run = read_json(checkpoint/'run.json')
        assert set(run['val_patients']) == expected
        assert set(run['train_patients']) == {p for p, s in split.items() if s == 'train'}
        summary = read_json(evaluated/'summary.json')
        assert summary['split'] == 'val' and summary['patients'] == 71
        assert summary['cases_attempted'] == 142 and summary['labeled_frames'] == 284
        assert summary['cases_failed'] == 0 and not summary['failures']
        assert digest(checkpoint/'best.pt') == summary['weights_sha256']
        with torch.serialization.safe_globals([torch.torch_version.TorchVersion]):
            saved = torch.load(checkpoint/'best.pt', map_location='cpu', weights_only=True)
        best_epoch = int(saved['epoch'])
        assert saved['run']['initial_weights_sha256'] == run['initial_weights_sha256']
        history = read_csv(checkpoint/'training.csv')
        assert [int(r['epoch']) for r in history] == list(range(1, len(history)+1))
        assert len(history) == read_json(checkpoint/'completed.json')['epochs_completed']
        assert int(min(history, key=lambda r: float(r['val_bce']))['epoch']) == best_epoch
        assert (len(history), best_epoch) == [(30, 7), (23, 17)][index]
        histories[run_id], metadata[run_id] = history, run
        for row in history:
            epoch_rows.append({'experiment': run_id, 'epoch': int(row['epoch']),
                               'train_bce': float(row['train_bce']), 'val_bce': float(row['val_bce']),
                               'selected_checkpoint': int(row['epoch']) == best_epoch})
        if index == 1:
            archived = ROOT/'reports/training/camus_regularized/training.csv'
            assert archived.read_bytes() == (checkpoint/'training.csv').read_bytes()
            sources.append(archived)
        configs.append({'experiment': run_id, 'display_label': LABELS[index],
                        'epochs_observed': len(history), 'selected_epoch': best_epoch,
                        'selected_weights_sha256': summary['weights_sha256'],
                        'initial_weights_sha256': run['initial_weights_sha256'],
                        'train_patients': len(run['train_patients']), 'validation_patients': 71,
                        'seed': run['seed'], 'batch_size': run['batch_size'], 'lr': run['lr'],
                        'augmentation': run.get('augmentation', {'enabled': False}),
                        'weight_decay': run.get('weight_decay', 0),
                        'baseline_decay_source': 'git 83f4489:cardiac/model.py:110, explicit weight_decay=0'
                            if index == 0 else None,
                        'early_stopping_patience': run.get('early_stopping_patience'),
                        'min_delta': run.get('min_delta', 0)})
        grouped = defaultdict(list)
        structure = read_csv(evaluated/'structure.csv')
        for row in structure:
            grouped[row['patient_id']].append(row)
        assert set(grouped) == expected and len(structure) == 284
        assert all(len(g) == 4 and {r['view'] for r in g} == {'2CH', '4CH'}
                   and len({(r['view'], r['frame']) for r in g}) == 4 for g in grouped.values())
        patient_dice[run_id] = {p: float(np.mean([float(r['dice']) for r in g]))
                                for p, g in grouped.items()}
        assert np.isclose(np.mean(list(patient_dice[run_id].values())), summary['dice_patient_mean'])
        all_valid_stats.append({'experiment': run_id, 'metric': 'patient_mean_dice',
                                'scope': 'all_valid_validation_patients',
                                **describe(list(patient_dice[run_id].values()))})
        function = read_csv(evaluated/'function.csv')
        ef_rows = [r for r in function if r['method'] == 'biplane_vs_CAMUS_reported_EF']
        assert len(ef_rows) == 71 and {r['patient_id'] for r in ef_rows} == expected
        patient_ef[run_id] = {}
        for row in sorted(ef_rows, key=lambda r: r['patient_id']):
            assert row['reference_scope'] == 'CAMUS_Info_cfg_EF'
            assert row['phase_selection'] == 'reference_ED_ES_for_segmentation_error_isolation'
            assert not row['HR'] and not row['CO']
            valid = bool(row['EF'] and row['ref_EF'])
            if valid:
                prediction, reference = float(row['EF']), float(row['ref_EF'])
                patient_ef[run_id][row['patient_id']] = (prediction, reference)
            full_ef.append({'experiment': run_id, **row, 'valid_label_EF_pair': valid,
                            'absolute_error_pp': abs(prediction-reference) if valid else None})
        errors = [abs(p-r) for p, r in patient_ef[run_id].values()]
        assert np.isclose(np.mean(errors), summary['function']['biplane_vs_CAMUS_reported_EF']['EF']['mae'])
        all_valid_stats.append({'experiment': run_id, 'metric': 'label_ef_absolute_error_pp',
                                'scope': 'all_valid_validation_patients', **describe(errors)})
        del saved
    for key in ['initial_weights_sha256', 'mean', 'std', 'model', 'seed', 'batch_size', 'lr',
                'optimizer', 'loss', 'BN', 'input_manifest_sha256']:
        assert metadata[RUNS[0]][key] == metadata[RUNS[1]][key], key
    common = sorted(set(patient_ef[RUNS[0]]) & set(patient_ef[RUNS[1]]))
    assert len(common) == 70 and expected-set(common) == {'patient0039'}
    missing = next(r for r in full_ef if not r['valid_label_EF_pair'])
    assert missing['experiment'] == RUNS[1] and missing['patient_id'] == 'patient0039'
    assert float(missing['ESV']) > float(missing['EDV'])
    pairs = []
    for patient in sorted(expected):
        a, b = [patient_dice[run_id][patient] for run_id in RUNS]
        pairs.append({'metric': 'dice', 'patient_id': patient, 'baseline': a,
                      'regularized': b, 'regularized_minus_baseline': b-a})
    for patient in common:
        values = [patient_ef[run_id][patient] for run_id in RUNS]
        assert values[0][1] == values[1][1]
        a, b = [abs(p-r) for p, r in values]
        pairs.append({'metric': 'label_ef_absolute_error_pp', 'patient_id': patient, 'baseline': a,
                      'regularized': b, 'regularized_minus_baseline': b-a})
    write_csv(OUT/'source_data/training_history.csv', epoch_rows)
    write_json(OUT/'source_data/configuration_comparison.json', configs)
    write_csv(OUT/'source_data/all_validation_label_ef.csv', full_ef)
    write_csv(OUT/'source_data/paired_patient_metrics.csv', pairs)
    write_csv(OUT/'source_data/all_valid_statistics.csv', all_valid_stats)
    write_json(OUT/'source_data/excluded_from_paired_ef.json', [{
        'patient_id': missing['patient_id'], 'experiment': missing['experiment'],
        'issues': missing['issues'], 'EDV_mL': float(missing['EDV']), 'ESV_mL': float(missing['ESV']),
        'predicted_EF': None, 'CAMUS_label_EF_percent': float(missing['ref_EF']),
        'reason': 'ESV exceeds EDV; original EF null retained; both runs omitted only from paired EF panel'}])

    fig = plt.figure(figsize=figure_size(height_mm=158))
    canvas = Canvas(fig)
    canvas.text(8, 152, 'DeepLabV3–ResNet50 · same split and initialization · one historical run per configuration')
    fig.legend(handles=[Line2D([], [], color=METHOD_COLORS[r], linestyle=ls, marker=m,
                              linewidth=LINEWIDTH['primary'], markersize=MARKER_SIZE['primary'], label=label)
                        for r, ls, m, label in zip(RUNS, LINES, MARKERS, LABELS)],
               loc='center', bbox_to_anchor=(.5, 144/158), ncol=2)
    axes = []
    for x, letter, key, title, note in [
            (19, 'a', 'train_bce', 'Training loss', '347 patients · observed epochs: 30 / 23'),
            (110, 'b', 'val_bce', 'Validation loss', '71 patients · selected epochs: 7 / 17')]:
        panel_heading(fig, letter, title, x-11, 136)
        canvas.text(x-1, 130, note)
        ax = canvas.axes(x, 90, 65, 36)
        for i, run_id in enumerate(RUNS):
            group = histories[run_id]
            ax.plot([int(r['epoch']) for r in group], [float(r[key]) for r in group],
                    color=METHOD_COLORS[run_id], linestyle=LINES[i], linewidth=LINEWIDTH['primary'])
            if key == 'val_bce':
                selected = configs[i]['selected_epoch']
                value = float(group[selected-1][key])
                ax.plot([selected, selected], [.015, value], color=METHOD_COLORS[run_id],
                        linestyle=':', linewidth=LINEWIDTH['comparison'])
                ax.plot(selected, value, color=METHOD_COLORS[run_id], marker=MARKERS[i],
                        markersize=MARKER_SIZE['reference'], linestyle='none')
        ax.set(xlim=(0, 31), xticks=[0, 10, 20, 30], ylim=(.015, .05),
               yticks=[.02, .03, .04, .05], xlabel='Epoch', ylabel='Mean BCE')
        axes.append(ax)
    stats = []
    for x, letter, metric, title, ylabel in [
            (19, 'c', 'dice', 'Paired LV overlap · n = 71', 'Patient mean Dice'),
            (110, 'd', 'label_ef_absolute_error_pp', 'Paired label EF agreement · n = 70',
             'Absolute EF error (pp)')]:
        group = [r for r in pairs if r['metric'] == metric]
        a, b = [np.array([r[k] for r in group]) for k in ['baseline', 'regularized']]
        sa, sb, delta = describe(a), describe(b), describe(b-a)
        stats.append({'metric': metric, 'n_patients': len(group),
                      'baseline': sa, 'regularized': sb, 'paired_difference': delta})
        panel_heading(fig, letter, title, x-11, 76)
        note = (f"Mean {sa['mean']:.4f} → {sb['mean']:.4f} · Δ {delta['mean']:+.4f}" if metric == 'dice'
                else f"MAE {sa['mean']:.2f} → {sb['mean']:.2f} pp · Δ {delta['mean']:+.2f}")
        canvas.text(x-1, 70, note)
        ax = canvas.axes(x, 26, 65, 36)
        offsets = np.array([int.from_bytes(r['patient_id'].encode(), 'little') % 71 / 70
                            for r in group]) * .16-.08
        for j, (start, stop) in enumerate(zip(a, b)):
            ax.plot([offsets[j], 1+offsets[j]], [start, stop], color=COLORS['muted'],
                    alpha=.20, linewidth=LINEWIDTH['comparison'], zorder=1)
        for i, values in enumerate([a, b]):
            ax.scatter(i+offsets, values, color=METHOD_COLORS[RUNS[i]], marker=MARKERS[i],
                       s=MARKER_SIZE['primary']**2, alpha=.75, edgecolors='none', zorder=2)
            ax.errorbar(i+.22, values.mean(), yerr=values.std(ddof=1),
                        color=COLORS['axis'], marker='D', markerfacecolor=COLORS['background'],
                        markersize=MARKER_SIZE['reference'], linewidth=LINEWIDTH['primary'],
                        capsize=MARKER_SIZE['primary'], zorder=3)
        if metric == 'dice':
            lower = min(.7, np.floor(min(a.min(), b.min())*10)/10)
            ax.set(ylim=(lower, 1), yticks=np.arange(lower, 1.001, .1))
        else:
            upper = np.ceil(max(a.max(), b.max(), sa['mean']+sa['sample_sd'],
                                sb['mean']+sb['sample_sd'])/10)*10
            ax.set(ylim=(0, upper), yticks=np.arange(0, upper+1, 10))
        ax.set(xlim=(-.2, 1.4), xticks=[0, 1], xticklabels=LABELS, ylabel=ylabel)
        ax.spines['bottom'].set_visible(False)
        ax.tick_params(axis='x', length=0)
        axes.append(ax)
    canvas.text(8, 12, 'Points/gray links: paired patients. Diamonds/whiskers: patient mean ± sample SD; no seed uncertainty.')
    canvas.text(8, 7, 'EF: common 70/71 patients; regularized patient0039 invalid (ESV > EDV). No imputation or significance tests.')
    write_json(OUT/'source_data/paired_statistics.json', stats)
    alignment(fig, OUT, STEM, axes, ['a', 'b', 'c', 'd'],
              [['a', 'b'], ['c', 'd']], [['a', 'c'], ['b', 'd']], args.alignment_auditor)
    export_figure(fig, OUT/STEM)
    plt.close(fig)
    caption = """Supplementary Figure 3 | Training history and paired validation performance of two existing configurations.
a,b, Observed training and validation mean binary cross-entropy (BCE), without smoothing or extrapolation. The baseline completed 30 epochs; the regularized configuration completed 23. Symbols and dotted guides in b mark the original validation-selected checkpoints (epochs 7 and 17), verified against the saved weights. Both runs used the same DeepLabV3–ResNet50 architecture, initialization, training-derived normalization, patient split (347 training and 71 validation patients), learning rate, batch size and seed (2026). Regularization combined image augmentation, weight decay and early stopping; this comparison does not isolate individual factors. Augmented training losses and unaugmented validation losses represent different data conditions. c, Dice averaged over four expert-labeled frames per validation patient (2CH/4CH × ED/ES; n = 71 patients, 284 frames per run). d, Absolute error against CAMUS Info.cfg EF labels, using the original expert ED/ES phases and 20-disk biplane shorter-axis predictions, for the common valid patients (n = 70). The regularized prediction for patient0039 had ESV > EDV and null EF; this patient remains in c and in the complete source table. Baseline/regularized EF coverage is 71/71 and 70/71; paired MAE is 8.24/9.83 percentage points (pp). Points show patients; gray lines connect matching patients, with deterministic horizontal offsets only. Diamonds and whiskers denote the patient mean ± sample standard deviation, not variability across training runs. There was one historical run per configuration; no hypothesis tests, new model selection or test-performance comparisons are shown. These public CAMUS transthoracic half-sequences are not wearable recordings; HR/CO are unavailable. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.
"""
    (OUT/'caption_en.md').write_text(caption, encoding='utf-8')
    provenance(OUT, sources, experiment='two_historical_CAMUS_training_configurations', figure='Fig.S3',
               data_split='training logs and validation metrics only', experiments=RUNS,
               configurations=configs, core_conclusion='A small Dice improvement does not establish improved clinical-label EF estimation.',
               n_validation_patients_dice=71, n_common_valid_ef=70,
               validation_ef_coverage={'baseline': 71, 'regularized': 70, 'attempted_each': 71},
               excluded_from_paired_ef=['patient0039'], excluded_from_segmentation=[],
               variability='Sample SD across patients; one training run per configuration, no seed uncertainty',
               hypothesis_tests=None, new_model_selection=False,
               panel_roles={'a': 'observed optimization', 'b': 'original validation checkpoint selection',
                            'c': 'paired spatial performance', 'd': 'paired clinical-label EF performance'},
               font_path=font, width_mm=183, height_mm=158,
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.S3: n=71 Dice, n=70 paired EF; caption {len(caption.split())} words; {OUT}')


if __name__ == '__main__':
    main()
