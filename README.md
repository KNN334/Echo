# Echo
A study on ultrasound-based segmentation

基于 CAMUS 和 EchoNet 分割架构的心尖切面分析研究。对应项目研究计划的五个模块：数据预处理 → 左室结构/关键点 → 时序和质量控制 → 容积与功能 → 可视化及评价。

## 已实现

- CAMUS 官方全量下载器、患者级 SHA256 文件清单及断点重跑。
- NIfTI/MetaImage/AVI 读取；核查帧率、时间戳、像素间距；去除分离的界面文字和无关区域，支持声窗多边形及排除框人工修订。
- 保存裁剪/缩放的双向坐标变换；预测还原到原始坐标后与原始标注评估。
- EchoNet 默认 DeepLabV3-ResNet50 单 logit 架构；适配 CAMUS 的训练、验证、完整序列推理及检查点兼容。
- 左室腔、轮廓几何心尖/瓣环候选、面积、长轴、20 层直径、单/双平面容积。
- EDV、ESV、SV、EF、CO 字段及 MAE；Dice、ASSD、HD95、最大边界距离、人工/轮廓派生关键点误差分开输出。
- 平滑、质量门控、完整周期检测、有效覆盖率、患者聚类统计和静态 HTML 容积曲线报告。

**代码已实现不等于完整数据实验已完成。** 当前实况以 `docs/project_status.json` 及提交记录为准；`smoke_training_not_final` 为小样本工程验证。CAMUS 半周期无法单独推断可靠心率/CO；没有独立 CO 真值不生成 CO MAE。没有人工点标签，不把轮廓几何代理误差称为人工关键点精度。

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

# 训练。归一化只用训练集，按验证损失选择 best.pt
.\.venv\Scripts\python -m cardiac.cli train --epochs 30 --batch 8

# 测试集评估，所有功能指标及中间特征写入 runs/baseline
.\.venv\Scripts\python -m cardiac.cli evaluate --weights checkpoints/camus_baseline/best.pt --output runs/baseline

# 计划中的消融：逐帧、时序、门控、时序+门控
.\.venv\Scripts\python -m cardiac.cli evaluate --weights checkpoints/camus_baseline/best.pt --output runs/temporal --temporal
.\.venv\Scripts\python -m cardiac.cli evaluate --weights checkpoints/camus_baseline/best.pt --output runs/gate --gate
.\.venv\Scripts\python -m cardiac.cli evaluate --weights checkpoints/camus_baseline/best.pt --output runs/temporal_gate --temporal --gate

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

原始 CAMUS 默认不被普通 `git add .` 加入，以免下载未完成就提交残缺数据。完成下载核查后可使用：

```powershell
git lfs install
git add -f data/raw/CAMUS
git add data/manifests/camus_download.json
git commit -m "data: archive complete CAMUS dataset with source checksums"
git push origin main
```

`.gitattributes` 已将 NIfTI、MetaImage raw、AVI 和模型权重指定为 Git LFS。完整影像上传受实际 GitHub LFS 账户配额及网络影响；不能把仅有 LFS 指针称为数据已上传。每次版本更新完成并验证后，使用新的 commit/tag；不要覆盖已有提交或强制推送。当前固定自定义患者划分不是 CAMUS 官方排行榜划分。

引用：Leclerc et al., IEEE TMI 2019, DOI: 10.1109/TMI.2019.2900516；Ouyang et al., Nature 2020, DOI: 10.1038/s41586-020-2145-8。
