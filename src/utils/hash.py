"""输入文件校验和 Git 运行来源。"""
import hashlib
import subprocess
from ..config.paths import PROJECT_ROOT


def sha256(path):
    """计算文件的 SHA-256，用于输入与产物完整性记录。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def provenance():
    """记录当前 Git 提交和工作区是否存在未提交改动。"""
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, True
    return {"git_commit": commit, "working_tree_dirty": dirty}
