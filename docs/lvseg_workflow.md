# 左心室分割基线工作流

本说明对应当前 `lvseg/` 和 `scripts/` 下可执行的实现。当前工作只覆盖公开超声 cine 视频上的左室分割与逐帧几何分析。

## 从来源到固定数据集

1. `scripts/download_camus.py` 从 CAMUS 官方 Girder 接口获取 2CH/4CH 半周期 cine NIfTI、专家掩码和 `Info_*.cfg`。每个文件按官方清单校验字节数与 SHA-256；下载清单另外记录完整性和来源许可。
2. `scripts/prepare_camus.py` 从每段 cine 读取有序帧、像素间距、帧率、ED/ES 索引及专家标签，将帧缩放到统一训练分辨率。专家 ED/ES 原图掩码、原图尺寸、双向坐标变换矩阵和来源哈希写入准备数据。
3. `configs/splits/camus_patients.json` 固定全部 500 名患者的 train/validation/test 分配。两种切面共享患者集合，禁止患者跨集合泄漏。

训练 Dataset 只索引 `labeled=True` 的帧。训练集计算并保存图像归一化均值和标准差；验证集参与早停。测试时读取每个 cine 的所有帧，不读取标签来选择 EDV/ESV 峰谷；测试标签只用于人工掩码帧上的 IoU/Dice 和掩码 Simpson 对照。

## 分割模型与比较

当前五种模型共享相同输入分辨率、患者划分、损失、优化器、训练迭代和验证选模规则：

- U-Net
- Attention U-Net
- U-Net++
- U-Net-mini
- VGG16 编码器 + U-Net 解码器

阶段不包含自定义网络或消融。五种模型的预测阈值在配置中固定；测试集不用于选模型或调阈值。

## 逐帧 Simpson 曲线与周期量

对每个 cine 的每一帧执行：

```text
B-mode 帧 → LV 分割掩码 → 恢复原图像素网格 → 20 圆盘单平面 Simpson 体积
                                                     ↓ 按时间排序
                                            LV 容积波形 V(t)
```

圆盘剖面沿掩码的主轴取得连续直径，使用图像 spacing 换算毫米；圆盘横截面采用圆形假设，故结果是单平面几何估计。CAMUS 的 2CH 和 4CH 视频是分开采集，不知道同步相位，不能逐帧凑成双平面 Simpson。两种切面分别输出曲线与标注帧对照。

波形局部峰为候选 EDV，之后局部谷为候选 ESV。专家 ED/ES 帧仅以另一类参考标记显示，不用于峰谷查找。只有在视频确认覆盖完整周期且检测到相邻 ED 峰时，才计算：

```text
T = 相邻 EDV 峰时间差
HR = 60 / T                         bpm
SV = EDV - ESV                       mL（需要空间标定）
EF = SV / EDV
CO = SV × HR                         mL/min
```

CAMUS 只有半周期片段，不能提供两次 EDV 峰，HR/CO 字段为空，并给出不可计算原因。EchoNet-Dynamic 的视频使用者需自行按 AIMI 条款申请；它是单一 A4C 视图且没有空间标定，容积只作为 `pixel3_proxy`，不得显示为 mL。

## 评价与图

- 分割：测试集中人工 ED/ES 掩码帧计算 IoU、Dice，并按患者先汇总再报告。
- 容积一致性：同一标注帧的预测掩码和专家掩码使用同一 Simpson 实现计算 Bland–Altman；按视图分别报告逐帧配对和患者内先平均的配对。参考是同方法轮廓派生量，不是独立临床容积。
- 容积波形：每个测试 cine 都保留全帧预测容积和时间；图中标记预测 EDV/ESV 极值、人工 ED/ES 参考帧和无法计算 HR/CO 的原因。
- 轮廓图：仅展示带专家掩码的帧，并同时叠加专家边界和模型预测边界。

正式运行产物保存在 `runs/lvseg_baselines/<模型名>/evaluation/`。主要文件为 `all_frame_volumes.csv`、`labeled_frame_metrics.csv`、`phase_events.csv`、`predicted_masks/`、`volume_curve_example.png`、`mask_comparison_example.png`、`volume_bland_altman.png` 和 `summary.json`。

完整数据、完整预处理、完整模型训练与缓存状态分开报告。模型工程检查不是临床验证；公开集结果不能单独证明贴片状态下的连续监测有效。
