# Fig.S1 制作检查

状态：第四批审阅稿，等待反馈。日期：2026-11-21。此前正文四图与两表（含Table 1零值行修订）已确认。

## 图件合同与证据

- 科学问题：同法双平面SV和EF是否与专家轮廓派生参考一致？核心信息：两者仍存在明显个体误差和宽一致性界限，不能用标签EF口径替换或掩盖。
- quantitative grid，2×2；借鉴Hu Fig.5c / EchoPrime SI Fig.1的散点与Bland–Altman组织，只借布局，没有复制图件。两列是正文Fig.3移出的次要功能终点，补齐Table 2完整证据，不另占正文图。
- 来源为冻结camus_cuda_progress的function.csv；20_disks_shorter_axis，专家ED/ES相位，专家轮廓经同一20层面双平面几何及较短代理轴计算参考。每指标全部82测试患者，164个配对；患者ID与固定测试集完全一致，无任何排除。
- 原始配对逐值核对冻结agreement_pairs，统计核对冻结表、完整性审计和Table 2。另用标准库math/statistics独立计算MAE、RMSE、bias、LOA、r、r²及预测R²，见qa/numerical_verification.json。
- SV：MAE8.03048 mL，bias−3.42680 mL，LOA−22.45102～15.59741 mL，r0.61218；同法EF：MAE9.26567 pp，bias−5.81135 pp，LOA−27.59726～15.97456 pp，r0.65874。所有低值和极端误差保留。
- bias=预测−参考；LOA=bias±1.96×差值样本SD，是描述性界限，不是CI或临床接受阈值。未新增假设检验、bootstrap、CI、校准或模型选择。
- 预测R²=1−SSE/SST(reference)，SV−0.00237、EF−0.04113保留在源表；不以r²代替。图内报告r，避免两种R²混用。
- 专家同法容积不是独立临床金标准；代理轴覆盖范围不一致仍未解决。当前仅公开CAMUS经胸半周期数据，不支持贴片佩戴、独立容积准确性或连续逐搏主张；未计算HR/CO、补造完整周期。

## 逐面板检查

| 面板 | 独特证据 | 中心/离散 | 统计单元 | 标签和坐标 | 对齐/碰撞 | 结论 |
|---|---|---|---|---|---|---|
| a | SV预测与同法参考关联 | 82原始点；MAE/r；无新CI | 患者 | mL，恒等线，n=82 | 与b同行、与c同列；PASS | 可读，所有点可见 |
| b | 同法EF关联，区别于正文标签EF | 82原始点；MAE/r；无新CI | 患者 | %与pp分开；n=82 | 与a同行、与d同列；PASS | 参考性质明确 |
| c | SV带符号误差范围 | bias与描述性LOA | 患者 | mL，实线/虚线/点线明确定义 | 与d同行、与a同列；PASS | 负向极端值未裁切 |
| d | 同法EF带符号误差范围 | bias与描述性LOA | 患者 | 差值pp；均值% | 与c同行、与b同列；PASS | 宽LOA如实保留 |

a/b提供关联、c/d提供带符号误差，不能互相替代。四轴44×44 mm；散点等比例；两列均0～100数值范围但保留各自单位，BA纵轴均−40～40。全部点和LOA均在范围内。全页及各面板、灰度/色觉诊断检查完成；定量点、恒等线与LOA用颜色和线型冗余区分。

## 导出、复现与边界

- 调用已确认style/；183×170 mm，嵌入Arial/Arial Bold，实际最小7 pt，分图裸字母8 pt粗体。纯矢量可编辑PDF，无内嵌栅格定量图；RGB600 dpi PNG和LZW TIFF；英文图注200词。
- 最终实测面板对齐通过1.5 pt容差，无豁免；最终PDF碰撞0 FAIL/0 WARN，字形审计无低于7 pt的文字；所有文字在页内。结果见alignment.json及qa/artifact_checks.json、glyph_audit.json、collision_audit.json。
- 单文件静态扫描仍有4 FAIL/2 WARN：无法追踪导入的全局字体、Type42编辑文本及共享PDF/位图导出，并检查未选择的SVG。原始source_preflight.json完整保留；实际字体、尺寸、RGB/dpi和矢量内容已逐项核实，不声称静态扫描全通过。
- 既有四图两表及共享样式152个受控文件与本批前版本一致；1049个来源SHA256匹配。见qa/preservation_checks.json。本批检查验证工程和数值一致性，不等于临床验证。
- 根目录运行 `python figures/fig_s01_sv_ef_agreement.py` 可重建；可用 `--alignment-auditor` 指定外部对齐检查入口。源表、参考/相位字段、输入与入口哈希均保留。更改后需重新审计新PDF。原始数值、模型、几何和共享样式未修改。
- CAMUS署名Leclerc et al., IEEE TMI (2019)，doi:10.1109/TMI.2019.2900516，CC BY-NC-SA 4.0。

项目要求的核心检查：`python -m pytest -q --basetemp=.work/pytest-figures-supplement01-final-20261121`，39项通过（7.77 s）；README目录核对通过。
