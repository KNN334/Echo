# Reviewer 3

## Review setup

**Input scope**

共同冻结包对应项目提交 `4d74af1ffc29573865d00b9a43caddb18589a9f4`，历史测试评价提交为 `83f44897747ab742bbeb387c0af4403438b854b5`。逐一读取并目视审查了 19 个科学展项的英文图注和预览，另查阅 1 张样式测试页及 10 张历史分析图和图注。科学展项包括 4 张正文图、3 张 R 候选图、8 张补充图和 4 张表。R 编号表示候选，不能与正文图累计为 7 张正式正文图。

**Assessment boundary**

只依据共同包。没有完整论文、作者指定的主要终点和最终投稿期刊，因此本报告评价现有图表及其可追溯实现，不虚构摘要、正文论点、正文缺段或文章行号。没有读取其他审阅者的报告、其他强调方向、后续综合或后续审计。没有训练、推理、修改图形、改动原数据或调整算法。

**Shared manuscript claim summary**

材料展示公开 CAMUS 经胸半序列上的固定患者划分、逐帧 LV 分割、轮廓派生几何和功能量，以及其误差、覆盖率和失败边界。作者明确区分专家轮廓同法参考与 Info.cfg EF 标签，保留 HR/CO 为 null，不把影像称为贴片佩戴数据，不声称已经完成连续监测、人工关键点定位或独立临床容积验证。本报告按这一实际范围评价。

**Visible evidence base**

依据 [READ_FIRST.md](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/READ_FIRST.md)、[manifest.json](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/manifest.json) 及共同 criteria。除图注和预览外，检查了各展项源表、provenance、队列元数据、冻结功能与分割输出、历史和当前相关几何及评价代码、测量口径和贴片接口说明。核对了图件及历史代码相关的 213 个清单文件哈希，均与 manifest 一致。这不是对全部 1,350 个文件或完整原始数组、权重的重新核验。

对 Fig.3、Fig.S1、Table 2、Table S1 的配对源表复算了 n、MAE、RMSE、bias、LOA、Pearson r 及 predictive R²，31 个展示组全部一致，其中存在重复展示，并非 31 个独立实验。另核对了 Fig.2 的 82 个患者各 4 张标注帧及患者均值与样本标准差。没有重新计算冻结的 bootstrap 区间，也未做新的推断统计。

**Missing materials affecting confidence**

完整论文、最终主张优先级和主要终点尚未提供。原始缓存数组和模型权重没有在本包重复提供，本次未核验其逐元素内容或重新运行模型。文献规划目录只能支持判断作者参考了哪些证据组织方式，不能替代本次未读取的论文全文，亦不能用作同口径性能排名。

## Overall assessment

现有材料已能支持一个范围清楚、可以追溯的 CAMUS 工程基线。最有说服力的组合是 Fig.1 的证据层级、Fig.2 的患者级分割分布和失败例、Fig.3/Table 2 的分层参考比较，以及 Fig.S6 至 Fig.S9 对几何、参考偏差和不可用输出的解释。图表没有把大量帧、直径或三角面片写成独立患者，也没有用小平均偏倚替代个体一致性。

最重要的开放问题是几何量究竟代表哪个空间范围。它已被作者正确披露，但直接制约功能量的生物学解释，仍值得作为一项非阻断的 Major Concern 保留。其余意见针对跨领域阅读入口和局部定义。没有发现足以阻断“固定算法的描述性工程基线”这一有限论点的确认问题。原创性、卓越科学重要性以及跨领域结论仍不能从本图集单独确立，这不等于推定完整论文必然缺少相应论证。

## Who would be interested in the results, and why

超声图像分析、医学机器学习和可穿戴传感系统研究者会关注这些结果，因为它清楚呈现了从像素重叠到功能量之间的几何及参考依赖。对相邻领域读者，最有价值的信息是“分割看起来较好、平均偏倚较小和数值能够输出，分别回答不同问题”。目前材料对公共数据基线和测量定义的启示，强于对新器件、新生理规律或临床应用的直接证据。

