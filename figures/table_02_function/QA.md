# Table 2 制作检查

状态：第三批审阅稿，等待用户反馈。日期：2026-11-21。

## 数据与统计

- 借鉴EchoPrime Table 2及EchoFM Tables IV/V的按参考分组组织；未复制图件。核心问题为“同一冻结基线在明确区分的参考下有多大功能误差”。正文只列5行，其他视图/相位口径安排于Table S1。
- 第一分区为20层双平面、较短代理长轴、专家ED/ES相位的EDV/ESV/SV/EF；参考来自专家轮廓同一几何算法，非独立临床容积金标准。第二分区的EF单独对照CAMUS Info.cfg临床EF标签。
- 从原始function.csv读取，每行恰为固定测试集82患者，每患者一个配对，共410个患者–指标配对。全部ID与固定划分一致，逐值匹配既有冻结agreement_pairs。没有排除离群值、插补或新推理。
- 5行的n/MAE/bias/LOA匹配冻结统计，RMSE/r匹配结果审计；另用标准库独立复核所有点统计一致。MAE 95% CI直接保留既有2000次患者bootstrap百分位区间，seed 2026，不因本批呈现重新采样/挑选区间。
- bias=预测−参考；95% LOA=bias±1.96×差值样本SD，是描述性一致性界限，非置信区间或临床容许误差。EF误差单位为百分点pp，容积为mL。
- 预测R²=1−SSE/SST(reference)，与Pearson r²另列于源表。SV预测R²=−0.002，同法EF=−0.041，标签EF=0.189，如实保留；不能由相关性替代准确性。
- 对照CAMUS标签EF：MAE9.0320 pp、RMSE11.1210 pp、bias+1.5615 pp、LOA−20.1527～23.2756 pp、r=0.662948。虽平均bias较小，一致性范围较宽，且同法参考与标签的偏倚可能抵消，不足以证明临床可替代性。
- 代理轴/基底几何范围不一致未修正；所有几何计算仍为冻结版本。没有测试反馈调参、校准、重选模型、显著性检验、ICC或临床接受区间。
- HR/CO保存为null、n=0及缺少完整周期/可靠参考HR/独立CO的原因，不填0误差。没有项目贴片采集或连续佩戴性能主张。单平面/自动相位不同n不能与本表5行合并报告。

## 导出与版面

- 全局style/、共享三线表排版；183×112 mm，8列数字右对齐，两参考区块各自命名。无竖线、网格、3D效果或阴影，不靠颜色区分参考。
- 可编辑PDF为纯矢量文字/线条，嵌入Arial/Arial Bold，全部实际字号至少7 pt；单元格边界与页内文字检查通过，最终PDF碰撞0 FAIL/0 WARN。单表对齐检查为NOT APPLICABLE。
- RGB600 dpi PNG/LZW TIFF为4322×2645 px，另存屏幕预览、英文图注、可编辑Markdown表、410行配对与全精度统计。源文件哈希一致；完整表及两分区已视觉检查，灰度/色觉诊断位于qa/。

## 静态扫描与复现

qa/source_preflight.json保留4 FAIL/4 WARN，未称静态扫描全通过。字体、可编辑文本、PDF/PNG/TIFF、dpi与尺寸由导入的共享样式/导出函数控制，扫描器不能跟踪；默认要求的SVG不属用户已选格式。实际成品由artifact_checks.json、glyph_audit.json和collision_audit.json核实。其“seed/mean无误差条”警告属于单文件推断：本表是一个冻结模型的患者配对统计，seed指患者bootstrap；MAE区间已明确列出，不虚构多种子训练误差条。

运行`python figures/table_02_function.py`可从冻结文件重建，`--alignment-auditor`可指定外部检查入口，本次已实际调用。版面变更后须重新检查PDF。数值独立复核见qa/numeric_verification.json。本批核心检查39项通过（7.56 s）；工程检查不等于独立临床验证。
