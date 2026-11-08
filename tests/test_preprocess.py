import numpy as np
import pytest
from cardiac.preprocess import Transform, process
from cardiac.metadata import audit_metadata


def test_coordinate_roundtrip_anisotropic_spacing():
    t = Transform((100, 200), (10, 20, 170, 80), (112, 112))
    p = np.array([[10, 20], [100.2, 65.7], [169, 79]])
    assert np.allclose(p, t.points(t.points(p), inverse=True))
    r = t.record([.4, .8])
    assert np.allclose(r["processed_spacing_xy_mm"], [.4 * 160 / 112, .8 * 60 / 112])


def test_text_exclusion_and_label_interpolation():
    x = np.ones((2, 50, 60), np.uint8) * 200
    y = np.zeros_like(x)
    y[:, 20:30, 20:30] = 1
    a, b, meta = process(x, {"output_hw": [80, 80], "exclude_boxes_xyxy": [[0, 0, 60, 10]]}, {}, y)
    assert a[:, :15].sum() == 0
    assert set(np.unique(b)) <= {0, 1}
    assert "missing_spatial_calibration" in meta["issues"]


def test_timing_not_invented():
    a = audit_metadata(3)
    assert a["timestamps_s"] is None
    assert audit_metadata(3, fps=50)["timestamps_s"] == [0, .02, .04]
    with pytest.raises(ValueError):
        audit_metadata(3, fps=50, timestamps_s=[0, .04, .08])
    with pytest.raises(ValueError):
        audit_metadata(3, timestamps_s=[0, .1, .1])


def test_auto_support_preserves_frame_count_and_removes_isolated_text():
    x=np.zeros((12,60,80),np.uint8)
    x[:,10:50,20:70]=100
    x[:,2:5,2:8]=255
    out,_,audit=process(x,{'auto_largest_support':True,'output_hw':[60,80]}, {'fps':50})
    assert audit['n_frames']==12 and len(audit['timestamps_s'])==12
    assert out[:,2:5,2:8].sum()==0
    assert out[:,20:30,30:40].mean()==100


def test_split_patient_disjoint(tmp_path):
    from cardiac.dataset import make_splits
    a = make_splits(["patient0001", "patient0002"], tmp_path / "a.json")
    b = make_splits(["patient0002", "patient0001"], tmp_path / "b.json")
    assert a == b
