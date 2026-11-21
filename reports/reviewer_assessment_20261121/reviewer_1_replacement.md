# Reviewer 1

## Review setup

**Input scope**

审查冻结于 `4d74af1ffc29573865d00b9a43caddb18589a9f4` 的共同材料包。输入为19个科学展项、1张样式辅助页、10张历史分析图、相应图注和源表，以及当前实现和历史评价代码。没有完整论文稿。本报告的强调方向为影像、轮廓与几何、功能参数及时间链的技术有效性和可复现性。

**Assessment boundary**

仅依据 `packet/READ_FIRST.md`、`manifest.json`、`snapshot/`、`historical/`、`criteria/` 独立形成意见。未读取此前的审稿输出、其他审稿人的材料或后续综合意见。本次为输出技术故障后的替代审阅，不推断此前意见。已查看全部当前展项和10张历史图的预览，并结合图注、源表和相关代码核查。未训练、推理、改图或更改计算规则；未重新核验完整原始数据、全部缓存数组或权重。以下路径均相对于共同包。

**Shared manuscript claim summary**

可见材料建立了公开CAMUS经胸半序列上的分割和轮廓派生功能量工程基线。固定自定义患者划分为347/71/82；测试涉及164个切面序列、328张专家ED/ES标注帧和3,167张观察帧。作者明确区分同几何轮廓参考、Info.cfg EF标签与独立临床参考，未宣称已完成贴片采集或连续佩戴验证。

**Visible evidence base**

关键依据为 `snapshot/runs/camus_cuda_progress/{experiment.json,summary.json,structure.csv,function.csv,frames.csv}`、`snapshot/checkpoints/camus_cuda_progress/`、各展项 `caption_en.md` 与 `source_data/`、方法说明，以及 `historical/83f4489/cardiac/`。历史测试提交为 `83f44897747ab742bbeb387c0af4403438b854b5`，不能以当前YAML的增强、权重衰减和早停设置代替历史基线。当前 `src/geometry/` 与历史 `cardiac/geometry.py` 保留相同的代理基底选择及容积定义。

**Missing materials affecting confidence**

完整论文的论证、摘要和正文可读性不可评估。独立容积、人工解剖点、中间帧真值、完整周期及贴片数据在本项目可见证据中不可用，作者已明确承认。缺失这些材料不等于作者声称完成了相应验证，也不等于其原始临床检查从未获得这些测量。

## Overall assessment

这是一套来源较清楚、边界表述谨慎的工程结果材料。患者级分割平均Dice为0.912，原坐标空间指标、失败病例、缺失输出和参考层级均有实质性记录。可支持的结论是该冻结模型在本划分上的ED/ES分割表现及既定几何计算的描述性结果。功能量具有数值单位和较高容积相关性，并不能据此判断其对应临床容积或生理过程的准确程度。

主要技术限制已经由作者主动揭示，但尚未解决。代理基底造成明显的空间覆盖差异；逐帧独立估轴又会把几何跳变传入容积。两者限制了功能测量和动态解释的科学价值。本报告将其列为Major、Blocking No，因为它们不否定作者目前收窄后的工程描述，也没有证据支持将当前材料判为临床验证。若希望建立可靠心功能测量的更强论点，则必须进一步跨越这些证据缺口。

## Who would be interested in the results, and why

超声分割、轮廓测量和可穿戴超声算法研究者会关注这套可追踪的误差传递实例。高Dice与较差SV/EF一致性并存，以及几何参考偏倚与分割偏倚相抵消的现象，对设计评价体系有用。心血管临床和柔性器件领域读者目前能获得的是算法准备工作的边界，尚非佩戴监测的有效性证据。

## Major strengths

