# Fig.R1：LV形态与直径剖面检查

审阅稿，2026-11-21；正文Fig.2整合候选，尚未替换已确认图。科学问题：预测LV轮廓能提供怎样的视图/相位形态与空间几何描述？主体是影像矩阵，剖面用于量化可见形态，不主张临床容积或解剖关键点准确性。

## 来源及面板

- a/b：两患者、四视图序列、八ED/ES真实帧。沿用冻结选择patient0327_2CH（83/164）及patient0229_2CH（1/164），另加入同患者4CH。排名是2CH序列ED/ES平均Dice在全部164测试视图序列中的位置，不能写成患者或4CH排名。
- c/d：患者0327的2CH/4CH各20层直径，预测/专家、ED/ES共160个值。每条曲线在自身轮廓的PCA代理轴归一化位置采样，非固定解剖位置对应。
- 对标仅为Wu & Lee 2025、DOI 10.1109/TUFFC.2025.3557519已见Fig.7矩阵及Fig.6e剖面结构；全文未取得。新图使用自己的数据，没有复制原图或移植dB/声束分辨率证据。

## 数值与影像完整性

读取原缓存图、原始专家掩膜、保存的预测掩膜及变换侧车。预测恢复到原坐标，ED/ES几何重新计算，与冻结特征逐值一致。80个预测剖面值再从导出CSV独立核对；80个专家剖面值由原专家掩膜和相同冻结几何法直接计算。所有160值均保留，无拟合或平滑。源数据和SHA256见source_data/及provenance.json。

影像均保留原112×112信息，固定灰度0–255；原始空间间距经坐标恢复用于mm显示，统一200×170 mm物理视野仅补黑，不额外裁剪或拉伸，无逐图对比度调整。20 mm比例尺按同一物理坐标生成。原ROI人工审阅仍为false。

## 统计与解释

展示两个固定患者的描述性实例，剖面只涉及一患者，无总体估计、CI、显著性检验或独立帧推断；因此不画误差条。专家轮廓只在ED/ES；其几何量非独立临床金标准。代理轴/基底覆盖问题尚未修复，不称解剖定位或真实全LV重建。2CH/4CH独立采集，非同步三维切面。数据为公开CAMUS经胸半序列，不代表贴片佩戴实测。

## 渲染检查

183×170 mm，Arial/Arial Bold实际最小7 pt、全部嵌入。PDF文字、轮廓、曲线为矢量可编辑；八张超声图原生112×112。PNG及LZW TIFF均RGB 600 dpi，英文图注223词。无额外边框、网格、3D或阴影；剖面统一0–100%及0–60 mm。

最终面板对齐PASS（1.5 pt容差）。最终PDF碰撞0 FAIL/4 WARN；四条WARN均为患者0327比例尺文字跨越原始影像矩形边缘，位于显示视野的下方黑色/图像边缘，不遮挡LV、可读，是有意的影像叠加。已逐项查看全图、a–d、灰度及色觉模拟；未发现误遮挡。所有色觉诊断图保存在qa/，不改变原数据。

单文件静态扫描原报告保留：4 FAIL/2 WARN，原因是不能跟踪外部共享样式及导出。FONT-FAMILY由实际PDF嵌入Arial证明；EDITABLE-TEXT由实际文字字体和矢量路径证明；EXPORT-VECTOR由本PDF证明（当前约定PDF，不要求SVG）；EXPORT-RASTER由600 dpi PNG/TIFF证明。字号及DPI两条WARN由实际产物检查消解。不把静态原始扫描写成PASS。

既有四图两表/全局样式未修改，1049个原有不同来源SHA256匹配。未训练、重新推理、反馈调参或重新选择病例。详细证据见qa/artifact_checks.json、independent_data_check.json、glyph_audit.json、collision_audit.json、source_preflight.json及本目录alignment.json。

复现：项目根目录运行 `.venv/Scripts/python.exe -X utf8 figures/fig_r01_lv_morphology.py`；可加 `--alignment-auditor` 指向可用的面板审计程序以重跑完整外部对齐检查。共享物理边界检查默认执行。生成后须对最终PDF重跑碰撞检查。

Core project checks: 39 passed in 8.47 s; `python -m pytest -q --basetemp=.work/pytest-lv-results-20261121`. These checks do not establish clinical validity.
