"""Project interpreter identity and PyCharm environment guard."""
import sys
import importlib

import pytest

from src.utils import runtime


def test_runtime_metadata_reports_versions_without_machine_paths():
    details = runtime.runtime_metadata()

    assert details['python']['version'] == sys.version.split()[0]
    assert details['python']['is_virtual_environment'] == (sys.prefix != sys.base_prefix)
    assert '\\Users\\' not in details['python']['executable']
    assert 'torch' in details['packages']


def test_project_venv_guard_checks_interpreter_and_prefix(tmp_path, monkeypatch):
    expected = tmp_path / '.venv'
    monkeypatch.setattr(runtime, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(sys, 'prefix', str(expected))
    monkeypatch.setattr(sys, 'executable', str(runtime.project_venv_python()))

    runtime.require_project_venv()

    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'python.exe'))
    with pytest.raises(RuntimeError, match='project virtual environment'):
        runtime.require_project_venv()


@pytest.mark.parametrize('entrypoint', ['prepare_data', 'train', 'evaluate', 'plot_results'])
def test_experiment_entrypoints_reject_other_interpreters_without_opt_in(tmp_path, monkeypatch, entrypoint):
    monkeypatch.setattr(runtime, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(sys, 'prefix', str(tmp_path / '.venv'))
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'python.exe'))
    with pytest.raises(RuntimeError, match='project virtual environment'):
        importlib.import_module('scripts.' + entrypoint).main([])
