"""数据准备入口：读取本地处理后数据集，核查并生成固定患者划分清单。"""
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime

from src.config.loader import load_experiment
from src.config.paths import project_path
from src.data.prepare import prepare_split_manifests, validate_prepared
from src.utils.run import record_stage


def main(argv=None):
    """只读取 data.dataset 指定的处理后数据，不下载原始数据或执行影像预处理。"""
    config, config_path = load_experiment('处理后数据读取与患者级划分', argv)
    data = config['data']
    print('阶段 1：读取处理后数据并划分训练/验证/测试集', flush=True)
    summary = prepare_split_manifests(data)
    summary = validate_prepared(data, check_arrays=True)
    audit = project_path('runs/data_preparation') / (datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
    record_stage(audit, 'prepare', config, config_path, prepared=summary)
    print(f'处理后数据：{project_path(data["dataset"])}', flush=True)
    print(f'患者划分：{summary["patient_splits"]}；病例划分：{summary["case_splits"]}', flush=True)
    print(f'训练清单：{project_path(data["train_path"])}', flush=True)
    print(f'验证清单：{project_path(data["val_path"])}', flush=True)
    print(f'测试清单：{project_path(data["test_path"])}', flush=True)
    print(f'本次核查审计：{audit}', flush=True)
    print('下一步：运行scripts/train.py。', flush=True)
    return summary


def cli():
    """控制台入口：只核查处理后数据并生成固定划分。"""
    main()


if __name__ == '__main__':
    cli()