- 训练、验证、测试以患者隔离。历史代码仅由训练标注帧计算归一化，固定0.5阈值；选模来自验证损失，未见测试集参与这几个决策的证据。
- 保留原始ED/ES真值及双向坐标变换。空间评价在恢复原坐标、采用原始毫米标定且未进行几何清理的预测上实施，避免把低分辨率真值回采样冒充原始标注。
- 患者是主要统计单位，参考口径分开。表2保留负预测R²，图S7呈现有符号偏倚抵消，图S9及表S1交代无效值和分母，未以零补缺。
- 图2保留最低排名ES失败；图4、R2、S8保留真实波动。没有把半序列补成完整心搏，HR/CO及人工点误差未被伪造为可评价量。

## Major Concerns

### R1-M1 代理基底与完整轮廓的空间范围不一致，功能几何尚无独立有效性依据

**Severity** Major  
**Blocking** No  
**Axis** technical soundness / clinical-validity

**Claim pointer** 图1的轮廓到功能量流程、图3及表2的双平面结果，以及图4的单平面容积，采用同一套尚未验证的代理长轴几何。作者已明确称其为工程基线，未宣称独立临床容积准确性。

**Evidence pointer** `historical/83f4489/cardiac/geometry.py` 的 `infer_landmarks`、`mask_features`、`biplane_volume`；`snapshot/src/geometry/{mask_features.py,volume.py}`；图S6的 `source_data/panel_statistics.csv` 中 `proxy_axis_to_mask_span`、`mask_area_beyond_proxy_base_fraction`、`biplane_to_mean_single_ratio`；图S7的 `source_data/agreement_statistics.csv` 和 `bias_identity.json`；表2的 `source_data/display_table.csv`。

**Concern** 基底由长轴后40%区间中最宽截面确定。单平面公式的面积取完整清理轮廓，长度却止于该内部代理基底；双平面盘径仅覆盖代理轴区间，盘厚又取两切面的较短轴。图S6源表显示，专家轮廓在ED/ES的平均轴向覆盖仅68.37%/71.80%，代理基底外仍有29.57%/27.82%的面积。专家轮廓双平面容积与两单平面均值之比为0.441/0.464。这些比值也受公式和切面形态影响，不能全部归因于截短，但足以表明几条路径的测量范围不可直接互换。对预测和专家轮廓套用同一方法，会共同继承该几何假设。图S7中专家几何EF相对标签偏倚为+7.37 pp，而预测相对专家几何为−5.81 pp；合计+1.56 pp只说明代数抵消，无法验证几何正确性。

**Why it matters** EDV/ESV的同法MAE 8.15/5.82 mL主要衡量分割与既定几何的组合一致性。即使空间标定和相关性正确，仍没有证明所算体积覆盖了预期的解剖腔体。表2中同几何SV/EF的预测R²分别为−0.002/−0.041，也说明较好的容积相关性不能自动传递成功能差值的预测能力。

**Resolution test** 在升级功能测量结论前，需要预先定义并经专家检查的心尖、瓣环和基底平面约定，报告其对空间覆盖及ED/ES功能量的影响，并以独立来源或独立测量流程检验容积。方法修改和规则选择应先在训练/验证数据上完成，再由预先定义的独立评价检验，不能在这82名测试患者上选择最有利几何。若保持当前范围，应把这些数值继续作为明确命名的代理输出和同法参考一致性，保留图S6/S7的限制，不以同名临床方法或小偏倚证明有效性。

### R1-M2 逐帧估轴的不稳定性尚未与真实动态分离

**Severity** Major  
**Blocking** No  
**Axis** technical soundness / experimental-design

**Claim pointer** 图4、R2/R3和S8展示真实观察时序中的轮廓派生直径及单平面容积。图注已限定其为描述性几何轨迹，未声称测量应变或证明中间帧准确性。

**Evidence pointer** 图S8的 `source_data/maximum_change_statistics.csv`、`example_step.json` 及预览c/d；图S2的 `source_data/phase_statistics.csv`；图S9的 `source_data/reverse_phase_sequences.csv`；历史 `cardiac/pipeline.py` 中 `mask_features(original, spacing)` 和 `auto_ed`/`after`/`auto_es` 选择代码。

