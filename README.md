# Echo

基于处理后超声心动图数据的左心室分割与心功能分析基线。模型采用 EchoNet 的 DeepLabV3-ResNet50 分割架构；CAMUS 处理后数据作为当前示例数据集。

## 三步运行

在 PyCharm 中依次右键运行 `scripts/` 下的三个 Python 文件：

1. `scripts/prepare_data.py`：读取本地处理后数据，检查原始标注和坐标审计，按患者级固定划分生成训练、验证、测试清单。
2. `scripts/train.py`：只读取训练与验证清单，计算训练集归一化参数，按验证损失选择模型。
3. `scripts/evaluate.py`：只读取测试清单，对已训练模型进行最终评价并导出结果。

详细步骤见 [PyCharm 三阶段运行指南](docs/pycharm_run.md)。默认配置是支持注释的 `configs/experiment.yaml`，按 `defaults` 合并模型、数据和训练组件。本次实验的配置可覆盖组件默认值；路径始终相对于项目根目录。

## 项目结构

以下目录树由实际项目文件生成，完整列出会提交的代码、配置、测试和说明文件。`data/`、`checkpoints/`、`runs/` 是内容随实验变化的本地运行目录，只列顶层；Git 历史、虚拟环境、PyCharm 本机设置、`AGENTS.md`、临时检查文件、Python 缓存及打包缓存不属于公开项目目录。

<!-- PROJECT_STRUCTURE:START -->
```text
Echo/
├── .github/
│   └── workflows/
│       └── tests.yml
├── .run/
│   ├── Prepare.run.xml
│   ├── Test.run.xml
│   └── Train.run.xml
├── checkpoints/  # 本地模型权重，Git 忽略
├── configs/
│   ├── data/
│   │   └── camus.yaml
│   ├── model/
│   │   └── deeplabv3_resnet50.yaml
│   ├── train/
│   │   └── baseline.yaml
│   ├── camus_splits.json
│   └── experiment.yaml
├── data/  # 本地数据，Git 忽略；内部文件由数据集决定
├── docs/
│   ├── data_sources/
│   │   ├── camus_download_manifest.json
│   │   ├── CAMUS_LICENSE_TERMS.md
│   │   ├── echonet_weights.json
│   │   ├── official_patient_index.json
│   │   └── prepared_provenance.json
│   ├── code_walkthrough.md
│   ├── measurement_protocol.md
│   └── pycharm_run.md
├── reports/
│   ├── full_baseline/
│   │   ├── patient_features.csv
│   │   ├── RESULTS.md
│   │   ├── summary.json
│   │   ├── training_history.csv
│   │   └── training_run.json
│   ├── input_equivalence.json
│   ├── release_artifacts.json
│   └── source_integrity.json
├── runs/  # 本地实验结果，Git 忽略
├── scripts/
│   ├── __init__.py
│   ├── download_weights.py
│   ├── evaluate.py
│   ├── fix_windows_torch_runtime.py
│   ├── prepare_data.py
│   └── train.py
├── src/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   └── paths.py
│   ├── data/
│   │   ├── camus/
│   │   │   ├── __init__.py
│   │   │   ├── dataset.py
│   │   │   ├── download.py
│   │   │   └── prepare.py
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── manifests.py
│   │   ├── medical_io.py
│   │   ├── metadata.py
│   │   ├── prepare.py
│   │   ├── splits.py
│   │   └── transforms.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── callbacks.py
│   │   ├── evaluator.py
│   │   └── trainer.py
│   ├── geometry/
│   │   ├── __init__.py
│   │   ├── functional.py
│   │   ├── mask_features.py
│   │   └── volume.py
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── cardiac.py
│   │   ├── segmentation.py
│   │   └── temporal.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── build.py
│   │   ├── deeplabv3.py
│   │   └── losses.py
│   ├── temporal/
│   │   ├── __init__.py
│   │   ├── beat_detection.py
│   │   ├── quality_gate.py
│   │   └── smoothing.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── device.py
│   │   ├── hash.py
│   │   ├── io.py
│   │   ├── project_structure.py
│   │   ├── run.py
│   │   └── seed.py
│   ├── visualization/
│   │   ├── __init__.py
│   │   ├── overlay.py
│   │   ├── plots.py
│   │   └── report.py
│   └── __init__.py
├── tests/
│   ├── test_camus.py
│   ├── test_config.py
│   ├── test_experiment.py
│   ├── test_geometry.py
│   ├── test_io.py
│   ├── test_model.py
│   ├── test_pipeline.py
│   ├── test_preprocess.py
│   ├── test_project_structure.py
│   └── test_training_progress.py
├── vendor/
│   ├── echonet/
│   │   ├── echonet/
│   │   │   ├── datasets/
│   │   │   │   ├── __init__.py
│   │   │   │   └── echo.py
│   │   │   ├── utils/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── segmentation.py
│   │   │   │   └── video.py
│   │   │   ├── __init__.py
│   │   │   ├── __main__.py
│   │   │   ├── __version__.py
│   │   │   └── config.py
│   │   ├── .gitignore
│   │   ├── example.cfg
│   │   ├── LICENSE
│   │   ├── README.md
│   │   ├── requirements.txt
│   │   └── setup.py
│   └── echonet_source.json
├── .gitattributes
├── .gitignore
├── pyproject.toml
├── README.md
└── requirements.txt
```
<!-- PROJECT_STRUCTURE:END -->

