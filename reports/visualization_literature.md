# 结果分析图的文献依据与参考流程核对

查阅日期：2026-11-16。本次围绕“分割是否准确、误差如何传到功能参数、哪些临床结论还不能成立”做主题调研，纳入下列 12 篇原始研究、方法论文及指南；这是叙述性调研，不是系统综述。通过 Europe PMC 官方接口复核全部题录，查阅可用摘要；重点重新核对 Hu 2023 与 Tromp 2022 的开放全文及图注，同时参考项目已有的 CAMUS、EchoNet 等文献记录。没有把全部文献都称为已逐页精读。机器可读题录、摘要与查阅范围保存在 [来源记录](visualization_sources.json)。

## 一、用户提供的图能否作为本项目流程图

这张图是 Hu 等 *A wearable cardiac ultrasound imager* 的 **Fig. 5** [3]，不是 CAMUS 或 EchoNet 的官方流程图。图 a 的“图像→左室分割→几何容积→功能参数”与本项目方向一致；网络、容积计算、数据连续性和验证条件有实质差异。

| 原图内容 | 本项目实际实现 | 适用结论 |
|---|---|---|
| FCN-32 网络与原文模型比较 | EchoNet 风格 DeepLabV3-ResNet50，使用已有权重初始化，再以 CAMUS ED/ES 标签监督训练 | 应替换网络框；当前不是半监督训练 |
| PCA、旋转、切片积分 | PCA 辅助轮廓候选关键点；单平面面积–长度法；双平面 20 椭圆盘 | 可保留几何测量思想，不能照抄其公式与算法名 |
| 图 b 的完整舒缩周期与多个心动阶段 | CAMUS 当前缓存为 ED 到 ES 的半周期，只有 ED/ES 专家掩膜 | 可画真实帧序预测与两个标注点，不能补画完整周期或填充中间真值 |
| 图 c 的模型与人工测量 Bland–Altman | 本项目可分别比较专家轮廓经同法计算的参考、CAMUS 报告 EF | 适用，但需按患者汇总并标清参考来源 |
| 图 d 的贴片与商用设备比较 | 目前没有本项目贴片与参考设备的配对受试者数据 | 当前不能给出设备等效性图 |
| 图 e–h 的长期恢复、HR、CO | 没有当前贴片连续采集、完整周期与独立 CO 参考 | 暂不绘制；后续获得真实数据后开展 |

原文图注中 d 的 n=12 指心动周期，不能挪作本项目 12 名受试者。原文把图 c 虚线称为置信区间，也不应直接复制为本项目统计定义：本次明确绘制差值均值 ±1.96×差值样本标准差的描述性一致性界限，MAE 的 bootstrap 置信区间另行报告 [11–12]。

项目已有 [方法流程图](../figures/camus_method_flow.svg) 更接近现有代码，可作为方法图。当前补充的 [10 组结果图](result_analysis/camus_cuda_progress/index.html) 用于证据展示。

## 二、从文献到本次实际图件

