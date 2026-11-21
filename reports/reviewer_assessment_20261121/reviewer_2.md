# Reviewer 2 独立结果材料审查

## Review setup

### Input scope

审查对象为冻结在提交 `4d74af1ffc29573865d00b9a43caddb18589a9f4` 的共同材料包。仅使用包内 `READ_FIRST.md`、`manifest.json`、`snapshot/`、`historical/83f4489/` 和 `criteria/`，未读取其他审阅者报告、私人记录、母任务进展或综合意见。预先强调方向为原创性与科学重要性，其余共同标准仍予评价。

以下证据路径均相对于材料包根目录 `C:/Users/LEN/Desktop/毕业设计/毕设-基于贴片式超声探头的心脏功能参数连续监测与分析/reports/reviewer_assessment_20261121/packet/`。`snapshot/` 表示当前冻结材料，`historical/83f4489/` 表示实际测试实验的历史实现，二者不互相替代。

### Assessment boundary

这是现有结果材料审查，没有完整论文、作者指定主要终点或最终投稿期刊。因此，不推断摘要、讨论或正文一定缺少某段，不虚构作者已作出的创新性或临床效用声明。本报告区分“公开数据基线作为工程结果是否成立”与“能否建立题目所指的贴片连续监测研究”，也不把 Nature 风格标准等同于毕业设计合格标准或正式编辑决定。

已逐一查看19个科学展项和10张历史图的现有预览与图注，并检查样式辅助页。所有科学展项均回溯到随包源表；重点复核了功能配对统计、患者分割汇总、R2/R3直径数据复用、相位顺序与缺失输出。未重新训练、推理、修改几何、调整阈值或选择病例。未读取包外完整缓存、原始影像或模型权重，因此不声称独立复现像素级推理、全部预处理或原始数据完整性。

### Shared manuscript claim summary

包内研究题目为“基于贴片式超声探头的心脏功能参数连续监测与分析”。现有图注实际支持的是另一层、较窄且已明确声明的结果，即固定患者划分的公开 CAMUS 经胸半序列上，冻结 DeepLabV3–ResNet50 分割适配基线及其轮廓代理几何输出。专家轮廓同算法参考、CAMUS Info.cfg EF标签和缺失的独立临床参考被分开。现有图注明确承认没有贴片采集、完整周期、可靠HR/独立CO、人工解剖点标注和中间帧参考。以下意见不将这些承认改写成作者宣称已完成验证。

### Visible evidence base

对 `manifest.json` 所列1350个当前文件及15个历史代码文件逐项计算SHA256，1365项均与清单相符。该结果只证明所审包的内部冻结一致性。

从 Table 2 的原始患者配对独立重算 n、MAE、RMSE、bias、LOA、Pearson r 和 predictive R²，五行均与其统计源表一致。Fig.2 的患者均值和样本SD也相符。主要事实包括以下几点。

- 测试集82人，164个切面序列，328张专家ED/ES标注帧。患者平均Dice为0.9119，ASSD为1.9627 mm，HD95为4.8114 mm。
- 双平面同几何参考下，EDV/ESV MAE为8.15/5.82 mL，但SV/EF的 predictive R²为−0.002/−0.041。EF对Info.cfg标签的MAE为9.03 pp，描述性LOA为−20.15至23.28 pp。高容积相关性、小均值偏倚和良好个体功能测量不能等同。
- Table S1有21组、1712个有效指标配对。S9有492条患者与方法范围记录。三个ES→ED序列保留，不能自动产生数值的两个4CH序列也保留在完整账本。
- S8的3167帧对应3003个相邻帧对。R2的720个直径数值与R3原始顶点表逐值相同。R3是同数据的新表达，不是新增患者、独立实验或新解剖证据。
- 冻结测试摘要明确记载历史提交 `83f4489`、`temporal=false`、`gate=false`、`beats=0`。这不能被当前代码存在平滑、门控或贴片条件流程替代。

### Missing materials affecting confidence

完整论文、预先指定主要终点及其接受标准、拟投稿类型未提供。文献包包含六篇研究的目录和逐图拆解，属于作者提供的二手研究笔记，本审查未读取这些论文的包外全文，因此不作完整优先权裁定。完整缓存、权重与独立临床参考未包含在包内，不能把图表及代码审查报告为临床复验。

