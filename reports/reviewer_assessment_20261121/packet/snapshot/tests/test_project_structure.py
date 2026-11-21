"""项目说明必须与实际源码树对应，保留文档中的本地链接必须可用。"""
from pathlib import Path
import re

from src.config.paths import PROJECT_ROOT
from src.utils.project_structure import update_readme


def test_readme_structure_matches_actual_project():
    """新增、移动、删除源码或文档后，未同步 README 应明确失败。"""
    assert update_readme(check=True)


def test_project_document_links_exist():
    """检查维护中的说明文档，避免清理后保留失效相对链接。"""
    paths = [PROJECT_ROOT / 'README.md', *sorted((PROJECT_ROOT / 'docs').glob('*.md'))]
    for document in paths:
        content = document.read_text(encoding='utf-8')
        for target in re.findall(r'\]\(([^)]+)\)', content):
            if '://' in target or target.startswith('#'):
                continue
            relative = target.split('#', 1)[0]
            assert (document.parent / relative).exists(), f'{document.relative_to(PROJECT_ROOT)}: {target}'