| 文献与证据定位 | 对本项目有用的做法 | 已落实图件及限制 |
|---|---|---|
| [1] CAMUS：数据标注、分割与临床参数评价 | 将像素级结构指标与容积/EF 误差分开；考虑切面、相位与图像质量 | 图 2、3、4、5、10。项目固定患者划分，与原论文的折分和质量筛选不同，不能直接宣称优于原论文 |
| [2] EchoNet-Dynamic：视频输入、逐搏分析与泛化评价 | 预测与人工标签对照，并展示自动分析的可解释环节 | 图 5、8、9。当前用的是分割架构/权重来源，未运行原文视频 EF 回归任务，也没有复现逐搏验证 |
| [3] Hu 2023：Fig. 5、深度学习及左室分析段落 | 用“轮廓→容积→EF”串联结构和功能证据；设备对照和连续动态需真实测量 | 图 3–5、8–9；保留半周期边界，不复刻恢复曲线 |
| [4] Tromp 2022：Fig. 1–2、Table 2、Supplementary Fig. 1 | 配对误差、Bland–Altman、有效产出率共同报告；临床等效需要预设准则与独立读者 | 图 3–7。没有多读者重复测量，不能套用 IEC 或声称非劣效 |
| [5] He 2023 随机盲法研究 | 临床效用需要盲法、独立审阅和预设终点，不能由高 Dice 推断 | 写入证据边界；当前不画临床效用或节省阅片时间 |
| [6] PanEcho 2025：多任务及泛化评价 | 按任务报告有效样本，拓展数据域时保留外部验证 | 图 7；当前没有多任务、POCUS 或跨设备外部结果，不制作虚构泛化对比 |
| [7–8] Metrics Reloaded 与 metric pitfalls | 根据任务选择互补指标，避免只依赖重叠分数和平均值；明确分析单位 | 图 2 用 Dice/ASSD/HD95；图 8 含失败病例；图 10 探索分割与功能误差关联 |
| [9] CLAIM 2024 | 交代数据来源、患者隔离、参考标准、评价口径与结果可复现性 | 全图同一实验、源数据 CSV、权重摘要、缺失值/样本数与复现入口 |
| [10] ASE/EACVI 2015 心腔量化指南 | 双平面圆盘法有临床依据，但心尖缩短、轮廓和长轴定位仍影响容积 | 图 3–5；本项目 PCA 候选关键点没有人工点真值，不能宣称等同专家定位 |
| [11–12] Bland–Altman 方法 | 分清相关性与一致性，按独立对象定义差值；重复观测需处理个体内依赖 | 图 3–5 每点一患者；没有把 3,167 帧作为 3,167 个独立样本 |

图 1 额外展示现有训练日志中的 BCE 曲线，记录验证选模和后期训练/验证损失分离。它不是新训练实验或多随机种子平均曲线。

## 三、本次图集的科学口径

只采用较新的完整冻结实验 `camus_cuda_progress` 与匹配权重，不按测试分数挑实验，不混用历史 `full_baseline`。模型选择依据验证集：第 7 轮验证 BCE 最低。测试集 82 位患者、164 个切面、328 张专家标注帧。

结构分析给出 Dice、ASSD、HD95；功能分析分别使用两种参考：

1. **专家 ED/ES 轮廓经相同几何法计算的参考**：可分析轮廓误差沿几何链传播，但预测与参考共享模型假设，不能证明绝对临床容积准确。
2. **CAMUS Info.cfg 报告 EF**：单独展示，不与前者平均，不称作本项目独立前瞻临床验证。

本轮患者均值 Dice 为 0.9119；EF 对 CAMUS 报告值的 MAE 为 9.03 个百分点。这支持“已有可复现基线，结构分割和下游功能误差需要分别评价”，尚不支持“达到临床可替代性”。图像质量分层是探索性结果，不能根据测试集分组再修改阈值。没有额外模型对照、多种子或半监督训练，因此没有制作模型优越性、标注效率、统计显著性或消融实验图。

所有有效数据点保留。箱体为 IQR，须为 1.5×IQR 范围内最远点；MAE 的 95% 区间用 2,000 次患者 bootstrap。Bland–Altman 界限仅作描述，未证明差值正态、同方差或临床合格。EF 水平用 %，EF 误差用百分点 pp；两者不能混写成相对百分比误差。

定性病例按全部切面 ED/ES 平均 Dice 排名取最差、25%、50%、75% 位置，避免只展示成功例。背景来自已有处理帧，重采样仅用于显示；原始专家标签和恢复后的预测掩膜用于对照，未声称恢复了原始影像细节。

## 四、后续贴片数据与论文结果组织

现阶段论文结果可按“数据与划分→训练行为→分割→容积及 EF 一致性→自动选相位与覆盖率→失败例和局限”组织，对应图 1–10。主文可优先用图 2、3、5、8–9，其余作为补充材料；一次跑通基线不是算法创新证据。

