"""测试入口：加载已训练模型，在固定测试集上计算指标并生成图像、表格和报告。"""
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.io import read_json
from src.config.loader import load_experiment
from src.config.paths import project_path
from src.data.prepare import validate_split_inputs
from src.utils.device import select_device
from src.utils.run import require_new_output, record_stage


def main(argv=None):
    """独立完成最终测试和结果导出；不会训练模型或自动选择最佳权重。"""
    config, path = load_experiment('固定测试集评估及结果生成', argv)
    data, options = config['data'], config['test']
    print('阶段 3：固定测试集评估与报告生成', flush=True)
    prepared = validate_split_inputs(data, ('test',))
    weights = project_path(options['weights'])
    if not weights.is_file():
        raise FileNotFoundError(f'没有找到训练权重：{weights}。请先运行 scripts/train.py，并核对 test.weights。')
    # 本项目训练权重旁的运行清单应对应同一预处理数据，避免误测另一轮实验。
    run_path = weights.parent / 'run.json'
    if run_path.is_file():
        run = read_json(run_path)
        if run.get('input_manifest_sha256') != prepared['manifest_sha256']:
            raise ValueError('测试数据清单与训练时不同，请核对数据和模型来源。')
    output = project_path(options['output'])
    require_new_output(output)
    for key in ('normalization', 'references', 'manual_landmarks'):
        file = project_path(options[key])
        if file is not None and not file.is_file():
            raise FileNotFoundError(f'{key} 文件不存在：{file}')
    device = select_device(options['device'], options['cpu_threads'])
    record_stage(output / 'experiment.json', 'test', config, path, prepared=prepared)
    from src.engine.evaluator import evaluate
    summary = evaluate(
        project_path(data['test_path']), weights, output, device=device,
        normalization=project_path(options['normalization']), temporal=options['temporal'],
        gate=options['quality_gate'], references=project_path(options['references']),
        manual_landmarks=project_path(options['manual_landmarks']),
        model_config=config['model'], adapter=data['adapter'],
    )
    if summary['cases_failed'] or not summary['cases_attempted']:
        raise RuntimeError(f'测试存在失败病例或无测试数据，请查看 {output / "summary.json"}。')
    print(f'测试完成：{summary["patients"]} 名患者，{summary["cases_attempted"]} 个切面。', flush=True)
    print(f'Dice：{summary["dice_patient_mean"]}；HD95：{summary["hd95_mm"]} mm。', flush=True)
    print(f'图像和报告：{output / "report.html"}', flush=True)
    print(f'心功能参数：{output / "function.csv"}\n逐帧特征：{output / "frames.csv"}', flush=True)
    print(f'结构误差：{output / "structure.csv"}\nMAE 汇总：{output / "summary.json"}', flush=True)
    print('缺少可靠心率/独立 CO 或人工关键点参考时，对应值保持为空。', flush=True)
    return summary


def cli():
    """控制台入口：成功时正常退出，失败时保留明确异常。"""
    main()


if __name__ == '__main__':
    cli()
