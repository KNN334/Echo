"""Rebuild Fig. 1 from the frozen CAMUS cohort, configuration and input cache."""
import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from style.palette import COLORS, LINEWIDTH, MM_PER_INCH, apply_style, export_figure, figure_size, panel_heading
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from _paper_common import (Canvas, PREPARED, RUN, alignment, calibrated_overlay, load_case,
                           provenance, read_csv, read_json, write_csv)

OUT = ROOT / 'figures/fig_01_data_workflow'
STEM = 'fig_01_data_workflow'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    OUT.mkdir(exist_ok=True)
    (OUT/'source_data').mkdir(exist_ok=True)
    manifest_path = PREPARED/'manifest.json'
    split_path = ROOT/'configs/camus_splits.json'
    experiment_path = ROOT/'checkpoints/camus_cuda_progress/experiment.json'
    training_path = ROOT/'checkpoints/camus_cuda_progress/training.csv'
    cases = read_json(manifest_path)['cases']
    splits = read_json(split_path)
    patients = splits['patients']
    assert all(patients[c['patient_id']] == c['split'] for c in cases)
    assert len(set(c['case_id'] for c in cases)) == len(cases) == 1000
    assert len(patients) == len(set(c['patient_id'] for c in cases)) == 500
    assert all(v == 2 for v in Counter(c['patient_id'] for c in cases).values())
    coverage = []
    for split in ['train', 'val', 'test']:
        group = [c for c in cases if c['split'] == split]
        coverage.append({'split': split, 'patients': len(set(c['patient_id'] for c in group)),
                         'view_sequences': len(group), 'frames': sum(c['frames'] for c in group),
                         'expert_labeled_frames': sum(c['labeled_frames'] for c in group)})
    assert [r['patients'] for r in coverage] == [347, 71, 82]
    total_frames = sum(r['frames'] for r in coverage)
    assert total_frames == 19232
    experiment = read_json(experiment_path)
    assert experiment['config']['test']['temporal'] is False
    assert experiment['config']['test']['quality_gate'] is False
    function = read_csv(RUN/'function.csv')
    reference_counts = []
    for method in ['20_disks_shorter_axis', 'biplane_vs_CAMUS_reported_EF']:
        group = [r for r in function if r['method'] == method]
        assert len(group) == len(set(r['patient_id'] for r in group)) == 82
        reference_counts.append({'method': method, 'patients': len(group),
                                  'reference_scope': group[0]['reference_scope']})
    write_csv(OUT/'source_data/cohort.csv', coverage)
    write_csv(OUT/'source_data/reference_coverage.csv', reference_counts)
    write_csv(OUT/'source_data/case_manifest.csv', [{k: c[k] for k in
              ['case_id', 'patient_id', 'view', 'split', 'frames', 'labeled_frames']} for c in cases])

    fig = plt.figure(figsize=figure_size(height_mm=163))
    canvas = Canvas(fig)
    panel_heading(fig, 'a', 'Current validation data', 8, 156)
    canvas.text(8, 148, f'CAMUS · {len(patients)} patients', fontweight='bold')
    canvas.text(8, 143, f'{len(cases):,} view sequences · {total_frames:,} frames')
    canvas.text(8, 138, '2CH + 4CH · ED–ES half-sequences')
    split_axes = []
    for x, title, row in zip([8, 32, 56], ['Train', 'Validation', 'Test'], coverage):
        split_axes.append(canvas.card(x, 119, 21, 15, title, [f"{row['patients']} patients"]))
    canvas.text(8, 113, 'Custom fixed split · no patient overlap')

    panel_heading(fig, 'b', 'Preprocessing and input', 91, 156)
    sources = [manifest_path, split_path, experiment_path, training_path,
               RUN/'function.csv', ROOT/'configs/model/deeplabv3_resnet50.yaml',
               ROOT/'src/data/camus/prepare.py', ROOT/'src/data/transforms.py',
               ROOT/'src/models/build.py', ROOT/'src/models/deeplabv3.py',
               ROOT/'src/engine/evaluator.py', ROOT/'src/geometry/mask_features.py',
               ROOT/'src/geometry/volume.py', ROOT/'src/geometry/functional.py', Path(__file__)]
    images = []
    # Q1 case and its paired view illustrate actual inputs; not a new selection for performance.
    for x, view in [(91, '2CH'), (109, '4CH')]:
        meta, arrays, paths = load_case('patient0189_'+view)
        sources.extend(paths)
        canvas.text(x, 146, view+' · ED')
        image_ax = canvas.axes(x, 125, 16, 16)
        images.append(calibrated_overlay(image_ax, meta, arrays, 'ED', field_mm=(200, 200),
                                          contours=False, scale=False))
    for y, text in zip([148, 143, 138, 133, 128, 123], [
            'Image-derived support', 'Resize to 112 × 112', 'Gray → 3 channels',
            'Training-set normalization', 'ED/ES labels retained', 'FPS-derived time']):
        canvas.text(129, y, text)
    canvas.text(91, 113, 'Inverse transform + spatial metadata retained')

    def arrow(x0, y0, x1, y1):
        fig.add_artist(FancyArrowPatch((x0/canvas.width, y0/canvas.height),
            (x1/canvas.width, y1/canvas.height), transform=fig.transFigure,
            arrowstyle='-|>', mutation_scale=7, color=COLORS['axis'], linewidth=LINEWIDTH['comparison']))

    arrow(79, 136, 89, 136)
    panel_heading(fig, 'c', 'LV segmentation to calibrated geometry and function', 8, 103)
    chain = [
        ('DeepLabV3–ResNet50', ['LV foreground · p ≥ 0.5', 'Validation-selected model', 'Framewise input from b'], 'primary'),
        ('Restore coordinates', ['112 × 112 → original', 'Largest LV + hole filling*', 'Original spacing (mm)'], 'axis'),
        ('Contour geometry', ['Area + proxy long axis', '20 diameters per view', 'PCA-derived proxy points'], 'axis'),
        ('Function estimates', ['EDV, ESV, SV (mL)', 'LVEF (%)', 'ED/ES or auto extrema'], 'primary')]
    chain_axes = []
    for x, (title, lines, color) in zip([8, 51, 94, 137], chain):
        chain_axes.append(canvas.card(x, 71, 38, 27, title, lines, color))
    for x in [46, 89, 132]:
        arrow(x+.3, 84, x+4.7, 84)
    canvas.text(8, 65, 'Single plane: area–length · calibrated volume (mL)')
    canvas.text(91, 65, 'Biplane: 20 paired disks · shorter long axis')
    canvas.text(8, 59, '*Geometry cleaning only; spatial metrics use the restored prediction before cleaning.')

    panel_heading(fig, 'd', 'Reference levels and available evidence', 8, 49)
    reference_axes = []
    reference_cards = [
        ('Expert ED/ES contours', ['Dice, ASSD, HD95 · n = 82', 'Volumes/EF via the same geometry',
                                  'Not an independent clinical standard'], 'expert_contour'),
        ('CAMUS EF labels (Info.cfg)', ['Biplane EF comparison · n = 82', 'Dataset clinical label reference',
                                       'No independent volume labels'], 'clinical_label'),
        ('HR and CO: unavailable', ['No full cycle or reliable reference HR', 'Manual point labels: unavailable',
                                   'Target: wearable; no patch data'], 'muted')]
    for x, (title, lines, color) in zip([8, 65.5, 123], reference_cards):
        reference_axes.append(canvas.card(x, 15, 53, 28, title, lines, color))
    canvas.text(8, 5, 'Current evidence: public transthoracic CAMUS. Wearable monitoring remains a target application.')

    alignment(fig, OUT, STEM, split_axes+chain_axes+reference_axes,
              ['train', 'val', 'test', 'c1', 'c2', 'c3', 'c4', 'd1', 'd2', 'd3'],
              [['train', 'val', 'test'], ['c1', 'c2', 'c3', 'c4'], ['d1', 'd2', 'd3']], [],
              args.alignment_auditor)
    export_figure(fig, OUT/STEM)
    plt.close(fig)
    caption = """Figure 1 | Current CAMUS validation cohort and contour-based cardiac function workflow.
a, Fixed custom patient-level training, validation and test partitions; this is not the official CAMUS split. b, Public transthoracic 2CH/4CH ED–ES half-sequences are processed to 112 × 112 pixels. Example ED inputs are the paired views of patient0189. Grayscale frames are replicated into three channels and normalized with training-set statistics. Original expert labels, spatial calibration and inverse coordinate transforms are retained. Time is derived from the reported frame rate. c, The frozen DeepLabV3–ResNet50 baseline segments each frame at a fixed probability threshold of 0.5. Predictions are restored to original coordinates before spatial evaluation. Geometry uses the largest LV component with hole filling and contour-derived proxy landmarks, followed by single-plane area–length or 20-disk biplane estimation using the shorter long axis. EDV/ESV yield SV and LVEF; automatic extrema are restricted to the available half-sequence. d, Expert ED/ES contours support spatial evaluation and same-geometry functional references; these volumes are not an independent clinical gold standard. CAMUS Info.cfg EF labels provide a separate dataset clinical-label comparison (n = 82 patients each for biplane references). HR/CO and manual landmark accuracy are unavailable with the present references. These data do not validate patch acquisition or continuous wearable monitoring. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0. Input images are shown without additional cropping or intensity adjustment.
"""
    (OUT/'caption_en.md').write_text(caption, encoding='utf-8')
    provenance(OUT, sources, figure='Fig.1', archetype='schematic-led composite',
               core_conclusion='The public half-sequence validation workflow and its reference boundaries are traceable.',
               panel_roles={'a': 'cohort and independent split', 'b': 'actual input and preprocessing',
                            'c': 'implemented inference and geometry', 'd': 'reference hierarchy and missing evidence'},
               model_selection='Existing validation-loss checkpoint; epoch 7 of 30; no reselection.',
               diagram_edges='a→b indicates preprocessing; c is the implemented inference chain. No wearable-data arrow.',
               input_example_selection='Existing Q1 patient0189 and paired view; illustrative, not quantitative evidence.',
               image_display=images, statistical_claims='Cohort counts only; no statistical testing or new uncertainty.',
               font_path=font, width_mm=183, height_mm=163,
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.1 exported to {OUT}; caption {len(caption.split())} words')


if __name__ == '__main__':
    main()
