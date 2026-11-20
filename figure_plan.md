# 心功能结果图表制作清单（清单已确认，阶段 4 待确认测试页）

更新日期：2026-11-21。用户已确认正文4图2表、补充候选及 `camus_cuda_progress` 主冻结实验，并选择 **1A/2A/3A/4A/5A**。当前状态：**阶段 4 全局样式与真实数据测试页已完成，等待测试页确认；阶段 5 投稿图尚未开始。**

本清单服务于“基于贴片式超声探头的心脏功能参数连续监测与分析”。当前实证范围是 **CAMUS 公开经胸超声上的 LV 分割及轮廓几何量化基线**。贴片连续佩戴是目标应用，尚无本项目佩戴实测证据。图表可以提高表达与可复核性；当前证据不足以支撑贴片连续监测、独立临床绝对容积验证或新算法全面优于同行的主张。

## 1. 交付索引与同行依据

- [结果资产清单](figures/planning/result_assets.md)：数据、分辨率、实验、已算/可补算/不可算指标及精确来源。
- [逐篇逐图逐表拆解](figures/planning/literature_breakdown.md)：Hu 2023、Ouyang 2020 两篇指定模板，以及 Chao 2025、EchoFM 2025、EchoPrime 2025 在线/2026 卷期、SAFU 2025 四篇补充全文，共 162 个图表条目。
- [文献结构化目录](figures/planning/literature_catalog.json) 与 [数量统计](figures/planning/literature_statistics.json)：图注摘录、图号、来源网址、核查范围与全文/附件校验记录。
- [本地资产机器核查](figures/planning/asset_inventory.json)：1,000 个缓存逐个解码、患者隔离、179 个既有冻结源文件校验；不是新增训练或临床验证。

六篇正文图中位数 **4，范围 3–7**；正文表中位数 **1.5，范围 0–9**。建议 **4 张正文图 + 2 张正文表**，另列 **5 张补充图候选和 1 张补充表**，不强行填满。非正文图（扩展图+SI）中位数 6、范围 1–42，仅计算附件数量已知的 5 篇；EchoFM 独立 SI 未查明，保留 NA。

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
| Table 1 | CAMUS 队列、患者划分与参考标签覆盖 | EchoFM Table I；EchoPrime Table 1 | 数据规模、有效参考及证据缺口均有明确分母 | ✅ 数据现成可做 | 正文 / P1，随 Fig.1 首次引用 |
| Fig.1 | 当前验证数据与 LV 轮廓至心功能参数的分析流程 | Ouyang Fig.1；Hu Fig.5a；EchoPrime Fig.1 | 从公开半周期输入到分层参考评价的完整路径可追溯 | ✅ 数据现成可做 | 正文 / P1 |
| Fig.2 | 全测试队列的 LV 分割性能及低分与典型病例 | Ouyang Fig.2d/e；Chao Fig.1；EchoFM Fig.4 | 全队列分布与固定排名样例同时显示空间误差及失败边界 | ✅ 数据现成可做 | 正文 / P1 |
| Fig.3 | 双平面容积同法一致性与对照 CAMUS EF 标签的误差 | Ouyang Fig.2a；Hu Fig.5c；EchoPrime SI Fig.1 | 容积同法参考与 EF 标签验证是不同证据，均保留偏倚与离散程度 | ⚠️ 补算各自配对的 RMSE、r、预测 R²；已有 MAE/bias/LOA/n | 正文 / P1 |
| Table 2 | 按几何法、相位策略与参考来源分层的功能误差 | EchoPrime Table 2；EchoFM Tables IV/V 的分层数值组织 | 不混合不同参考与有效数，完整列出 EDV/ESV/SV/EF 结果 | ⚠️ 补算各组 RMSE、r、预测 R²；ICC 暂不纳入 | 正文 / P1，随 Fig.3 首次引用 |
| Fig.4 | 从 ED 到 ES 的真实半周期容积轨迹与相位覆盖边界 | Ouyang Fig.2f；Hu Fig.5b 的时序结构，**仅借鉴排布** | 现有数据展示半周期内的逐帧变化，完整逐搏及 CO/HR 尚不可评价 | ✅ 数据现成可做 | 正文 / P1 |

### Table 1：队列与标签覆盖

