# CAMUS 方法流程图

**图题**：基于 CAMUS 的左室分割与心功能参数估算流程

**图注**：

① 输入保留原始 ED/ES 专家标注、空间和时间元数据的 CAMUS 2CH/4CH 已处理数据。② 核验清单、112 × 112 输出尺寸和正反坐标变换，沿固定的自定义患者级 70/15/15 规则建立互斥训练、验证和测试清单。③ 采用 EchoNet 风格 DeepLabV3-ResNet50，仅以专家标注的 ED/ES 帧监督训练，灰度复制为三通道；归一化仅由训练集计算，以 AdamW 和均值 BCE 优化，并按验证损失选模。④ 在隔离测试集上逐帧推理，以固定 0.5 阈值生成掩膜，恢复至原始图像坐标。⑤ 原始预测掩膜另与原始专家 ED/ES 掩膜计算分割误差；几何分支经最大连通域提取和填洞，利用轮廓 PCA 推导候选关键点及面积、长轴和截面直径。⑥ 有空间标定时估算单平面面积-长度容积与双平面 20 圆盘容积；单平面在专家相位与预测曲线自动选相位下的结果分开报告，双平面只配对同一患者、同一 ED/ES 相位的两个切面。⑦ 由 EDV/ESV 计算 SV 和 EF；CO 需要可靠 HR，按参考来源分层汇总患者级误差、偏倚、Bootstrap 区间、覆盖率和失败病例，导出特征、掩膜、叠图及 CSV/JSON/HTML 报告。

虚线表示条件分支。时序平滑及质量门控开关默认关闭：平滑仅在连续有效片段内进行，门控开启后按质量标志筛除异常帧。逐搏分析仅对代码中声明为完整序列的输入运行，仍须有可靠时间戳和完整相邻 ED 间期；CAMUS 半周期不反射、不拼接。

**核心主张**：该图描述一个可复现的 CAMUS 左室分割与几何心功能估算基线；它不表示端到端视频 EF 模型、严格复现 EchoNet 原论文训练设置，或已完成临床验证。

**假设及来源**：

1. 主流程从已有处理后 CAMUS 数据开始；日常数据准备入口核验清单和元数据，不代表自动重建了完整原始数据集。来源：`docs/code_walkthrough.md` 第 1 节、`src/data/prepare.py`。
2. 患者划分是固定的自定义 SHA256 70/15/15 划分，不是官方排行榜划分。来源：`configs/data/camus.yaml`、`src/data/splits.py`。
3. 模型是 EchoNet 风格 DeepLabV3-ResNet50 在 CAMUS 上的训练适配；AdamW 与均值 BCE 不应标成上游训练设置的严格复现。来源：`docs/measurement_protocol.md`、`src/engine/trainer.py`。
4. A2C/A4C（图中 2CH/4CH）为先后采集；双平面估算只在同一患者的同一 ED/ES 相位配对，不构造同步逐帧双平面曲线。来源：`docs/measurement_protocol.md`。
5. 默认配置关闭时序分析和质量门控；缺少完整周期或可靠参考 HR 时不输出 CO，缺少独立临床参考时不把几何代理误差称作临床真值。来源：`configs/experiment.yaml`、`docs/measurement_protocol.md`。

**编辑说明**：`camus_method_flow.svg` 保留可编辑文字和形状，元素 `id` 对应流程组件；PDF 保留可检索文字并嵌入字体；PNG 为 300 dpi 预览。字体使用 Microsoft YaHei UI，数字及部分英文字段使用 Arial。当前按 183 mm 宽、约 190.76 mm 高制作，目标期刊尚未指定；此尺寸是本次排版约定，不表示通过任何期刊的投稿审核。

**复现**：更新 SVG 后，在项目根目录执行 `python figures/render_method_flow.py`。需要 PyQt5、Microsoft YaHei UI 和 Arial；导出脚本不读取患者数据，同时核查文字边界、重叠及画布范围，并保存 `method_flow_export_check.json`。每次修改后需重新审阅最终 PDF。

**范围**：本图仅覆盖当前公共数据基线，未纳入尚未接入此流程的贴片探头采集或临床连续监测验证。轮廓派生关键点需要人工复核。人工关键点、独立 CO 或临床容积参考缺失时，相应参考/误差为 null 并记录原因，不表示已有预测量都必须为 null。

**实现核对**：训练监督取帧见 `src/data/base.py`；阈值、选相位、质量筛选、参考分层与结果导出见 `src/engine/evaluator.py`；几何见 `src/geometry/mask_features.py` 和 `src/geometry/volume.py`；时序条件见 `src/temporal/`。图件与工程检查不构成真实患者实验复跑或临床验证。论文定稿前仍需作者确认科学表述。
