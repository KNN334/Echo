# Echo

基于处理后超声心动图数据的左心室分割与心功能分析基线。模型采用 EchoNet 的 DeepLabV3-ResNet50 分割架构；CAMUS 处理后数据作为当前示例数据集。

## 三步运行

在 PyCharm 中依次右键运行 `scripts/` 下的三个 Python 文件：

1. `scripts/prepare_data.py`：读取本地处理后数据，检查原始标注和坐标审计，按患者级固定划分生成训练、验证、测试清单。
2. `scripts/train.py`：只读取训练与验证清单，计算训练集归一化参数，按验证损失选择模型。
3. `scripts/evaluate.py`：只读取测试清单，对已训练模型进行最终评价并导出结果。

详细步骤见 [PyCharm 三阶段运行指南](docs/pycharm_run.md)。默认配置是支持注释的 `configs/experiment.yaml`，按 `defaults` 合并模型、数据和训练组件。本次实验的配置可覆盖组件默认值；路径始终相对于项目根目录。

贴片采集、波束合成与当前 CAMUS 主链的衔接见 [更新后的全项目流程](docs/patch_acquisition_workflow.md)：说明通道 RF/IQ、已合成 IQ 与图像/视频分别从哪里接入，以及空间/时间标定、无标签推理、模型适配和连续心功能评价的条件。贴片成像及部署接口仍待接入，不能将现有 CAMUS 基线写成已完成贴片验证。

## 训练日志与环境

数据准备、训练、测试与绘图入口统一校验项目 `.venv`；可先在 PyCharm 运行“00 检查实验环境”。训练中每轮更新 `reports/training/<实验名>/` 下的 `training_log.txt` 和 `training.csv`；`run.json` 记录参数与 Python/依赖/CUDA 信息，结束时生成 `completed.json`，保存最佳轮次等完成信息。

已有正则化实验的 [训练日志](reports/training/camus_regularized/training_log.txt)、[逐轮损失](reports/training/camus_regularized/training.csv) 和 [归档说明](reports/training/camus_regularized/ARCHIVE.md) 可直接查看；旧实验没有保存完整环境信息。

统一环境后的 `camus_regularized_v2` 已完成 14 轮训练并触发早停，最低验证 BCE 为 `0.0363108074`（第 14 轮）。可查看本次 [训练日志](reports/training/camus_regularized_v2/training_log.txt)、[逐轮损失](reports/training/camus_regularized_v2/training.csv)、[运行环境](reports/training/camus_regularized_v2/run.json) 和 [实验说明](reports/training/camus_regularized_v2/RUN_NOTES.md)。本次完成训练/验证，未执行新的测试集评价。

## 结果分析图

本轮投稿图表规划见 [图表制作清单](figure_plan.md)、[结果资产盘点](figures/planning/result_assets.md) 和 [六篇同行论文逐图逐表拆解](figures/planning/literature_breakdown.md)。[全局样式](style/README.md)、[样式测试页](figures/style_test/style_test.pdf) 及四张正文图均已确认：[Fig.1 数据与方法框架](figures/fig_01_data_workflow/fig_01_data_workflow.pdf)、[Fig.2 分割验证](figures/fig_02_segmentation_validation/fig_02_segmentation_validation.pdf)、[Fig.3 功能一致性](figures/fig_03_function_agreement/fig_03_function_agreement.pdf)、[Fig.4 半周期轨迹](figures/fig_04_half_sequence/fig_04_half_sequence.pdf)。两张正文表尚未制作。按用户新增的完整覆盖要求，[可视化覆盖目录](figures/planning/visualization_coverage.md) 已收集10类旧分析图及新增诊断，提出核心补充8图2表、另3张有条件备选图，等待新增清单确认。所有结果仍限定于公开CAMUS半周期，保留几何与时序局限，不表述为贴片佩戴实测或独立临床容积准确性。