## Major strengths

- 统计分母和重复观测层级大多非常清楚。患者级分割使用 82 位患者的四帧均值，质量分层使用患者，时间图和曲面明确是重复测量。有效输出数与尝试数、共同配对人群和全体有效人群分别报告。
- 参考层级分开命名。专家轮廓经同一几何法所得容积与 CAMUS EF 标签没有混成一个临床金标准。Table 2 保留负 predictive R²，Fig.S7 用同一批 82 位患者说明偏倚的精确代数关系。
- 图件留存低分和无效病例。Fig.2 的 ES Dice 0.443、Fig.4 的高容积例、Fig.S8 的跳变及 Fig.S9 的 ESV 大于 EDV 与逆相序失败，都使成功示例具有可信的边界。
- 视觉编码稳定。预测、专家轮廓及训练配置的颜色和线型相对一致；真实超声采用相同灰度窗、物理比例和比例尺；时间轨迹没有补成完整周期。英文图注认真区分 LOA、置信区间与临床接受界值。

## Major Concerns

### R3-M1 [mechanism-evidence / figures-and-tables]

**Severity** Major

**Blocking** No

**Axis** technical soundness；readability for nonspecialists

**Claim pointer**

Fig.1c 将轮廓面积、代理长轴和 20 个直径转成标定容积及 EDV/ESV/SV/LVEF；Fig.3、Fig.4 和 R 候选图随后呈现这些量的功能或形态意义。受到质疑的是这些输出对同一左室空间对象的解释，不是源表算术，也不是作者宣称已完成临床验证。

**Evidence pointer**

[历史 geometry.py](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/historical/83f4489/cardiac/geometry.py:36) 在长轴后 40% 区间寻找最宽截面并将其设为代理基底。其第 70 行仅在心尖至该基底间采样盘径，第 81 行却使用完整清理掩膜的面积。当前 [mask_features.py](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/src/geometry/mask_features.py:69) 与 [volume.py](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/src/geometry/volume.py:21) 保留这一基本定义。Fig.S6 的 [panel_statistics.csv](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_s06_geometry_coverage/source_data/panel_statistics.csv) 显示专家轮廓 ED/ES 代理轴仅覆盖完整投影跨度均值 68.37%/71.80%，代理基底之外面积为 29.57%/27.82%；专家双平面与平均单平面容积比均值为 0.441/0.464。Fig.S7 的 [agreement_statistics.csv](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_s07_ef_reference_bias/source_data/agreement_statistics.csv) 给出 G−L 偏倚 +7.37 pp，P−G 偏倚 −5.81 pp。

**Concern**

现有空间标定把像素换成了毫米，却没有使完整轮廓面积、短代理轴和截断直径积分自动对应同一解剖测量对象。单平面和双平面结果差异还包含公式与切面差异，因此不能把上述容积比直接当成“漏掉的容积分数”，也不能把 Fig.S7 的代数相消当成已识别的生理机制。作者对这些限制的披露是恰当的。开放的技术问题在于，非专科读者仍需在 Fig.S6 和代码中才能看清各条计算路径使用了不同的空间支持范围，而正文流程图只写 area–length 和 20 paired disks。

**Why it matters**

这会影响主要功能输出的构念含义及跨领域可迁移性，而不仅是精度好坏。同法预测与参考相近能够证明固定构造下的一致性，不能消除双方共享的测量定义偏差。该问题不阻断分割统计和固定算法复算，也不否定作者已经限定的描述性基线，所以 Blocking 为 No。

**Resolution test**

保留历史算法的情况下，可以用主图中的简洁测量示意或明确交叉引用，画出完整面积、代理基底及盘径积分覆盖范围，并将结果结论明确落在这个特定构造上，避免把不同几何路径当作同一绝对容积的可互换估计。如果作者最终希望提出解剖容积准确性的更强结论，则需另行预定测量定义，并以人工解剖点或独立临床容积证据验证；不得据本测试集的这些图选择新基底、几何或校准系数。本次审阅不要求立即改动算法或重跑测试集。

