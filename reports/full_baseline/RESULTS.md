# CAMUS / EchoNet 全量基线实测报告

代码提交：`6186d976886fd4be0acd3810a870cc63064f69ba`；权重 SHA256：`824b3e1f735704c3172f14a2e7102067dd655d759b5ceb7842d7d3315310821f`。

预处理 500 名患者 / 1000 个切面 / 19232 帧；ED/ES 专家标注 2000 帧。

训练/验证/测试患者：347/71/82。测试尝试 82 名患者、164 个切面，失败 0 个切面。

## 结构误差

| 指标 | 实测值 |
|---|---:|
| 患者均值 Dice | 0.9125 |
| ASSD (mm) | 1.9439 |
| HD95 (mm) | 4.7562 |
| 轮廓派生关键点代理误差 (mm) | 5.3928 |
| 人工解剖关键点误差 | 不可计算 |

代理关键点来自对预测/专家轮廓使用相同几何算法；没有独立人工解剖点标签，因此不能将代理误差解释为真实解剖定位精度。

## 功能 MAE

| 计算与参考口径 | 指标 | MAE | 单位 | 有效患者 |
|---|---|---:|---|---:|
| 20_disks_shorter_axis | EDV | 8.9058 | mL | 82 |
| 20_disks_shorter_axis | ESV | 6.1107 | mL | 82 |
| 20_disks_shorter_axis | SV | 8.0488 | mL | 82 |
| 20_disks_shorter_axis | EF | 9.6188 | percentage_points | 82 |
| 20_disks_shorter_axis | CO | 不可计算 | L/min | 0 |
| biplane_vs_CAMUS_reported_EF | EDV | 不可计算 | mL | 0 |
| biplane_vs_CAMUS_reported_EF | ESV | 不可计算 | mL | 0 |
| biplane_vs_CAMUS_reported_EF | SV | 不可计算 | mL | 0 |
| biplane_vs_CAMUS_reported_EF | EF | 9.6685 | percentage_points | 82 |
| biplane_vs_CAMUS_reported_EF | CO | 不可计算 | L/min | 0 |
| single_plane_area_length_2CH | EDV | 29.2880 | mL | 82 |
| single_plane_area_length_2CH | ESV | 16.9256 | mL | 82 |
| single_plane_area_length_2CH | SV | 23.6263 | mL | 80 |
| single_plane_area_length_2CH | EF | 10.5957 | percentage_points | 80 |
| single_plane_area_length_2CH | CO | 不可计算 | L/min | 0 |
| single_plane_area_length_4CH | EDV | 22.3833 | mL | 82 |
| single_plane_area_length_4CH | ESV | 13.6606 | mL | 82 |
| single_plane_area_length_4CH | SV | 16.5797 | mL | 81 |
| single_plane_area_length_4CH | EF | 7.8069 | percentage_points | 81 |
| single_plane_area_length_4CH | CO | 不可计算 | L/min | 0 |
| single_plane_auto_extrema_2CH | EDV | 24.1318 | mL | 81 |
| single_plane_auto_extrema_2CH | ESV | 17.4703 | mL | 81 |
| single_plane_auto_extrema_2CH | SV | 20.2932 | mL | 81 |
| single_plane_auto_extrema_2CH | EF | 9.8840 | percentage_points | 81 |
| single_plane_auto_extrema_2CH | CO | 不可计算 | L/min | 0 |
| single_plane_auto_extrema_4CH | EDV | 21.2548 | mL | 80 |
| single_plane_auto_extrema_4CH | ESV | 14.7867 | mL | 80 |
| single_plane_auto_extrema_4CH | SV | 17.6015 | mL | 80 |
| single_plane_auto_extrema_4CH | EF | 8.4842 | percentage_points | 80 |
| single_plane_auto_extrema_4CH | CO | 不可计算 | L/min | 0 |

EDV/ESV/SV 的主要参考为专家轮廓经同一几何方法计算，不能冒充独立临床金标准。`biplane_vs_CAMUS_reported_EF` 才是与数据集 `Info.cfg` EF 标签的比较。参考相位和自动极值选相位结果分开报告。

CAMUS 仅提供半周期，不能由此可靠推导完整周期心率；没有独立 CO 真值，因此 CO 及其 MAE 为不可计算，绝不按双倍收缩时间伪造。

原始相位顺序：{'ED_before_ES': 979, 'ES_before_ED': 21}。保留原始采集顺序，不反转时间；自动极值选相位只在可用序列内寻找 ED 后的 ES，逆序半周期和边界极值可能无法选出有效相位，覆盖率见各项结果，不能解释为完整心搏检测精度。

## 可用性与限制

原始基线几何有效帧占比：1.0000，属于研究性几何可计算率，不是经人工验证的临床有效覆盖率。

默认 ROI 尚未逐病例人工审阅；自动最大声窗可去除分离文字，但与声窗相连的文字仍需人工排除。门控和平滑接口已实现，不能把未验证的阈值称为已证实有效的质量分类器。

实测端到端处理速度：18.8403 FPS（本机、本次输入及当前实现，不宣称通用实时性能）。

训练为 EchoNet 官方架构/权重上的 CAMUS 适配（AdamW、mean BCE、训练集归一化、冻结 BN 运行统计），不是官方 EchoNet 论文实验逐项复现。采用固定自定义患者划分，不是 CAMUS 官方排行榜分数。

详细中间特征：`patient_features.csv`、`frames.csv`；完整参考口径与置信区间：`summary.json`；每病例几何与坐标转换见运行目录 `*_features.json`。
