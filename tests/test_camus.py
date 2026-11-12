"""CAMUS 专用处理边界：官方标签身份、原始参考保留和声窗审计。"""
import numpy as np
import pytest

from src.data.camus.prepare import prepare_case


def test_camus_labels_and_coordinate_audit_are_preserved():
    frames = np.zeros((3, 20, 30), np.uint8)
    frames[:, 2:18, 3:27] = 100
    frames[:, 0, 29] = 255  # 模拟与声窗分离的界面文字
    raw = np.zeros_like(frames)
    raw[[0, 2], 5:15, 10:20] = 1
    raw[:, 3:5, 10:20] = 2  # 心肌不能当作左室腔
    raw[:, 15:18, 10:20] = 3  # 左房不能当作左室腔
    arrays, meta = prepare_case(frames, raw, np.array([True, False, True]),
                               {'patient_id': 'p1', 'view': '4CH', 'phases': {'ED': 0, 'ES': 2}},
                               {'output_hw': [20, 30], 'auto_largest_support': True})
    assert np.array_equal(arrays['original_gt'], raw[[0, 2]] == 1)
    assert arrays['original_gt_indices'].tolist() == [0, 2]
    assert not arrays['masks'][1].any() and not arrays['frames'][:, 0, 29].any()
    audit = meta['audit']
    assert audit['timestamps_s'] is None and audit['spacing_xy_mm'] is None
    assert not audit['roi_reviewed'] and audit['removed_foreground_label_pixels'] == 0
    assert np.allclose(np.array(audit['transform']['original_to_processed']) @
                       np.array(audit['transform']['processed_to_original']), np.eye(3))
    with pytest.raises(ValueError, match='擦除'):
        prepare_case(frames, raw, np.array([True, False, True]),
                     {'patient_id': 'p1', 'view': '4CH'}, {'crop_xyxy': [0, 0, 5, 20]})


def test_image_support_fallback_does_not_erase_expert_label():
    frames = np.zeros((2, 12, 12), np.uint8)
    frames[:, 2:10, 2:10] = 100
    labels = np.zeros_like(frames)
    labels[:, 1:5, 1:5] = 1
    arrays, meta = prepare_case(frames, labels, np.ones(2, bool),
                               {'patient_id': 'p2', 'view': '2CH'}, {'output_hw': [12, 12]})
    assert np.array_equal(arrays['masks'], labels)
    assert not meta['audit']['auto_support_applied']
    assert 'auto_support_disabled_to_preserve_expert_labels' in meta['audit']['issues']
