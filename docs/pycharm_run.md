# PyCharm 三阶段运行指南

项目日常使用三个互相独立的入口。数据只从本地处理后数据集读取，不会下载公开数据或从原始影像重新预处理。

## 首次准备

1. 在 PyCharm 打开项目根目录，确认解释器为项目 `.venv/Scripts/python.exe`。
2. 将已处理的数据包解压到 `data/processed/camus/`。目录中应有 `manifest.json`、每个病例的 `.npz` 数组和 `.json` 元数据。
3. 打开 `configs/experiment.yaml`。它会合并 `configs/model/`、`configs/data/` 和 `configs/train/` 中列出的 YAML 文件。到 `configs/data/camus.yaml` 确认 `dataset` 指向数据目录，期望患者数为 500。
4. 运行 `scripts/prepare_data.py`。它核查数据完整性、原始标签、坐标变换和时间记录，然后按固定患者清单写出三个子集清单。

如果没有初始化权重，可以在训练配置中将 `initial_weights` 设为 `null` 从头训练；已有 EchoNet 权重时将其放在 `checkpoints/` 并填写路径。此训练权重不属于数据下载流程。

## 完整运行

1. 展开 `scripts` 文件夹，右键 `prepare_data.py`，选择“运行”。确认训练、验证、测试清单已生成。
2. 右键同目录的 `train.py`，选择“运行”。它只读 `train.json` 与 `val.json`，用验证损失选模。控制台显示带时间戳的进度、速度、耗时及剩余时间。
3. 右键同目录的 `evaluate.py`，选择“运行”。它只读 `test.json` 和训练好的 `best.pt`，导出最终结果。

也可以从右上角运行配置依次选择“01 数据读取与固定患者划分”“02 训练模型”“03 测试与生成结果”。已更新的配置指向 `scripts/`。如果 PyCharm 仍显示旧配置，进入“运行 → 编辑配置”，将脚本路径改成上述新路径。

PyCharm 自动创建的运行配置需将工作目录设为项目根目录，解释器使用项目虚拟环境。也可以直接在 PyCharm 终端依次运行：

```powershell
.\.venv\Scripts\python.exe scripts/prepare_data.py
.\.venv\Scripts\python.exe scripts/train.py
.\.venv\Scripts\python.exe scripts/evaluate.py
```

## 配置说明

主配置为 `configs/experiment.yaml`，组件默认值在 `defaults` 指定的 YAML 文件里，主配置的同名字段优先。支持 `#` 注释。需要更换整套实验时，复制主配置，再通过 PyCharm 的“脚本参数”填写 `--config configs/你的实验.yaml`。

| 字段 | 作用 |
|---|---|
| `data.dataset` | 已处理数据根目录，默认 `data/processed/camus` |
| `data.split_assignments` | 固定的患者级划分；同一患者不会跨集合 |
| `data.train_path` | prepare 生成的训练病例清单 |
| `data.val_path` | prepare 生成的验证病例清单 |
| `data.test_path` | prepare 生成的测试病例清单 |
| `data.expected_patients` | 数据完整性预期患者数 |
| `train.*` | 训练轮数、批大小、学习率、设备、初始化权重和输出目录 |
| `test.*` | 最终测试权重、设备、参考数据和结果目录 |
| `model.*` | 模型工厂使用的网络名称、输入通道与前景通道 |

数据路径在 `configs/data/camus.yaml`，训练轮数/批大小在 `configs/train/baseline.yaml`。如果将训练输出改为 `checkpoints/experiment_02`，同时将测试权重改为 `checkpoints/experiment_02/best.pt`，测试输出改为 `runs/experiment_02`。目录中已有内容时请使用新名称；程序不会覆盖旧实验。

prepare 写出的清单只包含病例路径索引和溯源信息，不会复制数据数组。三个阶段分工如下：

```text
data/processed/camus/
        │
        ▼
scripts/prepare_data.py ──按患者固定划分──> train.json / val.json / test.json
                                  │              │              │
                                  ▼              ▼              ▼
                               train.py      train.py       evaluate.py
                               读取训练集     读取验证集       只读取测试集
                                  └──── best.pt ───┘
```

## 输出与安全规则

- `scripts/prepare_data.py` 输出 `data/processed/camus/splits/{train,val,test}.json` 及本次数据审计记录。
- `scripts/train.py` 输出 `best.pt`、`run.json`、`training.csv`、`training.log` 和完整合并配置快照。归一化仅来自训练集；验证集用于选模及可选早停。
- `scripts/evaluate.py` 输出分割掩膜、逐帧特征、Dice、边界距离、关键点误差、功能参数及 MAE 汇总和 `report.html`。运行结束后可在浏览器打开该 HTML。
- 新训练或测试结果必须使用新的输出目录。程序会拒绝覆盖已经存在内容的目录。
- 绝对容积需要空间标定。没有可靠完整周期或来源明确的心率时，CO 保持空值；没有人工关键点标签时，人工关键点误差保持空值。
- 工程测试通过不等于临床有效性验证。当前正式基线与测量口径见 `reports/full_baseline/RESULTS.md` 和 `docs/measurement_protocol.md`。

## 模块位置

- `src/config/`：YAML 配置合并与项目路径。
- `src/data/`：通用适配器、病例清单、固定划分、坐标与元数据核查。
- `src/data/camus/`：CAMUS 专用 Dataset 及可选独立下载/原始数组处理。
- `src/models/`：模型工厂、DeepLabV3 和分割损失。
- `src/engine/`：训练、验证、测试循环和进度/选模/早停回调。
- `src/geometry/`、`src/metrics/`、`src/temporal/`：几何特征、评价指标及时序分析。
- `src/visualization/`：叠图、容积曲线和 HTML 报告。
- `src/utils/`：读写、SHA256、设备和随机种子。
- `tests/`：项目工程回归检查，运行 `python -m pytest -q`。
- `vendor/echonet/`：带来源与许可信息的 EchoNet 上游代码。
