"""读取独立子集清单并验证处理后数据来源。"""
from pathlib import Path
from ..utils.io import read_json
from ..utils.hash import sha256


def read_split_manifest(path, expected_split=None):
    """读取一个数据子集清单，并解析它指向的共享处理后数据目录。"""
    path = Path(path).resolve()
    manifest = read_json(path)
    split = manifest.get('split')
    if split not in ('train', 'val', 'test'):
        raise ValueError(f'数据清单的 split 必须为 train、val 或 test：{path}')
    if expected_split is not None and split != expected_split:
        raise ValueError(f'需要 {expected_split} 清单，实际为 {split}：{path}')
    root_value = manifest.get('dataset_root')
    if not isinstance(root_value, str) or not root_value:
        raise ValueError(f'数据清单缺少 dataset_root：{path}')
    root = (path.parent / root_value).resolve()
    source_manifest = root / 'manifest.json'
    if not source_manifest.is_file():
        raise FileNotFoundError(f'处理后数据集缺少 manifest.json：{source_manifest}')
    expected_hash = manifest.get('dataset_manifest_sha256')
    if expected_hash and sha256(source_manifest) != expected_hash:
        raise ValueError(f'处理后数据集清单与 prepare 阶段不同：{source_manifest}')
    cases = manifest.get('cases')
    if not isinstance(cases, list) or not cases:
        raise ValueError(f'{split} 数据清单没有病例：{path}')
    return root, cases
