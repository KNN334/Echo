"""绘制单次已完成 CAMUS 实验的论文结果图；可直接在 PyCharm 中运行。"""
from pathlib import Path
import argparse
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.paths import project_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', default='runs/camus_cuda_progress', help='同一轮评估输出目录')
    parser.add_argument('--training', default='checkpoints/camus_cuda_progress', help='匹配的训练目录，包含 best.pt/run.json/training.csv')
    parser.add_argument('--prepared', default='data/processed/camus', help='匹配的处理后缓存；--no-images 可只画定量图')
    parser.add_argument('--output', default='reports/result_analysis/camus_cuda_progress')
    parser.add_argument('--no-images', action='store_true', help='没有病例缓存时跳过叠图和半周期示例')
    options = parser.parse_args(argv)
    from src.visualization.analysis import build_analysis
    result = build_analysis(project_path(options.results), project_path(options.training),
                            None if options.no_images else project_path(options.prepared),
                            project_path(options.output))
    print(f'完成 {result["figures"]} 张结果分析图，测试患者 {result["patients"]} 位。')
    print(f'图集：{Path(result["output"]) / "index.html"}')
    return result


def cli():
    main()


if __name__ == '__main__':
    cli()