**Concern** 逐帧重新确定代理基底与长轴，故同一归一化轴位置并不对应固定解剖位置。S8给出的患者0329在17.67 ms内面积变化+1.09%、代理轴变化−32.49%，对应容积+51.37%，符合面积平方除以轴长所产生的几何放大。全体序列最大相邻容积变化的均值为2CH 22.91%、4CH 24.23%。这些统计不是伪影率或生理异常率。自动极值又作用于同一未稳定的曲线，精确ED匹配为31/82和38/80，精确ES匹配为30/82和28/80。患者0217_2CH在原始ES→ED序列中仍返回第16/18帧的自动数值，而专家ED/ES为第20/0帧，说明数值存在与正确相位识别是两件事。作者已正确保留这些情况，展示本身无法验证动态测量。

**Why it matters** 当容积极值受到估轴跳变影响时，端点Dice和自动EF的汇总误差不足以确定时间链的可靠程度。R2热图和R3曲面可以帮助展示计算结果，但不能增加独立时序证据。当前时间信息也仅来自FPS，无法补足完整心搏、长期漂移或贴片运动下的验证。

**Resolution test** 若拟从几何轨迹推进到生理动态或自动监测，需要在独立标注/独立参考下分开评价中间帧分割、轴/基底稳定性、相位定位及输出覆盖率，并预先声明原始相位顺序的适用范围。若引入平滑或跟踪，应同时保留未处理曲线并证明没有压低收缩幅度或掩盖失败。当前可以继续将图4、R2/R3和S8定位为观察值及不稳定性分析，不能将更多可视化、数值覆盖率或半序列内极值等同于动态有效性。

## Minor Comments

### R1-m1 明确两代bootstrap区间的来源

**Severity** Minor  
**Blocking** No  
**Axis** reproducibility  
**Affected element** 表2与历史评价摘要中的MAE置信区间。

**Evidence pointer** `snapshot/runs/camus_cuda_progress/summary.json` 的 `function.20_disks_shorter_axis.EDV.mae_ci95`；历史 `cardiac/metrics.py` 的 `mae_summary`；`snapshot/src/visualization/analysis.py` 的 `agreement`；表2 `source_data/agreement_statistics.csv` 的 `mae_ci_source` 和图注。

**Issue** 表2采用后来冻结的2,000次患者bootstrap，EDV区间为[6.6642, 9.7487] mL；历史测试摘要为[6.6220, 9.7683] mL，历史代码实际使用1,000次抽样并在指标间延续随机流。这是可追踪的统计版本差异，并非点估计矛盾，也没有证据说明作者选择了有利区间。但只写“冻结区间，seed 2026”容易让读者误以为所有既有文件区间一致。

**Required correction** 在结果版本说明中标明表2区间来自历史分析源表及其算法，原测试摘要保留原状；给出抽样次数、患者排序和随机流约定。交叉引用应指向同一套投稿区间，不应静默覆盖历史文件。

### R1-m2 训练图中的Mean BCE应说明批次汇总方式

**Severity** Minor  
**Blocking** No  
**Axis** reproducibility  
**Affected element** 图S3a/b及历史图01的Mean BCE和验证选模规则。

**Evidence pointer** `historical/83f4489/cardiac/model.py` 的 `train`，其中每批计算mean BCE，随后以 `np.mean(losses)` / `np.mean(vloss)` 汇总；图S3图注及 `source_data/configuration_comparison.json` 的 `batch_size=8`；验证样本为71患者、284标注帧。

**Issue** 历史基线的轮次损失是批次均值的等权平均。284张验证帧形成35个完整批次及1个4帧批次，因此最后一批每帧的汇总权重为完整批次每帧的两倍。该指标仍可作为历史固定选模规则，但并非全部验证像素BCE的严格等权平均。不能据此断定选错模型，现有记录也不足以证明改成帧加权后会改变所选轮次。