拿到自采贴片数据后，增加独立章节评价跨设备迁移。先固定患者级外部测试，再确定需要多少带标注训练数据。如果研究目标转向半监督，需实际让无标签训练样本通过一致性或伪标签损失参与优化，并设置相同有标签预算的监督基线、不同标签比例及重复运行；仅对无标签帧推理不构成半监督。

贴片研究需要真实空间标定、可靠时间戳、多个完整周期及可追溯参考。届时再增加：同受试者配对设备图、真实连续容积与完整心搏示例、预设时间窗趋势、受试者聚类的重复测量一致性与漂移、有效监测时长覆盖率、运动伪影和失效案例。CO 仍需可靠 HR 与 SV，并单独说明是否有独立 CO 参考。若两台设备不能同时采集，应报告时间差与生理状态，不能直接把非同步波形视为逐帧真值。

## 五、核验文献

1. Leclerc S, et al. Deep Learning for Segmentation Using an Open Large-Scale Dataset in 2D Echocardiography. *IEEE Transactions on Medical Imaging* (2019). [DOI:10.1109/TMI.2019.2900516](https://doi.org/10.1109/TMI.2019.2900516).
2. Ouyang D, et al. Video-based AI for beat-to-beat assessment of cardiac function. *Nature* (2020). [DOI:10.1038/s41586-020-2145-8](https://doi.org/10.1038/s41586-020-2145-8).
3. Hu H, et al. A wearable cardiac ultrasound imager. *Nature* (2023). [DOI:10.1038/s41586-022-05498-z](https://doi.org/10.1038/s41586-022-05498-z). [开放全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC9876798/).
4. Tromp J, et al. A formal validation of a deep learning-based automated workflow for the interpretation of the echocardiogram. *Nature Communications* (2022). [DOI:10.1038/s41467-022-34245-1](https://doi.org/10.1038/s41467-022-34245-1).
5. He B, et al. Blinded, randomized trial of sonographer versus AI cardiac function assessment. *Nature* (2023). [DOI:10.1038/s41586-023-05947-3](https://doi.org/10.1038/s41586-023-05947-3).
6. Holste G, et al. Complete AI-Enabled Echocardiography Interpretation With Multitask Deep Learning. *JAMA* (2025). [DOI:10.1001/jama.2025.8731](https://doi.org/10.1001/jama.2025.8731).
7. Maier-Hein L, et al. Metrics reloaded: recommendations for image analysis validation. *Nature Methods* (2024). [DOI:10.1038/s41592-023-02151-z](https://doi.org/10.1038/s41592-023-02151-z).
8. Reinke A, et al. Understanding metric-related pitfalls in image analysis validation. *Nature Methods* (2024). [DOI:10.1038/s41592-023-02150-0](https://doi.org/10.1038/s41592-023-02150-0).
9. Tejani AS, et al. Checklist for Artificial Intelligence in Medical Imaging (CLAIM): 2024 Update. *Radiology: Artificial Intelligence* (2024). [DOI:10.1148/ryai.240300](https://doi.org/10.1148/ryai.240300).
10. Lang RM, et al. Recommendations for cardiac chamber quantification by echocardiography in adults: an update from the American Society of Echocardiography and the European Association of Cardiovascular Imaging. *Journal of the American Society of Echocardiography* (2015). [DOI:10.1016/j.echo.2014.10.003](https://doi.org/10.1016/j.echo.2014.10.003).
11. Bland JM, Altman DG. Statistical methods for assessing agreement between two methods of clinical measurement. *The Lancet* (1986). [DOI:10.1016/S0140-6736(86)90837-8](https://doi.org/10.1016/S0140-6736(86)90837-8).
12. Bland JM, Altman DG. Agreement between methods of measurement with multiple observations per individual. *Journal of Biopharmaceutical Statistics* (2007). [DOI:10.1080/10543400701329422](https://doi.org/10.1080/10543400701329422).

文献支持的是图件设计、统计口径及证据边界，不是为本项目代入或制造实验结果。此次所有定量图源于项目实测表；没有复制文献的受试者结果或恢复曲线。
