# 可穿戴/贴片式心脏超声公开数据集核查

核查日期：2026-11-22

## 结论先行

截至本次核查，没有发现由论文作者或官方数据仓库公开发布、可直接下载的**患者级可穿戴/贴片式心脏超声数据集**（例如通道 RF/IQ、逐帧 B-mode 原始序列、患者元数据、姿态/运动状态和可复现 ED/ES/HR/CO 标签的完整归档）。

与贴片最直接相关的 Hu 等论文（*A wearable cardiac ultrasound imager*, Nature 2023）只声明“所有数据在论文或补充信息中”，公开附件是论文、补充 PDF 和少量 MP4 演示视频；作者 GitHub 仓库的说明和目录也只显示代码、许可证及演示媒体，没有患者级数据下载入口。因此这些附件可以作为方法和可视化参考，不能称为可训练的贴片数据集。

CAMUS 和 EchoNet-Dynamic 是可公开获取的常规临床超声基线，能够支持 B-mode 图像/视频、分割、ED/ES 和 EF 的可复现实验，但二者都不是贴片采集，不能证明贴片硬件、RF/IQ 波束合成或佩戴状态下的连续监测能力。

## 数据资源逐条核查

### 1. Hu 等：A wearable cardiac ultrasound imager（直接贴片相关）

