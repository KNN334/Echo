# 心功能结果图表制作清单（正文已确认，三维直径曲面新稿待反馈）

更新日期：2026-11-21。用户已确认正文4图2表、原补充候选及 `camus_cuda_progress` 主冻结实验，并选择 **1A/2A/3A/4A/5A**，随后确认样式测试页。用户纠正结果叙事后，已制作R1/R2形态与实际ED–ES候选图，并进一步明确同意绘制三维直径时空曲面。当前：**Fig.R3已制作并检查，等待本批反馈，见第17节；R1/R2仍待最终选稿，制作三维版本不等于确认旧图。** Fig.1–4与Table 1/2保持原确认状态；S1/S7尚未确认，后续顺序不以误差诊断为主。R编号为审阅编号，未增加正式正文总图数或修改共享样式。

本清单服务于“基于贴片式超声探头的心脏功能参数连续监测与分析”。当前实证范围是 **CAMUS 公开经胸超声上的 LV 分割及轮廓几何量化基线**。贴片连续佩戴是目标应用，尚无本项目佩戴实测证据。图表可以提高表达与可复核性；当前证据不足以支撑贴片连续监测、独立临床绝对容积验证或新算法全面优于同行的主张。

## 1. 交付索引与同行依据

- [结果资产清单](figures/planning/result_assets.md)：数据、分辨率、实验、已算/可补算/不可算指标及精确来源。
- [逐篇逐图逐表拆解](figures/planning/literature_breakdown.md)：Hu 2023、Ouyang 2020 两篇指定模板，以及 Chao 2025、EchoFM 2025、EchoPrime 2025 在线/2026 卷期、SAFU 2025 四篇补充全文，共 162 个图表条目。
- [文献结构化目录](figures/planning/literature_catalog.json) 与 [数量统计](figures/planning/literature_statistics.json)：图注摘录、图号、来源网址、核查范围与全文/附件校验记录。
- [本地资产机器核查](figures/planning/asset_inventory.json)：1,000 个缓存逐个解码、患者隔离、179 个既有冻结源文件校验；不是新增训练或临床验证。
- [完整可视化覆盖目录](figures/planning/visualization_coverage.md)：10类旧图去重映射、领域分析覆盖矩阵、扩展图表的参考/源数据/排版/分母/优先级及缺失实验证据。

六篇正文图中位数 **4，范围 3–7**；正文表中位数 **1.5，范围 0–9**。保留 **4 张正文图 + 2 张正文表**。本轮扩展提案为 **核心补充8图+2表，另3张有条件备选图**，形成完整分析资料库，实际投稿按期刊与主张选择子集。非正文图（扩展图+SI）中位数 6、范围 1–42，仅计算附件数量已知的 5 篇；EchoFM 独立 SI 未查明，保留 NA。新增数量是项目覆盖方案，非领域必需配额。

该样本是叙述性选择，不是领域普查，也不是期刊图数上限。SAFU 是血管可穿戴器件研究，只借鉴真实工况的验证组织，不作为 LV/EF 算法性能对照。框架与流程在 5/6 篇正文出现；分割定性样例、回归散点、Bland–Altman 和损失曲线的实际频率详见拆解报告，不能称为“每篇都有”。

## 2. 冻结数据与统计口径

**实验身份**：沿用已有冻结图集的 `camus_cuda_progress`，DeepLabV3–ResNet50，验证损失选定第 7/30 轮；不是本轮按测试分数重新选模。权重 `checkpoints/camus_cuda_progress/best.pt`，SHA256 `b0e8b724ca453c4801fb651163ad0353cec495c0a8d745ada1dbab9067b607c9`。最新 `camus_regularized_v2` 只有训练/验证，没有新测试结果，不替换或借用旧测试。

**单位与覆盖**：500 患者、1,000 切面、19,232 帧、2,000 个 ED/ES 标注帧；患者级 train/val/test=347/71/82，无交叉。主测试有 82 患者、164 切面、328 标注帧、3,167 全序列帧。处理图像均为 112×112。距离和几何量使用原坐标标定，不把处理图像套上原始 0.308 mm 间距。中间帧的空掩膜不是背景真值。

| 报告口径 | 参考来源与意义 | 有效数 / 使用约束 |
|---|---|---|
| 双平面 20 层、专家 ED/ES 相位 | 专家轮廓经同一几何法计算；**非独立临床金标准** | EDV/ESV/SV/EF 各 n=82；反映分割误差经同法几何传播 |
| 单平面面积–长度、专家 ED/ES 相位 | 各切面专家轮廓经同一面积–长度法计算 | 2CH EDV/ESV n=82、SV/EF n=81；4CH 四项 n=82 |
| 半序列自动极值选相位 | 在已存半序列预测内选极值，不叫完整心搏识别 | 2CH 四项 n=82，4CH n=80；与专家选相位配对交集为 2CH n=81、4CH n=80 |
| 双平面 EF 对 CAMUS EF 标签 | `Info.cfg` 数据集标签；可以写“对照临床标签”，不是本研究前瞻临床验证 | n=82，与同法轮廓参考 EF 严格分开；误差单位为百分点（pp） |
| HR / CO、真实人工关键点 | 当前无完整周期、可靠参考 HR/独立 CO、人工点标签 | n=0、null 并说明原因；不画 HR/CO 或人工关键点准确性图 |

主结果锚点：Dice 0.9119、ASSD 1.963 mm、HD95 4.811 mm；同法双平面 EDV/ESV/SV MAE 为 8.151/5.822/8.030 mL；同法 EF MAE 9.266 pp；对 CAMUS 标签 EF MAE 9.032 pp。须同时保留全分布和 LOA，不能据平均值宣称临床可替代性。

统计以患者为独立单位；同一患者两切面/两相位不能当作四位患者。分割主汇总先按患者聚合，再报告 n=82；分层子图注明各层患者数与标注帧数。功能每一口径单独配对、过滤并报告 n 和无效原因。bias 定义预测减参考，描述性 95% LOA=均值±1.96×差值样本标准差；LOA 不是置信区间或预设临床容许误差。r、r² 与预测 R² 分开命名。

## 3. 正文图表总清单（按叙事顺序）

状态指**数据就绪程度**，不表示图已制作。P1=正文核心；P2=建议补充；P3=有条件备选。

