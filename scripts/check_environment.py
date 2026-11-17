"""核查 PyCharm 项目虚拟环境、训练依赖版本与 CUDA 状态。"""
from pathlib import Path
import json
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.runtime import require_project_venv, runtime_metadata


def main():
    require_project_venv()
    result = runtime_metadata(include_cuda=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result['accelerator']['cuda_available']:
        print('CUDA 当前不可用；如需 GPU 训练，请检查本虚拟环境的 PyTorch/CUDA 安装。')
    return result


if __name__ == '__main__':
    main()
