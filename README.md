# Echo
A study on ultrasound-based segmentation

基于 CAMUS 和 EchoNet 分割架构的心尖切面分析研究。对应项目研究计划的五个模块：数据预处理 → 左室结构/关键点 → 时序和质量控制 → 容积与功能 → 可视化及评价。

## 下载与查看结果

| 内容 | 入口 |
|---|---|
| 项目代码 | 本仓库 `main` 分支，`cardiac/`、`scripts/`、`tests/` |
| 完整原始 CAMUS | [500 名患者、7,500 文件，五个 ZIP](https://github.com/KNN334/Echo/releases/tag/camus-data-20261108) |
| 完整预处理数据 | [v0.3.4：1000 个切面、2000 个专家标注帧](https://github.com/KNN334/Echo/releases/tag/camus-prepared-v0.3.4) |
| 正式模型与完整中间输出 | [v0.4.0 研究基线](https://github.com/KNN334/Echo/releases/tag/v0.4.0) |
| 实测报告及逐患者结果 | [RESULTS.md](reports/full_baseline/RESULTS.md)、[patient_features.csv](reports/full_baseline/patient_features.csv) |

影像和模型体积较大，实际文件放在 **Releases**。仅下载仓库源代码 ZIP 不包含影像和权重。每个版本均保留 commit/tag 与来源校验记录；请使用修正版 v0.3.4 预处理包，旧包问题见 [修复记录](docs/preprocessing_v031_superseded.md)。

## v0.4.0 正式测试

完整预处理 500 名患者、1000 个 A2C/A4C 切面、19,232 帧。固定自定义患者划分为训练 347 / 验证 71 / 测试 82，训练 30 轮，按最低验证 BCE 选用第 6 轮。测试 164 个切面、328 个 ED/ES 标注帧，病例失败数为 0。

| 指标（患者级平均） | 实测值 |
|---|---:|
| Dice | 0.9125 |
| ASSD | 1.9439 mm |
| HD95 | 4.7562 mm |
| 轮廓派生关键点代理误差 | 5.3928 mm |
| 双平面 EDV / ESV / SV MAE | 8.9058 / 6.1107 / 8.0488 mL |
| 双平面 EF MAE，参考为同几何法专家轮廓 | 9.6188 个百分点 |
| 双平面 EF MAE，参考为 CAMUS 自带 EF 标签 | 9.6685 个百分点 |

双平面结果使用数据集给定 ED/ES 相位，用于隔离分割误差；自动选相位和单平面结果在报告中另列。EDV/ESV/SV 的参考来自专家轮廓经同一几何法计算，并非独立临床容积金标准。没有人工解剖关键点标签，因此代理误差不能称为人工关键点误差。全部序列为半周期（979 个 ED 在 ES 前、21 个顺序相反），没有可靠完整周期心率和独立 CO 真值，CO 和 CO MAE 保持空值。

## 已实现

- CAMUS 官方全量下载器、患者级 SHA256 文件清单及断点重跑。
- NIfTI/MetaImage/AVI 读取；核查帧率、时间戳、像素间距；去除分离的界面文字和无关区域，支持声窗多边形及排除框人工修订。
- 保存裁剪/缩放的双向坐标变换；预测还原到原始坐标后与原始标注评估。
- EchoNet 默认 DeepLabV3-ResNet50 单 logit 架构；适配 CAMUS 的训练、验证、完整序列推理及检查点兼容。
- 左室腔、轮廓几何心尖/瓣环候选、面积、长轴、20 层直径、单/双平面容积。
- EDV、ESV、SV、EF、CO 字段及 MAE；Dice、ASSD、HD95、最大边界距离、人工/轮廓派生关键点误差分开输出。
- 平滑、质量门控、完整周期检测、有效覆盖率、患者聚类统计和静态 HTML 容积曲线报告。

**已完成一次全量数据研究基线，不代表临床验证。** 当前实况以 `docs/project_status.json`、正式报告及提交记录为准；早期 `smoke_training_not_final` 和中止实验不纳入正式结果。声窗尚未逐病例人工审阅，时序、门控模块已实现但尚未完成效益验证。

完整原始 CAMUS 已发布在 [CAMUS 数据 Release](https://github.com/KNN334/Echo/releases/tag/camus-data-20261108)：500 名患者，分成五个数据包，附全文件及压缩包 SHA256。下载五个 ZIP 并解压到同一目录即可组合完整数据集；数据体积较大，所以放在 Release 中，仓库源代码目录保留许可和校验清单。

## 安装

Python 3.10+，建议带 NVIDIA GPU。Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[model,medical,test]"
.\.venv\Scripts\python -m pytest -q
```

已有 CUDA 环境时，根据 PyTorch 官网匹配安装 torch / torchvision，再安装本项目。核心几何和单元检查不依赖 GPU。

## 运行

```powershell
# 完整 500 患者下载，约 3.8 GB；中断后重跑可跳过已完成患者
.\.venv\Scripts\python scripts\download_camus.py --workers 8

# 预处理，生成每病例 NPZ、审计 JSON、患者独立划分
.\.venv\Scripts\python -m cardiac.cli prepare

# 下载官方 EchoNet 分割权重，随后进行 CAMUS 适配训练
.\.venv\Scripts\python scripts\download_weights.py
.\.venv\Scripts\python -m cardiac.cli train --epochs 30 --batch 8 --weights checkpoints/echonet_official.pt --output checkpoints/camus_full

# 测试集评估，所有功能指标及中间特征写入 runs/baseline
.\.venv\Scripts\python -m cardiac.cli evaluate --weights checkpoints/camus_full/best.pt --output runs/full_baseline
.\.venv\Scripts\python scripts\build_experiment_report.py

# 计划中的消融：逐帧、时序、门控、时序+门控
.\.venv\Scripts\python -m cardiac.cli evaluate --weights checkpoints/camus_full/best.pt --output runs/temporal --temporal
.\.venv\Scripts\python -m cardiac.cli evaluate --weights checkpoints/camus_full/best.pt --output runs/gate --gate
.\.venv\Scripts\python -m cardiac.cli evaluate --weights checkpoints/camus_full/best.pt --output runs/temporal_gate --temporal --gate

# 或完成下载→训练→四种评估；任一步失败即停止
.\scripts\run_baseline.ps1 -Epochs 30 -Workers 8
```

默认声窗未人工确认，门控版会拒绝并明确标记，不能据此宣称已经验证质量门控收益。请先根据叠加图和 `configs/camus.json` 对声窗完成核查；不要为提高覆盖率跳过审查。

官方源模型权重可用 `scripts/download_weights.py` 获取。其归一化需要真实来源；官方训练集统计缺失时不能随意填写常数。本项目 CAMUS 训练检查点内已保存训练集统计。`--weights` 可初始化 CAMUS 微调，但必须把它与零样本官方复现分开报告。

## 输出和参考

| 文件 | 内容 |
|---|---|
| `frames.csv` | 时间、原始/分析容积、面积、长轴、原始坐标关键点、置信度、质量标志 |
| `*_features.json` | 每帧轮廓几何、20 层直径、空间与时间审计、正反坐标变换 |
| `structure.csv` | ED/ES Dice、ASSD、HD95、最大距离、关键点分项/平均误差 |
| `function.csv` | EDV/ESV/SV/EF/CO 及参考值，单/双平面与自动/参考选相位分开 |
| `beats.csv` | 仅完整且有效的相邻 ED 周期参数；半周期不造心搏 |
| `summary.json` | 患者级 MAE、偏倚、置信区间、病例失败及覆盖率、代码/权重溯源 |
| `report.html` | 叠加图、逐帧容积曲线、功能 MAE 与 CSV 链接 |

外部独立参考使用 `--references path.json`，人工点使用 `--manual-landmarks path.json`，详细格式、单位、测量方法和不可计算条件见 [测量协议](docs/measurement_protocol.md)。

## 数据、许可与 GitHub

CAMUS 原始影像采用 [官方 CC BY-NC-SA 4.0 条款](data/licenses/CAMUS_LICENSE_TERMS.md)，仅非商业科研，必须署名并保留相同许可。下载器保留原始文件、MANDATORY_CITATION 和校验清单。不得去掉这些文件后当作本项目自有数据发布。

EchoNet 官方代码位于 `vendor/echonet`，保留其 MIT 许可，来源提交和压缩包 SHA256 见 `vendor/echonet_source.json`。本项目训练适配不是论文原数值复现。EchoNet-Dynamic **影像数据**另有申请和使用协议，本项目只随附其公开代码，不擅自再发布该影像库。

原始 CAMUS、预处理数组、训练权重和逐帧运行产物在普通 Git 历史中排除，实际文件通过上述 Releases 发布，仓库保留代码、报告、许可、来源和 SHA256 清单。请分别下载数据包和模型；仅克隆代码不会自动获得 Release 资产。`.gitattributes` 保留可选 Git LFS 规则，但本次已发布资产不依赖 LFS 配额，也不是只有指针的占位文件。每次版本更新完成并验证后，使用新的 commit/tag；不要覆盖已有提交或强制推送。当前固定自定义患者划分不是 CAMUS 官方排行榜划分。

引用：Leclerc et al., IEEE TMI 2019, DOI: 10.1109/TMI.2019.2900516；Ouyang et al., Nature 2020, DOI: 10.1038/s41586-020-2145-8。
