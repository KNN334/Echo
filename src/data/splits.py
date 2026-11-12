"""固定患者级划分，仅供数据准备阶段使用。"""
import hashlib
from ..utils.io import write_json


def make_splits(patients, output, seed=2026):
    """按患者 ID 和种子哈希固定划分，不受文件顺序或下载完整度影响。"""
    splits = {}
    for pid in sorted(set(patients)):
        value = int(hashlib.sha256(f"{seed}:{pid}".encode()).hexdigest()[:8], 16) / 2**32
        splits[pid] = "train" if value < .7 else "val" if value < .85 else "test"
    write_json(output, {"protocol": "patient_sha256_70_15_15_custom_not_official", "seed": seed, "patients": splits})
    return splits
