# 结果资产清单

盘点日期：2026-11-20。项目根目录为 `C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析`；以下路径均相对此目录。机器核查记录见 [asset_inventory.json](asset_inventory.json)，可用项目 Python 运行 [audit_assets.py](audit_assets.py) 复查。

## 1. 当前证据支持什么

当前是 **CAMUS 公开经胸超声上的左室分割与轮廓几何量化基线**。有 500 位患者的 2CH/4CH ED→ES 半序列，没有本项目贴片佩戴采集、完整心搏、独立临床 EDV/ESV/CO 或人工关键点标签。可以制作可追溯的空间验证、同法几何误差传播、对照 CAMUS EF 标签及真实半序列图；不能把这些图称为连续佩戴或临床替代性验证。

## 2. 数据、分辨率与存放位置

| 资产 | 已核查数量 / 格式 | 空间信息 | 时间 / 相位信息 | 位置与可用边界 |
|---|---|---|---|---|
| 原始 CAMUS 数据 | 历史下载清单记载 500 患者、7,500 个原始文件的逐项大小与 SHA256；本地 `data/raw/` 不存在 | NIfTI 原始信息由缓存侧车保留；原始影像不能假称当前本地可读 | 原缓存为 half_sequence | `docs/data_sources/camus_download_manifest.json`；原始数据在 GitHub Release 的既有记录，本次未联网重新校验全部 Release 资产 |
| 处理后超声帧 | **1,000 / 1,000 NPZ 均解码通过**；19,232 帧；uint8 | 全部 112×112；原始 H=292–973、W=323–1181 px（各轴范围，不代表同一病例）；原始间距均约 0.308×0.308 mm | 10–42 帧/切面，中位 19；32.6–85.6 FPS，中位 56.5；时长 0.159–0.688 s；全部为半序列 | `data/processed/camus/patientXXXX_{2CH,4CH}.npz:frames`；不是原始像素画质，不是贴片影像 |
| 原始专家标注与处理后标注 | 2,000 张 ED/ES 标签；每 NPZ 有 `original_gt`、`original_gt_indices`、`masks`、`labeled` | 原始专家标注保留原始 H×W；处理后 mask 为 112×112 | 仅每个切面的两个专家相位有标签；中间帧的零数组不能当作背景真值 | 同上；LV 腔为 CAMUS label 1；评价使用原始标注和还原到原坐标的预测 |
| 标定、坐标与审计侧车 | 1,000 个病例 JSON，manifest 与患者固定划分 | 保存裁剪、原/处理尺寸、3×3 正反变换、间距；处理后 x 间距约 0.888–3.248 mm，y 约 0.803–2.676 mm，不能套用 0.308 mm | 帧率来源 `Info.cfg:FrameRate`；全部时间戳为 `derived_from_fps`，不是硬件原始时间戳 | `data/processed/camus/patientXXXX_VIEW.json`；声窗人工审阅全部为 false；不得更名为“已审阅” |
| 主冻结实验预测掩膜 | 164 个 NPZ；与对应输入帧数和 112×112 尺寸全部匹配 | 二值预测 mask；原坐标恢复依赖侧车 | 覆盖 82 测试患者、164 切面、3,167 帧 | `runs/camus_cuda_progress/*_pred.npz` |
| 逐帧几何 / 容积 | `frames.csv` 3,167 行；164 个 `*_features.json` | 面积 mm²、长轴 mm、单平面容积 mL；PCA 轮廓派生候选点；20 层盘径 | 帧号、派生秒数；不跨切面同步，不拼成整搏 | `runs/camus_cuda_progress/frames.csv`、`*_features.json`；`analysis_volume_ml` 与原容积同存；该实验无时序平滑/门控 |
| 空间指标 | `structure.csv` 328 行 | Dice、ASSD、HD95、HDmax、轮廓派生候选点代理误差；边界单位 mm | 每切面 ED/ES 各一行 | `runs/camus_cuda_progress/structure.csv`；真正人工点误差为空 |
| 功能指标配对表 | `function.csv` 490 行；不是 490 位患者 | EDV/ESV/SV mL、EF %；按 method/view/reference_scope 分组 | 专家相位、半序列自动极值、双平面 ED/ES；不同口径有效 n 不同 | `runs/camus_cuda_progress/function.csv`；HR/CO 全部缺失；不能跨口径混合 |
| 患者级派生统计 | 配对统计、覆盖率、相位比较、质量分层、样例排名等 CSV | MAE/bias/LOA；EF 误差用 pp | 每位患者或配对视图，不能把逐帧当独立患者 | `reports/result_analysis/camus_cuda_progress/source_data/`；主要源为原始 runs 表 |
| 训练记录 / 权重 | PT 检查点；CSV/JSON/TXT/LOG | DeepLabV3-ResNet50 单前景输出；灰度复制三通道 | 逐轮 train/val BCE、训练速度和耗时；按验证损失选模 | `checkpoints/`、`reports/training/`；权重文件约 159 MB 不等于参数量 |
| 原始逐搏 / 采集视频 | `beats.csv` 0 数据行；未发现本研究贴片原始视频 / RF / IQ | 无可用于贴片验证的标定原始采集 | 完整搏数 0 | 视频读取与 beat detection 的代码存在不等于已有实验 |
| 已有图与可编辑框图 | 10 组 PNG/PDF/SVG、图注、源数据与 QA；旧方法框图 | 现有示例背景来自 112×112 缓存 | 半周期曲线，未造完整搏 | `reports/result_analysis/camus_cuda_progress/`、`figures/camus_method_flow.*`、`figures/workflow_parts/`；均为旧产物，不是本次已批准的投稿图或新视觉主题 |

