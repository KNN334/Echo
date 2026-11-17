# 统一虚拟环境后的训练记录

本次实验名为 `camus_regularized_v2`。从 PyCharm 配置所使用的项目 `.venv/Scripts/python.exe` 启动训练；没有新建其他训练环境，也没有修改已安装依赖。

| 项目 | 本次记录 |
|---|---|
| Python | 3.12.4 |
| 解释器 | `.venv/Scripts/python.exe` |
| 项目虚拟环境校验 | `True` |
| PyTorch | 2.11.0+cu128 |
| CUDA 运行时 | 12.8 |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU |
| 训练/验证患者 | 347 / 71 |
| 完成轮数 / 最大轮数 | 14 / 30 |
| 最佳轮次 | 14 |
| 最低验证 BCE | 0.0363108074 |
| 提前停止 | True |
| 累计训练耗时（秒） | 231.3 |

`training_log.txt` 是带时间戳的训练过程；`training.csv` 是逐轮损失、速度和耗时。`run.json` 保存实际解释器、关键依赖、CUDA、归一化和患者清单；`environment_packages.json` 是本次运行完成后的完整已安装包版本清单。`experiment.json` 是实际合并配置的副本，`completed.json` 是训练完成与最佳权重记录。

使用原有固定患者划分、EchoNet 初始化权重、训练图像/标签同步增强、AdamW 权重衰减及验证早停。数据清单、初始化权重摘要和正则化参数与 `camus_regularized` 历史实验相同；历史实验没有完整环境记录，不能宣称两次运行环境相同。

早停计数使用 `patience=6`、`min_delta=0.0002`，要求验证损失达到设定的改善幅度；最佳权重则始终按所有轮次中绝对最小的验证损失保存。因此，本次最佳轮次与停止轮次相同，并不意味着没有执行早停。

本次只执行训练/验证，没有运行新的测试集评价，也没有用测试结果调参。验证损失最低轮次对应本地 `checkpoints/camus_regularized_v2/best.pt`；日志与检查点的对应关系见 `archive_checks.json`。增强后的训练损失和无增强的验证损失来自不同数据条件，数值差距需要结合验证曲线解释；采用正则化和早停本身不能证明过拟合已彻底消除。

运行来源为提交 `a9840e7db9b5cae4b1239248bd451dd364ac7f4d`。`working_tree_dirty` 保留实际值 `True`；启动时工作区保留了之前的 README 与目录说明中的文献调研改动。旧实验与原始检查点均保留。

如需再次训练，请为训练输出、对应测试权重及测试输出选择新的实验名；现有目录受覆盖保护。