| 编号 | 拟定标题 | 对标参考图表 | 核心信息 | 状态 | 位置 / 优先级 |
|---|---|---|---|---|---|
| Table 1 | CAMUS 队列、患者划分与参考标签覆盖 | EchoFM Table I；EchoPrime Table 1 | 数据规模、有效参考及证据缺口均有明确分母 | ✅ 用户已确认，含零值可用性行修订；500患者/1000侧车统计核对 | 正文 / P1，随 Fig.1 首次引用 |
| Fig.1 | 当前验证数据与 LV 轮廓至心功能参数的分析流程 | Ouyang Fig.1；Hu Fig.5a；EchoPrime Fig.1 | 从公开半周期输入到分层参考评价的完整路径可追溯 | ✅ 数据现成可做 | 正文 / P1 |
| Fig.2 | 全测试队列的 LV 分割性能及低分与典型病例 | Ouyang Fig.2d/e；Chao Fig.1；EchoFM Fig.4 | 全队列分布与固定排名样例同时显示空间误差及失败边界 | ✅ 数据现成可做 | 正文 / P1 |
| Fig.3 | 双平面容积同法一致性与对照 CAMUS EF 标签的误差 | Ouyang Fig.2a；Hu Fig.5c；EchoPrime SI Fig.1 | 容积同法参考与 EF 标签验证是不同证据，均保留偏倚与离散程度 | ✅ 图中三口径配对统计已补齐并核对；当前几何局限保留，见自检 | 正文 / P1 |
| Table 2 | 两类参考下的主功能误差 | EchoPrime Table 2；EchoFM Tables IV/V 的分层数值组织 | 同法双平面四指标与CAMUS标签EF分别报告；其他口径见Table S1 | ✅ 用户已确认；五行各82患者，含MAE区间/RMSE/bias/LOA/r/预测R² | 正文 / P1，随 Fig.3 首次引用 |
| Fig.4 | 从 ED 到 ES 的真实半周期容积轨迹与相位覆盖边界 | Ouyang Fig.2f；Hu Fig.5b 的时序结构，**仅借鉴排布** | 现有数据展示半周期内的逐帧变化，完整逐搏及 CO/HR 尚不可评价 | ✅ 数据现成可做 | 正文 / P1 |

### Table 1：队列与标签覆盖

- **源数据**：`data/processed/camus/manifest.json`、`configs/camus_splits.json`、1,000 个病例 JSON；`figures/planning/asset_inventory.json`；`reports/result_analysis/camus_cuda_progress/source_data/coverage.csv`。
- **排版**：一张表，train/val/test/合计四列；患者数、切面数、总帧数、ED/ES 标注数、2CH/4CH、官方图像质量、帧率/半序列时长、空间尺寸分行。按用户反馈，不把六类缺失证据的全零计数作为队列特征行；CAMUS EF标签覆盖并入患者区块，缺失证据及ROI未审阅写在表注。训练与验证分层帧数从 manifest 分组汇总，不按比例推算。
- **注释**：原始数据全量仅有历史清单，本地 1,000 切面缓存完整是本次实核结论；人工 ROI 审阅均为 false。尚无贴片、EchoNet 本项目外部评价或人工关键点。本轮只读核对500患者的Age/Sex/EF字段齐全且两视图一致，可按固定划分汇总真实年龄、性别和EF；不推定不存在的病种或临床容积标签。

### Fig.1：数据与方法框架

- **源数据**：上述队列来源；`configs/model/deeplabv3_resnet50.yaml`、冻结实验配置与 `checkpoints/camus_cuda_progress/training.csv`；`src/data/camus/prepare.py`、`src/data/transforms.py`、`src/geometry/`、`src/engine/evaluator.py` 中的实际处理链；`runs/camus_cuda_progress/*_features.json` 和 `function.csv`。沿用旧 `figures/camus_method_flow.*` 的可核对结构，不沿用尚未批准的样式。
- **排版**：a 左上为当前 CAMUS 数据和固定患者划分；b 上方为 2CH/4CH ED→ES 输入与预处理/坐标还原；c 中部横向为 DeepLabV3–ResNet50→LV 轮廓→面积/长轴/20 层盘径→单平面/双平面参数；d 底部为三种参考层级及可算/缺失输出。以流程为主，不伪装成新架构创新。
- **边界**：目标贴片场景若需要出现，只作分离的小框“目标应用，尚未实测”，不得用箭头暗示贴片实测数据已流入 CAMUS 验证。主链只输出 EDV/ESV/SV/EF；HR/CO 以缺失说明出现，不画输出数值。

### Fig.2：空间分割验证与病例

- **源数据**：`runs/camus_cuda_progress/structure.csv`、164 个 `*_pred.npz`、对应处理帧与 `original_gt`/侧车坐标；`source_data/structure.csv`、`example_selection.csv`（该目录完整前缀为 `reports/result_analysis/camus_cuda_progress/`）。
- **排版**：a–c 顶排三个量化面板为 Dice、ASSD、HD95，以患者点与分布为主，并用切面/相位分层作辅助；d 底部为 **2 行（ED/ES）×4 列（固定排名病例）**的影像+专家/预测轮廓。每格注明视图、相位和对应指标，保留比例或尺度信息。
- **固定选择**：沿用旧图集已记录的 Lowest/Q1/Median/Q3，不重新按外观挑例：`patient0229_2CH`（1/164）、`patient0189_4CH`（42/164）、`patient0327_2CH`（83/164）、`patient0075_4CH`（123/164）。最低排名病例必须保留；这些是按病例 ED/ES 平均 Dice 排名，不能说成独立患者四分位随机样本。
- **补算边界**：主图已有三项指标即可制作。IoU 和新的患者区间如需要，作为显式补算再导出；不能把平均 Dice 直接换算为平均 IoU。轮廓派生代理点不进入人工点准确性图。

### Fig.3：功能参数一致性

- **源数据**：`runs/camus_cuda_progress/function.csv`、`summary.json`；`reports/result_analysis/camus_cuda_progress/source_data/agreement_pairs.csv` 与 `agreement_statistics.csv`。从原始配对重算，校验既有 82 人汇总及源文件哈希。
- **排版**：**2×3**，三列分别为 EDV（同法双平面参考）、ESV（同法双平面参考）、EF（CAMUS 标签）；第一行预测–参考散点与恒等线，第二行对应 Bland–Altman。容积两列和 EF 标签列分区标明参考性质，mL 与 %/pp 不共用轴。图上优先标 n、MAE、r 和 bias/LOA；RMSE 与预测 R² 在表中完整报告，避免挤满面板。
- **一致性**：散点横纵轴在同一指标内等范围、等比例；BA 横轴为两测量均值，纵轴为预测−参考。容积和 EF 的量纲不同，不强行统一数值范围。全部 82 患者点保留，不删极端值，也不凭测试分布添加“临床合格区”。
- **移出材料**：SV 与同法轮廓参考 EF 的完整 BA/散点放 Fig.S1；这些结果仍列入正文 Table 2，避免只展示较好的 EF 口径。

### Table 2：主功能误差（全部口径另见Table S1）

