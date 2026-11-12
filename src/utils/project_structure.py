"""从实际源码目录生成 README 结构；忽略环境缓存及运行产物的内容。"""
import argparse
from pathlib import Path

from ..config.paths import PROJECT_ROOT

START = '<!-- PROJECT_STRUCTURE:START -->'
END = '<!-- PROJECT_STRUCTURE:END -->'
RUNTIME_DIRECTORIES = {
    'data': '本地数据，Git 忽略；内部文件由数据集决定',
    'checkpoints': '本地模型权重，Git 忽略',
    'runs': '本地实验结果，Git 忽略',
}
ENVIRONMENT_DIRECTORIES = {
    '.git', '.venv', '.idea', '.work', '.pytest_cache', '.pytest_work',
    'build', 'dist',
}
PRIVATE_PROJECT_FILES = {'AGENTS.md'}


def _visible(path, root):
    """仅排除明确的本机环境和可再生缓存，其余源码/文档必须列出。"""
    if path.name == '__pycache__' or path.suffix in ('.pyc', '.pyo'):
        return False
    if path.parent == root:
        return (
            path.name not in ENVIRONMENT_DIRECTORIES
            and path.name not in PRIVATE_PROJECT_FILES
            and not path.name.endswith('.egg-info')
        )
    return True


def render_tree(root=PROJECT_ROOT):
    """完整列出实际源码/配置/测试/文档，运行目录只显示顶层占位。"""
    root = Path(root).resolve()
    lines = ['Echo/']

    def visit(directory, prefix=''):
        entries = {p.name: p for p in directory.iterdir() if _visible(p, root)}
        if directory == root:
            # Git 新检出时运行目录可能不存在，说明中仍展示其约定位置。
            entries.update({name: root / name for name in RUNTIME_DIRECTORIES})
        ordered = sorted(entries.values(), key=lambda p: (
            not (p.is_dir() or (directory == root and p.name in RUNTIME_DIRECTORIES)),
            p.name.casefold(),
        ))
        for index, path in enumerate(ordered):
            last = index == len(ordered) - 1
            runtime = directory == root and path.name in RUNTIME_DIRECTORIES
            is_directory = runtime or path.is_dir()
            label = path.name + ('/' if is_directory else '')
            if runtime:
                label += '  # ' + RUNTIME_DIRECTORIES[path.name]
            lines.append(prefix + ('└── ' if last else '├── ') + label)
            if is_directory and not runtime:
                visit(path, prefix + ('    ' if last else '│   '))

    visit(root)
    return '\n'.join(lines)


def structure_block(root=PROJECT_ROOT):
    return START + '\n```text\n' + render_tree(root) + '\n```\n' + END


def update_readme(root=PROJECT_ROOT, check=False):
    """只更新受标记的结构块；check 模式发现差异时报错，不改文件。"""
    root = Path(root).resolve()
    path = root / 'README.md'
    content = path.read_text(encoding='utf-8')
    if content.count(START) != 1 or content.count(END) != 1:
        raise ValueError('README 必须包含唯一的目录结构起止标记。')
    start = content.index(START)
    end = content.index(END, start) + len(END)
    expected = structure_block(root)
    matches = content[start:end] == expected
    if check and not matches:
        raise ValueError('README 目录与实际文件不一致，请运行 python -m src.utils.project_structure --write')
    if not check and not matches:
        path.write_text(content[:start] + expected + content[end:], encoding='utf-8', newline='\n')
    return matches


def main(argv=None):
    parser = argparse.ArgumentParser(description='生成或核查 README 的实际项目目录')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true', help='根据实际文件更新 README 目录')
    mode.add_argument('--check', action='store_true', help='只检查一致性')
    options = parser.parse_args(argv)
    update_readme(check=options.check)
    print('README directory matches project files.' if options.check else 'README directory updated.')


if __name__ == '__main__':
    main()
