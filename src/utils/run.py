"""输出目录保护和阶段配置/代码溯源。"""
from datetime import datetime
from .io import write_json
from .hash import provenance, sha256


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