- **源数据**：同 Fig.3；补充 `paired_phase_errors.csv`、`runs/camus_cuda_progress/summary.json:function`。
- **排版**：正文按“专家轮廓同法双平面四指标”和“对CAMUS临床EF标签”两区，共五行；列为n、MAE [95% CI]、RMSE、bias、95% LOA、r、预测R²。单平面2CH/4CH及自动极值明细安排于Supplementary Table 1，不压缩字号强塞。
- **统计**：不同指标独立核对有效 n；MAE 的患者 bootstrap CI 已有来源时沿用并注明算法。ICC 只有确定模型、绝对一致性/一致性、单次/平均及区间算法后才新增，不能为凑指标选择更好看的定义。HR/CO 用 null 与原因脚注保留，不填 0 误差。

### Fig.4：真实半周期过程

- **源数据**：`runs/camus_cuda_progress/frames.csv`、同病例 `*_features.json`、缓存侧车帧率与 `phases`；Fig.2 固定排名样例。
- **排版**：**2×2 病例面板**；每格为单切面面积–长度容积（mL）随派生时间（s）的逐帧轨迹，标注有效起止、专家 ED/ES 帧与各自同法参考点。边缘可用同病例 ED/ES 小叠图辅助解释，不能挤压坐标字号。
- **边界**：2CH/4CH 不是同步采集，不能做逐帧同步双平面曲线。中间帧没有专家真值，只能展示预测过程；两个专家端点不连成“真值轨迹”。不反射、不拼接、不假设收缩占比、不外推整搏；缺失/无效处留断点。时间注明由 FPS 派生。图名与图注不使用连续佩戴、逐搏真值或 CO/HR 波形措辞。

## 4. 扩展补充材料清单（范围已确认，分批制作）

每项的精确参考图、真实源文件、排版、分母、科学信息及补算内容，统一见[完整覆盖目录第5–6节](figures/planning/visualization_coverage.md)。沿用原S1–S5身份，避免与旧清单混号。

| 编号/标题 | 数据和布局摘要 | 核心信息 | 就绪状态 | 位置/优先级 |
|---|---|---|---|---|
| Fig.S1 同法双平面SV与EF完整一致性 | function配对，2×2散点/BA，各82患者 | 同法EF不能被标签EF替代 | ✅ 已制作/复核，含预测R²源表；待本批反馈 | 核心补充/P1 |
| Fig.S2 半序列自动ED/ES定位与功能误差 | 功能/相位CSV，2×2，交集2CH=81/4CH=80 | 自动相位改变误差和覆盖，非整搏识别 | ⚠️ 分母和派生秒复核 | 核心补充/P1 |
| Fig.S3 验证选模与组合正则化 | 两份training.csv和验证结果，2×2损失/ΔDice/ΔEF误差 | 分割改善不代表标签EF改善，变差如实保留 | ⚠️ 验证71/EF共同70及权重配对 | 核心补充/P2 |
| Fig.S4 质量分层及分割—功能误差关联 | 质量/structure/患者EF误差，2×2 | 高Dice不保证EF准确；仅域内探索 | ✅ 部分现成；⚠️ 患者联表 | 核心补充/P2 |
| Fig.S6 几何覆盖和容积路径差异 | geometry_diagnostics/cross_geometry_volume_ratios，2×2 | 代理轴/基底覆盖不一致，不是人工点定位精度 | ✅ 诊断；⚠️ 误差联表 | 核心补充/P1 |
| Fig.S7 两类EF参考与偏倚抵消 | 预测/专家同法/标签三方，2×2 | 小bias部分来自抵消，非准确性充分证据 | ✅ 已制作/复核，82完整三方源表；待本批反馈 | 核心补充/P1 |
| Fig.S8 全半序列时序质量和真实跳变 | 164序列/3167帧，2×2分布/联动/轨迹/帧 | 数值有限不代表生理稳定，不补造整搏 | ✅ 诊断；⚠️ 相邻差值 | 核心补充/P1 |
| Fig.S9 覆盖与真实无效案例 | coverage/function及0072/0068/0203原帧，2×2 | 技术执行、几何有效、参考和临床分母不同 | ✅ 数据；⚠️ 病例联表 | 核心补充/P1 |
| Table S1 完整功能口径和无效原因 | 全部21组统计，按几何/视图/相位/参考分区 | 全量结果及null原因可追溯 | ✅ 主要统计；⚠️ 其余R²/交集 | 核心补充/P1 |
| Table S2 空间指标完整分层 | Dice/IoU/ASSD/HD95/HDmax，82患者/328帧 | 次要指标完整而不重复占正文 | ⚠️ 逐帧IoU再患者聚合 | 核心补充/P2 |
| Fig.S5 规范效率 | 网络/几何/总流程、参数量/显存 | 历史21.13FPS仅含I/O端到端 | ⚠️ 需规范基准测量 | 有条件备选/P3 |
| Fig.S10 空间错误位置 | 真掩膜FP/FN/mm边界距离，2×2 | 展示错在哪里，不制造概率场 | ⚠️ 需补算；与Fig.2去重 | 有条件备选/P3 |
| Fig.S11 全功能口径误差总览 | 四指标分面，每口径MAE/患者区间 | 扫描全结果，不把不同几何参考用于排行榜 | ⚠️ 核对区间/n；可由Table S1替代 | 有条件备选/P3 |

可选动态材料M1只播放真实ED–ES帧，不往返/接缝循环，不把专家端点补成中间真值。无独立概率场时不做概率校准图；无人为重复测量时不做观察者重复性。所有扩展仍受第5节缺失证据约束。

Fig.S3不称单因素消融；两历史实验测试集均已评价，不能由本次图表反馈继续挑模型/调参。Fig.S6–S8解释的几何、参考和时序问题会改变结论，正文必须写明并引用，不能只藏在附件。新增方案在训练/验证上定义，并安排独立最终评价。

## 5. 缺失结果：不列入当前可制作图件

