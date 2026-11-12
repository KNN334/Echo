"""通用处理后数据核查及固定患者划分；训练和评估只检查各自子集。"""
import os
from pathlib import Path
import numpy as np
from ..config.paths import project_path
from ..utils.io import read_json, write_json
from ..utils.hash import sha256
from .splits import make_splits
from .transforms import Transform


def prepare_split_manifests(data_config):
    """只读取现有处理后数据，生成固定患者划分及三个独立数据清单。"""
    root = project_path(data_config['dataset'])
    source_manifest_path = root / 'manifest.json'
    if not source_manifest_path.is_file():
        raise FileNotFoundError(f'找不到已处理数据集清单：{source_manifest_path}')
    source = read_json(source_manifest_path)
    if source.get('failures'):
        raise ValueError('处理后数据集清单含失败病例，请先修复数据。')
    cases = source.get('cases', [])
    if not cases:
        raise ValueError(f'处理后数据集清单没有病例：{source_manifest_path}')
    patients = {row.get('patient_id') for row in cases}
    if None in patients or len(patients) != data_config['expected_patients']:
        raise ValueError(f'处理后数据包含 {len(patients - {None})} 名患者，'
                         f'期望 {data_config["expected_patients"]} 名。')

    assignments_path = project_path(data_config['split_assignments'])
    if assignments_path.is_file():
        assignments = read_json(assignments_path).get('patients', {})
    elif all(row.get('split') in ('train', 'val', 'test') for row in cases):
        # 已有预处理清单带有患者划分时直接沿用，不产生新的随机划分。
        assignments = {}
        for row in cases:
            pid, split = row['patient_id'], row['split']
            if pid in assignments and assignments[pid] != split:
                raise ValueError(f'同一患者被分配到多个数据集：{pid}')
            assignments[pid] = split
        write_json(assignments_path, {'protocol': 'preserved_from_processed_manifest', 'patients': assignments})
    else:
        assignments = make_splits(patients, assignments_path, data_config.get('split_seed', 2026))
    if set(assignments) != patients or any(v not in ('train', 'val', 'test') for v in assignments.values()):
        raise ValueError('患者划分清单必须与处理后数据中的患者集合完全一致。')

    groups = {name: [] for name in ('train', 'val', 'test')}
    patient_groups = {name: set() for name in groups}
    seen = set()
    for row in cases:
        pid, view, case_id = row.get('patient_id'), row.get('view'), row.get('case_id')
        split = assignments.get(pid)
        if not isinstance(case_id, str) or not case_id or Path(case_id).name != case_id or case_id in seen:
            raise ValueError(f'重复或非法病例编号：{case_id}')
        if not isinstance(view, str) or split not in groups:
            raise ValueError(f'病例缺少切面或患者划分：{case_id}')
        if row.get('split') is not None and row['split'] != split:
            raise ValueError(f'病例划分与固定患者清单不符：{case_id}')
        if not (root / (case_id + '.npz')).is_file() or not (root / (case_id + '.json')).is_file():
            raise FileNotFoundError(f'病例数组或元数据缺失：{case_id}')
        groups[split].append({**row, 'split': split})
        patient_groups[split].add(pid)
        seen.add(case_id)
    if any(not group for group in groups.values()):
        raise ValueError('训练、验证和测试划分都必须非空。')
    for split in groups:
        manifest_path = project_path(data_config[f'{split}_path'])
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        dataset_root = os.path.relpath(root, manifest_path.parent)
        write_json(manifest_path, {
            'schema_version': 1, 'split': split, 'dataset_root': dataset_root,
            'dataset_manifest_sha256': sha256(source_manifest_path),
            'patients': sorted(patient_groups[split]), 'cases': groups[split],
        })
    return {
        'patients': len(patients), 'cases': len(cases),
        'patient_splits': {key: len(value) for key, value in patient_groups.items()},
        'case_splits': {key: len(value) for key, value in groups.items()},
        'manifest_sha256': sha256(source_manifest_path),
        'array_contents_checked': False,
    }

