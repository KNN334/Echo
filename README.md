# 左心室视频分割基线

本阶段只实现左心室 B-mode 视频分割与逐帧几何分析，不包含贴片硬件、RF/IQ 采集或波束合成。训练模型为 U-Net、Attention U-Net、U-Net++、U-Net-mini 和 VGG16-U-Net；暂不加入项目自定义模型或消融模块。

操作步骤和实现边界详见[左室工作流](docs/lvseg_workflow.md)与[PyCharm 运行指南](docs/pycharm_run.md)。 See the [baseline result report](reports/lvseg_baselines/RESULTS.md).

## 数据

当前主要数据为 CAMUS 官方发布的 500 名患者、2CH/4CH 动态超声序列。原始影像以多帧 NIfTI cine volume 提供，不是静态图片；处理时按源文件帧顺序解码。当前本地下载清单记录了 3,500 个原始文件，合计 3,470,387,058 字节，SHA-256 校验全部通过。原始与处理后影像不纳入 Git。

CAMUS 只提供 ED/ES 专家掩码，且序列是半周期片段。训练仅读取人工标注帧；测试推理按时间顺序处理视频中的每一帧，无标签帧也进入容积波形。只有有掩码的帧参与 IoU、Dice 和专家掩码容积对照。2CH 与 4CH 是不同采集序列，不能假定同步后逐帧合并为双平面容积。

患者级固定划分为 train/validation/test = 400/50/50。训练归一化参数来自训练标注帧；验证集用于早停；测试集只用于最终评价。CAMUS 半周期没有相邻两个完整 ED 峰，因此不会从它计算 HR 或 CO。

EchoNet-Dynamic 可作为完整 A4C 视频的可选外部数据。数据需由使用者先按 Stanford AIMI 条款授权获取；代码不会绕过访问许可或下载受控数据。它没有空间标定，Simpson 输出只能标为像素立方代理值，不能报告 mL、mL/min 或临床容积。完整视频里检测到相邻 ED 峰时才会估计 HR；无法从该数据得到同步第二切面。

CAMUS 用于非商业科研，遵循 CC BY-NC-SA 4.0，保留署名及完整来源校验清单。引用：S. Leclerc et al., “Deep Learning for Segmentation using an Open Large-Scale Dataset in 2D Echocardiography,” *IEEE Transactions on Medical Imaging*, 38(9), 2198–2210, 2019, doi: [10.1109/TMI.2019.2900516](https://doi.org/10.1109/TMI.2019.2900516)。详见 [CAMUS 使用条款](docs/data_sources/CAMUS_LICENSE_TERMS.md)。

## 运行

在项目虚拟环境中执行：

```powershell
.venv\Scripts\python.exe scripts\download_camus.py --workers 4
.venv\Scripts\python.exe scripts\prepare_camus.py --overwrite
.venv\Scripts\python.exe scripts\run_baselines.py --stage all --device cuda
```

已完成的完整数据可跳过下载和预处理步骤。准备脚本拒绝不完整或校验失败的原始集；训练与评估结果保存到 `runs/lvseg_baselines/`。可用 `--model UNet-mini` 选择单个基线，`--epochs 1 --limit-test-cines 1` 只用于流程冒烟检查，不能当作正式实验结果。

若已授权获取 EchoNet-Dynamic，可先执行：

```powershell
.venv\Scripts\python.exe scripts\prepare_echonet.py --raw-root <EchoNet根目录> --output data/processed/echonet
.venv\Scripts\python.exe scripts\run_baselines.py --stage evaluate --external-test-manifest data/processed/echonet/splits/test.json --device cuda
```

## 逐帧容积与结果

每个推理帧的预测掩码恢复到原图网格；用原始像素间距计算 20 圆盘单平面 Simpson 估计，按帧时间排列为左室容积曲线。单平面圆盘包含旋转对称近似，不等于同步双平面 Simpson 或独立临床容积测量。曲线上局部峰标为预测 EDV，随后谷标为 ESV；人工 ED/ES 位置另行标记，不用于选择预测峰谷。

若完整视频存在相邻 ED 峰，周期为 `T`，`HR = 60/T`，`SV = EDV − ESV`，`EF = SV/EDV`，`CO = SV × HR`。仅在体积经空间标定且完整周期成立时输出绝对容积单位和 CO；否则输出代理量或空值及原因。CAMUS 半周期的 HR/CO 保持不可用。

分割结果用专家标注帧上的 IoU/Dice 评价。容积 Bland–Altman 对照也只用带标签帧，并以专家掩码通过同一 Simpson 几何法形成参照；它不是独立临床容积验证。结果目录包含全帧容积 CSV、带标签帧指标、ED/ES 事件、预测掩码、标注帧轮廓对照图、容积曲线、Bland–Altman 图和汇总 JSON。

运行完整检查：

```powershell
.venv\Scripts\python.exe -m pytest -q
```
