"""公共工具：JSON/CSV 读写、SHA-256 校验与 Git 运行来源记录。"""
from pathlib import Path
import csv
import hashlib
import json
import subprocess
import numpy as np


def sha256(path):
    """计算文件的 SHA-256，用于输入与产物完整性记录。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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


def provenance():
    """记录当前 Git 提交和工作区是否存在未提交改动。"""
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, True
    return {"git_commit": commit, "working_tree_dirty": dirty}