## Minor Comments

### R3-m1 [writing-clarity]

**Severity** Minor

**Blocking** No

**Axis** readability for nonspecialists

**Claim pointer / Affected element**

Fig.1 的首次阅读入口及 Fig.2、Fig.3 对 LV、ED/ES、EDV/ESV、SV、LVEF、PCA 和误差指标的使用。

**Evidence pointer**

[Fig.1 图注](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_01_data_workflow/caption_en.md) 与预览 c、d，及 [Fig.2 图注](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_02_segmentation_validation/caption_en.md)。Figure 2 展开 ASSD/HD95，但图集最前面的入口没有用一句通俗的话解释 ED/ES、SV 与 EF 的生理关系；较完整的 2CH/4CH、ED/ES 展开出现在 Table S2。

**Issue**

当前边界说明很充分，但基础背景比限制条件更压缩。非专科读者知道了哪些结果不能外推，仍可能不知道每个核心量在回答什么问题。这是局部阅读门槛，不是缺少临床证据或推定正文没有背景段。

**Required correction / Resolution test**

在图组入口添加一次简短定义，说明 LV 是左心室，ED/ES 是舒张末和收缩末，SV 为两个容积之差，EF 为该差占 EDV 的比例，并标明 Dice 越大越好、边界距离越小越好。PCA 只需解释为用于轮廓轴方向的数学估计。之后继续使用缩写即可，不必把每条图注变成教材。

### R3-m2 [figures-and-tables]

**Severity** Minor

**Blocking** No

**Axis** technical soundness；readability for nonspecialists

**Claim pointer / Affected element**

Table 1 英文图注把 `(frame count minus one)/FPS` 描述为 “observed ED-to-ES interval”，会使读者理解为全部原序列均按 ED 到 ES 的方向存储。

**Evidence pointer**

[Table 1 图注](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/table_01_cohort/caption_en.md) 与 [制表代码](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/table_01_cohort.py:161)。按其 [sequence_metadata.csv](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/table_01_cohort/source_data/sequence_metadata.csv) 的 1,000 个 case_id 查阅包内对应 sidecar 的 phases，有 21 个序列 ED 索引大于 ES 索引，其中训练 17、验证 1、测试 3。测试集三个序列可直接在 [reverse_phase_sequences.csv](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_s09_output_availability/source_data/reverse_phase_sequences.csv) 核验。例如 patient0068_4CH 的 ED/ES 为 35/0，patient0203_4CH 为 30/0，patient0217_2CH 为 20/0。

**Issue**

正的观测时长本身没有算错，但文字将“两个端点之间的区间”与“时间方向”混在了一起。Fig.S8/S9 已正确说明逆相序，所以这是 Table 1 的局部措辞不一致，不能据此认定作者反转过数据或伪造过周期。

**Required correction / Resolution test**

将图注改为观测半序列首末帧间时长或 ED/ES 两端点间隔，并在适当位置给出原始相序计数或指向 Fig.S9。保留存储顺序和现有时长数值，无需反转或重算轨迹。

### R3-m3 [figures-and-tables]

**Severity** Minor

**Blocking** No

**Axis** readability for nonspecialists

**Claim pointer / Affected element**

R1 的直径轮廓、R2 的热图和 R3 的曲面共用 “Proxy-axis position (%)”，R3 顶部另称 “20 layers”。

**Evidence pointer**

[R1 图注](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_r01_lv_morphology/caption_en.md)、[R2 图注](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_r02_systolic_dynamics/caption_en.md)、[R3 图注](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_r03_diameter_surface/caption_en.md) 及预览坐标轴。R1 的 [diameter_profiles.csv](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_r01_lv_morphology/source_data/diameter_profiles.csv) 与 R2 的 frame_diameters.csv 将测量点列为 2.5%、7.5% 至 97.5%；[采样代码](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/src/geometry/mask_features.py:69) 使用 `(j+0.5)L/20`。