完整性分别报告：①原始全量仅有历史完整清单，本次未重新下载/核验；②本地处理后 1,000 切面完整并逐文件解码；③主冻结实验 train/val/test 有配套记录；④最新 v2 只有训练/验证，测试结果缺失。不能将四者合称“全部完成”。CAMUS 保留 CC BY-NC-SA 4.0 与 Leclerc 等署名；涉及投稿再核对目标期刊对含数据影像派生图的许可要求。

## 3. 已做实验与对比

固定患者 train/val/test=**347/71/82**；训练标注 1,388 帧、验证 284 帧、测试 328 帧。本次核对三个患者集合无交叉。所有训练归一化、选模和阈值应保持既有训练/验证来源；不追加测试调参。

| 实验 | 现有证据 | 结果 / 使用范围 |
|---|---|---|
| `full_baseline` | 历史完整训练及测试；`runs/full_baseline/`、`reports/full_baseline/`、`checkpoints/camus_full/` | 测试 Dice 0.912459，EF 标签 MAE 9.6685 pp；历史复现档案，不能混到主冻结实验中 |
| `camus_cuda_progress` | 30 轮，验证最优第 7 轮；测试及图集齐全 | 本计划沿用既有冻结主分析身份；测试 Dice 0.911909，EF 标签 MAE 9.0320 pp；不是依据本次重新比较测试分数挑选 |
| `camus_regularized` | 同架构、同患者划分、同初始化；同步增广+weight decay+早停组合，23 轮，最优第 17 轮；验证和测试齐全 | 验证 Dice 0.902091→0.903628；相同有效 70 人的标签 EF MAE 8.2443→9.8289 pp；不是单因素消融，也不是多种子实验 |
| `camus_regularized_v2` | 统一 PyCharm 环境后重训；14 轮，最优第 14 轮，验证 BCE 0.0363108 | `reports/training/camus_regularized_v2/` 与 `checkpoints/camus_regularized_v2/`；**没有新的测试结果**，不借用旧版本测试值 |
| 早期训练档案 | `checkpoints/camus_cuda/`、`camus_pycharm_run/`、`camus_standard/` | 检查点/部分训练记录存在；没有找到各自完整配套测试，不能升级为独立方法对照 |
| 同法口径对比 | 双平面 20 层较短长轴；2CH/4CH 单平面面积–长度；专家 ED/ES vs 半序列自动极值 | 已存功能配对表；不同参考与有效 n 严格分开。几何口径对照不等于新分割模型对照 |
| 切面、相位、图像质量分层 | 2CH/4CH、ED/ES；Good/Medium/Poor；按 Dice 固定排名典型例与失败例 | CAMUS 域内分层；质量数据来自官方侧车，不是自训质量分类器；不能称外部泛化或运动工况验证 |
| 未发现的实验 | U-Net/nnU-Net/其他分割架构的同划分结果；真正单因素消融；标签比例；多种子；跨设备/贴片/EchoNet 实测；完整周期/连续事件；真实人机阅片效率 | 标记缺失。`vendor/echonet` 与官方初始化权重存在，不代表 EchoNet 数据集已在本项目测试 |

两种历史模型的测试集均已使用；这些结果只能作既有最终评价的描述。后续消融应在训练/验证集预先设计，不能继续用此测试集挑新方案。

## 4. 已算指标、未算指标与不可算指标