### 展项覆盖与证据用途

下表中的目录均在 `snapshot/figures/` 下，图注为该目录的 `caption_en.md`。

| 科学展项 | 核对的主要源表或代码 | 可支持的证据用途 |
|---|---|---|
| Fig.1 `fig_01_data_workflow` | `source_data/cohort.csv`、`case_manifest.csv`、`reference_coverage.csv`，方法说明与历史 `pipeline.evaluate` | 500人、347/71/82划分及已实现链路；不是贴片系统完成图 |
| Fig.2 `fig_02_segmentation_validation` | `patient_metrics.csv`、`frame_metrics.csv`、`example_frame_metrics.csv`、`example_selection.csv` | 原坐标ED/ES分割表现，保留最低分失败；不是中间帧准确率 |
| Fig.3 `fig_03_function_agreement` | `agreement_pairs.csv`、`agreement_statistics.csv` | 82人同几何容积一致性和单独标签EF比较；不是独立容积验证 |
| Fig.4 `fig_04_half_sequence` | `frames.csv`、`expert_endpoints.csv`、`curve_statistics.csv` | 四个固定排名半序列的实际帧估计；不能验证整条真实容积轨迹 |
| Fig.R1 `fig_r01_lv_morphology` | `diameter_profiles.csv`、`image_display.json`、`example_selection.csv` | 两例轮廓与一例直径剖面；横轴不是对应解剖点 |
| Fig.R2 `fig_r02_systolic_dynamics` | `frame_geometry.csv`、`frame_diameters.csv`、`heatmap_cells.json` | 两例36帧及720个重复直径测量；没有组织跟踪或应变证据 |
| Fig.R3 `fig_r03_diameter_surface` | `observed_vertices.csv`、`mesh_facets.csv`、`sequences.csv`，`native_mesh` | R2同数值的三角面显示；不是三维心室或声场重建 |
| Fig.S1 `fig_s01_sv_ef_agreement` | `agreement_pairs.csv`、`agreement_statistics.csv` | 同几何SV/EF个体分歧；不能从相关性推论准确性 |
| Fig.S2 `fig_s02_phase_selection` | `paired_EF.csv`、`phase_offsets.csv`、`phase_statistics.csv`、`sequence_coverage.csv` | 有效配对的半序列选相位与偏移分布，覆盖率分开；不是完整心搏检测 |
| Fig.S3 `fig_s03_training_comparison` | `configuration_comparison.json`、`paired_patient_metrics.csv`、`paired_statistics.json`、`excluded_from_paired_ef.json` | 同初始化、同划分的两次历史训练描述；不是独立因素消融或多次训练重复 |
| Fig.S4 `fig_s04_quality_associations` | `patient_analysis.csv`、`quality_statistics.csv`、`associations.csv` | 患者级探索性质量关联；不能作因果或外部泛化结论 |
| Fig.S6 `fig_s06_geometry_coverage` | `source_geometry.csv`、`patient_geometry.csv`、`volume_paths.csv`、`panel_statistics.csv`，`mask_features` | 代理几何覆盖和计算路径差异；没有独立解剖或容积真值 |
| Fig.S7 `fig_s07_ef_reference_bias` | `ef_triplets.csv`、`bias_identity.json`、`agreement_statistics.csv` | 同82人的精确有符号差值恒等式；不能认作误差来源的因果分解 |
| Fig.S8 `fig_s08_observed_temporal_variation` | `all_observed_frames.csv`、`adjacent_changes.csv`、`example_step.json`、`sequence_summary.csv` | 真实存储顺序下的代理几何跳变；没有参考支持生理事件判断 |
| Fig.S9 `fig_s09_output_availability` | `patient_scope_availability.csv`、`sequence_ledger.csv`、`reverse_phase_sequences.csv`、`unpaired_metrics.csv` | 完整分母、失效和逆序边界；数值可用率不等于定位正确率 |
| Table 1 `table_01_cohort` | `patient_metadata.csv`、`sequence_metadata.csv`、`cohort_statistics.json`、`unavailable_evidence.json` | 500人现有队列及可用证据层级；不能代表贴片受试人群 |
| Table 2 `table_02_function` | `agreement_pairs.csv`、`agreement_statistics.csv`、`unavailable_metrics.json` | 五个范围明确的主要工程结果，患者bootstrap区间有来源 |
| Table S1 `table_s01_function` | `agreement_pairs.csv`、`agreement_statistics.csv`、`patient_scope_availability.csv`、`unpaired_metrics.csv` | 完整21组范围及不同n；不同几何/参考下的MAE不宜直接排名 |
| Table S2 `table_s02_segmentation` | `frame_metrics.csv`、`patient_stratum_metrics.csv`、`stratum_statistics.csv` | 同一82人的重叠分层，不是九个独立验证队列 |