def validate_prepared(data_config, check_arrays=False):
    """核查处理后影像、专家标注、时间空间元数据及三个独立患者清单。"""
    from .manifests import read_split_manifest

    root = project_path(data_config['dataset'])
    source_manifest_path = root / 'manifest.json'
    source = read_json(source_manifest_path)
    if source.get('failures'):
        raise ValueError('处理后数据集清单含失败病例。')
    cases = source.get('cases', [])
    if not cases:
        raise ValueError('处理后数据集清单没有病例，请先运行 scripts/prepare_data.py。')
    assignments = read_json(project_path(data_config['split_assignments']))['patients']
    patient_groups = {name: set() for name in ('train', 'val', 'test')}
    seen = set()
    case_by_id = {}
    for row in cases:
        pid, view, split, key = row['patient_id'], row['view'], assignments.get(row['patient_id']), row['case_id']
        if not isinstance(key, str) or not key or Path(key).name != key or key in seen:
            raise ValueError(f'重复或非法病例编号：{key}')
        if split not in patient_groups or (row.get('split') is not None and row['split'] != split):
            raise ValueError(f'病例划分与固定患者清单不符：{key}')
        seen.add(key)
        case_by_id[key] = row
        patient_groups[split].add(pid)
        array_path = root / (key + '.npz')
        if not array_path.is_file():
            raise FileNotFoundError(f'缺少处理后数组：{array_path}')
        meta = read_json(root / (key + '.json'))
        if (meta.get('patient_id'), meta.get('view')) != (pid, view) or (
                meta.get('split') is not None and meta['split'] != split):
            raise ValueError(f'病例元数据与清单不符：{key}')
        audit = meta.get('audit')
        if not isinstance(audit, dict) or 'transform' not in audit:
            raise ValueError(f'病例缺少预处理坐标审计：{key}')
        tr = audit['transform']
        transform = Transform(tuple(tr['original_hw']), tuple(tr['crop_xyxy']), tuple(tr['output_hw']))
        expected_hw = data_config.get('preprocessing', {}).get('output_hw')
        if expected_hw is not None and list(tr['output_hw']) != list(expected_hw):
            raise ValueError(f'处理后尺寸与配置不符：{key}。修改配置不会自动重处理缓存。')
        if not np.allclose(transform.matrix, tr['original_to_processed']) or not np.allclose(
                np.linalg.inv(transform.matrix), tr['processed_to_original']):
            raise ValueError(f'正反坐标变换记录不一致：{key}')
        if check_arrays:
            with np.load(array_path, allow_pickle=False) as archive:
                frames, masks, labeled = archive['frames'], archive['masks'], archive['labeled']
                gt, indices = archive['original_gt'], archive['original_gt_indices']
            n = len(frames)
            if frames.ndim != 3 or masks.shape != frames.shape or labeled.shape != (n,):
                raise ValueError(f'帧/标签尺寸不匹配：{key}')
            if labeled.dtype != np.bool_ or not np.isin(masks, [0, 1]).all() or not np.isin(gt, [0, 1]).all():
                raise ValueError(f'专家标签不是二值掩膜或标注帧标志不是布尔值：{key}')
            if list(frames.shape[1:]) != tr['output_hw'] or not np.isfinite(frames).all():
                raise ValueError(f'图像尺寸或像素值异常：{key}')
            if not np.array_equal(indices, np.flatnonzero(labeled)) or gt.shape != (len(indices), *tr['original_hw']):
                raise ValueError(f'原始专家标签或帧索引不完整：{key}')
            if n != row['frames'] or int(labeled.sum()) != row['labeled_frames'] or n != audit['n_frames']:
                raise ValueError(f'帧数与审计清单不符：{key}')
            times = audit['timestamps_s']
            if times is not None and (len(times) != n or not np.isfinite(times).all() or np.any(np.diff(times) <= 0)):
                raise ValueError(f'时间戳数量或顺序异常：{key}')
    patients = set(assignments)
    if len(patients) != data_config['expected_patients'] or patients != {row['patient_id'] for row in cases}:
        raise ValueError(f'处理后数据患者覆盖与预期不符：期望 {data_config["expected_patients"]} 名患者。')
    if data_config.get('views'):
        for pid in patients:
            actual = [row['view'] for row in cases if row['patient_id'] == pid]
            if sorted(actual) != sorted(data_config['views']):
                raise ValueError(f'{pid} 的切面集合与配置不符。')
    for a, b in (('train', 'val'), ('train', 'test'), ('val', 'test')):
        if patient_groups[a] & patient_groups[b]:
            raise ValueError(f'{a}/{b} 患者重叠。')
    split_counts = {}
    for split in patient_groups:
        split_root, rows = read_split_manifest(project_path(data_config[f'{split}_path']), split)
        if split_root != root.resolve():
            raise ValueError(f'{split} 清单指向了不同的处理后数据目录。')
        ids = {r['case_id'] for r in rows}
        if len(ids) != len(rows) or ids != {k for k, v in case_by_id.items() if assignments[v['patient_id']] == split}:
            raise ValueError(f'{split} 清单与固定患者划分不一致。')
        split_counts[split] = len(ids)
    return {
        'patients': len(patients), 'cases': len(cases),
        'patient_splits': {key: len(value) for key, value in patient_groups.items()},
        'case_splits': split_counts,
        'manifest_sha256': sha256(source_manifest_path),
        'array_contents_checked': check_arrays,
    }