| 主题 / 原可借鉴图 | 当前状态 | 建议 |
|---|---|---|
| 新架构方法优势：Chao Tables 1/2、EchoFM Fig.4/Table IV | ❌ 无相同患者划分与统一训练条件下的 U-Net/nnU-Net 等配套结果 | 当前只报告可复现基线与几何口径对照，不画跨论文数值排行榜；若补实验，先定训练/验证方案及独立最终评价安排 |
| 真正单因素消融、标签预算、多随机种子：EchoFM Figs.6/7、Tables VIII/IX | ❌ 缺对应结果 | 不用两种组合训练方案代替；按科学问题补实验后再决定是否进入正文 |
| 外部泛化：Ouyang Fig.2b、EchoFM Table V、EchoPrime Fig.2 | ❌ 缺 EchoNet、跨设备/跨中心/贴片外部评价 | 2CH/4CH 与 Good/Medium/Poor 是 CAMUS 域内分层，不改名“外部泛化” |
| 贴片连续与工况事件：Hu Figs.4/5e–h、SAFU Figs.3/4 | ❌ 无本项目佩戴影像、运动/恢复长时记录或连续独立参考 | 只在框架中区分目标场景与当前证据；不制备恢复期、运动期或24小时监测图 |
| HR/CO 及其误差：Hu Fig.5b/c/g/h | ❌ 当前不可计算 | 保持 null 与原因；不得双倍收缩时长估 HR、用预测 SV 倒推 HR/CO、反射半周期或合成波形 |
| 真解剖关键点定位与临床 EDV/ESV 金标准 | ❌ 缺人工点及独立容积参考 | 不画关键点人工误差；同法专家轮廓参考明确命名，不升级为独立临床金标准 |
| EF 阈值分类 / AUC / 混淆矩阵 | ❌ 当前未开展预定义分类任务 | 不为补齐图表类型临时在测试集选阈值；如另立分类问题，先明确标签定义与分析方案 |

## 6. 后续制作约定与进度

| 阶段 | 状态 | 下一步条件 |
|---|---|---|
| 1 资产盘点 | 已整理，附机器核查 | 用户可指出漏掉的实验/路径 |
| 2 模板、补充检索与规律 | 已整理，两篇模板已确认 | 仅引用实际读取到的全文/附件；EchoFM SI保留未知 |
| 3 清单 | **原范围及扩展清单已确认** | 正文4图2表；核心补充8图2表，另3张有条件备选 |
| 4 视觉主题 | **用户已确认，2026-11-21** | 已选1A/2A/3A/4A/5A；全局样式与真实数据测试页保留 |
| 5 分批制作 | **Fig.1–4、Table 1/2均已确认；Fig.S1/S7待本批反馈** | S1/S7已检查并交付；确认后再做S2/S8，其余补充尚未制作 |

最终尺寸、色系、色带、方法配色及Nature规格已在阶段 4 选定并写入共享样式；新投稿图均调用该样式。

本轮核查：1,000 个处理后缓存逐个解码通过，179 个既有冻结源文件哈希全部匹配，164 个预测掩膜维度匹配，患者划分无交叉；6 篇全文及4个已取得附件的哈希、162个图表条目的数量/作用分类核对通过。项目核心工程检查 39 项通过；工程检查不等于临床验证。

以后每张图均需：全局样式调用；有效数和缺失原因；单位与定义；最终尺寸最小字号 ≥7 pt；相同比较的范围统一；影像注明视图/ED/ES/轮廓；患者为统计单元；保留低分与极端值；可复跑来源及独立脚本；英文图注；最终尺寸可读性、面板对齐与文字碰撞检查。若数据否定计划，先报告并更新本清单，不能悄悄换病例或调参数。

## 7. 阶段 4：视觉主题选项（用户已选择五项A）

下面保留各选项的说明；用户已选择1A/2A/3A/4A/5A并确认测试页，A方案已写入全局样式。使用 Python/Matplotlib。白底，超声保留灰度；二值分割用离散轮廓，连续色带仅用于有来源的连续量。

### 7.1 主色系

| 选项 | 色值（从主方法到辅助色） | 预览说明与依据 |
|---|---|---|
| A 推荐：蓝–橙 | `#0072B2`、`#E69F00`、`#009E73`、`#CC79A7` | 深蓝主线、橙色对比、青绿/紫红辅助；借鉴 Hu/Ouyang/Chao 的蓝橙对比关系，采用 Okabe–Ito 色盲友好色值，不声称是论文原始 hex |
| B 紫–青绿 | `#AA4499`、`#44AA99`、`#88CCEE`、`#DDCC77` | 紫色主方法、青绿对照、浅蓝/沙黄辅助；Paul Tol muted 子集，适合较柔和的影像与统计混排 |
| C 橙红–蓝 | `#D55E00`、`#0072B2`、`#009E73`、`#CC79A7` | 橙红主方法、蓝色对照；Okabe–Ito 子集，主方法在灰度超声与白底统计中更醒目 |

定量图均以线型、点形及文字冗余区分；后续测试页检查色觉差异与灰度可辨性，不仅依赖红绿差别。

### 7.2 连续 / 发散色带

- A 推荐：`cividis` + Scientific Colour Maps `vik`。蓝→黄的顺序量，蓝→浅中性→红的带符号误差。
- B：`viridis` + cmocean `balance`。紫→青绿→黄；蓝→浅中性→红。
- C：Scientific Colour Maps `batlow` + `broc`。较柔和多色顺序量；蓝→浅中性→棕的误差。

发散色带以0居中，比较子图采用相同对称范围；不使用 jet/rainbow。当前没有概率场时不制造概率图。

### 7.3 固定方法配色与强调程度

主实验为“当前方法”，组合正则化为已有变体，不包装成新架构。几何法/相位用分面、点形或线型辅助编码，不能把参考标签当成另一预测模型。

- A 推荐：各实验使用所选色系中的固定不同颜色，主实验用第一色并增加线宽/点权重；全图保持同一映射。
- B：主实验用第一色，其余实验用固定且可区分的灰阶与点形；主结果最突出。
- C：各实验固定不同颜色，主实验用实心点、其余实验空心点，线宽相同；较密集散点的遮挡更少。

### 7.4 目标图件规格、字体与最终尺寸

| 选项 | 字体 / 最终字号 | 宽度与来源范围 |
|---|---|---|
| A 推荐：Nature / Arial | 普通文字7 pt，分图标号8 pt粗体 | 单栏89 mm、双栏183 mm，官方明确尺寸；分图裸字母 a/b；所有图中文字仍≥7 pt |
| B：Nature / Helvetica | 普通文字7 pt，分图标号8 pt粗体 | 同A，需核对本机实际字体可用性，不能静默替代 |
| C：npj Digital Medicine / Arial | 8 pt，包括分图标号 | 官方建议按预期发表尺寸、8 pt、适应A4页宽；本次读到的指南未给固定单/双栏mm。提出89/180 mm作为制作选择，不能称为该刊官方栏宽 |
| D：IEEE TMI / Times New Roman | 9–10 pt | IEEE通用图件指南给出最大宽182 mm，具体单/双栏按TMI模板核定后制作；不得照套Nature栏宽 |

若目标另有期刊，用户可给期刊名，再查询该刊要求后确定；目前不推断实际投稿目标。Arial/Helvetica是否安装在开始渲染前核对。

### 7.5 输出包