10张历史图均位于 `snapshot/reports/result_analysis/camus_cuda_progress/`。它们与当前展项主要复用同一次测试，不计为十次新增实验。

| 历史图 | 核对源表与当前对应关系 | 判断 |
|---|---|---|
| `01_training.png` | `source_data/training.csv`，对应S3基线分支 | 验证选模epoch 7，单次训练 |
| `02_segmentation.png` | `structure.csv`，对应Fig.2及Table S2 | 相同82人按切面/相位分层 |
| `03_volume_agreement.png` | `agreement_pairs.csv`、`agreement_statistics.csv`，对应Fig.3容积 | 同几何参考已在图注声明 |
| `04_function_agreement.png` | 同上，对应S1与Table 2 | 同几何SV/EF，不是另一次验证 |
| `05_reported_ef.png` | 同上，对应Fig.3标签EF | 标签EF范围独立命名 |
| `06_phase_selection.png` | `paired_phase_errors.csv`，对应S2 | 配对n与方法总覆盖率分开 |
| `07_coverage.png` | `coverage.csv`，对应S9及各表缺失说明 | 无参考的0/82表示不可评价，不是零误差 |
| `08_examples.png` | `example_selection.csv`、`structure.csv`，对应Fig.2固定排名 | 最低分保留，无随机抽样主张 |
| `09_half_sequences.png` | `frames.csv`，对应Fig.4 | 实际半序列，无完整周期外推 |
| `10_error_associations.png` | `error_associations.csv`，对应S4 | 观察性关联，未声称因果 |

## Reviewer 2

### Overall assessment

现有材料最有价值的结果是一个可审计的公共数据工程基线，以及对“分割看起来不错”和“功能测量已经可靠”之间差距的实证展示。其长处是参考层级、失败覆盖、历史代码身份和原始帧顺序均较清楚。统计源表主要点估计能够复算，未见通过删去低分病例制造结果的迹象。

现有材料尚未建立新的贴片成像方法、连续监测系统或经过临床验证的心功能测量技术。原创性也主要停留在本项目的适配、结果组织和实现审计，尚无可据此认定的领域方法突破。S6至S8提供了比单报Dice更有用的问题定位，但覆盖不匹配、偏倚抵消与时序跳变目前是这个冻结实现的观察结果，不能直接提升为普遍生理规律或通用新方法。把这些发现写成清楚的工程基线与测量边界研究，是现有证据可承担的论文范围。

### Who would be interested in the results, and why

直接读者包括超声图像分割与心功能量化研究者、准备连接自研采集设备的工程团队，以及需要避免把同几何参考当成独立临床真值的复现实验人员。对这些读者，病例级溯源与失败分母有实际用途。

跨领域的吸引点是测量链路中共享算法偏差可能掩盖功能误差。S7的差值恒等式很好地说明了这个风险，但单中心公开数据、单个冻结几何实现、没有独立参考的现状，还不足以说明影响范围、临床收益或对广泛研究社群的显著技术推进。

### Major strengths

1. 患者级固定划分与实际历史实验配置有记录。`snapshot/checkpoints/camus_cuda_progress/run.json` 明确使用训练统计和验证选模，实际测试身份可追到 `83f4489`，避免将当前默认配置追认为历史设置。
2. 参考层级处理认真。专家同算法参考、Info.cfg标签、人工点和独立HR/CO缺失分开；HR/CO保持null。没有用拼接半序列制造完整周期。
3. 结果包含失败与失效范围。固定排名保留ES Dice 0.443病例，S9解释逆序与ESV大于EDV，完整源表使配对选择可复核。
4. 功能层面的负面结果没有隐藏。负predictive R²、宽LOA及偏倚抵消被保留，这对判断后续研究优先级比单独展示高Dice更有用。
5. R系列明确限制为描述性代理几何展示。720个数值没有被冒充为720个独立样本，也未把曲面称为三维解剖重建。