源码主线为 `configs/` → `scripts/` → `src/` → `runs/`；`tests/` 检查程序行为。`docs/data_sources/` 保存数据许可与完整校验清单，`reports/` 保存正式历史实验及审计，`vendor/` 保存固定版本的 EchoNet 上游代码与 MIT 许可。

### 目录与模块功能

| 目录或文件 | 主要作用 |
|---|---|
| `.github/workflows/tests.yml` | GitHub Actions 自动安装测试依赖并运行测试，检查提交是否破坏基础功能。 |
| `.run/` | PyCharm 的三个运行配置，分别启动数据核查/划分、训练、测试；工作目录使用项目根目录。首次克隆后需在 PyCharm 为本机选择 Python 解释器。 |
| `configs/experiment.yaml` | 实验总配置入口；通过 `defaults` 合并模型、数据、训练配置，并设置权重及结果目录。 |
| `configs/model/` | 模型名称、输入通道、分割类别等网络配置。 |
| `configs/data/` | 处理后数据目录、患者划分文件、三份子集清单路径和数据完整性预期。 |
| `configs/train/` | 训练轮数、批大小、学习率、设备和早停等训练参数。 |
| `configs/camus_splits.json` | 固定患者级训练、验证、测试归属，同一患者不会进入多个集合。 |
| `scripts/prepare_data.py` | 第一阶段入口：读取已处理数据，做完整性与溯源核查，写出固定划分的病例清单；不下载数据。 |
| `scripts/train.py` | 第二阶段入口：只读取训练集、验证集，训练分割模型并保存最佳权重及日志。 |
| `scripts/evaluate.py` | 第三阶段入口：只读取测试集与训练好的权重，导出分割、几何特征、指标和报告。 |
| `scripts/download_weights.py` | 可选获取 EchoNet 初始化权重；只下载模型权重，不下载影像数据。 |
| `scripts/fix_windows_torch_runtime.py` | Windows 特定运行库辅助工具，仅在 PyTorch 动态库加载冲突时使用。 |
| `src/config/` | 读取和合并带注释 YAML 配置，解析以项目根目录为基准的路径。 |
| `src/data/` | 通用数据接口、病例清单、固定划分、影像读取、元数据审计及裁剪/缩放坐标变换。 |
| `src/data/camus/` | CAMUS 数据适配器；包含已处理数据集读取，以及需要显式调用的可选下载和原始数组处理工具。日常三阶段流程不重新处理原始数据。 |
| `src/models/` | 创建 DeepLabV3-ResNet50 分割模型、载入检查点并计算 BCE 分割损失。 |
| `src/engine/` | 训练、验证和测试循环；管理进度记录、验证集选模、最佳权重与可选早停。 |
| `src/geometry/` | 从左室掩膜计算面积、长轴、关键点/截面，并按可用空间标定估算容积与功能参数。 |
| `src/metrics/` | 计算 Dice、边界距离、关键点误差，以及有可靠参考时的心功能误差汇总。 |
| `src/temporal/` | 提供曲线平滑、质量门控和心搏周期识别；不把半周期伪造成完整周期。 |
| `src/visualization/` | 生成预测叠图、曲线图和离线 HTML 结果报告。 |
| `src/utils/` | 通用文件读写、SHA256 溯源、设备和随机种子设置；`project_structure.py` 生成并核查本 README 的目录树。 |
| `tests/` | 配置、数据处理、几何、模型、训练流程和 README 一致性等自动检查。 |
| `docs/` | PyCharm 操作指南、测量口径、逐文件代码讲解、数据许可与来源校验材料。 |
| `reports/` | 已完成正式基线的汇总结果和输入/来源审计记录；新运行结果写入本地 `runs/`。 |
| `vendor/echonet/` | 随项目保留的 EchoNet 上游实现、版本来源和 MIT 许可，用于核对基线来源。 |
| `pyproject.toml`、`requirements.txt` | 项目安装元数据、依赖、测试配置和命令行入口。 |
| `data/`、`checkpoints/`、`runs/` | 本地数据、模型权重和新运行产物目录，默认由 Git 忽略；数据和权重按项目 Release/来源清单获取。 |

