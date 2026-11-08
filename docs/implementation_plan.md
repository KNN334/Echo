# 实现计划与版本

依据 `research/drafts.json` 中计划书第 4–7 节：

1. v0.1：原始影像与元数据审计、显式 ROI/界面遮罩、可逆坐标转换、患者级划分。
2. v0.2：EchoNet DeepLabV3-ResNet50 单通道输出基线、CAMUS 稀疏 ED/ES 训练及全序列推理。
3. v0.3：轮廓/几何关键点、单平面与双平面容积、逐搏参数、质量门控和评估导出。
4. 每个完成且验证的版本分别 commit；训练产物附源代码提交号、配置与输入校验值。

## 参考与边界

- EchoNet 官方代码：https://github.com/echonet/dynamic ，实际分割默认模型为 `deeplabv3_resnet50`，不是视频 EF 回归网络。
- CAMUS 官方：https://www.creatis.insa-lyon.fr/Challenge/camus/ ，500 名患者、A2C/A4C、ED/ES 稀疏标注。
- CAMUS 两个切面通常为先后采集，不能假装逐帧同步；双平面仅配对同患者、同 ED/ES 相位，连续曲线用单平面近似。
- 人工关键点标签和独立 CO 真值不是默认已有；缺失时输出 null 和原因，几何推导参考与人工参考分开报告。
- 当前已有研究材料明确记载“尚未下载数据”。不把合成验证标成真实数据实验，不把未训练网络称为已完成基线。