| 类别 | 已算并有文件 | 能算但尚未形成冻结报告 | 当前不能支持 |
|---|---|---|---|
| 分割 | Dice、ASSD、HD95、最大 HD，mm；患者聚合与切面/相位分层 | IoU：先逐标注帧由二值 mask 或 Dice 转换再按患者汇总，不能将平均 Dice 直接转换；患者 bootstrap CI；逐视图误差分解 | 真正人工解剖关键点定位误差：无标签。5.399 mm 仅轮廓派生代理误差，不能标成人工点准确性 |
| 功能 | EDV/ESV/SV/EF 的 MAE、bias、描述性 95% LOA；已有 MAE 患者 bootstrap CI；EF 对照 CAMUS 标签单列 | RMSE、Pearson r、预测决定系数 R²；ICC 须先定义绝对一致性/一致性、单次/平均测量及区间算法；r² 与预测 R² 不混写；必要时 LOA 的 CI 与异方差诊断 | 独立临床 EDV/ESV/SV 误差；CO/HR 误差；不能从相同几何参考证明临床绝对容积准确 |
| 相位 / 时间 | ED/ES 自动选择帧误差字段，专家 vs 自动极值 EF 的配对误差 | 分患者汇总相位帧误差；在帧率可靠范围换算派生秒误差 | 完整周期识别率、逐搏 EF 真值轨迹、HR/CO 波形；中间帧没有专家容积真值 |
| 分类 | 未发现 AUC、敏感性、特异度或混淆矩阵 | 有 EF 标签和预测，可在另行明确疾病定义、阈值及统计计划后做探索性 EF 阈值分类；本计划不自动新增 | 临床疾病诊断验证、基于测试最优阈值的分类结果 |
| 效率 | 主实验端到端 149.8525 s / 3,167 帧=21.1341 FPS；可算术换算约 47.32 ms/帧；记录含加载、几何与导出，并非纯网络延迟；训练有 train/val frames/s | 模型参数量；指定硬件、batch、同步、预热、重复数下的网络/几何/总流程延迟分解与峰值显存 | 实时贴片部署、能耗、连续佩戴可用率；训练吞吐不能冒充推理 FPS |
| 失败 / 覆盖 | 主实验技术失败 0/164；结构 82/82；双平面 82/82；自动 4CH 80/82；完整搏 0；临床独立参考/人工点 0 | 按预定义标准做几何异常、低 Dice、相位失败等分层计数；未建立临床失败阈值 | 0 技术异常≠0 临床失败；所有 ROI 未人工审阅，不能宣称 100% 临床有效 |

主冻结实验指标如下。LOA 为预测减参考的均值±1.96×患者差值样本标准差，不是临床等效界限；单位 mL / pp。

| 参考口径 | 指标 | n | MAE | bias | 95% LOA |
|---|---|---:|---:|---:|---|
| 专家轮廓经同一双平面 20 层几何法，**非独立临床金标准** | EDV | 82 | 8.151 | -0.873 | [-22.085, 20.340] |
| 同上 | ESV | 82 | 5.822 | 2.554 | [-11.025, 16.134] |
| 同上 | SV | 82 | 8.030 | -3.427 | [-22.451, 15.597] |
| 同上 | EF | 82 | 9.266 | -5.811 | [-27.597, 15.975] |
| CAMUS Info.cfg EF 标签 | EF | 82 | 9.032 | 1.561 | [-20.153, 23.276] |
| 无完整搏 / 无可靠参考 HR / 无独立 CO 参考 | HR、CO | 0 | null | null | null |

单平面和自动极值完整有效数：专家相位 2CH EDV/ESV n=82、SV/EF n=81；4CH 四项均 n=82；自动 2CH 四项均 n=82、4CH 均 n=80。相位策略比较取交集：2CH n=81，4CH n=80。对应 MAE 与 LOA 已在 `runs/camus_cuda_progress/summary.json:function` 保存，不能拿 n=82 的摘要替代交集配对统计。

## 5. 已有可用图件与补算优先级

现成：`02_segmentation`、`03_volume_agreement`、`04_function_agreement`、`05_reported_ef`、`06_phase_selection`、`07_coverage`、`08_examples`、`09_half_sequences`、`10_error_associations`，加 `01_training`。这些图和旧框图可作为重组的数据与结构依据，但本轮不提前复用为“样式已确认”。

优先补算：按参考口径和患者重新导出 RMSE/r/R² 与 n；按患者聚合 IoU；将两种已有验证模型按同患者配对并保留无效原因。次优先：模型参数量和规范延迟测试；ICC 在确认统计定义后再计算。真正外部泛化、单因素消融和连续贴片验证属于补实验，不能靠绘图脚本补出来。