**Required correction** 明确注明历史图使用“各批次mean BCE的平均”，历史检查点仍按原规则标识。后续实验若调整汇总方式，应作为新的协议版本，不应将新规则追溯套用于这次冻结测试。

## Current exhibit inventory

下表逐项记录审阅范围。每项均查看预览和图注，结合所列源表；它是证据覆盖清单，不代表每项都是独立实验。目录均位于 `snapshot/figures/`。

| 展项 | 已核对的证据及评价边界 |
|---|---|
| fig_01_data_workflow | cohort、case_manifest、reference_coverage及流程。患者隔离、三层参考和HR/CO缺失边界清楚。 |
| fig_02_segmentation_validation | patient_metrics、frame_metrics、example_selection及分布。82名患者汇总与固定排名一致；空间分割证据较强，低分ES被保留。 |
| fig_03_function_agreement | agreement_pairs/statistics。容积同法参考与临床EF标签分列，不能从相关性推出临床有效性。 |
| fig_04_half_sequence | frames、expert_endpoints、curve_statistics。四个既定病例的原始半序列，只有端点参考，病例间未连接。 |
| fig_r01_lv_morphology | diameter_profiles、example_selection及影像矩阵。配对4CH未重新排名，直径归一化位置不是解剖对应位置。 |
| fig_r02_systolic_dynamics | frame_geometry、frame_diameters、expert_endpoints及热图。两病例、36帧、720直径测量，不形成队列动态验证。 |
| fig_r03_diameter_surface | observed_vertices、mesh_facets、display_settings及曲面。与R2同一批720值，三角连接是显示，不能作为新增3D或生理证据。 |
| fig_s01_sv_ef_agreement | agreement_pairs/statistics。82患者同几何SV/EF一致性，广泛差异和参考限制被保留。 |
| fig_s02_phase_selection | paired_EF、paired_statistics、phase_statistics和sequence_coverage。2CH/4CH配对n分别81/80，自动可用n为82/80；均值变化不能替代相位准确性。 |
| fig_s03_training_comparison | training_history、configuration_comparison、paired_statistics及剔除记录。两配置各一次历史运行，复合正则化未被误称为单因素消融；只比较验证集。 |
| fig_s04_quality_associations | quality_statistics、patient_analysis、associations。31/39/12患者的观察分层及探索关联，无因果或外部泛化证据。 |
| fig_s06_geometry_coverage | panel_statistics、source_geometry和volume_paths。直接量化覆盖差异，是功能解释的重要限制，见R1-M1。 |
| fig_s07_ef_reference_bias | ef_triplets、agreement_statistics、bias_identity。偏倚加和成立；MAE不可相加，未把代数分解包装成因果归因。 |
| fig_s08_observed_temporal_variation | all_observed_frames、adjacent_changes、maximum_change_statistics、example_step。164序列、3,003相邻对的描述，见R1-M2。 |
| fig_s09_output_availability | availability_cells、sequence_ledger、reverse_phase_sequences和unpaired_metrics。完整展示无效SV/EF与反向相位边界，可用率不等于有效率。 |
| table_01_cohort | display_table、patient_metadata、sequence_metadata。500患者/1,000序列和19,232帧，空间与时间来源、未审阅ROI和参考缺失单列说明。 |
| table_02_function | display_table、agreement_statistics及pairs。五个主结果保留n、MAE区间、LOA、相关性和预测R²，三种概念区分正确。 |
| table_s01_function | 21组display_table、agreement_pairs及可用性表。单/双平面、专家/自动相位和标签参考分开，保留10个未配对指标记录。 |
| table_s02_segmentation | frame_metrics、patient_stratum_metrics、stratum_statistics。IoU先逐帧计算再汇总；重叠分层未被视为独立队列。 |
| style_test | 预览与bars/curve仅作为样式辅助核查，不计入19个科学展项，不增加样本或实验数。 |

## Historical display check