- A 推荐：可编辑矢量 PDF + 600 dpi TIFF + 600 dpi PNG。
- B：A + 矢量 EPS；EPS 对半透明叠加支持有限，必要时仅影像/透明层栅格化，文字与轮廓保持矢量。
- C：A + 可编辑 SVG，便于后续逐对象调整；字体仍需保留或嵌入。

600 dpi 是交付母版设置，不提高112×112源图的信息分辨率。若选择Nature，正文使用可编辑矢量；Extended Data另导出符合该刊≤300 ppi、≤10 MB要求的投稿副本，600 dpi母版保留。若选择TMI，需要按其政策重排补充候选：该刊不接收扩展论文式的补充文字/图文文档，不能原样提交当前SI图包。

### 7.6 本轮核查的官方指南

访问日期：2026-11-20。以下只作为图件规格来源，色系是本研究的设计提案。

- [Nature final submission](https://www.nature.com/nature/for-authors/final-submission)：生产阶段尺寸89/183 mm、普通文字5–7 pt、标号8 pt、Extended Data规则；初投稿与生产阶段要求分开。
- [Nature research figure specifications](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/)：可编辑矢量、字体、色盲可读性、图像分辨率及禁止装饰性效果。
- [npj Digital Medicine submission guidelines](https://www.nature.com/npjdigitalmed/for-authors-and-referees/submission-guidelines)：Arial/Helvetica、最适字号8 pt、RGB、至少300 dpi；未给固定mm栏宽。
- [IEEE graphics file formatting](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/file-formatting/)：推荐字体包括Arial/Helvetica/Times New Roman、约9–10 pt、最大宽182 mm、可用格式与字体嵌入。
- [TMI instructions to authors](https://ieeetmi.org/authors-instructions/)：双栏模板、图件嵌入正文、补充文档类型限制。

## 8. 已制作的样式测试页

- [全局样式](style/paper.mplstyle)、[固定配色与导出](style/palette.py)、[样式说明](style/README.md)、[绘图依赖](style/requirements.txt)。所有后续新图必须调用，不在单图另设颜色或字号；旧历史产物保持原有溯源。
- [测试页预览](figures/style_test/style_test_preview.png)、[可编辑PDF](figures/style_test/style_test.pdf)、[600 dpi PNG](figures/style_test/style_test.png)、[600 dpi TIFF](figures/style_test/style_test.tiff)。尺寸183×145 mm，Arial普通文字7 pt、分图8 pt。
- [独立复现入口](figures/style_test.py)、[真实源数据](figures/style_test/source_data/)、[来源校验](figures/style_test/provenance.json)、[英文图注](figures/style_test/style_test.caption.md)、[检查说明](figures/style_test/QA.md)。
- 四组件：固定色卡+cividis/vik；最低排名病例18帧真实半周期曲线；同病例ES轮廓失败示例（Dice0.443）；82患者已有双平面容积MAE及患者bootstrap区间。仅为样式审阅，没有新增训练、推理或科学评价。
- 检查：实际PDF字体嵌入与7 pt下限、物理尺寸、定量面板对齐、文字碰撞均通过；色觉与灰度诊断在 `figures/style_test/qa/`。通用单文件静态扫描不能追踪导入的样式与导出，相关误报保留并用实际文件核实，见QA说明。

样式测试页已于2026-11-21获得用户确认，进入每批1–2张的制作流程。

## 9. 第一批交付：Fig.1 与 Fig.2

| 图件 | 交付与来源 | 实际制作及检查 | 当前状态 |
|---|---|---|---|
| Fig.1 | [PDF](figures/fig_01_data_workflow/fig_01_data_workflow.pdf) · [预览](figures/fig_01_data_workflow/fig_01_data_workflow_preview.png) · [独立脚本](figures/fig_01_data_workflow.py) · [英文图注](figures/fig_01_data_workflow/caption_en.md) · [QA](figures/fig_01_data_workflow/QA.md) | 183×163 mm；a队列与患者划分、b真实配对ED输入、c实际推理/几何链、d参考层级与缺失输出；b使用同患者2CH/4CH ED图作输入示意，ED–ES半序列范围写明。未绘制新的模型结构或贴片数据箭头 | **用户已确认，2026-11-21** |
| Fig.2 | [PDF](figures/fig_02_segmentation_validation/fig_02_segmentation_validation.pdf) · [预览](figures/fig_02_segmentation_validation/fig_02_segmentation_validation_preview.png) · [独立脚本](figures/fig_02_segmentation_validation.py) · [英文图注](figures/fig_02_segmentation_validation/caption_en.md) · [QA](figures/fig_02_segmentation_validation/QA.md) | 183×170 mm；全部82位患者均值及328标注帧；下排固定4病例×ED/ES。8幅影像统一270×200 mm视野，保留物理比例、20 mm尺及最低病例ES失败。8帧三项指标从掩膜重算均匹配原CSV | **用户已确认，2026-11-21** |

两图输出目录均含同名600 dpi RGB PNG/LZW TIFF、`source_data/`、`provenance.json`、面板对齐与字体/碰撞/色觉检查。英文图注分别225/232词。Fig.2仅新增患者级描述性聚合（四帧均值、跨患者样本SD及分布），没有新增推理、bootstrap、检验或置信区间。完整源文件SHA256保留，既有冻结来源逐一核对匹配。

最终实际PDF字体全部嵌入Arial，最小7 pt；面板对齐通过1.5 pt容差检查。Fig.1碰撞0 FAIL/0 WARN；Fig.2碰撞0 FAIL/2 WARN，均为20 mm标签横跨原始影像与黑色补边的预期叠放，已逐项视觉核查。单文件静态扫描不追踪共享样式与导出，保留原始提示，并以实际文件核实其误报；未冒称静态扫描全部通过。

本批项目规定的核心工程检查：`python -m pytest -q --basetemp=.work/pytest-figures-batch01-20261121`，39项通过（7.28 s）。这只验证工程一致性，不等于新增临床验证。

用户已确认第一批Fig.1/2并要求继续；该停止点已解除，当前停止点见第二批交付。

## 10. 2026-11-21 数据结果自检（用户追加要求）

[完整报告](reports/result_integrity/camus_cuda_progress_20261121/report.md)及[复算入口](figures/planning/audit_results.py)。179个冻结来源匹配；全部328标注帧分割距离/重叠、3,167帧已存特征/公式、490功能行复算无硬性不匹配。分割统计可保留，未排除低分。

**新增主要问题：代理基底线/长轴使两条几何路径覆盖范围不一致。** 专家ED轮廓的代理长轴/完整轮廓投影跨度中位69.35%，28.70%轮廓面积在代理基底线之外；单平面用全面积、双平面只积短长轴。预测双平面EDV与两单平面均值之比中位0.449。此诊断不是人工解剖点误差，不代表已确定临床正确几何。

专家轮廓同法EF对CAMUS标签本身MAE7.88 pp、bias+7.37 pp；模型对该几何参考bias−5.81 pp，部分抵消后对标签bias+1.56 pp。模型对标签EF MAE9.03 pp、RMSE11.12 pp、r0.663、LOA−20.15～23.28 pp，不能用小bias宣称准确。110/164条半序列至少一处相邻容积变化>20%（探索诊断阈值，不是临床失败定义）；代理轴跳变有明确实例。

自检当时建议先复核几何定义；**随后用户确认Fig.1/2并明确要求继续制图**。本次据此继续如实呈现冻结基线，保留全部已知局限；不把继续制图解释为几何问题已解决。Fig.3/Table 2不能主张独立临床容积准确性，Fig.4不能宣称稳定逐搏/连续佩戴监测。不调整旧结果、不选更好看的测试参数；若修几何，先在训练/验证数据确定定义及规则，另立版本并安排独立最终评价。

## 11. 第二批交付：Fig.3 与 Fig.4

| 图件 | 交付与来源 | 实际制作及检查 | 当前状态 |
|---|---|---|---|
| Fig.3 | [PDF](figures/fig_03_function_agreement/fig_03_function_agreement.pdf) · [预览](figures/fig_03_function_agreement/fig_03_function_agreement_preview.png) · [独立脚本](figures/fig_03_function_agreement.py) · [英文图注](figures/fig_03_function_agreement/caption_en.md) · [QA](figures/fig_03_function_agreement/QA.md) | 183×170 mm；2×3散点/BA，EDV/ESV同法轮廓参考与CAMUS标签EF分开；每列82患者，无剔除；原始配对、MAE/r/bias/LOA逐项复核，RMSE及两种R²定义另存源表。明确当前几何覆盖范围问题，未修改模型/几何/预测 | **用户已确认，2026-11-21** |
| Fig.4 | [PDF](figures/fig_04_half_sequence/fig_04_half_sequence.pdf) · [预览](figures/fig_04_half_sequence/fig_04_half_sequence_preview.png) · [独立脚本](figures/fig_04_half_sequence.py) · [英文图注](figures/fig_04_half_sequence/caption_en.md) · [QA](figures/fig_04_half_sequence/QA.md) | 183×170 mm；2×2固定病例，共4患者76帧；统一时间/容积范围，全部有效原始帧与2个专家端点；原始跳变、不一致和高容积病例均保留；仅画到各自ES，不补造完整心搏、不画CO/HR | **用户已确认，2026-11-21** |

两图均含PDF、600 dpi RGB PNG/LZW TIFF、`source_data/`、`provenance.json`及字体/尺寸/面板对齐/碰撞/色觉检查。英文图注分别232/235词。实际嵌入Arial最小7 pt，1.5 pt面板对齐通过；最终PDF碰撞两图均0 FAIL/0 WARN。单文件静态扫描无法追踪共享样式/导出，原始提示保留，实际文件核实详见QA，不声称静态扫描全通过。

本批核心工程检查：`python -m pytest -q --basetemp=.work/pytest-figures-batch02-20261121`，39项通过（7.88 s）。四张正文图全部已记录来源哈希继续匹配；未改第一批图件或原始冻结结果。

正文四张图均已确认；Table 1/2已于后续第三批制作，见第12节。补充图表待逐批制作。所有功能图继续限定为现有工程基线，不等于已修复几何问题或完成临床验证。

第二批停止点已由用户“没问题”解除；当前新增范围的停止点见第12节。

## 12. 结果分析可视化完整覆盖审计（用户追加要求）

用户询问“当前是否只有这几张图，需要结果分析可视化齐全完备”。结论是：项目已有 `reports/result_analysis/camus_cuda_progress/` 的10类旧分析输出，当前统一样式的正文图只是其中已重制的4张；另外结果完整性审计新增了几何覆盖、跨几何比值、半周期跳变和无效原因等诊断。为避免旧图与新图重复，已建立[结果分析可视化覆盖审计](figures/planning/visualization_coverage.md)，将所有结果映射为正文、补充材料和内部质控三层。

更新后的建议集合：**正文4图+2表，核心补充8图+2表，另3张有条件备选图及可选真实半序列动态材料**。内部4类质控单独留记录。正文仍与同行中位数相当；补充资料库覆盖现有分析主题，但不表示缺失临床/外部/贴片证据已补齐。不制作HR/CO、人工点准确性、临时疾病分类、外部泛化、跨论文排行榜或真正单因素消融，因为现有数据不支持。

新增完整清单的关键项目包括：

- S1/S2：SV与同法EF一致性、自动相位与误差；S3/S4：训练/组合方案与质量分层，保留原编号身份；
- S6/S7/S8/S9：几何覆盖、两类EF参考/偏倚抵消、时序跳变、覆盖和真实功能无效案例；
- Table S1/S2：全功能口径/无效原因、全分层空间指标（需补逐帧IoU）；
- S5/S10/S11为备选：规范效率、空间错误位置、全功能误差总览；无新增信息时不重复画表中数据。

用户随后回复“继续”，扩展清单已确认；本轮据此完成Table 1/2，当前停止点见下。

## 13. 第三批交付：正文Table 1/2（已确认，含零值行修订）

| 项目 | 交付与检查 | 状态 |
|---|---|---|
| Table 1 | [PDF](figures/table_01_cohort/table_01_cohort.pdf) · [可编辑表](figures/table_01_cohort/table_01_cohort.md) · [英文图注](figures/table_01_cohort/caption_en.md) · [QA](figures/table_01_cohort/QA.md)；183×145 mm，固定347/71/82患者；22行真实队列数据，已按反馈移除六行全零证据计数，原因移至表注 | 用户“继续”确认修订，2026-11-21 |
| Table 2 | [PDF](figures/table_02_function/table_02_function.pdf) · [可编辑表](figures/table_02_function/table_02_function.md) · [英文图注](figures/table_02_function/caption_en.md) · [QA](figures/table_02_function/QA.md)；183×112 mm，五行各82患者，410个患者–指标配对；含冻结MAE患者区间、RMSE、bias、LOA、r及预测R² | 用户“继续”确认，2026-11-21 |

Table 1直接核对1000侧车及500个患者记录，独立计数/四分位数复核一致，无缺失插补或排除。Table 2从原始function.csv重算点统计，核对冻结配对、既有统计及审计；保留2000次患者bootstrap、seed 2026的既有MAE区间，未重选区间。预测R²严格为1−SSE/SST(reference)，SV−0.002、同法EF−0.041如实保留；标签EF r=0.663、预测R²=0.189，不能互换。

两表使用全局样式，嵌入Arial/Arial Bold，可编辑PDF及RGB600 dpi PNG/LZW TIFF，实际最小字7 pt；单元格均在列边界内，最终PDF碰撞各0 FAIL/0 WARN。单表不含可比较面板，对齐记录为NOT APPLICABLE。共享样式/导出不能被单文件静态扫描跟踪的限制已保留原报告并在QA说明，不声称静态扫描全通过。既有四图49个不同来源哈希继续匹配。

本批项目核心检查39项通过（7.56 s），README目录核对通过；工程检查不代表临床验证。

几何覆盖问题、同法参考非独立临床标准及偏倚抵消风险均保留。HR/CO为null、n=0并列原因。用户反馈后，Table 1删除独立容积、人工点、完整周期、HR/CO参考、贴片采集、ROI人工审阅六行全零可用性计数；原因逐项核实并保存，不再把缺失证据计数当作队列特征。22行真实数据不变、三份队列源表内容一致（忽略Git换行编码差异）、全部患者保留，相关限制在表注保留。Table 2未改动。

Table 1修订后重新完成PDF字体/碰撞与逐行对照检查；183×145 mm，实际最小字7 pt，碰撞0 FAIL/0 WARN；项目核心检查39项通过（7.60 s）。

第三批停止点已由用户“继续”解除，当前停止点见第14节。本批未改动已确认四图及两表。

## 14. 第四批交付：Fig.S1 与 Fig.S7（等待反馈）

| 图件 | 交付与来源 | 实际制作和结论 | 状态 |
|---|---|---|---|
| Fig.S1 | [PDF](figures/fig_s01_sv_ef_agreement/fig_s01_sv_ef_agreement.pdf) · [预览](figures/fig_s01_sv_ef_agreement/fig_s01_sv_ef_agreement_preview.png) · [独立入口](figures/fig_s01_sv_ef_agreement.py) · [英文图注](figures/fig_s01_sv_ef_agreement/caption_en.md) · [QA](figures/fig_s01_sv_ef_agreement/QA.md) | 183×170 mm，2×2散点/BA；SV与同法EF各82患者，共164配对；MAE8.03 mL/9.27 pp，bias−3.43 mL/−5.81 pp，宽LOA及所有极端值保留；补齐预测R²源表，不替换成标签EF口径 | 已制作并核查，等待反馈 |
| Fig.S7 | [PDF](figures/fig_s07_ef_reference_bias/fig_s07_ef_reference_bias.pdf) · [预览](figures/fig_s07_ef_reference_bias/fig_s07_ef_reference_bias_preview.png) · [独立入口](figures/fig_s07_ef_reference_bias.py) · [英文图注](figures/fig_s07_ef_reference_bias/caption_en.md) · [QA](figures/fig_s07_ef_reference_bias/QA.md) | 183×170 mm，2×2；82完整三方EF配对，散点/BA、同患者三类差值连线及均值bias浮动条；−5.81+7.37=+1.56 pp为带符号均值恒等式，不是因果归因，MAE不可相加 | 已制作并核查，等待反馈 |

两图均直接重建原始function.csv，患者ID与固定测试集完全一致；用独立标准库算法复核全部配对/三方值、MAE/RMSE/bias/LOA/r/两类R²及逐患者/均值恒等式。既有四图两表及共享样式152个受控文件与本批前版本一致，1049个不同来源SHA256全部匹配。未新增训练、推理、筛除、插补、拟合或临床接受阈值。

两图均调用已确认样式，嵌入Arial/Arial Bold，实际最小7 pt；纯矢量可编辑PDF和RGB600 dpi PNG/LZW TIFF，英文图注200/233词。四面板最终实测对齐通过1.5 pt容差，最终PDF碰撞各0 FAIL/0 WARN；全页、各面板、色觉/灰度均检查。源级扫描不能追踪共享样式与导出，原始4 FAIL/2 WARN保留并逐项以实际文件核实，未声称静态扫描全通过。检查和统计边界见各自QA。

同法专家轮廓参考不是独立临床容积金标准；当前代理轴几何覆盖范围问题仍未解决。S7仅作描述性事后诊断，小总体bias不能证明个体准确。当前数据仍为CAMUS半周期；无HR/CO或贴片佩戴性能主张。

本批核心工程检查：`python -m pytest -q --basetemp=.work/pytest-figures-supplement01-final-20261121`，39项通过（7.77 s），README目录核对通过。工程检查不等于临床验证。

**【停】等待本批Fig.S1/S7反馈；确认后再制作Fig.S2/S8，不提前进入下一批。**

## 15. 用户反馈与DCF论文适用性评估

用户认为上一批图件不够美观，要求评估[Directional Coherence Factor for Volumetric Ultrasound Imaging With Matrix Arrays](https://doi.org/10.1109/TUFFC.2025.3557519)的可视化能否用于本项目。已核对Crossref/PubMed题录和摘要、用户所示Fig.6/7；未取得全文，不声称通读或拆解未见图表。详细[适用性评估](figures/planning/directional_coherence_applicability.md)分别记录原图作用、资产支持、补算要求和限制。

结论：优先借鉴“同对象影像矩阵＋局部剖面＋总体定量”的证据组织，适合已有S10错误位置和S6几何覆盖主题；现有结果支持原图/轮廓/FP-FN/局部放大和派生直径剖面。无RF/IQ、三维体、仿体或保存的像素概率，不能复刻声束dB曲面、真实三正交平面、物理分辨率或概率图。彩虹色及各方法单独调动态范围不沿用。

S1/S7反馈已收到，需讨论版面修订；本轮仅评估，不绘新图。建议增大有效绘图区、减少重复说明，保留全患者散点/一致性及个体差值。是否优先S6/S10由用户进一步指示，不将评估当作制作确认。原全局样式、已确认正文图表、冻结数据及各类参考边界不变。

**历史停止点：**此处的“仅评估、不出新图”已由用户后续“先借鉴这篇论文的结果分析，把能迁移到我项目中的结果分析图绘制了”更新；当前停止点见第16节。S1/S7仍未确认。

## 16. 结果叙事调整及第五批：Fig.R1/R2（待反馈）

用户明确要求纠正“持续分析错误、误差”的主线。本批按“分割形态 → 空间几何量化 → 真实时间过程”制作；必要的精度验证和低分样例保留，但不再优先堆叠诊断图。以前的误差候选留作资料库，不等于每张都要进入论文。

| 编号及标题 | 对标及核心信息 | 真实数据与排版 | 状态及位置建议 |
|---|---|---|---|
| Fig.R1 LV形态与截面直径剖面 | Wu & Lee 2025 Fig.7影像矩阵、Fig.6e剖面组织；展示轮廓如何形成空间几何描述 | 原固定中位/最低排名2CH序列所属患者0327/0229及配对4CH；2行×4张ED/ES图，下方2个0327的2CH/4CH剖面；8标注帧、160剖面值 | ✅ [PDF](figures/fig_r01_lv_morphology/fig_r01_lv_morphology.pdf)、[预览](figures/fig_r01_lv_morphology/fig_r01_lv_morphology_preview.png)、[英文图注](figures/fig_r01_lv_morphology/caption_en.md)、[QA](figures/fig_r01_lv_morphology/QA.md)；待反馈；P1，正文Fig.2整合候选，最终选择后再编正式图号 |
| Fig.R2 真实ED–ES形态与几何时间过程 | 同篇Fig.7矩阵与Fig.6e“图像—剖面—定量”的组织思想；时序热图为本项目新增分析，不冒充参考论文原有内容 | 两条固定2CH序列各18帧；2行×5张实际帧，下方2个逐帧×20层直径热图及1个容积面板；定量含全部36帧、720直径、4专家端点 | ✅ [PDF](figures/fig_r02_systolic_dynamics/fig_r02_systolic_dynamics.pdf)、[预览](figures/fig_r02_systolic_dynamics/fig_r02_systolic_dynamics_preview.png)、[英文图注](figures/fig_r02_systolic_dynamics/caption_en.md)、[QA](figures/fig_r02_systolic_dynamics/QA.md)；待反馈；P1，正文Fig.4整合候选，最终选择后再编正式图号 |

两图为183×170 mm，沿用已确认全局样式、Arial最小7 pt；PDF保留可编辑文字/轮廓/曲线，超声图保留112×112原信息；输出RGB 600 dpi PNG/LZW TIFF。所有图像固定灰度0–255、200×170 mm物理视野、等比例、无额外裁剪或单图亮度调整。最终面板对齐均PASS（1.5 pt）；PDF碰撞0 FAIL。R1四条、R2两条WARN均为20 mm比例尺文字与原始图像矩形边缘的预期叠加，逐项查看后可读且不盖住LV。静态扫描不跟随共享样式/导出，保留4 FAIL/2 WARN及实际文件核对说明，不声称静态扫描通过。

预测几何从恢复原坐标的掩膜复算，与冻结特征一致；源表160个剖面值、720个时序直径、36帧标量逐值核对，容积公式独立复算一致。既有四图两表及全局样式未变，1049个原有不同来源哈希继续匹配。专家轮廓仅ED/ES，其他帧不制造参考；热图不插值、有效时间之外留白，逐帧曲线不平滑，所有原波动保留。代理轴逐轮廓/逐帧估计，不表示固定解剖对应、组织追踪、应变或独立人工关键点准确性。几何轴尚未独立验证；同法专家端点不是独立临床容积金标准。CAMUS与目标可穿戴场景继续分开，无HR/CO及贴片实测主张。

本批独立入口为 `figures/fig_r01_lv_morphology.py` 和 `figures/fig_r02_systolic_dynamics.py`；只读已有结果，一次运行即可重建。每图目录含源表、显示约定、来源SHA256、英文图注及检查记录。英文图注223/242词。

本批核心检查：`python -m pytest -q --basetemp=.work/pytest-lv-results-20261121`，39项通过（8.47 s）；README目录核对及Git空白检查通过。工程与排版检查不替代医学验证。

**【停】本批只交付Fig.R1/R2，等待用户反馈后再继续。S1/S7不视为已确认；不自动进入原S2/S8顺序。**

## 17. 第六批：Fig.R3 LV直径时空曲面（待反馈）

用户询问参考论文Fig.6a–d三维曲面可否用于项目，并明确回复“可以，按照你的规划来绘制”。据此制作一张两面板候选：

| 编号/标题 | 对标及核心信息 | 数据与排版 | 状态及位置 |
|---|---|---|---|
| Fig.R3 LV直径时空曲面 | Wu & Lee 2025已核对Fig.6a–d的三维标量表达；展示原始直径在实际ED–ES区间内的层间差异与时间起伏 | 固定0327/0229两例2CH；1×2、每例18帧×20层；x时间(s)、y每帧自身代理轴位置(%)、z直径(mm)；统一视角/色带/范围 | ✅ [PDF](figures/fig_r03_diameter_surface/fig_r03_diameter_surface.pdf) · [预览](figures/fig_r03_diameter_surface/fig_r03_diameter_surface_preview.png) · [英文图注](figures/fig_r03_diameter_surface/caption_en.md) · [QA](figures/fig_r03_diameter_surface/QA.md)；待反馈；P1，R2热图的替代表达候选，暂不新增正式正文图数 |

全部720个原始节点保留，与冻结features.json及R2源表逐值一致；时间核对侧车及FPS。固定网格划分产生1292个显示三角片，顶点仅引用相邻原始测量；颜色为每片三个顶点直径均值。平面片只用于图形连接，不增加测量/采样、不平滑或补造周期；缺失单元不补面。本批全720值有效，无排除。曲面到各自实际ES停止，外侧留白。两个病例沿用原固定中位/最低序列排名，不重新筛病例。

183×115 mm、嵌入Arial最小7 pt；蓝—青—绿—黄共享色带0–60 mm、正交投影、同视角和框体比例。PDF曲面/文字可编辑、RGB 600 dpi PNG/LZW TIFF、240词英文图注均已保存。最终面板对齐PASS（1.5 pt），PDF碰撞0 FAIL/0 WARN；色觉/灰度及逐面板已查看。源级扫描保留4 FAIL/3 WARN及共享样式/导出和水平标签识别限制，不声称静态检查PASS。旧四图两表、R1/R2及基础样式未修改，1058个不同原有来源哈希匹配。

直径曲面为标量展示，非真实三维LV、声束dB、组织追踪或应变。代理轴逐帧估计且未独立验证，中间帧无专家标签；两患者重复测量不作总体推断。CAMUS半序列与贴片目标场景分开，不画HR/CO。原“避免多余3D效果”继续用于装饰性立体图；本轮三维定量表达已由用户明确授权。

本批核心检查：`python -m pytest -q --basetemp=.work/pytest-lv-surface-20261121`，39项通过（7.62 s）；README目录核对及Git空白检查通过。工程检查不替代医学验证。

用户随后认为原cividis色调难看，明确要求按照所给参考图的色调重配。本次已改用共享style/surface_palette.py的蓝—青—绿—黄色带，保持两图同一0–60 mm线性范围。全部数据CSV、面片几何、视角及最终面板边界SHA256均与修订前相同；基础palette.py和旧图不变。配色例外为用户本次明确指定，色带是视觉近似而非声称恢复原论文查色表。修订后重新完成最终PDF检查并等待本批反馈。

**【停】本批只交付Fig.R3，等待用户反馈；不据此视为R1/R2或S1/S7已经最终确认。**