运行链路是：`prepare_data.py` 生成病例清单 → `train.py` 以训练集更新模型、以验证集选最佳权重 → `evaluate.py` 用预先固定的测试集生成最终指标和结果文件。`src/` 内部再按配置、数据、模型、引擎、几何、指标及时序/可视化职责拆分；逐文件调用关系和数学口径见 [完整代码讲解](docs/code_walkthrough.md)。

初次阅读代码可看 [从数据来源到结果表格的完整讲解](docs/code_walkthrough.md)，包含流程图、真实病例、函数职责、指标公式与输出字段。已删除废弃整理脚本、旧状态快照和重复报告；历史代码可通过 Git 提交记录查看。

新增、移动或删除项目文件后，执行以下命令同步目录树；测试也会检查 README 与实际结构是否一致：

```powershell
python -m src.utils.project_structure --write
python -m src.utils.project_structure --check
```

## 数据准备

Git 源码中不包含超声影像。首次使用时，从 [CAMUS 处理后数据 Release](https://github.com/KNN334/Echo/releases/tag/camus-prepared-v0.3.4) 获取已处理数据包，按发布清单校验并解压到：

```text
data/processed/camus/
├── manifest.json
├── patient0001_2CH.npz
├── patient0001_2CH.json
└── ...
```

正常训练只依赖该处理后目录。按本次目录框架保留 `src/data/camus/download.py` 和 `prepare.py` 两个可选工具模块：前者要求 HTTPS 来源与可信 SHA256，只获取归档，不绕过原始数据访问许可；后者处理显式传入的原始数组，保留 ED/ES 原始专家标签与正反坐标审计。三阶段入口不调用这两个工具。CAMUS 署名和 CC BY-NC-SA 4.0 许可见 [`docs/data_sources/CAMUS_LICENSE_TERMS.md`](docs/data_sources/CAMUS_LICENSE_TERMS.md)，校验清单见 `docs/data_sources/`。

`scripts/prepare_data.py` 生成 `data/processed/camus/splits/{train,val,test}.json`，不复制大型影像。现有患者划分保存在 `configs/camus_splits.json`。更换数据集时，配置独立的数据目录、适配器和划分清单；不要覆盖正式实验的固定划分。训练与评价引擎通过统一适配器读取病例。

## 模型与结果

安装依赖并检查：

```powershell
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
python -m pytest -q
```

首次训练如未配置初始化权重，可通过 `scripts/download_weights.py` 获取 EchoNet 官方模型权重；它只下载模型参数，不下载数据。也可以将 `train.initial_weights` 设为 `null` 从头训练。

已有 CUDA 版 PyTorch 可直接复用；安装依赖时检查解释器仍为项目 `.venv`。默认训练 30 轮、批大小 8，使用可用 CUDA；新实验在 `configs/experiment.yaml` 设置新的训练/测试输出目录。训练显示带时间戳的进度、耗时和速度，可选择启用验证集早停。每次运行保存完整合并配置及所有 YAML 来源摘要。

结果包含 Dice、ASSD、HD95、关键点误差、逐帧特征和功能参数 MAE。缺少可靠参考时，CO 或人工关键点误差为空并注明原因。绝对容积需要空间标定；半周期不会拼接成完整心搏。同几何法轮廓参考、CAMUS EF 标签和独立临床参考分别报告。

当前保存的 CAMUS / EchoNet 基线是研究工程结果，不代表临床验证。完整基线和参考值口径见 `reports/full_baseline/RESULTS.md` 与 `docs/measurement_protocol.md`。