历史图目录为 `snapshot/reports/result_analysis/camus_cuda_progress/`。已查看01至10全部PNG，并核对 `analysis_manifest.json` 的图注及相关source_data。这些是同一冻结基线的旧表达。

| 历史图 | 与当前证据的关系 |
|---|---|
| 01_training | 同一基线30轮训练、验证选择第7轮，与S3基线曲线相同。 |
| 02_segmentation | 四个切面/相位组的帧分布，与图2患者总体及表S2分层互补，不增加患者。 |
| 03_volume_agreement | 同几何EDV/ESV点估计，与当前图3/表2重复。 |
| 04_function_agreement | 同几何SV/EF，与S1/表2重复。 |
| 05_reported_ef | Info.cfg EF标签比较，与图3/表2最后口径重复。 |
| 06_phase_selection | 同一81/80共同有效患者，与S2a/b重复。 |
| 07_coverage | 同一可评价覆盖及缺失参考，当前S9/表S1提供更细台账。 |
| 08_examples | 与图2相同四个排名病例，配色变化不构成重复验证。 |
| 09_half_sequences | 与图4相同四条半序列，旧版纵轴各自缩放，当前共享坐标利于比较；都无中间真值。 |
| 10_error_associations | 与S4相同质量分层及Dice/EF关联，当前增加HD95关联仍来自同一82患者。 |

## Technical failings that need to be addressed before the case is established

在当前明确限定的工程描述范围内，未识别必须标为Blocking Yes的独立问题。建立更强的功能测量或动态监测论点之前，需解决R1-M1的几何有效性及R1-M2的时间链有效性。现有图注已对这些限制做出正确披露，披露本身不等于完成验证。

## Assessment against Nature-style criteria

| 标准 | 本次判断 |
|---|---|
| originality | 可确认自建了结果追踪、评价和展示链，但已知分割架构及启发式几何的集成本身不构成已证明的新科学原理。包中主要是展项和文献图表目录，不能据此判定完整论文没有创新论证，也不能假称核查过所列全部论文全文。 |
| scientific importance | 对可复现基线和评价纪律有用。尚未由当前材料证明突出的科学重要性，尤其未形成独立有效的功能测量或贴片监测发现。 |
| interdisciplinary readership | 误差在分割、几何和功能差值之间传递，以及偏倚抵消的实例，能连接影像算法与测量科学。对器件和临床领域的直接意义仍依赖尚未建立的验证链。 |
| technical soundness | 固定患者划分、原始真值、毫米标定和完整失败记录可靠；目前最强证据是ED/ES分割。功能几何及中间动态仍受R1-M1/M2限制，不能用工程检查代替医学验证。 |
| readability for nonspecialists | 流程、参考层级、单位和样本量总体清楚。图注较长但对防止误读有必要；R3最好与影像和定义同读。完整摘要、正文结构和跨领域叙述不可评估。 |

## Recommendation posture

支持将其作为范围明确、可追踪的CAMUS工程基线材料继续整理。若拟形成以可靠心功能或连续监测为中心的论文，现有证据尚未建立该更强论点；若拟提出Nature层面的科学重要性和跨领域影响，目前共同包亦不足以支持。这是基于部分材料的审稿判断，不是编辑决定。

## Risk / unsupported claims

- 本报告未认定作者已作出临床等效、完整周期、贴片佩戴、HR/CO或人工关键点准确性主张。这些都在可见材料中被适当限制。
- 相关性、很小的平均偏倚、同法参考误差和输出可用率均不足以独立证明功能测量有效性；不同参考及几何口径不宜混合排名。
- R1/R2/R3、历史图和当前图之间存在有意重用的同一患者和同一测量。它们可支持不同表达目的，但不能累计为额外实验或独立样本。
- 原始数据完整下载、完整预处理审计、完整模型实验与本地缓存覆盖率未在本次替代审阅中重新验证，不能由19个科学展项的齐全程度推断。
