# CAMUS / EchoNet 下游基线

公开数据基线沿用手写笔记的主线：

```text
B-mode/视频输入
  -> 逐帧左心室分割
  -> 物理坐标下的面积、长轴和直径
  -> EDV / ESV
  -> SV / EF
  -> 有可靠时间轴和完整周期时才计算 HR；有独立 HR 与 CO 参考时才计算 CO
  -> 按图像、分割、几何、功能和证据覆盖率分层验证
```

训练只使用有专家轮廓的帧。推理时逐帧处理整段 B-mode/视频，逐帧分割和计算几何量；后续容积曲线和功能指标不要求每一帧都有标签，标签只用于训练、ED/ES 轮廓误差和阶段性质量核查。EchoNet 视频即使没有标注帧或只有一张标注帧，也保留整段视频用于推理；这类视频不参与监督损失，也不能提供需要 ED/ES 标签帧的参考对照。

因此，结果中的 `single_plane_auto_extrema_*` 是按推理容积曲线选相位的下游输出；`single_plane_area_length` 和专家 ED/ES 双平面行只用于把分割误差与相位选择误差拆开，不能替代整段推理曲线。

CAMUS 的处理后数据包含像素间距和专家 ED/ES 轮廓，因此可用于分割、同几何容积和 EF 基线。CAMUS 的半周期不被反射、拼接或声明为完整周期；没有独立 HR/CO 时，HR/CO 输出保持 `null`。

EchoNet-Dynamic 的公开输入是常规 A4C 视频及 ED/ES 轮廓、EF/EDV/ESV 数据集标签，不是贴片 RF/IQ 数据。运行 `python scripts/prepare_echonet.py --raw-root <EchoNet根目录>` 可将 `FileList.csv`、`Videos/` 和 `VolumeTracings.csv` 转成项目统一的 NPZ/JSON 病例格式。若 `FileList.csv` 没有患者标识，预处理会使用 study filename 代理，并在 `manifest.json`、结果 `summary.json` 和 `evidence_status.json` 中标记 `study_proxy`；此时只能报告 study-level 基线，不能称为患者级泛化。

## 推荐运行顺序

1. 预处理 EchoNet 视频和轮廓：

   ```text
   python scripts/prepare_echonet.py --raw-root <EchoNet根目录> --output data/processed/echonet
   ```

2. 根据生成的 `manifest.json` 运行 `scripts/prepare_data.py`，生成固定 train/val/test 清单。EchoNet 使用官方 Split 字段；CAMUS 使用仓库内固定患者级清单。

3. 使用 `configs/experiment.yaml` 运行 CAMUS 分割、几何和功能基线；使用 `configs/experiment_echonet.yaml` 运行 EchoNet 视频分割基线。测试集只在预先定义的最终评价阶段读取。

4. 使用 `scripts/plot_results.py` 生成训练曲线、分割分布、ED/ES 与容积曲线、预测/参考一致性、Bland–Altman 和阶段覆盖率图。每个结果目录还会保存 `evidence_status.json`，把“不可计算”与“计算失败”分开。

## 结果解释边界

- EchoNet 没有空间标定时，预测轮廓只能给出像素几何；绝对 EDV/ESV 和 SV 保留 `null` 及 `missing_spatial_calibration`。可用逐帧像素几何代理量计算无量纲 EF，但必须标为 `pixel_proxy`，只与 EchoNet 数据集 EF 标签单独比较，不声称是空间标定容积或临床容积验证。
- EchoNet 的 EF/EDV/ESV 是数据集标签，可作为参考来源单独记录，不能改名为贴片标签，也不能替代独立 CO 参考。
- `full_cycle_verified` 未明确为真时不计算 HR/CO；容器 FPS 或文件表 FPS 只作为时间元数据审计，不自动等同于生理采样时间。
- EchoNet 的全片推理极值按当前视频片段内可用推理帧选择，结果不命名为完整心动周期；训练标签帧上的 EF 只作为分割/相位误差隔离，另行输出整段推理极值 EF。
- 这些公开数据只验证 B-mode/视频下游算法；贴片姿态、RF/IQ、波束合成和运动中连续监测仍需真实贴片队列。