[2026-11-21结果自检](reports/result_integrity/camus_cuda_progress_20261121/report.md)：328标注帧分割指标与490行功能结果均可复算；发现代理长轴/基底导致的几何范围不一致、EF偏倚抵消和逐帧跳变风险。功能主图需先复核几何定义；原冻结结果保持不变。

已保存实验的 10 组结果图见 [离线图集](reports/result_analysis/camus_cuda_progress/index.html)、[全部图件 PDF](reports/result_analysis/camus_cuda_progress/all_figures.pdf) 和 [中文解读](reports/result_analysis/camus_cuda_progress/RESULTS_ANALYSIS.md)。图集使用同一轮冻结实验，分别展示同法轮廓参考与 CAMUS 报告 EF；不把半周期推理称为完整心搏或半监督训练。

新增 [绘图与复现说明](docs/result_analysis.md) 和 [文献与参考图分析](reports/visualization_literature.md)。运行 `python scripts/plot_results.py` 可重新生成图集；此入口不重新训练模型。

## 项目结构

以下目录树由实际项目文件生成。每个目录和文件的功能说明紧跟在对应路径下一行，过长说明会自动换行。`data/`、`checkpoints/`、`runs/` 是内容随实验变化的本地运行目录，只列顶层；Git 历史、虚拟环境、PyCharm 本机设置、`AGENTS.md`、临时检查文件、Python 缓存及打包缓存不属于公开项目目录。

