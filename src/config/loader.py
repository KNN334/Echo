"""安全读取 YAML；依次合并组件默认配置和本次实验覆盖项。"""
import argparse
from copy import deepcopy
from pathlib import Path

import yaml

from .paths import project_path
from ..utils.hash import sha256

DEFAULTS = {
    'model': {'name': 'deeplabv3_resnet50', 'in_channels': 3, 'num_classes': 1},
    'data': {'adapter': 'camus', 'split_seed': 2026, 'views': ['2CH', '4CH']},
    'train': {'epochs': 30, 'batch_size': 8, 'learning_rate': 0.0001,
              'seed': 2026, 'device': 'auto', 'cpu_threads': 2,
              'early_stopping_patience': None, 'min_delta': 0.0},
    'test': {'device': 'auto', 'cpu_threads': 2, 'temporal': False,
             'quality_gate': False, 'normalization': None,
             'references': None, 'manual_landmarks': None},
}


def deep_merge(base, override):
    """递归合并映射；标量、列表和 null 由后加载的值覆盖。"""
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _load_yaml(path, sources, stack=()):
    path = Path(path).resolve()
    if path in stack:
        raise ValueError(f'YAML defaults 存在循环引用：{path}')
    if not path.is_file():
        raise FileNotFoundError(f'找不到 YAML 配置：{path}')
    document = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(document, dict):
        raise ValueError(f'YAML 顶层必须是映射：{path}')
    sources[str(path)] = sha256(path)
    defaults = document.pop('defaults', [])
    if not isinstance(defaults, list):
        raise ValueError(f'defaults 必须是列表：{path}')
    merged = {}
    for entry in defaults:
        if not isinstance(entry, dict) or len(entry) != 1:
            raise ValueError('defaults 每一项必须是 section: 相对YAML路径。')
        section, relative = next(iter(entry.items()))
        if section not in DEFAULTS or not isinstance(relative, str):
            raise ValueError(f'不支持的组件默认配置：{entry}')
        component = _load_yaml(path.parent / relative, sources, (*stack, path))
        merged[section] = deep_merge(merged.get(section, {}), component)
    return deep_merge(merged, document)


def load_config(path='configs/experiment.yaml'):
    """返回合并后的配置，并记录所有组件文件摘要用于实验溯源。"""
    sources = {}
    config = deep_merge(DEFAULTS, _load_yaml(project_path(path), sources))
    for section in DEFAULTS:
        if not isinstance(config.get(section), dict):
            raise ValueError(f'{section} 必须是 YAML 映射。')
    required = {
        'data': ('dataset', 'split_assignments', 'train_path', 'val_path', 'test_path', 'expected_patients'),
        'train': ('output', 'initial_weights'), 'test': ('weights', 'output'),
    }
    for section, fields in required.items():
        for field in fields:
            if field not in config[section] or (config[section][field] is None and field != 'initial_weights'):
                raise ValueError(f'配置缺少 {section}.{field}')
    count = config['data']['expected_patients']
    if not isinstance(count, int) or isinstance(count, bool) or count < 3:
        raise ValueError('data.expected_patients 必须是至少为 3 的患者总数。')
    config['_config_sources'] = sources
    return config


def load_experiment(description, argv=None):
    """三个脚本共用的 --config 参数；无参数时直接运行默认 YAML。"""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--config', default='configs/experiment.yaml', help='实验 YAML 配置路径')
    args = parser.parse_args(argv)
    path = project_path(args.config).resolve()
    config = load_config(path)
    print(f'实验配置：{path}', flush=True)
    return config, path
