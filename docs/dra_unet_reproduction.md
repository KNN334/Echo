# DRA-UNet 复现

DRA-UNet 是消融组 `DTE`。它使用宽度为 24、48、96、192、384 的五级空洞残差编码器、384 通道瓶颈上的 ConvLSTM、四条 Attention Gate 跳连和一个辅助边缘头。[结构图](../reports/lvseg_ablation/assets/dra_unet_architecture.svg) · [训练配置](../configs/lvseg_ablation.yaml)

## 训练与验证

在独立工作目录检出训练版本 `1895536`。该版本的训练源码与发布结果的 SHA-256 锁一致。在该工作目录按 README 准备 CAMUS 数据，并安装项目的模型、医学影像和可视化依赖。

```powershell
git worktree add --detach ../Echo-ablation-reproduction 1895536
Set-Location ../Echo-ablation-reproduction
python -m pip install -e ".[model,medical,visualization,test]"
python scripts/download_camus.py --workers 4
python scripts/prepare_camus.py
python scripts/run_ablations.py --config configs/lvseg_ablation.yaml --device cuda
```

训练使用固定的 400 名训练患者、50 名验证患者及种子 2026、2027、2028。三次训练的 DTE 权重分别写入 `runs/lvseg_ablation/seed_<seed>/DTE/best.pt`。每次以验证分割损失最低的权重计算指标。CUDA 版本与硬件可能影响重复训练的数值，导出时使用与该次训练配套的 `results.json` 校验检查点。[实验协议](lvseg_ablation_protocol.md) · [历史实验锁](../reports/lvseg_ablation/protocol_lock.json)

## 导出预览

从发布版本的根目录运行以下命令。默认路径需要已准备的 CAMUS、种子 2026 的 DTE 权重、与该权重匹配的验证结果，以及五种基线的同种子预测缓存。五种基线缓存由 README 中的 `run_baselines.py --stage all` 生成。若文件在独立复现目录，用 `--checkpoint`、`--results`、`--prepared` 和 `--baselines` 指向对应位置。

```powershell
python scripts/export_dra_readme_assets.py --device cpu --output .work/dra_readme_assets
```

预览使用固定测试患者 `patient0015`，并沿时间顺序推理两个切面的所有帧。导出的 GIF 为慢速预览，MP4 使用源帧率。双切面对比按每个切面的原始 ED/ES 标签选帧。发布版本的训练权重需本地生成。[已发布素材的来源](../reports/lvseg_ablation/assets/provenance.json)
