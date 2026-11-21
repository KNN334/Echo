"""Rebuild Table 1 from the complete CAMUS manifest and local metadata."""
import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use('Agg')
import numpy as np
from style.palette import apply_style
from _paper_common import PREPARED, RUN, provenance, read_csv, read_json, write_csv, write_json
from _paper_tables import render_table, write_markdown

OUT = ROOT/'figures/table_01_cohort'
STEM = 'table_01_cohort'
SPLITS = ['train','val','test','total']


def quantiles(values):
    values = np.asarray(values,dtype=float)
    assert len(values) and np.isfinite(values).all()
    return {'n':len(values),'median':float(np.median(values)),
            'q1':float(np.quantile(values,.25,method='linear')),
            'q3':float(np.quantile(values,.75,method='linear')),
            'minimum':float(values.min()),'maximum':float(values.max())}


def iq(values, decimals=1):
    q = quantiles(values)
    return f"{q['median']:.{decimals}f} [{q['q1']:.{decimals}f}, {q['q3']:.{decimals}f}]"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor',type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True,exist_ok=True)
    manifest_path = PREPARED/'manifest.json'
    split_path = ROOT/'configs/camus_splits.json'
    inventory_path = ROOT/'figures/planning/asset_inventory.json'
    manifest = read_json(manifest_path)
    splits = read_json(split_path)['patients']
    assert not manifest['failures']
    cases, patients, sources = [], {}, [manifest_path,split_path,inventory_path,Path(__file__),
                                      ROOT/'figures/_paper_tables.py',RUN/'summary.json',
                                      RUN/'function.csv',RUN/'beats.csv']
    input_paths = []
    for case in manifest['cases']:
        meta_path = PREPARED/(case['case_id']+'.json')
        meta = read_json(meta_path)
        sources.append(meta_path)
        cfg, audit = meta['config'], meta['audit']
        tr = audit['transform']
        pid = case['patient_id']
        assert meta['split'] == case['split'] == splits[pid]
        assert meta['patient_id'] == pid and meta['view'] == case['view']
        assert meta['sequence_type'] == 'half_sequence'
        input_paths.append(meta['input_path'])
        assert case['frames'] == audit['n_frames'] and case['labeled_frames'] == 2
        assert tuple(tr['output_hw']) == (112,112)
        assert audit['timestamp_source'] == 'derived_from_fps'
        assert set(meta['phases']) == {'ED','ES'}
        assert set(meta['phases'].values()) == {0,case['frames']-1}
        assert not audit['roi_reviewed']
        patient = {'patient_id':pid,'split':case['split'],'age_years':float(cfg['Age']),
                   'sex':cfg['Sex'],'dataset_ef_percent':float(cfg['EF'])}
        if pid in patients:
            assert patients[pid] == patient, 'Conflicting patient-level view metadata'
        else:
            patients[pid] = patient
        assert patient['sex'] in ['F','M']
        assert cfg['ImageQuality'] in ['Good','Medium','Poor']
        assert meta['fps'] > 0
        cases.append({'case_id':case['case_id'],**patient,'view':case['view'],
                      'frames':case['frames'],'labeled_frames':case['labeled_frames'],
                      'quality':cfg['ImageQuality'],'fps':float(meta['fps']),
                      'half_sequence_duration_s':(case['frames']-1)/meta['fps'],
                      'original_height_px':tr['original_hw'][0],
                      'original_width_px':tr['original_hw'][1],
                      'original_spacing_x_mm':audit['spacing_xy_mm'][0],
                      'original_spacing_y_mm':audit['spacing_xy_mm'][1],
                      'processed_spacing_x_mm':tr['processed_spacing_xy_mm'][0],
                      'processed_spacing_y_mm':tr['processed_spacing_xy_mm'][1],
                      'roi_reviewed':audit['roi_reviewed']})
    assert len(cases)==1000 and len(patients)==500
    assert len({c['case_id'] for c in cases}) == 1000
    assert all(n==2 for n in Counter(c['patient_id'] for c in cases).values())
    summary = read_json(RUN/'summary.json')
    assert len([p for p in patients.values() if p['split']=='test']) == summary['patients'] == 82
    assert summary['manual_keypoint_labeled_frames']==summary['beats']==0
    assert summary['reference_file_sha256'] is None
    assert summary['manual_landmark_file_sha256'] is None
    assert summary['manual_keypoint_error'] is None
    function_rows = read_csv(RUN/'function.csv')
    assert len(function_rows)==490
    assert all(not r['HR'] and not r['CO'] and not r['ref_CO'] for r in function_rows)
    assert not read_csv(RUN/'beats.csv')
    assert all('/CAMUS/' in p.replace('\\','/') and 'half_sequence' in p for p in input_paths)
    groups = {key:([p for p in patients.values() if p['split']==key],
                  [c for c in cases if c['split']==key]) for key in SPLITS[:-1]}
    groups['total'] = (list(patients.values()),cases)
    assert [len(groups[s][0]) for s in SPLITS] == [347,71,82,500]
    assert sum(c['frames'] for c in cases)==19232

    rows = []
    def section(label):
        rows.append((True,[label,'','','','']))
    def row(label, getter):
        rows.append((False,[label,*[getter(*groups[s]) for s in SPLITS]]))
    def count_pct(items, key, value):
        n = sum(p[key]==value for p in items)
        return f'{n:,} ({100*n/len(items):.1f})'

    section('Patient-level characteristics')
    row('Patients, n',lambda ps,cs:f'{len(ps):,}')
    row('Age, years; median [IQR]',lambda ps,cs:iq([p['age_years'] for p in ps]))
    row('Female, n (%)',lambda ps,cs:count_pct(ps,'sex','F'))
    row('Male, n (%)',lambda ps,cs:count_pct(ps,'sex','M'))
    row('CAMUS EF label, %; median [IQR]',lambda ps,cs:iq([p['dataset_ef_percent'] for p in ps]))
    row('CAMUS EF label coverage, patients',lambda ps,cs:f'{len(ps):,} / {len(ps):,}')
    section('View-sequence and frame-level characteristics')
    row('View sequences, n',lambda ps,cs:f'{len(cs):,}')
    row('2CH / 4CH sequences, n',lambda ps,cs:' / '.join(str(sum(c['view']==v for c in cs)) for v in ['2CH','4CH']))
    row('Observed frames, n',lambda ps,cs:f"{sum(c['frames'] for c in cs):,}")
    row('Expert ED / ES frames, n',lambda ps,cs:f'{len(cs):,} / {len(cs):,}')
    for quality in ['Good','Medium','Poor']:
        row('Image quality - '+quality+', n (%)',lambda ps,cs,q=quality:count_pct(cs,'quality',q))
    row('Frames per sequence; median [IQR]',lambda ps,cs:iq([c['frames'] for c in cs],0))
    row('Frame rate, FPS; median [IQR]',lambda ps,cs:iq([c['fps'] for c in cs]))
    row('ED-ES duration, s; median [IQR]',lambda ps,cs:iq([c['half_sequence_duration_s'] for c in cs],3))
    section('Spatial sampling (one value per sequence)')
    row('Processed raster, height x width; pixels',lambda ps,cs:'112 x 112')
    for label,key in [('Original height, pixels; range','original_height_px'),
                      ('Original width, pixels; range','original_width_px')]:
        row(label,lambda ps,cs,k=key:f"{min(c[k] for c in cs)}-{max(c[k] for c in cs)}")
    assert all(np.isclose(c['original_spacing_x_mm'],.308) and
               np.isclose(c['original_spacing_y_mm'],.308) for c in cases)
    row('Original x / y spacing, mm',lambda ps,cs:'0.308 / 0.308')
    for direction in ['x','y']:
        row('Processed '+direction+' spacing, mm; median [IQR]',
            lambda ps,cs,k='processed_spacing_'+direction+'_mm':iq([c[k] for c in cs],3))

    notes = [
        'Patient statistics use one record per patient; quality and sampling statistics use view sequences.',
        'Values are n (%), median [25th, 75th percentiles], or ranges; IQR boundaries use linear quantiles.',
        'Custom patient split; both views stay together. All data are CAMUS transthoracic ED-ES half-sequences.',
        'Time is derived from FPS, not acquisition timestamps. Original and processed spacing are distinct.',
        'Expert-contour-derived volumes are available but are not independent clinical volume standards.',
        'Independent volume, manual point and HR/CO references, full cycles and project patch recordings are unavailable.',
        'All ROIs retain their unreviewed status. Missing evidence is stated here, not listed as cohort characteristics.'
    ]
    caption = ('Table 1 | CAMUS cohort, patient partitions and available reference evidence.\n\n'
               'The table summarizes all 500 patients and 1,000 two- and four-chamber view sequences '
               'in the local prepared cohort. Age, sex and dataset EF labels were checked for agreement '
               'between both views before retaining one record per patient. Counts, medians and interquartile '
               'boundaries are derived from the fixed patient split and original metadata, with no exclusions '
               'or imputation. Image-quality categories are provided by CAMUS and counted per view sequence. '
               'Sequence duration is the observed ED-to-ES interval, (frame count minus one)/FPS. Original '
               'pixel spacing and the spacing of the 112-by-112 processed raster are reported separately. '
               'Unavailable reference and acquisition evidence is described in the notes rather than '
               'listed as zero-valued cohort characteristics. This concerns available project assets, '
               'not measurements that may have been obtained during the original clinical examination. '
               'Expert ED/ES contours support geometry-derived reference volumes, '
               'but no independent clinical volume standard, manually annotated anatomical points, '
               'complete cardiac cycles, independent HR/CO reference or project wearable acquisition '
               'is available. All ROIs retain their unreviewed status. No between-split hypothesis tests '
               'were performed. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; '
               'data license: CC BY-NC-SA 4.0.\n')
    headers = ['Characteristic','Train','Validation','Test','Total']
    dimensions = render_table(OUT,STEM,'Table 1 | Cohort, patient partitions and reference coverage',
                              headers,[66,26.25,26.25,26.25,26.25],rows,notes,
                              height_mm=145,row_height_mm=3.65,header_top_mm=133,
                              auditor=args.alignment_auditor)
    write_csv(OUT/'source_data/patient_metadata.csv',sorted(patients.values(),key=lambda p:p['patient_id']))
    write_csv(OUT/'source_data/sequence_metadata.csv',cases)
    numeric = {}
    for key,(ps,cs) in groups.items():
        numeric[key] = {'patients':len(ps),'sequences':len(cs),
                        'frames':sum(c['frames'] for c in cs),
                        'female_patients':sum(p['sex']=='F' for p in ps),
                        'male_patients':sum(p['sex']=='M' for p in ps),
                        'age_years':quantiles([p['age_years'] for p in ps]),
                        'dataset_ef_percent':quantiles([p['dataset_ef_percent'] for p in ps]),
                        'quality_sequences':dict(Counter(c['quality'] for c in cs)),
                        'sampling':{name:quantiles([c[name] for c in cs]) for name in
                            ['frames','fps','half_sequence_duration_s','processed_spacing_x_mm',
                             'processed_spacing_y_mm','original_height_px','original_width_px']}}
    write_json(OUT/'source_data/cohort_statistics.json',numeric)
    write_json(OUT/'source_data/unavailable_evidence.json', {
        'scope':'Available CAMUS project assets; not a claim about all original clinical examinations.',
        'previous_display':'Six evidence-availability counts were explicitly rendered as 0 in every split.',
        'revision':'Remove these rows; retain unavailability and unreviewed status in notes. No patient exclusion.',
        'items':[
            {'removed_row':'Independent clinical volume references, patients', 'measurement':None,
             'reason':'No independent reference file supplied to the frozen experiment; contour-derived volumes use the same geometry.',
             'evidence':{'reference_file_sha256':summary['reference_file_sha256']}},
            {'removed_row':'Manual anatomical point labels, patients', 'measurement':None,
             'reason':'No independent manual-landmark file supplied; contour-derived proxy points are not manual labels.',
             'evidence':{'manual_landmark_file_sha256':summary['manual_landmark_file_sha256'],
                         'manual_keypoint_labeled_frames':summary['manual_keypoint_labeled_frames'],
                         'manual_keypoint_error':summary['manual_keypoint_error']}},
            {'removed_row':'Complete cardiac cycles, n', 'measurement':None,
             'reason':'All 1000 manifest sequences are ED-ES half-sequences; frozen beats.csv has no data rows.',
             'evidence':{'half_sequences_checked':len(cases),'complete_beats_reported':summary['beats']}},
            {'removed_row':'Independent HR/CO references, patients', 'measurement':None,
             'reason':'No reliable independent HR/CO reference or complete cycle; HR/CO/ref_CO are absent in all 490 functional rows.',
             'evidence':{'functional_rows_checked':len(function_rows)}},
            {'removed_row':'Project wearable ultrasound acquisitions, n', 'measurement':None,
             'reason':'Every included source path is CAMUS half-sequence data, not a project wearable acquisition.',
             'evidence':{'source_paths_checked':len(input_paths)}},
            {'removed_row':'Human-reviewed ROIs, sequences', 'measurement':None,
             'reason':'All 1000 sidecars explicitly retain roi_reviewed=false; automated processing is not human review.',
             'evidence':{'sidecars_checked':len(cases),'roi_reviewed_true':sum(c['roi_reviewed'] for c in cases)}}]})
    (OUT/'caption_en.md').write_text(caption,encoding='utf-8')
    write_markdown(OUT/(STEM+'.md'),caption,headers,rows,notes)
    provenance(OUT,sources,table='Table 1',statistical_unit='Patients; sequence metadata separately labelled',
               age_sex_ef_view_disagreements=0,missing_demographics=0,
               new_statistics='Descriptive fixed-split counts, percentages, medians and linear quartiles only.',
               hypothesis_tests=None,imputation=None,excluded_patients=[],
               revision='Removed six unavailable-evidence count rows from table; notes retain the limitations.',
               data_scope='Local prepared CAMUS half-sequences; no project patch acquisition.',
               original_data_integrity='Historical manifest only; no new full raw-data download or verification.',
               font_path=font,**dimensions,external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Table 1: {len(patients)} patients, {len(cases)} sequences, {len(rows)} rows; {OUT}')


if __name__=='__main__':
    main()