**Issue**

图注已明确这些坐标不跟踪固定组织，这一点应保留。尚缺的是最直观的方向定义，读者无法仅看图判断 0% 与 100% 分别位于哪里，也容易把 layers 理解为心肌层或真实三维切层，而不是重估代理轴上的 20 个截面位置。

**Required correction / Resolution test**

在一处示意及相关图注中说明 0% 为推断的代理心尖、100% 为该帧代理基底，实际采样位于 20 个区间中点。将 R3 的 “20 layers” 改成 “20 proxy-axis positions”，并在图内保留一句每帧重新估计、不是组织跟踪的简短提示。无需增加采样或改变原数值。

## Technical failings that need to be addressed before the case is established

本次没有 Blocking Yes 问题。R3-M1 是把现有特定几何输出提升为解剖或临床功能测量之前需要解决的技术解释关口，不阻断已经限定的工程基线。R3-m1 至 R3-m3 可通过图组入口和局部文字修订解决。

## Assessment against Nature-style criteria

| 共同标准 | 基于所见材料的评价 |
|---|---|
| originality | 已有框架、公开 CAMUS 和常规几何计算的可追溯适配得到展示。作者没有在本包提出可逐句检验的首创论断。新算法、新器件或新科学结论的原创性不能由图形重排、参考层级解释或文献图表目录单独确立。 |
| scientific importance | 保留失败和识别测量定义风险对本领域有实际价值。卓越科学重要性目前未由本包建立。未提供的论文论证和其他证据列为不可评价，不据此断言其不存在。 |
| interdisciplinary readership | “像素分割、几何构造与临床标签回答不同问题”能连接机器学习、超声和传感测量领域。若以此作为现有结果的明确阅读主线，比并列呈现大量同病例曲线更容易体现对相邻领域的意义。贴片应用仍是目标而非本包验证结果。 |
| technical soundness | 固定患者划分、训练归一化和验证选模、原坐标评价、参考分层及患者级聚合有可信记录。已核对的配对统计与源表一致。R3-M1 限制几何功能量解释，完整数组和权重的独立重现本次未评估。 |
| readability for nonspecialists | 一致配色、比例尺、配对连接、共同坐标和清楚分母是优点。基础术语和代理轴方向仍需更早解释。图注通常同时承载方法、统计、来源和边界，主图应先使读者看懂证据作用，再由图注补全细节。 |

## Recommendation posture

作为有限的 CAMUS 描述性工程基线，持支持进一步完善的态度。作为拟提出广泛科学进展的论文，原创性、重要性和跨领域中心结论目前尚未从提供的材料中建立。本报告不代替期刊编辑决定，也不把未提供完整论文转化成一项人为的阻断要求。

## 展项逐一审查记录

下表每行均已读取英文图注并用图像工具目视预览。源表抽取和算术核对用于识别证据单位，不构成新的模型评价。关键来源位于各展项的 source_data 目录。