### Major Concerns

#### R2-M1 [claim-moderation]

**Severity** Major  
**Blocking** No  
**Axis** claim-moderation  
**Issue key** target-title-patch-continuous-scope  
**Claim pointer** 研究题目以贴片式探头和连续监测限定研究对象，而现有实证范围是公开经胸ED/ES半序列的冻结图像分析基线。  
**Evidence pointer** `READ_FIRST.md` 的作者研究背景；`snapshot/docs/patch_acquisition_workflow.md` 第4节及其待接入说明；Fig.1d、Fig.4图注；Table 1的 `source_data/unavailable_evidence.json`；`snapshot/runs/camus_cuda_progress/summary.json` 的 `beats=0`、`reference_file_sha256=null` 和 `gate=false`。  
**Evidence status** located  
**Concern** 贴片采集、设备到图像的标定、跨设备域偏移、完整周期和长期有效覆盖均未成为本包实测对象。逐帧计算约0.3 s的半序列，只建立了对这些帧执行算法的能力。R2/R3的更丰富显示也不增加时间跨度或独立参考。作者已在图注中清楚承认这一点，因此本意见不是指控图注虚称完成验证，而是指出目前证据与题目层面的完成性论证尚不匹配。  
**Why it matters** 贴片与连续监测正是应用层科学重要性的来源。缺少该层证据时，无法把公共图像基线性能直接转为佩戴监测收益、可用性或临床连续心功能测量能力。狭义基线结论仍然可成立，故本项不是阻断该结论的Blocking问题。  
**Resolution test** 若本阶段只报告现有结果，题目、副标题和结论应明确为面向贴片应用的CAMUS图像分析基线，并把贴片与完整周期链路标成后续目标。若保持“已建立贴片连续监测”的中心论点，则应提供真实贴片数据及受试者隔离方案、空间/真实时间依据、完整周期和相应独立参考、连续片段覆盖及失效记录。条件流程图或半周期延长显示不能替代这些证据。

#### R2-M2 [novelty-significance]

**Severity** Major  
**Blocking** No  
**Axis** novelty-significance  
**Issue key** incremental-baseline-no-demonstrated-method-advance  
**Claim pointer** 现有19个展项能否支撑具有独立方法原创性、性能推进或广泛科学重要性的论文定位。完整论文未提供，未将“新架构”“优于现有方法”写成作者已经作出的声明。  
**Evidence pointer** `snapshot/docs/measurement_protocol.md` 的“分割与关键点”“容积与功能”；`historical/83f4489/cardiac/model.py` 的 `build_model`、`train`；`snapshot/checkpoints/camus_cuda_progress/run.json` 的 `reproduction_scope`；Fig.S3的 `source_data/configuration_comparison.json`、`paired_statistics.json`；`snapshot/figures/planning/literature_breakdown.md` 的“这是为本研究选择图表证据的叙述性样本”及“本项目的可验证长处”。  
**Evidence status** located  
**Concern** 方法主体是已有DeepLabV3–ResNet50的CAMUS适配与既有容积公式，代理关键点是未训练的轮廓启发式。唯一训练配置比较为每配置一次历史运行，且同时改变增强、权重衰减和早停。其验证Dice从0.9021变为0.9036，同时共同70人的标签EF MAE从8.24变为9.83 pp。这个比较有助于记录工程过程，却不能分辨各因素作用，也未建立功能性能提升。所给文献工作详尽拆解图表组织，但并非本方法与最近工作的同口径定量定位。现有证据因此不足以认定原创方法推进或出众科学重要性。  
**Why it matters** 可复现性与诚实边界是研究质量基础，但它们本身不自动构成广泛的新科学结论。此处存在有价值的领域内工程贡献，尚未展示其相对于既有分割和功能分析链路的新增能力、可迁移洞见或显著收益。对明确定位为基线的毕业设计不必强加新架构要求，对方法创新或广泛影响的论文则需要额外论证。  
**Resolution test** 先明确贡献类型，并用与CAMUS分割、EchoNet式功能分析和贴片系统最接近的工作建立证据比较，至少列清输入、划分、训练来源、空间/时间依据、几何/参考口径和实际验证范围，避免跨数据集直接比较MAE。若主张方法性能推进，需以冻结方案设计合适对照、与所主张因素相符的消融及训练重复性证据，模型和几何选择只用训练/验证数据。若定位为可复现工程基线，则限制优越性和原创方法措辞即可，不要求为增加图表数量而进行无关模型竞赛。仅新增曲面或热图不满足该项。

