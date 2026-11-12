"""处理后数据元信息、正反坐标和患者级划分的回归检查。"""
import numpy as np
import pytest

from src.data.metadata import audit_metadata
from src.data.transforms import Transform


def test_coordinate_roundtrip_anisotropic_spacing():
    """验证非等距缩放时关键点正向和反向坐标变换可逆。"""
    transform = Transform((100, 200), (10, 20, 170, 80), (112, 112))
    points = np.array([[10, 20], [100.2, 65.7], [169, 79]])
    assert np.allclose(points, transform.points(transform.points(points), inverse=True))
    record = transform.record([.4, .8])
    assert np.allclose(record['processed_spacing_xy_mm'], [.4 * 160 / 112, .8 * 60 / 112])


def test_timing_not_invented():
    """缺少可靠采集时间时不生成伪造时间戳。"""
    assert audit_metadata(3)['timestamps_s'] is None
    assert audit_metadata(3, fps=50)['timestamps_s'] == [0, .02, .04]
    with pytest.raises(ValueError):
        audit_metadata(3, fps=50, timestamps_s=[0, .04, .08])
    with pytest.raises(ValueError):
        audit_metadata(3, timestamps_s=[0, .1, .1])


def test_split_patient_disjoint(tmp_path):
    """固定患者划分可复现，患者不会跨训练、验证和测试集。"""
    from src.data.splits import make_splits
    patients = [f'patient{i:04d}' for i in range(1, 100)]
    first = make_splits(patients, tmp_path / 'first.json')
    second = make_splits(list(reversed(patients)), tmp_path / 'second.json')
    assert first == second
    assert set(first.values()) == {'train', 'val', 'test'}
