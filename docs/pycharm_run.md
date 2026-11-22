# PyCharm 运行步骤

确保 PyCharm 使用项目 `.venv` 中的 Python，并安装根目录 `requirements.txt` 中的依赖。

首次获取完整 CAMUS 数据并准备训练文件：

```powershell
.venv\Scripts\python.exe scripts\download_camus.py --workers 4
.venv\Scripts\python.exe scripts\prepare_camus.py
```

训练五个固定基线并评价：

```powershell
.venv\Scripts\python.exe scripts\run_baselines.py --stage all --device cuda
```

没有 CUDA 时将 `--device cuda` 改为 `--device cpu`。查看单个模型可追加 `--model UNet-mini`。仅流程冒烟测试可使用 `--epochs 1 --limit-test-cines 1`；此结果不作为正式模型评价。

脚本入口如下：

- `scripts/download_camus.py`：校验下载完整性后获取 CAMUS 原始 cine。
- `scripts/prepare_camus.py`：统一处理影像帧与专家标注，生成固定划分清单。
- `scripts/run_baselines.py`：训练、全帧推理、指标汇总与绘图。
- `scripts/plot_volume_curve.py`：从已有推理 CSV 单独重画一个病例的逐帧容积曲线。

若已有按官方许可获取的 EchoNet-Dynamic，可运行 `scripts/prepare_echonet.py --raw-root <数据根目录>` 准备完整 A4C 视频。该数据没有空间标定，不能报告绝对容积或 mL/min。

运行检查：

```powershell
.venv\Scripts\python.exe -m pytest -q
```

数据在 `data/raw/` 和 `data/processed/`，模型、曲线、指标和图表在 `runs/lvseg_baselines/`。这些文件不提交到 Git。
