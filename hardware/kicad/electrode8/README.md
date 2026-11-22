# 8 阵元电极接点与引出线教学工程

本工程配合 `docs/hardware/` 下的两份中文教程使用。它是用于学习 KiCad 的铜电极接点与布线示例，参数由本次教学设定，不是 Hu 等 Nature 2023 论文的加工图。

- `electrode8.kicad_pro`：双击后在 KiCad 工程管理器打开。
- `electrode8.kicad_sch`：9 路连接关系；CH1–CH8 为独立通道，RET 为公共返回接点。
- `electrode8.kicad_pcb`：24 × 30 mm、仅正面布线的完成示例。
- `PatchLesson.pretty/`、`PatchLesson.kicad_sym`：工程自带的教学封装、符号；不依赖下载第三方库。
- `fp-lib-table`、`sym-lib-table`：使用 `${KIPRJMOD}` 相对路径，可整体复制工程。
- `exports/`：电极铜层 SVG/DXF、Gerber、连接检查报告。
- `../../tools/build_electrode_lesson.py`：重建示例的源文件；会覆盖示例，个人练习请另存工程。

先阅读 [软件使用说明](../../../docs/hardware/01_KiCad中文使用说明.md)，再按 [从零画电极教程](../../../docs/hardware/02_从零绘制电极图教程.md) 在新工程中操作。

RET 表示本练习中的公共返回连接，不自动等同于保护地、人体参考电极或任何实际设备的地。示例没有超声发射、接收、供电、隔离与驱动电路；也未建立压电片、柔性基底、液态金属层和封装的实物堆叠关系。导出文件用于学习导出和图形核对。