| 展项及来源 | 证据作用与分母 | 关键源表 | 目视和解释核对 |
|---|---|---|---|
| [Fig.1](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_01_data_workflow) | 数据和方法入口；347/71/82 患者，1,000 序列、19,232 帧。 | cohort.csv、case_manifest.csv、reference_coverage.csv | 独立划分和三层参考清楚，HR/CO 缺失没有零填。R3-M1、R3-m1。 |
| [Fig.2](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_02_segmentation_validation) | 空间分割证据；82 患者、328 标注帧；Dice 无量纲，ASSD/HD95 为 mm。 | frame_metrics.csv、patient_metrics.csv、distribution_summary.csv、example_selection.csv | 0.912±0.032、1.96±0.64 mm、4.81±1.86 mm 可复核。图注说明 min/max 须与固定排名，低分例保留。 |
| [Fig.3](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_03_function_agreement) | 主要功能比较；三个指标各 82 患者，EDV/ESV 用同法轮廓参考，EF 用标签。 | agreement_pairs.csv、agreement_statistics.csv | mL、%、pp 区分；r、MAE 与差值图分工明确，相关性没有替代 LOA。R3-M1。 |
| [Fig.4](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_04_half_sequence) | 实际观测时间过程；4 个患者/切面，76 帧，8 个专家端点。 | frames.csv、expert_endpoints.csv、curve_statistics.csv | 共同量程保留高容积例，轨迹到实际 ES 截止，未把端点连成参考真值曲线。只证明估计值的观测轨迹。 |
| [Fig.R1](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_r01_lv_morphology) | 空间形态示例；2 患者、4 切面、8 标注帧；轮廓剖面来自 1 患者。 | diameter_profiles.csv、example_selection.csv | 160 个直径值是源/切面/相位/位置的重复构造。排名只指预选 2CH 序列，配对 4CH 没有冒用排名。R3-m3。 |
| [Fig.R2](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_r02_systolic_dynamics) | 形态到时间的桥接；2 患者各 18 帧，720 个直径、36 个容积及 4 个专家端点。 | frame_diameters.csv、frame_geometry.csv、expert_endpoints.csv | 真实帧、直径图和容积轨迹各有证据作用；热图行不是固定组织。R3-m3。 |
| [Fig.R3](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_r03_diameter_surface) | 同一时空标量数据的曲面表达；2 患者、720 个原始节点。 | observed_vertices.csv、mesh_facets.csv、sequences.csv | 与 R2 的 720 个直径值逐行相同，属于备选表达而非新增验证。网格不增加样本；遮挡使局部读取弱于热图，可按最终叙事择用。R3-m3。 |
| [Fig.S1](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_s01_sv_ef_agreement) | 同几何 SV/EF 的补充功能证据；各 82 患者。 | agreement_pairs.csv、agreement_statistics.csv | SV MAE 8.03 mL、EF MAE 9.27 pp 及宽 LOA 完整呈现。与 Table 2 重合为同一结果，不能累计证据人数。 |
| [Fig.S2](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_s02_phase_selection) | 选相位影响和定位；EF 共同配对为 81/80，定位为 82/80 患者。 | paired_EF.csv、paired_statistics.csv、phase_offsets.csv、sequence_coverage.csv | EF 用 pp，定位用 ms；0.14/0.84 pp 为各自共同人群 MAE 的描述性差。所有有效自动 2CH 的 10.16 pp 与共同 81 人的 10.06 pp 分开，分母差异有解释。 |
| [Fig.S3](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_s03_training_comparison) | 训练配置对比；每配置 1 次历史运行，71 验证患者，EF 共同 70 人。 | training_history.csv、paired_patient_metrics.csv、all_valid_statistics.csv | 验证选模和多因素配置边界交代清楚。患者 SD 没被称为种子重复误差；+0.0015 Dice 与 +1.58 pp EF MAE 未写成普遍改善。 |
| [Fig.S4](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_s04_quality_associations) | 观测质量和误差关联；31/39/12 患者分层，关联均为 82 患者。 | quality_statistics.csv、patient_analysis.csv、associations.csv | 较差切面质量汇总和潜在混杂已写明；r=-0.270/0.114 为探索性关联，没有作因果解释。 |
| [Fig.S6](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_s06_geometry_coverage) | 解释几何覆盖；656 个源/切面/相位记录，328 个患者/源/相位聚合值及 328 容积比。 | source_geometry.csv、patient_geometry.csv、volume_paths.csv、panel_statistics.csv | 每相位/来源 82 患者，尺度和均值/SD 清楚。此图提供理解功能数字所必需的测量定义，见 R3-M1。 |
| [Fig.S7](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_s07_ef_reference_bias) | 解释参考偏移；相同 82 位患者的 P/G/L 三元组。 | ef_triplets.csv、agreement_statistics.csv | −5.81+7.37=+1.56 pp 在未舍入数据上相等。相加的是均值偏倚而非 MAE，图注明确不作因果归因。 |
| [Fig.S8](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_s08_observed_temporal_variation) | 总体时序波动及一例解释；164 序列、3,167 帧、3,003 相邻对。 | all_observed_frames.csv、adjacent_changes.csv、sequence_summary.csv | 每切面最大变化先汇总到患者；所有相邻对作为重复观测。51.4% 容积跳变与 −32.5% 轴变化是同一几何恒等式中的观测量，不是独立机制验证。 |
| [Fig.S9](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/fig_s09_output_availability) | 分母和失败边界；82 尝试患者/范围、492 患者范围记录、10 未配对指标。 | availability_cells.csv、sequence_ledger.csv、reverse_phase_sequences.csv、unpaired_metrics.csv | 21 个适用指标组的分母与 Table S1 对齐。不可适用符号不作零值；逆相序、有输出但相位不正确与缺失输出都保留。 |
| [Table 1](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/table_01_cohort) | 队列、采样和参考资源；500 患者、1,000 序列。 | patient_metadata.csv、sequence_metadata.csv、display_table.csv | 性别年龄按患者，质量和空间采样按序列；原始与处理后间距分开。时长方向措辞见 R3-m2。 |
| [Table 2](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/table_02_function) | 五组主要功能统计；各 82 患者。 | agreement_pairs.csv、agreement_statistics.csv、display_table.csv | 冻结患者 bootstrap 的 MAE CI 与描述性 LOA 分开。r² 与 predictive R² 定义分开；同法 SV/EF 的负 predictive R² 原样保留，提示不能只读相关性。 |
| [Table S1](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/table_s01_function) | 完整几何、切面、相位和参考范围；21 组、1,712 有效指标配对。 | agreement_pairs.csv、agreement_statistics.csv、patient_scope_availability.csv、unpaired_metrics.csv | 每行有效 n 和各范围不同参考清楚。1,712 是指标配对次数，不是新增患者；不能跨范围排名精度。 |
| [Table S2](C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/snapshot/figures/table_s02_segmentation) | 空间分割分层；82 患者、328 帧，9 个重叠分层。 | frame_metrics.csv、patient_stratum_metrics.csv、stratum_statistics.csv | IoU 从逐帧交并像素计算后再聚合，无平均 Dice 的代数替换；距离仍为原始标定 mm。分层不可相加。 |