def validate_split_inputs(data_config, required_splits):
    """只核查指定阶段的数据清单和病例，避免训练/测试读取其他子集。"""
    from .manifests import read_split_manifest

    expected = data_config['expected_patients']
    assignments = read_json(project_path(data_config['split_assignments']))['patients']
    if len(assignments) != expected:
        raise ValueError(f'固定划分有 {len(assignments)} 名患者，期望 {expected} 名。')
    roots, patient_sets = set(), {}
    for split in required_splits:
        root, cases = read_split_manifest(project_path(data_config[f'{split}_path']), split)
        roots.add(root)
        patients = set()
        seen = set()
        for row in cases:
            pid, case_id = row.get('patient_id'), row.get('case_id')
            if assignments.get(pid) != split:
                raise ValueError(f'{split} 清单中的患者不属于该集合：{pid}')
            if not isinstance(case_id, str) or not case_id or Path(case_id).name != case_id or case_id in seen:
                raise ValueError(f'{split} 清单有重复或非法病例编号：{case_id}')
            seen.add(case_id)
            patients.add(pid)
            if not (root / (case_id + '.npz')).is_file() or not (root / (case_id + '.json')).is_file():
                raise FileNotFoundError(f'{split} 数据中病例数组或元数据缺失：{case_id}')
            meta = read_json(root / (case_id + '.json'))
            if (meta.get('patient_id'), meta.get('view')) != (pid, row.get('view')):
                raise ValueError(f'{split} 病例清单与元数据不匹配：{case_id}')
            if meta.get('split') is not None and meta['split'] != split:
                raise ValueError(f'{split} 病例元数据标记了其他数据集：{case_id}')
        if not cases or not patients:
            raise ValueError(f'{split} 数据清单为空。')
        patient_sets[split] = patients
    if len(roots) != 1:
        raise ValueError('所需数据子集没有指向同一处理后数据集。')
    for i, a in enumerate(required_splits):
        for b in required_splits[i + 1:]:
            if patient_sets[a] & patient_sets[b]:
                raise ValueError(f'{a}/{b} 数据清单存在患者重叠。')
    root = roots.pop()
    return {
        'dataset_root': str(root),
        'manifest_sha256': sha256(root / 'manifest.json'),
        'patient_splits': {split: len(patients) for split, patients in patient_sets.items()},
        'case_splits': {split: len(read_json(project_path(data_config[f'{split}_path']))['cases'])
                        for split in required_splits},
        'validated_splits': list(required_splits),
    }