| 字段 | 核查结果 |
|---|---|
| 官方来源 | [Nature/PMC 全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC9876798/)、[作者代码仓库](https://github.com/UCSD-XuGroup/Wearable-Cardiac-Ultrasound-Imager) |
| 是否公开下载 | **部分公开，但不是数据集**。论文的 Data availability 明确为“所有数据在论文或 Supplementary Information 中”；补充文件可直接下载。未发现患者级数据仓库或批量数据清单。 |
| 可下载内容 | [补充信息 PDF](https://pmc.ncbi.nlm.nih.gov/articles/PMC9876798/bin/41586_2022_5498_MOESM1_ESM.pdf)；[Supplementary Video 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC9876798/bin/41586_2022_5498_MOESM2_ESM.mp4)（正交阵列长轴/短轴）；[Video 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC9876798/bin/41586_2022_5498_MOESM3_ESM.mp4)（A4C/A2C）；[Video 3](https://pmc.ncbi.nlm.nih.gov/articles/PMC9876798/bin/41586_2022_5498_MOESM4_ESM.mp4)（休息、运动、恢复连续成像）；[Video 4](https://pmc.ncbi.nlm.nih.gov/articles/PMC9876798/bin/41586_2022_5498_MOESM5_ESM.mp4)（FCN-32 左室分割演示）；[Video 5](https://pmc.ncbi.nlm.nih.gov/articles/PMC9876798/bin/41586_2022_5498_MOESM6_ESM.mp4)（仿体穿刺演示）。 |
| 信号/图像层级 | 论文展示 B-mode、M-mode 和由图像推导的左室容积波形；没有公开通道 RF/IQ、阵元级采集、发射事件或可复现波束合成输入。公开 MP4 是渲染/演示视频，不等同于原始 B-mode 帧归档。 |
| 患者级时间序列 | 论文展示连续记录和运动/恢复过程，但 Data availability 没有提供患者级长序列、时间戳、采样率、文件索引或可批处理的下载包。不能据演示视频推断队列规模或可重复的患者划分。 |
| 视图、姿态、运动 | 正文展示 PLAX、PSAX、A4C、A2C；并报告坐姿、站立、弯腰、仰卧、侧卧等姿态，以及休息/自行车运动/恢复过程。它们是论文示例和实验条件，不是随数据一起提供的结构化标签表。 |
| 分割/ED-ES/HR/CO | 论文展示人工标注、FCN-32 分割、左室容积、SV、EF、CO、HR 波形和比较图；未提供可下载的逐帧 mask、ED/ES 索引、独立 CO 参考或机器可读 HR/CO 标签。不能把论文曲线当作公开标签集。 |
| 许可 | 论文开放获取许可为 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)；[GitHub 仓库](https://github.com/UCSD-XuGroup/Wearable-Cardiac-Ultrasound-Imager)的代码许可证为 MIT。论文/补充材料中的第三方材料仍需按其标注行确认，数据没有单独的数据集许可证声明。 |
| 适用性 | 可用于阅读硬件、成像链路、姿态/运动条件和方法流程；不能直接作为患者级贴片训练集、独立临床验证集或 RF/IQ 波束合成输入。 |

**一手证据：** PMC 页面中的 [Data availability](https://pmc.ncbi.nlm.nih.gov/articles/PMC9876798/#notes3) 写明“所有数据在论文或 Supplementary Information 中”，[Code availability](https://pmc.ncbi.nlm.nih.gov/articles/PMC9876798/#notes4) 单独指向 GitHub。仓库 README 仅列出分割模型代码来源，并嵌入一个 `fcn32-exe` 演示媒体；仓库目录只有 `LICENSE`、`README.md` 和 `media/` 下的 AVI/GIF，没有原始数据目录。

### 2. CAMUS（常规临床 B-mode 基线，不是贴片数据）

| 字段 | 核查结果 |
|---|---|
| 官方来源 | [CAMUS 项目主页](https://www.creatis.insa-lyon.fr/Challenge/camus/)、[数据属性页](https://www.creatis.insa-lyon.fr/Challenge/camus/databases.html)、[下载门户](https://humanheart-project.creatis.insa-lyon.fr/database/#collection/6373703d73e9f0047faa1bc8) |
| 是否公开下载 | 官方主页提供下载入口；当前下载门户按其访问权限和注册流程执行。项目页将 CAMUS 描述为 500 名患者的公开数据集。 |
| 信号/图像层级 | 常规超声设备导出的 2D B-mode 序列；官方说明原始输入以 `raw/mhd` 提供，序列以极坐标 B-mode 图像导出并统一插值到笛卡尔网格。没有通道 RF/IQ 或贴片阵元采集。 |
| 患者级时间序列 | 500 名患者，训练 450、测试 50；每位患者有 2CH 和 4CH 序列。官方数据属性页说明每个视图至少采集一个完整心动周期。项目本地准备包另有 `half_sequence` 文件，使用时仍应保留原始序列与周期状态，不能把半序列反射/拼接成完整周期。 |
| 视图、姿态、运动 | 2D 心尖四腔（4CH）和两腔（2CH）视图；官方资料未提供佩戴姿态、运动阶段或连续运动状态标签。 |
| 分割/ED-ES/HR/CO | 训练数据提供一名心脏专家的手工参考及舒张/收缩期相位时刻；任务涉及左室内膜、左室外膜/心肌和左房边界，并支持左室容积和 EF 估计。官方页面没有 HR 或独立 CO 标签。测试页历史说明手工参考不向参赛者提供，实际下载内容应以当前门户权限为准。 |
| 许可 | 项目配套条款为 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode)，并要求引用 Leclerc 等 CAMUS 论文；不得据此推断可穿戴数据许可。 |
| 适用性 | 适合分割、ED/ES、B-mode 几何量化和患者级划分的可复现基线；不能验证贴片 RF/IQ、佩戴姿态鲁棒性、运动中成像或独立 CO。 |

### 3. EchoNet-Dynamic（常规临床视频基线，不是贴片数据）

| 字段 | 核查结果 |
|---|---|
| 官方来源 | [Stanford EchoNet-Dynamic 项目页](https://echonet.github.io/dynamic/)、[Stanford AIMI 数据门户](https://stanford.redivis.com/datasets/66s1-2hsmzj5rn)、[官方代码](https://github.com/echonet/dynamic) |
| 是否公开下载 | **可申请下载**。官方页要求注册并接受 Stanford EchoNet-Dynamic Research Use Agreement；下载入口指向 Stanford AIMI Shared Datasets Portal，不是匿名直链。 |
| 信号/图像层级 | 10,030 个常规临床超声心动图视频，均为心尖四腔（A4C）视图；每个视频裁剪/遮罩后下采样为 112×112。官方资料没有提供 RF/IQ 或通道级输入，因此应视为显示级 B-mode/视频数据。 |
| 患者级时间序列 | 每条视频是一个时间序列，并与临床测量关联；数据页未提供可穿戴式长期连续监测、跨日随访或同一患者多次佩戴记录。 |
| 视图、姿态、运动 | 仅 A4C；数据来自 2016–2018 年 Stanford 医院常规临床检查，官方描述为 typical/resting echocardiography acquisition，未提供姿态或运动阶段标签。 |
| 分割/ED-ES/HR/CO | 每条视频关联 EF、EDV、ESV；左室心内膜在 ED 和 ES 两个时刻有专家 tracing，坐标和对应帧号随视频标识。官方页没有 HR 或 CO 标签，也没有贴片运动状态标签。 |
| 许可/访问约束 | Research Use Agreement 允许个人、非商业研究使用；禁止再分发数据或分享下载链接，禁止重新识别，且仅限 Research Use Only，不得用于诊疗。它不是标准开源许可证，应按协议使用。 |
| 适用性 | 适合视频分割、EF/EDV/ESV 预测和时序模型基线；不能代表贴片设备、运动佩戴环境、RF/IQ 波束合成或连续 HR/CO 监测。 |

## 与贴片研究的字段对齐

| 数据资源 | 公开形式 | RF/IQ | B-mode/视频 | 患者级序列 | 视图/姿态/运动标签 | ED/ES/分割 | HR/CO | 许可/访问 |
|---|---|---:|---:|---:|---|---|---|---|
| Hu 2023 可穿戴成像论文附件 | 论文、补充 PDF、少量 MP4 演示 | 否 | 仅演示视频 | 否（无可批处理队列） | 论文示例有，结构化标签无 | 结果展示有，机器可读标签无 | 曲线展示有，独立标签无 | CC BY 4.0；代码 MIT |
| CAMUS | 公开门户下载，`raw/mhd` B-mode 序列 | 否 | 是 | 是，500 患者 | 2CH/4CH；无姿态/运动标签 | 专家 ED/ES 参考，训练集明确 | 未提供 HR/CO | CC BY-NC-SA 4.0 |
| EchoNet-Dynamic | 注册后从 Stanford AIMI 门户下载 | 否 | 是，10,030 A4C 视频 | 视频级序列，无长期佩戴序列 | A4C；无姿态/运动标签 | ED/ES tracing、EF、EDV、ESV | 未提供 HR/CO | Stanford Research Use Agreement |

## 对本项目的使用建议

1. 将 Hu 2023 作为贴片硬件、B-mode/M-mode、视图和姿态/运动状态的**方法来源与证据边界**，不要把补充 MP4 当作训练数据或完整连续队列。
2. 将 CAMUS / EchoNet-Dynamic 明确标为常规临床 B-mode 基线；可以复现分割、ED/ES、几何容积和 EF，但不能写成贴片临床验证或 RF/IQ 波束合成验证。
3. 在真实贴片数据尚未取得前，RF/IQ、空间标定、时间戳、完整周期、HR、独立 CO、姿态和运动状态应继续按项目契约保留为 `null` 或“未提供”，并记录缺失原因。

## 来源清单

- Hu 等，*A wearable cardiac ultrasound imager*：<https://pmc.ncbi.nlm.nih.gov/articles/PMC9876798/>；DOI <https://doi.org/10.1038/s41586-022-05498-z>。
- Hu 等作者代码仓库：<https://github.com/UCSD-XuGroup/Wearable-Cardiac-Ultrasound-Imager>。
- CAMUS 项目主页：<https://www.creatis.insa-lyon.fr/Challenge/camus/>；数据属性：<https://www.creatis.insa-lyon.fr/Challenge/camus/databases.html>。
- CAMUS 下载门户：<https://humanheart-project.creatis.insa-lyon.fr/database/#collection/6373703d73e9f0047faa1bc8>。
- CAMUS 许可：<https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode>。
- EchoNet-Dynamic 官方页：<https://echonet.github.io/dynamic/>。
- EchoNet-Dynamic Stanford AIMI 门户：<https://stanford.redivis.com/datasets/66s1-2hsmzj5rn>。
- EchoNet-Dynamic 代码：<https://github.com/echonet/dynamic>。
