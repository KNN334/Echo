"""三个独立实验入口的公共配置、数据完整性检查和运行来源工具。"""
import argparse
from datetime import datetime
import os
from pathlib import Path

import numpy as np

from .common import read_json, write_json, sha256, provenance
from .transforms import Transform


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_path(value):
    """将配置中的相对路径统一解析到项目根目录；null 保持为空。"""
    if value is None:
        return None
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_experiment(description, argv=None):
    """读取共享配置；在 PyCharm 无参数运行时使用 experiment.json。"""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--config', default='configs/experiment.json', help='实验配置 JSON 路径')
    args = parser.parse_args(argv)
    # 固定工作目录，避免相对文件路径随 PyCharm 默认设置变化。
    os.chdir(PROJECT_ROOT)
    path = project_path(args.config)
    config = read_json(path)
    for section in ('data', 'train', 'test'):
        if not isinstance(config.get(section), dict):
            raise ValueError(f'配置缺少 {section} 字段，或该字段不是对象：{path}')
    count = config['data'].get('expected_patients')
    if not isinstance(count, int) or isinstance(count, bool) or count < 3:
        raise ValueError('data.expected_patients 必须是至少为 3 的患者总数。')
    print(f'实验配置：{path}', flush=True)
    return config, path


def select_device(requested='auto', cpu_threads=2):
    """按配置选择计算设备；明确要求 CUDA 时不可静默改用 CPU。"""
    import torch
    if requested not in ('auto', 'cpu', 'cuda'):
        raise ValueError('device 只支持 auto、cpu、cuda。')
    if requested == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('当前解释器的 CUDA 不可用，请先修复环境，或将 device 设为 cpu。')
    device = 'cuda' if requested == 'auto' and torch.cuda.is_available() else requested
    if device == 'auto':
        device = 'cpu'
    if device == 'cpu':
        if not isinstance(cpu_threads, int) or isinstance(cpu_threads, bool) or cpu_threads < 1:
            raise ValueError('cpu_threads 必须是正整数。')
        torch.set_num_threads(cpu_threads)
    print(f'计算设备：{device}', flush=True)
    return device


def require_new_output(path):
    """拒绝复用已有产物目录，防止覆盖旧模型或混合两次测试结果。"""
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise FileExistsError(f'输出目录已有内容：{path}。请在配置中使用新的输出目录。')


def record_stage(output, stage, config, config_path, **details):
    """保存本阶段配置快照和代码、配置文件的来源。"""
    write_json(output, {
        **provenance(), 'stage': stage,
        'created_local': datetime.now().astimezone().isoformat(),
        'config_path': str(config_path), 'config_sha256': sha256(config_path),
        'config': config, **details,
    })


def validate_prepared(data_config, check_arrays=False):
    """核查病例完整性、患者互斥及处理参数；可完整读取数组以检查缓存。"""
    root = project_path(data_config['processed'])
    split_file = project_path(data_config['splits'])
    settings = read_json(project_path(data_config['preprocessing'])) if data_config.get('preprocessing') else None
    splits = read_json(split_file)['patients']
    manifest = read_json(root / 'manifest.json')
    if manifest.get('failures'):
        raise ValueError('预处理清单含失败病例，请先修复数据准备。')
    cases = manifest.get('cases', [])
    if not cases:
        raise ValueError('预处理清单没有病例，请先运行 prepare.py。')
    patient_groups = {'train': set(), 'val': set(), 'test': set()}
    seen = set()
    for row in cases:
        pid, view, split = row['patient_id'], row['view'], row['split']
        key = row['case_id']
        if not isinstance(key, str) or not key or Path(key).name != key or '/' in key or '\\' in key or key in seen:
            raise ValueError(f'重复或非法病例编号：{key}')
        if split not in patient_groups or splits.get(pid) != split:
            raise ValueError(f'病例划分与固定患者清单不符：{key}')
        seen.add(key)
        patient_groups[split].add(pid)
        array_path = root / (key + '.npz')
        if not array_path.is_file():
            raise FileNotFoundError(f'缺少处理后数组：{array_path}')
        meta = read_json(root / (key + '.json'))
        if (meta.get('patient_id'), meta.get('view'), meta.get('split')) != (pid, view, split):
            raise ValueError(f'病例元数据与清单不符：{key}')
        if settings is not None:
            desired = settings.get('overrides', {}).get(key, settings.get('default', settings))
            if meta.get('preprocess_config') != desired:
                raise ValueError(f'缓存的预处理参数与当前配置不同：{key}，请使用新的数据输出目录重新预处理。')
        tr = meta['audit']['transform']
        transform = Transform(tuple(tr['original_hw']), tuple(tr['crop_xyxy']), tuple(tr['output_hw']))
        if not np.allclose(transform.matrix, tr['original_to_processed']) or not np.allclose(
                np.linalg.inv(transform.matrix), tr['processed_to_original']):
            raise ValueError(f'正反坐标变换记录不一致：{key}')
        if check_arrays:
            # 完整读取 NPZ：检查压缩数据能否解码、原始专家标签和帧索引是否仍在。
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
            if n != row['frames'] or int(labeled.sum()) != row['labeled_frames'] or n != meta['audit']['n_frames']:
                raise ValueError(f'帧数与审计清单不符：{key}')
            times = meta['audit']['timestamps_s']
            if times is not None and (len(times) != n or not np.isfinite(times).all() or np.any(np.diff(times) <= 0)):
                raise ValueError(f'时间戳数量或顺序异常：{key}')
    patients = set.union(*patient_groups.values())
    if len(patients) != data_config['expected_patients']:
        raise ValueError(f'预处理覆盖 {len(patients)} 名患者、{len(cases)} 个切面，'
                         f'期望 {data_config["expected_patients"]} 名患者。')
    if data_config.get('views'):
        for pid in patients:
            actual = [row['view'] for row in cases if row['patient_id'] == pid]
            if sorted(actual) != sorted(data_config['views']):
                raise ValueError(f'{pid} 的切面集合与配置不符。')
    if len(patients) == len(splits) and patients != set(splits):
        raise ValueError('患者集合与固定划分清单不同。')
    if any(not group for group in patient_groups.values()):
        raise ValueError('训练、验证和测试划分必须均非空。')
    for a, b in (('train', 'val'), ('train', 'test'), ('val', 'test')):
        if patient_groups[a] & patient_groups[b]:
            raise ValueError(f'{a}/{b} 患者重叠。')
    return {
        'patients': len(patients), 'cases': len(cases),
        'patient_splits': {key: len(value) for key, value in patient_groups.items()},
        'manifest_sha256': sha256(root / 'manifest.json'),
        'array_contents_checked': check_arrays,
    }
