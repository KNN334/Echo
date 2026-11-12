"""训练入口：读取处理后数据，训练 EchoNet 分割模型，按验证损失保存权重。"""
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.io import write_json
from src.config.loader import load_experiment
from src.config.paths import project_path
from src.data.prepare import validate_split_inputs
from src.utils.device import select_device
from src.utils.run import require_new_output, record_stage


def main(argv=None):
    """独立训练和验证；不执行预处理，不计算最终测试指标。"""
    config, path = load_experiment('处理后数据集分割模型训练', argv)
    data, options = config['data'], config['train']
    print('阶段 2：模型训练与验证', flush=True)
    summary = validate_split_inputs(data, ('train', 'val'))
    epochs, batch, lr = options['epochs'], options['batch_size'], options['learning_rate']
    if not isinstance(epochs, int) or isinstance(epochs, bool) or epochs < 1:
        raise ValueError('epochs 必须为正整数。')
    if not isinstance(batch, int) or isinstance(batch, bool) or batch < 1:
        raise ValueError('batch_size 必须为正整数。')
    if not isinstance(lr, (int, float)) or not 0 < lr < float('inf'):
        raise ValueError('learning_rate 必须为有限正数。')
    initial = project_path(options['initial_weights'])
    if initial is not None and not initial.is_file():
        raise FileNotFoundError(f'缺少初始化权重：{initial}。请先运行 scripts/download_weights.py。')
    output = project_path(options['output'])
    require_new_output(output)
    device = select_device(options['device'], options['cpu_threads'])
    print(f'患者划分：{summary["patient_splits"]}，训练 {epochs} 轮，批大小 {batch}。', flush=True)
    print('仅训练集参与参数更新和归一化；验证集选择模型；测试集不参与调参。', flush=True)
    record_stage(output / 'experiment.json', 'train', config, path, prepared=summary)
    from src.engine.trainer import train
    history = train(project_path(data['train_path']), project_path(data['val_path']), output,
                    epochs=epochs, batch=batch,
                    lr=lr, seed=options['seed'], weights=initial, device=device,
                    model_config=config['model'], adapter=data['adapter'],
                    early_stopping_patience=options['early_stopping_patience'],
                    min_delta=options['min_delta'])
    write_json(output / 'completed.json', {'epochs_completed': len(history), 'best_weights': str(output / 'best.pt')})
    print(f'训练结束。最佳模型：{output / "best.pt"}\n损失记录：{output / "training.csv"}', flush=True)
    print('下一步：运行scripts/evaluate.py。', flush=True)
    return history


def cli():
    """控制台入口不返回结果对象，避免其被当作错误退出码。"""
    main()


if __name__ == '__main__':
    cli()
