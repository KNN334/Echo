"""Rebuild Table S2 with direct frame IoU and patient-level stratified summaries."""
import argparse
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use('Agg')
import numpy as np
from style.palette import apply_style
from src.data.transforms import Transform
from _paper_common import (RUN, load_case, provenance, read_csv, read_json, write_csv)
from _paper_tables import render_table, write_markdown

STEM = 'table_s02_segmentation'
OUT = ROOT/'figures'/STEM
METRICS = ['dice', 'iou', 'assd', 'hd95', 'hd_max']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True, exist_ok=True)
    path = RUN/'structure.csv'
    split_path = ROOT/'configs/camus_splits.json'
    expected = {p for p, s in read_json(split_path)['patients'].items() if s == 'test'}
    assert len(expected) == 82
    sources = [path, split_path, Path(__file__), OUT/'figure_contract.md',
               ROOT/'figures/_paper_tables.py', ROOT/'src/data/transforms.py',
               ROOT/'figures/fig_02_segmentation_validation/source_data/patient_metrics.csv']
    saved = read_csv(path)
    assert len(saved) == 328 and {r['patient_id'] for r in saved} == expected
    by_case = defaultdict(list)
    for row in saved:
        by_case[row['case_id']].append(row)
    assert len(by_case) == 164
    frames = []
    for case, rows in sorted(by_case.items()):
        meta, arrays, paths = load_case(case)
        sources.extend(paths)
        assert len(rows) == 2 and meta['patient_id'] in expected
        assert set(int(r['frame']) for r in rows) == set(meta['phases'].values())
        tr = meta['audit']['transform']
        transform = Transform(tuple(tr['original_hw']), tuple(tr['crop_xyxy']), tuple(tr['output_hw']))
        for row in rows:
            frame = int(row['frame'])
            phase = next(p for p, i in meta['phases'].items() if i == frame)
            prediction = transform.restore_mask(arrays['prediction'][frame]).astype(bool)
            truth = arrays['original_gt'][list(arrays['original_gt_indices']).index(frame)].astype(bool)
            assert prediction.shape == truth.shape == tuple(tr['original_hw'])
            intersection = int(np.count_nonzero(prediction & truth))
            union = int(np.count_nonzero(prediction | truth))
            n_pred, n_truth = int(prediction.sum()), int(truth.sum())
            assert n_pred > 0 and n_truth > 0 and union > 0
            dice = 2*intersection/(n_pred+n_truth)
            iou = intersection/union
            assert np.isclose(dice, float(row['dice']), atol=1e-12, rtol=0), (case, phase)
            assert np.isclose(iou, dice/(2-dice), atol=1e-12, rtol=0)
            assert row['distance_unit'] == 'mm' and row['distance_status'] == 'ok'
            frames.append({'patient_id': row['patient_id'], 'case_id': case, 'view': row['view'],
                           'phase': phase, 'frame': frame, 'prediction_pixels': n_pred,
                           'expert_pixels': n_truth, 'intersection_pixels': intersection,
                           'union_pixels': union, 'dice': dice, 'iou': iou,
                           **{m: float(row[m]) for m in ['assd', 'hd95', 'hd_max']},
                           'distance_unit': 'mm', 'distance_status': row['distance_status']})
    specifications = [('Overall', None, None), ('2CH, ED + ES', '2CH', None),
                      ('4CH, ED + ES', '4CH', None), ('ED, 2CH + 4CH', None, 'ED'),
                      ('ES, 2CH + 4CH', None, 'ES'), ('2CH, ED', '2CH', 'ED'),
                      ('2CH, ES', '2CH', 'ES'), ('4CH, ED', '4CH', 'ED'), ('4CH, ES', '4CH', 'ES')]
    patient_rows, summary, table_rows = [], [], []
    original_patients = {r['patient_id']: r for r in read_csv(
        ROOT/'figures/fig_02_segmentation_validation/source_data/patient_metrics.csv')}
    for name, view, phase in specifications:
        subset = [r for r in frames if (view is None or r['view'] == view)
                  and (phase is None or r['phase'] == phase)]
        grouped = defaultdict(list)
        for row in subset:
            grouped[row['patient_id']].append(row)
        assert set(grouped) == expected
        count_per_patient = (2 if view is None else 1)*(2 if phase is None else 1)
        assert all(len(g) == count_per_patient for g in grouped.values())
        group_means = []
        for patient, group in sorted(grouped.items()):
            means = {m: float(np.mean([r[m] for r in group])) for m in METRICS}
            patient_rows.append({'stratum': name, 'patient_id': patient,
                                 'n_frames': len(group), **means})
            group_means.append(means)
            if name == 'Overall':
                assert all(np.isclose(means[m], float(original_patients[patient][m]), atol=1e-12)
                           for m in ['dice', 'assd', 'hd95'])
        cells = [name, str(len(grouped)), str(len(subset))]
        for metric in METRICS:
            values = np.array([r[metric] for r in group_means])
            assert np.isfinite(values).all()
            mean, sd = float(values.mean()), float(values.std(ddof=1))
            summary.append({'stratum': name, 'metric': metric, 'n_patients': len(grouped),
                            'n_frames': len(subset), 'mean': mean, 'sample_sd': sd,
                            'minimum': float(values.min()), 'median': float(np.median(values)),
                            'maximum': float(values.max()),
                            'unit': 'dimensionless' if metric in ['dice', 'iou'] else 'mm'})
            digits = 3 if metric in ['dice', 'iou'] else 2
            cells.append(f'{mean:.{digits}f} ± {sd:.{digits}f}')
        table_rows.append((False, cells))
    assert len(frames) == 328 and len(patient_rows) == 9*82 and len(summary) == 45
    notes = [
        'Values: mean ± sample SD of patient means within each stratum (n = 82); frames are repeated observations.',
        'Dice/IoU are dimensionless. ASSD/HD95/HDmax use original image coordinates and spatial calibration.',
        'IoU was calculated directly for each restored binary mask, then averaged per patient, not from mean Dice.',
        'Strata overlap; counts must not be added. No patients/frames were excluded; no imputation or significance tests.',
        '2CH/4CH: two-/four-chamber; ED/ES: end-diastole/end-systole. Expert labels are available only at ED/ES.',
        'Public CAMUS half-sequences (CC BY-NC-SA 4.0); 112 × 112 caches; not wearable patch recordings.'
    ]
    headers = ['Stratum', 'Patients\nn', 'Frames\nn', 'Dice', 'IoU', 'ASSD\n(mm)', 'HD95\n(mm)', 'HDmax\n(mm)']
    caption = """Supplementary Table 2 | Patient-level LV segmentation performance by view and reference phase on CAMUS.
The frozen DeepLabV3–ResNet50 baseline was evaluated in all 82 test patients (164 view sequences; 328 expert-labeled frames). Each cell reports the mean ± sample standard deviation across patient means within the stated stratum. Overall values average four frames per patient; view-only and phase-only values average two; view–phase values use one. The strata overlap and do not constitute independent cohorts. Dice and intersection-over-union (IoU) were calculated from the binary predictions restored to original image coordinates and the original expert masks. IoU was computed per frame from intersection and union pixel counts before patient aggregation, rather than by transforming an averaged Dice. Average symmetric surface distance (ASSD), 95th-percentile Hausdorff distance (HD95) and maximum Hausdorff distance (HDmax) retain the original frozen metrics, evaluated using original pixel spacing in millimetres. The overall Dice/ASSD/HD95 patient values match Figure 2. No patient, frame or outlier was removed; no imputation, confidence intervals or hypothesis tests were used. ED and ES denote expert end-diastole and end-systole; 2CH/4CH denote independently acquired two-/four-chamber views. Intermediate frames have no expert reference. These are public CAMUS transthoracic half-sequences with 112 × 112 image caches, not wearable patch acquisitions. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.
"""
    dimensions = render_table(OUT, STEM, 'Supplementary Table 2 | LV segmentation by view and phase',
                              headers, [31, 12, 12, 22, 22, 24, 24, 24], table_rows, notes,
                              height_mm=112, row_height_mm=6, header_top_mm=99,
                              auditor=args.alignment_auditor)
    write_csv(OUT/'source_data/frame_metrics.csv', frames)
    write_csv(OUT/'source_data/patient_stratum_metrics.csv', patient_rows)
    write_csv(OUT/'source_data/stratum_statistics.csv', summary)
    (OUT/'caption_en.md').write_text(caption, encoding='utf-8')
    write_markdown(OUT/(STEM+'.md'), caption, headers, table_rows, notes)
    provenance(OUT, sources, table='Table S2', n_patients_per_stratum=82,
               n_original_frames=328, n_view_sequences=164, n_overlapping_strata=9,
               statistical_unit='Patient mean within stratum', variability='Sample SD across 82 patient means',
               new_statistics='Direct per-frame IoU from restored binary masks, followed by patient aggregation.',
               distance_metrics='Frozen original-coordinate, original-mm-calibrated values; not recomputed',
               excluded_patients=[], excluded_frames=[], imputation=None, hypothesis_tests=None,
               confidence_intervals=None, overall_patient_metrics_match_figure_2=True,
               font_path=font, **dimensions,
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Table S2: 9 strata, 82 patients each, 328 frames; {OUT}')


if __name__ == '__main__':
    main()
