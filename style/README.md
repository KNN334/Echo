# 全局图件样式

用户已选择1A/2A/3A/4A/5A；此为首次测试版，等待样式测试页确认。新图一律调用 `style.palette.apply_style()`，不得在各图脚本重新定义颜色或字号。旧历史图件保留原样，不等于已按本样式重新制作。

- Nature生产尺寸：单栏89 mm、双栏183 mm；高度不超过170 mm。普通文字7 pt，分图字母8 pt粗体；Arial必须真实可用，不静默替换。PDF字体嵌入为Type 42，文字不转轮廓。
- 主实验 `camus_cuda_progress` 蓝色 `#0072B2`；已有变体 `camus_regularized` 橙色 `#E69F00`。青绿 `#009E73` 保留给尚未分配的比较实验；专家轮廓及同法参考点统一紫红 `#CC79A7`；CAMUS数据集EF标签与其他中性元素使用深灰。参考层级不能仅靠颜色判断，仍须文字命名。
- 主方法线宽1 pt、已有变体0.7 pt；专家轮廓用0.85 pt虚线/菱形点，构成颜色之外的冗余编码。仅有一个模型的三种指标不能分别染成三种“方法色”。
- 连续色带为cividis，发散色带为Scientific Colour Maps vik（cmcrameri 1.10分发）；发散范围以0居中，同类比较使用统一对称范围。二值掩膜不假装成连续概率；超声保持灰度。
- 输出可编辑PDF、RGB 600 dpi PNG和LZW压缩TIFF；保持物理画布尺寸，不用tight裁剪改变栏宽。600 dpi不提高112×112输入的信息分辨率。Nature Extended Data提交副本按该刊≤300 ppi、≤10 MB要求另行导出，600 dpi母版保留。

安装绘图与检查依赖：`python -m pip install -r style/requirements.txt`。在项目根目录运行 `python figures/style_test.py` 即可从已有结果重建测试页；需要本地处理缓存与冻结结果。可用 `--alignment-auditor` 传入额外的面板对齐检查工具，独立运行时仍检查定量面板的实测矩形。

测试页源数据、选择规则和处理记录见输出目录的 `source_data/`、`provenance.json`、`QA.md`。定量面板来自真实数据，不是演示随机数；最低排名样例是旧图集已记录的规则，不在本轮换选。

已读取的期刊依据：[Nature final submission](https://www.nature.com/nature/for-authors/final-submission)、[Nature figure specifications](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/)。图内尺寸及字体是按生产规范提前制作，尚不意味着稿件已达发表或临床验证要求。
