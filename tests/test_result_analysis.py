"""结果图的参考层级、患者统计、缺失及来源隔离检查。"""
import numpy as np
import pytest

from src.visualization.analysis import (
    REF_GEOMETRY, REF_DATASET, agreement, number, patient_pairs, paired_errors,
    read_csv, load_bundle,
)
from src.utils.io import write_csv, write_json


def row(pid, pred, ref, scope=REF_GEOMETRY, method='single_plane_area_length', view='4CH'):
    return {'patient_id': pid, 'EF': pred, 'ref_EF': ref, 'reference_scope': scope,
            'method': method, 'view': view}


def test_reference_sources_and_duplicate_patient_observations_are_not_pooled():
    rows = [row('p1', 55, 50), row('p1', 65, 50), row('p2', 30, ''),
            row('p3', 40, 50, REF_DATASET), row('p4', 40, 50, view='2CH')]
    ids, pred, ref = patient_pairs(rows, 'EF', method='single_plane_area_length',
                                    reference_scope=REF_GEOMETRY, view='4CH')
    assert ids == ['p1']
    np.testing.assert_allclose(pred, [60])
    np.testing.assert_allclose(ref, [50])


def test_agreement_uses_patient_differences_and_sample_sd():
    result = agreement([12, 23, np.nan], [10, 20, 30])
    assert result['n'] == 2 and result['mae'] == 2.5 and result['bias'] == 2.5
    assert result['loa_low'] == pytest.approx(2.5 - 1.96 * np.sqrt(.5))
    assert agreement([10], [10])['loa_low'] is None
    assert agreement([], [])['mae'] is None


def test_phase_comparison_keeps_only_common_valid_patients():
    rows = [row('p1', 60, 50), row('p2', 60, 50),
            row('p1', 65, 50, method='single_plane_auto_extrema_4CH'),
            row('p3', 65, 50, method='single_plane_auto_extrema_4CH')]
    ids, first, second, na, nb = paired_errors(rows, '4CH')
    assert ids == ['p1'] and na == nb == 2
    np.testing.assert_allclose(first, [10])
    np.testing.assert_allclose(second, [15])


def test_empty_nonfinite_csv_values_are_never_zero_and_bom_is_read(tmp_path):
    for value in ('', None, 'NaN', 'inf', '-inf'):
        assert np.isnan(number(value))
    path = tmp_path / 'history.csv'
    write_csv(path, [{'epoch': 7, 'val_bce': .04}])
    assert read_csv(path)[0]['epoch'] == '7'


def _bundle_fixture(tmp_path):
    results, training = tmp_path / 'results', tmp_path / 'training'
    results.mkdir(); training.mkdir()
    (training / 'best.pt').write_bytes(b'frozen-test-checkpoint')
    from src.visualization.analysis import digest
    write_json(results / 'summary.json', {'split': 'test', 'weights_sha256': digest(training / 'best.pt')})
    write_json(training / 'run.json', {'train_patients': ['p1'], 'val_patients': ['p2']})
    write_csv(training / 'training.csv', [{'epoch': 1, 'train_bce': .1, 'val_bce': .2}])
    for name in ('structure', 'function', 'frames'):
        write_csv(results / (name + '.csv'), [{'patient_id': 'p1'}])
    return results, training


def test_mismatched_checkpoint_stops_before_plotting(tmp_path):
    results, training = _bundle_fixture(tmp_path)
    (training / 'best.pt').write_bytes(b'another-run')
    with pytest.raises(ValueError, match='训练权重与测试摘要不匹配'):
        load_bundle(results, training)


def test_hidden_test_patient_in_training_is_rejected(tmp_path):
    results, training = _bundle_fixture(tmp_path)
    with pytest.raises(ValueError, match='患者集合缺失或相互重叠'):
        load_bundle(results, training)