- **源数据**：`data/processed/camus/manifest.json`、`configs/camus_splits.json`、1,000 个病例 JSON；`figures/planning/asset_inventory.json`；`reports/result_analysis/camus_cuda_progress/source_data/coverage.csv`。
- **排版**：一张表，train/val/test/合计四列；患者数、切面数、总帧数、ED/ES 标注数、2CH/4CH、官方图像质量、帧率/半序列时长、空间尺寸分行。参考覆盖另作表内区块，避免把“0”写成“未发现”。训练与验证分层帧数从 manifest 分组汇总，不按比例推算。
- **注释**：原始数据全量仅有历史清单，本地 1,000 切面缓存完整是本次实核结论；人工 ROI 审阅均为 false。尚无贴片、EchoNet 本项目外部评价或人工关键点。只列已存在的人口字段，不补造年龄/性别/病种。

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

### Table 2：全部口径功能误差

- **源数据**：同 Fig.3；补充 `paired_phase_errors.csv`、`runs/camus_cuda_progress/summary.json:function`。
- **排版**：按“同法双平面/同法单平面2CH/4CH/自动极值2CH/4CH/对 CAMUS EF 标签”分区；指标逐行，列为 n、MAE、RMSE、bias、95% LOA、r、预测 R²。表宽超出目标期刊允许尺寸时，正文保留双平面四项与标签 EF，单平面/自动极值明细转 Supplementary Table 1；不缩字强塞。
- **统计**：不同指标独立核对有效 n；MAE 的患者 bootstrap CI 已有来源时沿用并注明算法。ICC 只有确定模型、绝对一致性/一致性、单次/平均及区间算法后才新增，不能为凑指标选择更好看的定义。HR/CO 用 null 与原因脚注保留，不填 0 误差。

### Fig.4：真实半周期过程

- **源数据**：`runs/camus_cuda_progress/frames.csv`、同病例 `*_features.json`、缓存侧车帧率与 `phases`；Fig.2 固定排名样例。
- **排版**：**2×2 病例面板**；每格为单切面面积–长度容积（mL）随派生时间（s）的逐帧轨迹，标注有效起止、专家 ED/ES 帧与各自同法参考点。边缘可用同病例 ED/ES 小叠图辅助解释，不能挤压坐标字号。
- **边界**：2CH/4CH 不是同步采集，不能做逐帧同步双平面曲线。中间帧没有专家真值，只能展示预测过程；两个专家端点不连成“真值轨迹”。不反射、不拼接、不假设收缩占比、不外推整搏；缺失/无效处留断点。时间注明由 FPS 派生。图名与图注不使用连续佩戴、逐搏真值或 CO/HR 波形措辞。

## 4. 补充材料候选（已确认为备选，随分批制作决定采用）

