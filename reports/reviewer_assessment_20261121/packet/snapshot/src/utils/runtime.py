"""项目 Python 环境核查与可追溯运行时信息。"""
from importlib import metadata
from pathlib import Path
import platform
import sys

from ..config.paths import PROJECT_ROOT


PACKAGE_DISTRIBUTIONS = {
    'numpy': 'numpy',
    'scipy': 'scipy',
    'Pillow': 'Pillow',
    'PyYAML': 'PyYAML',
    'torch': 'torch',
    'torchvision': 'torchvision',
    'tqdm': 'tqdm',
    'SimpleITK': 'SimpleITK',
    'opencv-python-headless': 'opencv-python-headless',
    'matplotlib': 'matplotlib',
}


def project_venv_path():
    """Return the venv configured for this project."""
    return PROJECT_ROOT / '.venv'


def project_venv_python():
    """Return the platform-specific project venv interpreter path."""
    venv = project_venv_path()
    return venv / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')


def runtime_metadata(include_cuda=False):
    """Capture versions and project-relative interpreter identity without local paths."""
    executable = Path(sys.executable).resolve()
    try:
        executable_label = executable.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        executable_label = executable.name
    prefix = Path(sys.prefix).resolve()
    is_virtual_environment = prefix != Path(sys.base_prefix).resolve()
    in_project_venv = prefix == project_venv_path().resolve()
    packages = {}
    for name, distribution in PACKAGE_DISTRIBUTIONS.items():
        try:
            packages[name] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            packages[name] = None

    result = {
        'python': {
            'version': platform.python_version(),
            'implementation': platform.python_implementation(),
            'executable': executable_label,
            'is_virtual_environment': is_virtual_environment,
            'is_project_venv': in_project_venv,
        },
        'packages': packages,
    }
    if include_cuda:
        if packages['torch'] is None:
            result['accelerator'] = {'cuda_available': False, 'reason': 'torch_not_installed'}
        else:
            import torch

            result['accelerator'] = {
                'torch_cuda_version': torch.version.cuda,
                'cuda_available': torch.cuda.is_available(),
                'device_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            }
    return result


def require_project_venv():
    """Raise unless the current process uses this project's .venv interpreter."""
    expected_prefix = project_venv_path().resolve()
    expected_python = project_venv_python().resolve()
    actual_prefix = Path(sys.prefix).resolve()
    actual_python = Path(sys.executable).resolve()
    if actual_prefix != expected_prefix or actual_python != expected_python:
        raise RuntimeError(
            'PyCharm/project run must use the project virtual environment. '
            f'Expected {expected_python}; received {actual_python}.'
        )
