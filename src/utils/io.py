"""JSON/CSV/NPZ 文件读写，不依赖训练框架。"""
from pathlib import Path
import csv
import json
import numpy as np


def write_json(path, obj):
    """以 UTF-8 写入可读 JSON，并转换 NumPy 标量和数组。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False,
                               default=lambda x: x.tolist() if isinstance(x, np.ndarray) else x.item()), encoding="utf-8")

def read_json(path):
    """读取 UTF-8 编码的 JSON 文件。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write_csv(path, rows):
    """按行字典的字段并集写入 CSV，兼容中文表格软件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def read_npz(path):
    """关闭文件句柄后返回数组字典，禁止不可信 pickle 对象。"""
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def write_npz(path, **arrays):
    """保存压缩数组；大型病例放在被 Git 忽略的数据目录。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)