| 编号 / 标题 | 对标参考 | 数据与子图安排 | 核心信息 | 状态 / 待做内容 | 位置 / 优先级 |
|---|---|---|---|---|---|
| Fig.S1 同法双平面 SV 与 EF 的完整一致性 | Hu Fig.5c；EchoPrime SI Fig.1 | 与 Fig.3 相同配对来源；2×2，SV/同法 EF 两列，散点/BA 两行；各 n=82 | 全部双平面参数都展示，不把轮廓参考 EF 隐去 | ⚠️ 补算对应 RMSE/r/预测 R²；保留 EF MAE 9.266 pp、bias −5.811 pp 及宽 LOA | 补充 / P2 |
| Fig.S2 单平面几何与自动极值选相位的配对差异 | Ouyang Fig.2f/3d 的选搏/聚合敏感性组织，**不照搬整搏任务**；Hu ED Fig.6 的方法比较结构 | `function.csv`、`paired_phase_errors.csv`；2×2，上排两视图的专家选相位 vs 自动 EF 配对误差，下排 ED/ES 选帧偏差及无效数；几何全指标列附表 | 半序列内自动选相位会改变误差与有效覆盖，不能与专家相位混报 | ⚠️ 复核交集 2CH n=81、4CH n=80；汇总相位帧误差，必要时换算派生秒；不是新模型消融 | 补充 / P2 |
| Fig.S3 组合正则化对空间与 EF 验证误差的不同影响 | Ouyang ED Fig.3；EchoFM Fig.6（只借鉴受控比较布局） | `checkpoints/camus_cuda_progress/training.csv`、`reports/training/camus_regularized/training.csv`、`runs/validation_camus_cuda_progress/`、`runs/validation_camus_regularized/`；2×2：损失轨迹、同患者 Dice 差、同患者标签 EF 绝对误差差、有效覆盖/差值分布 | 空间指标的小幅改善没有转化为标签 EF 改善 | ⚠️ 复核权重身份和相同患者配对；标签 EF 共同有效 n=70，MAE 8.2443→9.8289 pp 的变差必须保留；无新训练 | 补充 / P2 |
| Fig.S4 图像质量、切面与误差传播的探索性分层 | Chao Fig.1；Ouyang Fig.2e；EchoPrime Fig.3 的解释性组织 | `structure.csv`、病例官方质量 JSON、`error_associations.csv`、同法功能配对；2×2：质量层的空间误差、2CH/4CH、ED/ES、患者聚合分割误差与 EF 绝对误差关联 | 域内误差异质性有迹可查，关联不足以说明机制或外部泛化 | ✅ 现有分层/关联可做；新置信区间或交集分析需显式补算；各层标 n，小样本如实显示，不按测试结果定分组/删例 | 补充 / P2 |
| Fig.S5 冻结模型的规范计算效率分解 | Ouyang ED Fig.4、ED Table 4 | 固定权重；3面板：网络/几何/总流程延迟，FPS/批量设置，参数量与峰值显存表内嵌；硬件与预热/重复/同步方式完整记录 | 计算代价的结论取决于测量边界，端到端吞吐不能当作网络延迟 | ⚠️ 需要新基准测量与参数量统计；149.85 s/3,167 帧=21.13 FPS 仅为历史含 I/O/导出的端到端记录；不据此宣称贴片实时部署 | 补充 / P3，有规范测量再做 |
| Supplementary Table 1 有效数、无效原因与完整单平面结果 | EchoPrime ED Tables 1–6 的分层组织；Chao Tables 1/2 | `coverage.csv`、`function.csv`、`summary.json`；按方法/视图/相位/参考分区，含 Table 2 放不下的全指标 | 技术执行、几何有效、参考覆盖和临床有效是四种分母 | ✅ 覆盖数据现成；⚠️ 新数值列随 Table 2 补算；0/164 技术异常不写成0临床失败 | 补充 / P2 |

Fig.S3 的训练记录可以展示选模过程，不能把组合增广+weight decay+早停称为单因素消融。两个历史实验均已评价过测试集，不以本次图表反馈继续调参、挑模型或重新选择测试阈值。仅为描述已有历史结果；真正新比较应先在训练/验证集定义方案，并为后续最终评价安排独立数据。

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
| 3 清单 | **用户已确认，2026-11-20** | 正文4图2表、补充候选及主实验身份已确认 |
| 4 视觉主题 | **1A/2A/3A/4A/5A已选；等待测试页确认** | 已写 `style/paper.mplstyle`、`style/palette.py` 并生成真实数据测试页；确认测试页后再继续 |
| 5 分批制作 | 未开始 | 每批1–2张；每图独立 `figures/fig_XX_名称.py`、真实源数据、英文图注、PDF及600 dpi位图；每批等反馈 |

最终尺寸、色系、色带、方法配色及Nature规格已在阶段 4 选定并写入共享样式；当前只制作样式测试页，尚未制作新投稿图。

本轮核查：1,000 个处理后缓存逐个解码通过，179 个既有冻结源文件哈希全部匹配，164 个预测掩膜维度匹配，患者划分无交叉；6 篇全文及4个已取得附件的哈希、162个图表条目的数量/作用分类核对通过。项目核心工程检查 39 项通过；工程检查不等于临床验证。

以后每张图均需：全局样式调用；有效数和缺失原因；单位与定义；最终尺寸最小字号 ≥7 pt；相同比较的范围统一；影像注明视图/ED/ES/轮廓；患者为统计单元；保留低分与极端值；可复跑来源及独立脚本；英文图注；最终尺寸可读性、面板对齐与文字碰撞检查。若数据否定计划，先报告并更新本清单，不能悄悄换病例或调参数。

## 7. 阶段 4：视觉主题选项（用户已选择五项A）

下面保留各选项的说明；用户本轮已选择1A/2A/3A/4A/5A，A方案已写入全局样式，测试页等待确认。使用 Python/Matplotlib。白底，超声保留灰度；二值分割用离散轮廓，连续色带仅用于有来源的连续量。

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

**【停】等待用户确认样式测试页。确认后才按已确认清单每批制作1–2张正文/补充图，每批仍须等待反馈。**