#### R2-M3 [experimental-design]

**Severity** Major  
**Blocking** No  
**Axis** experimental-design  
**Issue key** proxy-geometry-physiological-estimand-unvalidated  
**Claim pointer** 图3、图4、R系列和表2所称的容积、直径及功能估计，能否成为生理量化进展的主要证据，而不只是同一代理算法的输出比较。  
**Evidence pointer** `historical/83f4489/cardiac/geometry.py` 的 `infer_landmarks`、`mask_features`、`biplane_volume`，与当前 `snapshot/src/geometry/mask_features.py` 同名函数及 `snapshot/src/geometry/volume.py`；Fig.S6的 `source_data/panel_statistics.csv`；Fig.S7的 `source_data/bias_identity.json`、`ef_triplets.csv`；Table 2的 `source_data/agreement_statistics.csv`；Fig.S8的 `source_data/example_step.json`。  
**Evidence status** located  
**Concern** 已提供材料明确承认代理几何未验证，而且给出了实质性失配。专家ED代理轴平均仅覆盖轮廓投影跨度68.37%，代理基底外仍有29.57%的轮廓面积；专家ED双平面容积与两单平面容积均值之比为0.441。实现中单平面使用完整清理后面积与该代理长度，圆盘法仅沿所推断心尖至代理基底采样。两个输出因此不是可直接互换的同一解剖体积估计。S7还显示G−L均值为+7.37 pp，P−G为−5.81 pp，两者相加得到较小P−L偏倚+1.56 pp。该恒等式证明抵消可能发生，但不能证明标签与几何的分歧都由这一个轴定义造成。S8的面积+1.1%、轴长−32.5%、容积+51.4%的单步变化同样说明时序曲线受到几何构造显著影响，尚无中间帧参考区分生理变化与构造跳变。  
**Why it matters** 这些不是图形美观问题，而是主要输出究竟测量什么的问题。相同几何应用到专家和预测轮廓可以很好地审计误差传递，却不能检验共享几何偏差。不同路径MAE更小也可能受数值尺度影响。当前结果足以展示实现边界，尚不足以把绝对容积、局部收缩形态或时间事件作为已验证的新生理测量结果。作者的限制说明是正确的，但限制说明不补足这条测量证据链。  
**Resolution test** 若保留当前冻结基线，中心结果应持续明确称为特定代理几何的数值输出及参考间分歧，不以双平面更小MAE证明几何优越，不把R系列解释为对应组织运动或真实解剖容积变化。若提出生理量化方法贡献，应先以人工解剖依据或有来源的独立容积/功能参考核验轴与覆盖约定，并在训练/验证范围确定规则，后续采用预先锁定评价。解释G−L时应保留标签、采集和几何等多种可能来源。无需更改本次冻结测试来“修好”已观察到的现象。

### Minor Comments

#### R2-m1 [writing-clarity]

**Severity** Minor  
**Blocking** No  
**Axis** writing-clarity  
**Claim pointer** Table 1图注把序列时长统一解释为观测的“ED-to-ES interval”。  
**Evidence pointer** `snapshot/figures/table_01_cohort/caption_en.md`；`snapshot/figures/table_01_cohort.py` 中 `half_sequence_duration_s=(frames-1)/fps`；Fig.S9的 `source_data/reverse_phase_sequences.csv` 中 `patient0068_4CH`、`patient0203_4CH` 和 `patient0217_2CH`。  
**Evidence status** located  
**Concern / Why** 计算的是首帧到末帧的正向存储时长，至少三个测试序列存储为ES→ED，不能把全部时长解释为舒张末期到收缩末期的经过时间。该问题不改变时长数值，但会让读者误以为所有序列都是收缩时段，与S8/S9的相位顺序说明不一致。  
**Resolution test** 将该行和图注表述为观测半序列时长或ED/ES端点之间的观测时长，注明原始顺序可能反向并引用完整相位顺序表，保留原始序列与数值。