<!-- PROJECT_STRUCTURE:START -->
```text
Echo/
# 左心室分割与心功能分析项目根目录
├── .github/
│   # GitHub 仓库自动化配置
│   └── workflows/
│       # 提交与拉取请求触发的自动检查流程
│       └── tests.yml
│           # 安装核心测试依赖并运行 pytest；缺少可选依赖的测试会跳过
├── .run/
│   # PyCharm 环境核查、三阶段与结果绘图配置；统一使用项目 .venv
│   ├── CheckEnvironment.run.xml
│   │   # 启动环境检查：核对项目 .venv、依赖版本和 CUDA
│   ├── PlotResults.run.xml
│   │   # 分析已保存实验并生成结果图，不重新训练或测试选模
│   ├── Prepare.run.xml
│   │   # 启动阶段 1：数据核查与固定患者划分
│   ├── Test.run.xml
│   │   # 启动阶段 3：测试集评价与结果导出
│   └── Train.run.xml
│       # 启动阶段 2：模型训练与验证
├── checkpoints/
│   # 本地模型权重，Git 忽略
├── configs/
│   # 可注释的 YAML 实验配置及固定患者划分
│   ├── data/
│   │   # 数据集路径、视图和处理约定
│   │   └── camus.yaml
│   │       # CAMUS 数据目录、子集清单、患者数及预处理尺寸等参数
│   ├── model/
│   │   # 模型结构与输入输出定义
│   │   └── deeplabv3_resnet50.yaml
│   │       # DeepLabV3-ResNet50 名称、输入通道和前景输出通道
│   ├── train/
│   │   # 训练超参数默认值
│   │   └── baseline.yaml
│   │       # 训练轮数、batch、学习率、随机种子、设备及可选早停
│   ├── camus_splits.json
│   │   # 固定训练/验证/测试患者归属，防止同一患者跨集合
│   └── experiment.yaml
│       # 实验总入口：合并组件配置，指定初始权重和训练/测试输出路径
├── data/
│   # 本地数据，Git 忽略；内部文件由数据集决定
├── docs/
│   # 运行指南、全流程讲解、测量口径和数据来源材料
│   ├── data_sources/
│   │   # 数据/权重来源、许可及完整性校验清单
│   │   ├── camus_download_manifest.json
│   │   │   # CAMUS 原始文件路径、大小和 SHA256 校验清单
│   │   ├── CAMUS_LICENSE_TERMS.md
│   │   │   # CAMUS 署名、CC BY-NC-SA 4.0 许可及使用条件
│   │   ├── echonet_weights.json
│   │   │   # EchoNet 官方初始化权重的来源与校验信息
│   │   ├── official_patient_index.json
│   │   │   # 官方患者、视图及原始文件的索引
│   │   └── prepared_provenance.json
│   │       # 处理后数据的代码/配置摘要、规模和审阅状态
│   ├── code_walkthrough.md
│   │   # 数据到结果表格的全链路、流程图、公式和逐文件讲解
│   ├── measurement_protocol.md
│   │   # 空间/时间标定、坐标恢复、指标与参考值的计算口径
│   ├── patch_acquisition_workflow.md
│   │   # 贴片 RF/IQ 到超声成像、模型接入与连续心功能分析的条件流程
│   ├── pycharm_run.md
│   │   # PyCharm 环境确认、三个入口运行和配置修改步骤
│   └── result_analysis.md
│       # 结果图的证据设计、参考图适用范围、导出格式及复现方法
├── figures/
│   # 论文图表规划、方法流程图、可编辑源稿和导出预览
│   ├── fig_01_data_workflow/
│   │   # 已确认的Fig.1：队列与方法框架、PDF/600dpi位图、源数据、英文图注与检查
│   ├── fig_02_segmentation_validation/
│   │   # 已确认的Fig.2：全患者分布及固定排名ED/ES病例、源数据、英文图注与检查
│   ├── fig_03_function_agreement/
│   │   # 已确认的Fig.3：同法容积与CAMUS标签EF散点/BA、配对源数据、图注与检查
│   ├── fig_04_half_sequence/
│   │   # 已确认的Fig.4：四固定病例真实ED–ES半序列轨迹、端点源数据、图注与检查
│   ├── planning/
│   │   # 结果资产盘点、同行逐图逐表拆解与图表规划的可复核材料
│   │   ├── asset_inventory.json
│   │   │   # 缓存规模、空间时间范围、冻结来源校验与现有实验清单
│   │   ├── audit_assets.py
│   │   │   # 只读核查缓存、患者划分和冻结源文件，不重训或重选模型
│   │   ├── audit_results.py
│   │   │   # 重算全部测试标注帧与功能算术，审计代理几何覆盖和时序风险，不改冻结结果
│   │   ├── literature_breakdown.md
│   │   │   # 两篇模板与四篇近期论文的逐图逐表拆解及共同做法
│   │   ├── literature_catalog.json
│   │   │   # 六篇已读论文逐图表结构、原始图注和来源校验记录
│   │   ├── literature_statistics.json
│   │   │   # 图表数量中位数、范围和十二类论证作用的统计结果
│   │   ├── result_assets.md
│   │   │   # 输出资产、分辨率、实验和已算/待算/不可算指标的中文清单
│   │   ├── summarize_literature.py
│   │   │   # 从人工核查目录生成拆解表并统计图表数量与论证作用
│   │   └── visualization_coverage.md
│   │       # 结果分析可视化覆盖审计、正文/补充/质控分层及不可制作项目
│   ├── style_test/
│   │   # 已确认的全局样式测试页、真实源数据、英文图注及字体/排版/色觉检查
│   ├── workflow_parts/
│   │   # 当前项目流程图规划、独立零件及审阅图集；总图待讨论后组装
│   ├── _paper_common.py
│   │   # 新投稿图共用的源数据溯源、物理坐标叠图、毫米排版及面板对齐检查
│   ├── camus_method_flow.pdf
│   │   # 用于论文排版的矢量版方法流程图
│   ├── camus_method_flow.png
│   │   # 由 SVG 源稿生成的流程图预览
│   ├── camus_method_flow.svg
│   │   # CAMUS 左室分割与心功能参数估算可编辑流程图
│   ├── fig_01_data_workflow.py
│   │   # 从冻结CAMUS队列与实际配置重建Fig.1数据和方法框架，不重新训练或推理
│   ├── fig_02_segmentation_validation.py
│   │   # 从全部82位测试患者和固定排名病例重建Fig.2，复核8帧轮廓指标
│   ├── fig_03_function_agreement.py
│   │   # 从冻结患者级配对重建Fig.3散点和Bland–Altman，分开参考口径并保留全部误差
│   ├── fig_04_half_sequence.py
│   │   # 重建Fig.4固定病例原始半序列容积及两个专家端点，不平滑或补造完整周期
│   ├── method_flow_caption.md
│   │   # 流程图图注、核心主张和实现假设
│   ├── method_flow_export_check.json
│   │   # 导出尺寸、文字边界和重叠检查记录
│   ├── render_method_flow.py
│   │   # 从 SVG 导出保留文字的矢量 PDF 和 300 dpi 预览
│   └── style_test.py
│       # 从冻结CAMUS结果重建样式测试页；使用共享样式，不重训或重选病例
├── reports/
│   # 历史基线结果、训练日志与审计；不代表当前代码已重新训练
│   ├── full_baseline/
│   │   # 历史完整基线的汇总指标、患者特征和训练记录
│   │   ├── patient_features.csv
│   │   │   # 患者级预测/参考心功能特征表
│   │   ├── RESULTS.md
│   │   │   # 历史基线结果、数据规模、参考口径及局限说明
│   │   ├── summary.json
│   │   │   # 分割与心功能评价的结构化汇总
│   │   ├── training_history.csv
│   │   │   # 历史每轮训练/验证损失记录
│   │   └── training_run.json
│   │       # 历史训练参数、患者划分、归一化和运行溯源
│   ├── result_analysis/
│   │   # 实测结果图集、中文解读、源数据及图件检查；内容由绘图入口生成
│   ├── result_integrity/
│   │   # 冻结结果全量复算、几何/EF偏倚/时序风险自检报告及逐项诊断数据；不改写原结果
│   ├── training/
│   │   # 逐实验训练日志、每轮损失、运行环境与完成记录；内容由训练入口生成
│   ├── input_equivalence.json
│   │   # 历史本地输入与处理后发布数据包的一致性审计
│   ├── release_artifacts.json
│   │   # 历史结果发布归档的大小、摘要及校验信息
│   ├── source_integrity.json
│   │   # 历史评价源码与被记录提交的对应关系审计
│   ├── visualization_literature.md
│   │   # 十二篇相关文献的结果图设计依据、参考流程图核对和论文建议
│   └── visualization_sources.json
│       # 本次图件调研的核验题录、摘要、来源及查阅范围
├── runs/
│   # 本地实验结果，Git 忽略
├── scripts/
│   # 可直接在 PyCharm 运行的薄入口及辅助工具
│   ├── __init__.py
│   │   # Python 包初始化与模块说明，无需单独运行
│   ├── check_environment.py
│   │   # 核对 PyCharm 是否使用项目 .venv，并报告依赖版本与 CUDA 状态
│   ├── download_weights.py
│   │   # 可选下载 EchoNet 初始化权重并核查摘要，不下载数据集
│   ├── evaluate.py
│   │   # 阶段 3：检查测试清单/权重，调用评估引擎生成结果
│   ├── fix_windows_torch_runtime.py
│   │   # 专项修复 Windows/Anaconda C++ 运行库冲突，非日常步骤
│   ├── plot_results.py
│   │   # 从匹配的冻结实验导出患者级图集及可追溯源数据
│   ├── prepare_data.py
│   │   # 阶段 1：核查已有处理后数据，生成固定患者级三份子集清单
│   └── train.py
│       # 阶段 2：读取训练/验证清单，启动训练并保存配置和完成记录
├── src/
│   # 项目算法与工程实现，按职责拆分的 Python 源码包
│   ├── config/
│   │   # YAML 配置加载、默认值合并和路径解析
│   │   ├── __init__.py
│   │   │   # Python 包初始化与模块说明，无需单独运行
│   │   ├── loader.py
│   │   │   # 安全读取 YAML、递归合并组件/覆盖值并记录配置文件摘要
│   │   └── paths.py
│   │       # 定位项目根目录，统一解析配置中的相对路径
│   ├── data/
│   │   # 通用数据适配、清单、固定划分、影像读取与坐标/元数据处理
│   │   ├── camus/
│   │   │   # CAMUS 专用适配及独立原始数据工具；日常流程读取已有缓存
│   │   │   ├── __init__.py
│   │   │   │   # Python 包初始化与模块说明，无需单独运行
│   │   │   ├── dataset.py
│   │   │   │   # CAMUS 适配器与 Dataset，仅以专家标注 ED/ES 帧监督训练
│   │   │   ├── download.py
│   │   │   │   # 可选独立归档下载，要求 HTTPS 来源与可信 SHA256
│   │   │   └── prepare.py
│   │   │       # 可选原始数组处理：左室标签、声窗、裁剪/缩放及原始标注审计
│   │   ├── __init__.py
│   │   │   # Python 包初始化与模块说明，无需单独运行
│   │   ├── base.py
│   │   │   # 数据适配器接口与带标注帧 Dataset，供训练和评价统一读取
│   │   ├── manifests.py
│   │   │   # 读取子集病例清单，解析数据根目录并校验源 manifest 摘要
│   │   ├── medical_io.py
│   │   │   # 读取医学影像/视频及轮廓标注，提取可用空间与时间信息
│   │   ├── metadata.py
│   │   │   # 审计帧数、像素间距、帧率和时间戳，明确缺失及推导来源
│   │   ├── prepare.py
│   │   │   # 核查处理后数据、原始标签/坐标审计并生成三份子集清单
│   │   ├── splits.py
│   │   │   # 患者级固定划分及集合隔离检查
│   │   └── transforms.py
│   │       # 裁剪/缩放正反坐标映射、掩膜恢复与训练归一化
│   ├── engine/
│   │   # 训练、验证、最终评价与进度/选模回调
│   │   ├── __init__.py
│   │   │   # Python 包初始化与模块说明，无需单独运行
│   │   ├── callbacks.py
│   │   │   # 时间戳日志、批次进度与速度、最佳权重保存及可选早停
│   │   ├── evaluator.py
│   │   │   # 测试推理、恢复原始坐标、提取特征并汇总指标和报告
│   │   └── trainer.py
│   │       # 训练集统计归一化、AdamW/BCE 训练和验证损失选模
│   ├── geometry/
│   │   # 左室掩膜几何测量、单/双平面容积与心功能计算
│   │   ├── __init__.py
│   │   │   # Python 包初始化与模块说明，无需单独运行
│   │   ├── functional.py
│   │   │   # EDV/ESV → SV/EF；仅在心率可靠时计算 CO
│   │   ├── mask_features.py
│   │   │   # 掩膜 → 面积、长轴、轮廓派生关键点与截面直径
│   │   └── volume.py
│   │       # 单平面面积-长轴法及双平面圆盘法容积估算
│   ├── metrics/
│   │   # 分割、关键点、心功能与时序定位误差
│   │   ├── __init__.py
│   │   │   # Python 包初始化与模块说明，无需单独运行
│   │   ├── cardiac.py
│   │   │   # 按患者汇总心功能 MAE、偏倚及不确定性
│   │   ├── segmentation.py
│   │   │   # Dice、ASSD、HD95 及关键点距离误差
│   │   └── temporal.py
│   │       # ED/ES 相位帧差；时间戳可靠时换算秒误差
│   ├── models/
│   │   # 模型工厂、DeepLabV3 网络及损失函数
│   │   ├── __init__.py
│   │   │   # Python 包初始化与模块说明，无需单独运行
│   │   ├── build.py
│   │   │   # 按配置创建网络、兼容 EchoNet 检查点并分批推理
│   │   ├── deeplabv3.py
│   │   │   # 构建 EchoNet 风格的单前景 DeepLabV3-ResNet50 分割网络
│   │   └── losses.py
│   │       # 计算均值二元交叉熵 BCE 分割损失
│   ├── temporal/
│   │   # 可选时序分析；不拼接/反射半周期伪造完整心搏
│   │   ├── __init__.py
│   │   │   # Python 包初始化与模块说明，无需单独运行
│   │   ├── beat_detection.py
│   │   │   # 在可靠时间与完整序列上识别心动周期并计算周期特征
│   │   ├── quality_gate.py
│   │   │   # 根据几何/时间连续性标记质量异常帧
│   │   └── smoothing.py
│   │       # 对容积等时序曲线进行平滑
│   ├── utils/
│   │   # 读写、溯源、设备、随机种子及 README 结构维护工具
│   │   ├── __init__.py
│   │   │   # Python 包初始化与模块说明，无需单独运行
│   │   ├── device.py
│   │   │   # 选择 CUDA/CPU 并设置 CPU 线程数
│   │   ├── hash.py
│   │   │   # SHA256 与代码/运行来源记录
│   │   ├── io.py
│   │   │   # JSON/NPZ 读写及 CSV 结果导出
│   │   ├── project_structure.py
│   │   │   # 按实际文件生成带功能注释的目录树并检查 README 一致性
│   │   ├── run.py
│   │   │   # 保护已有输出目录，保存阶段配置与数据检查快照
│   │   ├── runtime.py
│   │   │   # 记录 Python/依赖/CUDA 版本并校验项目虚拟环境
│   │   └── seed.py
│   │       # 设置 Python、NumPy、PyTorch/CUDA 随机种子
│   ├── visualization/
│   │   # 预测叠图、曲线及离线 HTML 报告
│   │   ├── __init__.py
│   │   │   # Python 包初始化与模块说明，无需单独运行
│   │   ├── analysis.py
│   │   │   # 核验实验来源，绘制训练/分割/一致性/覆盖率及失败病例图
│   │   ├── overlay.py
│   │   │   # 将预测/参考轮廓叠加到超声图像
│   │   ├── plots.py
│   │   │   # 绘制容积等时序曲线
│   │   └── report.py
│   │       # 汇总指标、图像和曲线生成离线 HTML 报告
│   └── __init__.py
│       # Python 包初始化与模块说明，无需单独运行
├── style/
│   # 所有新投稿图共用的字体、色系、色带、尺寸与导出设置
│   ├── __init__.py
│   │   # Python 包初始化与模块说明，无需单独运行
│   ├── palette.py
│   │   # 固定实验/参考配色、cividis/vik色带、字体与物理尺寸及统一导出
│   ├── paper.mplstyle
│   │   # 用户选定的Nature/Arial全局样式：普通文字7pt、600dpi位图
│   ├── README.md
│   │   # 已确认的全局样式映射、期刊尺寸、复现方法及导出约定
│   └── requirements.txt
│       # 样式绘图、科学色带和PDF/色觉检查所需依赖
├── tests/
│   # 自动工程回归检查，不替代真实患者实验或临床验证
│   ├── test_camus.py
│   │   # 检查左室标签身份、原始标注/坐标保留及声窗保护回退
│   ├── test_config.py
│   │   # 检查 YAML 合并、路径、模型工厂与三阶段入口衔接
│   ├── test_experiment.py
│   │   # 检查处理后数据审计、子集清单与输出目录保护
│   ├── test_geometry.py
│   │   # 检查几何、容积、心功能及周期计算
│   ├── test_io.py
│   │   # 检查 EchoNet 轮廓 CSV 转掩膜及对应帧身份
│   ├── test_model.py
│   │   # 检查 DeepLabV3 输出及检查点加载兼容性
│   ├── test_pipeline.py
│   │   # 检查模拟预测到结果导出的流程和缺失参考处理
│   ├── test_preprocess.py
│   │   # 检查图像排除区、插值、时间缺失及患者隔离
│   ├── test_project_structure.py
│   │   # 检查 README 目录树与实际文件一致、文档本地链接有效
│   ├── test_result_analysis.py
│   │   # 检查实验混用、患者泄漏、参考来源、缺失值及配对统计保护
│   ├── test_runtime.py
│   │   # 检查运行环境元数据和项目虚拟环境守卫
│   └── test_training_progress.py
│       # 检查训练进度/吞吐量记录、验证选模及早停
├── vendor/
│   # 保留固定版本上游代码、来源和许可
│   ├── echonet/
│   │   # EchoNet 上游参考实现，独立于本项目三阶段入口
│   │   ├── echonet/
│   │   │   # 上游 EchoNet Python 包
│   │   │   ├── datasets/
│   │   │   │   # 上游 EchoNet-Dynamic 数据集读取模块
│   │   │   │   ├── __init__.py
│   │   │   │   │   # Python 包初始化与模块说明，无需单独运行
│   │   │   │   └── echo.py
│   │   │   │       # 上游视频、患者划分、EF 和轮廓标签读取实现
│   │   │   ├── utils/
│   │   │   │   # 上游图像/视频工具及训练任务
│   │   │   │   ├── __init__.py
│   │   │   │   │   # 上游视频读写、统计与通用工具导出
│   │   │   │   ├── segmentation.py
│   │   │   │   │   # 上游分割训练/评价实现，供基线来源核对
│   │   │   │   └── video.py
│   │   │   │       # 上游视频 EF 回归任务，未接入当前 CAMUS 流程
│   │   │   ├── __init__.py
│   │   │   │   # 上游包初始化，导出数据与工具模块
│   │   │   ├── __main__.py
│   │   │   │   # 上游命令行任务入口，非本项目日常入口
│   │   │   ├── __version__.py
│   │   │   │   # 上游包版本声明
│   │   │   └── config.py
│   │   │       # 上游数据路径等配置读取
│   │   ├── .gitignore
│   │   │   # 上游仓库的文件忽略约定
│   │   ├── example.cfg
│   │   │   # 上游配置示例，非当前 YAML 实验配置
│   │   ├── LICENSE
│   │   │   # EchoNet 上游 MIT 许可证
│   │   ├── README.md
│   │   │   # 上游项目说明与使用方法
│   │   ├── requirements.txt
│   │   │   # 上游依赖清单，当前项目依赖以根目录文件为准
│   │   └── setup.py
│   │       # 上游打包脚本；本项目使用根目录 pyproject.toml
│   └── echonet_source.json
│       # 上游仓库、固定提交、归档 SHA256 与许可来源
├── .gitattributes
│   # 文本换行和医学影像/模型等 Git LFS 类型规则
├── .gitignore
│   # 排除本机环境、数据、权重、运行产物和私有协作文件
├── figure_plan.md
│   # 正文和补充图表制作清单、证据边界、待补计算与阶段确认进度
├── pyproject.toml
│   # 项目元数据、可选依赖、安装入口及 pytest 配置
├── README.md
│   # 项目概览、带功能注释的文件树和运行方法
└── requirements.txt
    # 完整运行依赖清单；CUDA 版 PyTorch 需匹配驱动安装
```
<!-- PROJECT_STRUCTURE:END -->

源码主线为 `configs/` → `scripts/` → `src/` → `runs/`；`tests/` 检查程序行为。`docs/data_sources/` 保存数据许可与完整校验清单，`reports/` 保存正式历史实验及审计，`vendor/` 保存固定版本的 EchoNet 上游代码与 MIT 许可。

初次阅读代码可看 [从数据来源到结果表格的完整讲解](docs/code_walkthrough.md)，包含流程图、真实病例、函数职责、指标公式与输出字段。已删除废弃整理脚本、旧状态快照和重复报告；历史代码可通过 Git 提交记录查看。

新增或移动项目文件时，先在 `src/utils/project_structure.py` 中补充对应路径的功能说明，再执行以下命令同步目录树；删除文件后直接重新生成。测试也会检查 README 与实际结构是否一致：

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
