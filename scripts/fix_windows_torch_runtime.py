"""修复 Anaconda 虚拟环境的旧 C++ 运行库与 CUDA PyTorch 的加载冲突。"""
import os
from pathlib import Path
import sys


HOOK = '''"""Use the current Windows C++ runtime before loading CUDA PyTorch.

The Anaconda Python 3.12 base contains older runtime DLLs. Loading the
system copies first prevents c10.dll initialization error 1114 in this venv.
This hook is local to this virtual environment and does not modify Anaconda.
"""
import os

if os.name == 'nt':
    import ctypes
    from pathlib import Path

    _cuda_system_directory = Path(os.environ.get('SystemRoot', r'C:\\Windows')) / 'System32'
    _cuda_runtime_handles = [
        ctypes.WinDLL(str(_cuda_system_directory / name))
        for name in ('vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll')
    ]
'''


def main():
    """只修改当前虚拟环境；保留其他工具创建的启动配置与系统运行库。"""
    if os.name != 'nt' or sys.prefix == sys.base_prefix:
        raise RuntimeError('请用 Windows 项目的 .venv/Scripts/python.exe 运行本文件。')
    system = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32'
    for name in ('vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll'):
        if not (system / name).is_file():
            raise FileNotFoundError('缺少系统 C++ 运行库；请先安装 Microsoft Visual C++ x64 Redistributable。')
    target = Path(sys.prefix) / 'Lib' / 'site-packages' / 'sitecustomize.py'
    if target.exists() and target.read_text(encoding='utf-8').strip() != HOOK.strip():
        raise FileExistsError(f'已有其他启动配置，请保留并人工合并：{target}')
    target.write_text(HOOK, encoding='utf-8')
    print(f'已配置本虚拟环境优先加载系统 C++ 运行库：{target}')
    print('请关闭已打开的 Python 控制台，并在新进程中核查 torch.cuda.is_available()。')


if __name__ == '__main__':
    main()
