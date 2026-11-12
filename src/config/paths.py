"""所有配置路径相对于项目根目录，与 PyCharm 工作目录无关。"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def project_path(value):
    """相对路径定位到项目根目录；可选文件的 null 保留为 None。"""
    if value is None:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path