#### R2-m2 [figures-and-tables]

**Severity** Minor  
**Blocking** No  
**Axis** figures-and-tables  
**Claim pointer** Fig.S9b的蓝色标记图例写为“Expert ED”“Expert ES”。  
**Evidence pointer** `snapshot/figures/fig_s09_output_availability/fig_s09_output_availability_preview.png` 的b面板及其图注；`source_data/example_trajectories.csv`；`snapshot/figures/fig_s09_output_availability.py` 的绘图文字。  
**Evidence status** located  
**Concern / Why** 标记位置是专家相位对应的预测容积，而不是专家轮廓计算的参考容积。图注已正确解释，但当前短图例容易让只看图的读者把68.95/75.32 mL误读为专家参考值，尤其同套图中洋红菱形经常代表专家同几何容积。  
**Resolution test** 图例改成“Prediction at expert ED/ES”或同等简短且明确的表述，数据和相位位置保持不变，使图内含义与图注一致。

### Technical failings that need to be addressed before the case is established

在作者已经限定的“冻结CAMUS工程基线描述”范围内，本审查没有识别出需要标记Blocking Yes的项目。R2-M1和R2-M3限制了向贴片连续监测及已验证生理量化的推论，R2-M2限制了原创方法和广泛重要性的论文定位。它们应通过相应证据或明确收窄中心论点处理，不能用图件数量或视觉表现代替。

### Assessment against Nature-style criteria

| 共同标准 | 判断 | 依据与边界 |
|---|---|---|
| originality | 领域方法原创性未由现有材料建立；本项目适配和审计工作有独立劳动价值 | 已有架构与几何公式为主体，尚无充分对照证明新能力；不能仅据缺少全文判定不存在其他创新或作完整优先权裁定 |
| scientific importance | 对工程复现和测量链路检查有用，出众科学重要性未建立 | S6至S8揭示具体实现风险，但未证明其普遍性、临床收益或广泛技术影响；贴片层证据待接入 |
| interdisciplinary readership | 直接受众明确，跨领域结论仍较局部 | 参考不独立、共享偏差及功能误差传递可能吸引医学AI和测量科学读者，但目前只是单实现证据 |
| technical soundness | 描述性基线的可追溯性较好，物理解剖有效性和连续监测能力仍开放 | 哈希、主要配对统计、历史代码和缺失分母可核；未复验完整原数组/模型，也没有独立容积或中间帧参考 |
| readability for nonspecialists | 图1的证据层级和图注边界清楚，完整论文可读性不可评价 | 应继续区分“相位标记”“专家同几何参考”“临床EF标签”；R3尤其须伴随其不是三维解剖或组织跟踪的解释 |

### Recommendation posture

**目前未由所给证据建立广泛原创性与重要性的研究主张；支持将材料定位为有明确边界的可复现工程基线。** 这不是对毕业设计或投稿的编辑决定。若期望中心结论仍是贴片连续心功能监测，应补足R2-M1所指的实际研究对象和时间证据，并处理R2-M3的测量有效性。若当前工作止于CAMUS基线，则应将研究题目、贡献和结论与已完成证据对齐，以真实分割、代理形态、功能一致性和观测时间过程组织结果，无需把所有展项改写成误差分析，也不应把新作图当作新增科学实验。

## Risk / unsupported claims

- 本审查未见明确的新架构或性能领先声明，也未见已完成贴片临床验证声明。不能把缺少完整论文当成这些声明已经出现。若未来采用这些表述，现包不能支持。
- 同几何EDV/ESV一致性不能成为独立绝对容积准确性的证明；P−L小bias不能代替个体一致性，S7也不是因果分解。
- 现有半序列、不同患者示例、分开采集的2CH/4CH和R3曲面，均不能支持长期连续、逐搏、同步双平面或三维解剖测量主张。
- 缺少完整论文、原始数组复验及包外文献全文使部分原创性、完整方法复现和全文可读性判断保持未评估。没有把这些未评估事项一律升级为缺陷。

本报告完成后以同名SHA256旁文件冻结。冻结后不因其他报告或综合意见改写。