### 辅助及历史表达的处理

样式测试页仅核查视觉约定，不作为科学展项或新实验计数。10 张历史分析图均查看了预览和中文图注。其训练、分割、容积/EF 一致性、自动相位、覆盖率、病例、半序列及质量关联分别与当前展项存在来源重合，不能再作为独立重复验证。旧图的轮廓颜色与新图不同，若最终只使用新图，避免将两套配色混排即可，无需为此改变冻结历史。

## Risk / unsupported claims

- **确认的技术解释限制** 是 R3-M1 的测量范围不一致。不能从现有源表推出其造成了多少独立临床容积误差，也不能将观测比值当成单一原因的因果效应。
- **确认的局部表述问题** 是 R3-m2 的方向措辞。原始元数据的逆相序存在，不等于曾做过反射、拼接、伪造完整周期或测试集选模。
- **不支持但作者也未作出的主张** 包括贴片佩戴性能、完整心搏 HR/CO、临床可替代性、人工解剖点精度、真实三维左室重建及应变。应保持现有克制命名，不能将这些边界写成作者已经作出的夸大主张。
- **不可评价** 包括完整论文的主张顺序、所有论证段落、外部研究全文所能证明的原创性、完整原始数据及权重的逐元素重现。未把这些项目自动列为 Major Concern。
- **统计解释边界** 是本图集主要为描述性结果。患者 SD 不等于训练重复的不确定性，LOA 不等于置信区间或临床接受界值，相关性不等于一致性；当前多数图注已正确说明。没有理由为了形式统一而给所有描述性图追加 p 值、把重复帧当作独立样本，或以同一测试集寻找更漂亮的分析规则。