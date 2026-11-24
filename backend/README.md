# EchoLab 后端

FastAPI 服务提供公开 CAMUS 报表查询及上传影像的 DRA-UNet 左心室分割。报表在启动时加载到内存，替换报表后重启服务。上传与报表查询使用独立存储。**研究基线 · 非临床验证。**

## 本地启动

需要 Python 3.10+。在仓库根目录执行以下命令。Windows 可将 `python` 换成 `.venv/Scripts/python.exe`。

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload --no-access-log
```

打开 [接口文档](http://127.0.0.1:8000/docs) 或 [服务状态](http://127.0.0.1:8000/api/health)。在 `backend/` 下也可使用 `python -m uvicorn app.main:app --reload --no-access-log`。

本机启用推理时，先从种子 2026 的私有 PyTorch 权重导出 ONNX。导出程序校验源权重、保留训练归一化与三帧因果上下文，并输出 ONNX 的 SHA-256。

```powershell
python -m pip install torch onnx
python -m backend.export_model runs/lvseg_ablation/seed_2026/DTE/best.pt .work/dra-unet-seed2026.onnx
python -m pip install -r backend/requirements-inference.txt
$env:ECHO_UPLOADS_ENABLED = 'true'
$env:ECHO_INFERENCE_CHECKPOINT = '.work/dra-unet-seed2026.onnx'
python -m uvicorn backend.app.main:app --no-access-log
```

从 [前端说明](../web/README.md) 设置本地 API 地址，然后在「影像分割」上传去标识的 MP4、AVI、PNG 或 JPEG。视频按解码顺序逐帧分割，网页并排回放原始灰阶影像及预测掩膜。DICOM 可先从超声设备导出为去标识的 MP4。

## 接口和数据来源

| 方法 | 路径 | 内容 |
| --- | --- | --- |
| GET | `/api/health` | 报表加载、上传配置及推理状态 |
| GET | `/api/overview` | 患者与标注帧数、分割指标、心功能 MAE 与评估流程 |
| GET | `/api/results/segmentation` | 分割指标、单位、原始评价口径与缺测原因 |
| GET | `/api/results/function` | MAE、偏倚、95% 置信区间、一致性界限、有效人数与覆盖率 |
| GET | `/api/results/training-history` | 按训练轮次返回损失 |
| GET | `/api/patients` | 搜索、排序、问题筛选与分页 |
| GET | `/api/patients/{patient_id}` | 预测、参考、配对误差、ED/ES 叠图与逐帧容积（如有） |
| POST | `/api/upload?for_inference=true` | 校验并存档待推理影像，表单须提交 `deidentified=true` |
| POST | `/api/inference/{case_id}` | 提交已上传影像的分割任务，返回 `202` |
| GET | `/api/inference/{case_id}/status` | 读取任务状态、处理帧数或失败原因 |
| GET | `/api/inference/{case_id}/result` | 已完成的分割回放数据及受限影像地址 |

- 报表和公开病例接口接受 `study=legacy` 或 `study=dra`。默认 `legacy` 读取 `reports/full_baseline/`，对应 DeepLabV3-ResNet50 在 CAMUS 固定测试集的 82 名患者、328 个标注帧，患者测量使用专家标注相位与同几何法双平面参考，训练日志为 mean BCE。
- `study=dra` 的评估读取 `reports/lvseg_ablation/results.json` 内 DTE 的 CAMUS 50 人验证集结果，训练曲线为种子 2026 的真实 BCE + Dice 主分割损失。病例查询读取 `web/src/assets/camus-cases.json`，对应 10 名固定测试集公开 A2C 回放病例。病例叠图来自同目录发布的 WebP，曲线保留所有已发布帧及有效峰谷。历史双平面报表的逐帧曲线、独立轮廓点列及 DRA 平滑曲线目前缺测，接口返回 `null` 与原因。
- EF 数值用 `%`，误差用百分点。HR、CO、独立人工解剖关键点等缺测时返回 `null`，并注明具体原因。容积差值的参考由专家掩膜经同一几何法派生。公开回放遵循 CAMUS 的 CC BY-NC-SA 4.0。 [数据许可与署名](../docs/data_sources/CAMUS_LICENSE_TERMS.md)
- 患者查询支持 `search`、`sort_by`、`order`、`issue_filter`、`page` 与 `page_size`。例如 [按 EF 降序查询历史病例](http://127.0.0.1:8000/api/patients?sort_by=EF&order=desc&page_size=8)。
- 缺少或损坏的报表在 `/api/health` 标为 `missing` 或 `invalid`。评估接口返回降级提示与空结果。病例报表不可用时返回 `503`。

## 环境变量

列表值使用 JSON 数组，CORS 来源也可用逗号分隔。默认目录以仓库根目录为基准。

| 变量 | 默认值 |
| --- | --- |
| `ECHO_REPORTS_DIR` | `reports/full_baseline` |
| `ECHO_DRA_RESULTS_FILE` | `reports/lvseg_ablation/results.json` |
| `ECHO_CAMUS_ASSETS_DIR` | `web/src/assets` |
| `ECHO_CORS_ORIGINS` | `["http://localhost:5173","http://127.0.0.1:5173"]` |
| `ECHO_UPLOADS_ENABLED` | `false` |
| `ECHO_UPLOAD_DIR` | `backend/data/uploads` |
| `ECHO_UPLOAD_MAX_BYTES` | `52428800`（50 MiB） |
| `ECHO_UPLOAD_FORMATS` | `[".png",".jpg",".jpeg",".avi",".mp4",".zip"]` |
| `ECHO_INFERENCE_CHECKPOINT` | 私有 ONNX 路径，默认留空 |
| `ECHO_INFERENCE_SHA256` | ONNX SHA-256，Render 下载模型时必填 |
| `ECHO_INFERENCE_MAX_FRAMES` | `300`，Render Blueprint 设置为 `180` |

存档使用随机 UUID 目录，元数据保存存档文件名、大小、时间和校验状态。文件内容保留原件，上传前由用户确认已去标识。预测和分割影像只通过随机病例 ID 查询，响应禁止公共缓存。部署时为存储配置访问限制、磁盘配额和清理周期。

## Render 部署与原网址接入

1. 在 Render 登录并连接 `KNN334/Echo`，选择 **New → Blueprint** 应用仓库中的 [render.yaml](../render.yaml)。也可新建 Python Web Service，根目录用整个仓库，复制 Blueprint 的构建和启动命令。Uvicorn 监听 Render 注入的 `$PORT`，每个实例启动一个推理 worker。
2. 将导出的 ONNX 保存在有权限控制的私有存储。在 Blueprint 表单填写 `ECHO_CHECKPOINT_URL`（Render 可访问的私有 HTTPS 源）、`ECHO_INFERENCE_SHA256` 和 `ECHO_CHECKPOINT_TOKEN`。使用私有 GitHub Release 时，填写资产的 API 地址和仅对模型仓库授予 **Contents: Read-only** 的细粒度令牌。Render 每次冷启动都可能重新读取模型。将令牌直接填写在 Render 中。 [创建细粒度令牌](https://github.com/settings/personal-access-tokens/new)
3. `ECHO_CORS_ORIGINS` 设置为 `https://knn334.github.io,http://localhost:5173,http://127.0.0.1:5173`。网页来源只包含协议、域名和端口。Render 地址分配后，用公网 HTTPS 测试 `/docs` 和 `/api/health`，确认 `inference_enabled` 为 `true`。
4. 在 GitHub 仓库的 **Settings → Secrets and variables → Actions → Variables** 设置 `VITE_API_BASE_URL` 为 Render 分配的实际 HTTPS 地址，再运行 [Publish EchoLab](https://github.com/KNN334/Echo/actions/workflows/pages.yml)。通过原网址打开「影像分割」并上传一段已有授权的公开研究影像。 [影像分割](https://knn334.github.io/Echo/#/segment)

Blueprint 的免费实例使用 ONNX Runtime CPU，空闲时会休眠，上传和分割结果保存在临时磁盘。首次访问须等待唤醒。长期保存研究数据需要另配私有持久化存储。 [Render 免费实例说明](https://render.com/docs/free)

## 验证

```powershell
python -m pip install -r backend/requirements-test.txt
python -m pytest -q backend/tests --basetemp=.work/pytest-echo-backend
```

可通过 `ECHO_TEST_INFERENCE_MODEL` 和 `ECHO_TEST_CINE` 指向私有 ONNX 与已授权的 CAMUS A2C 视频，运行真实上传、分割与回放集成测试。

对带像素标注的 PNG 检查集，可在同一份 ONNX 上复核方向校正。原方向与自动校正的结果都转换回原图分辨率，再按左室腔标注计算图像级 Dice 和 IoU。将 `85` 替换为该数据的左室腔标签编码。

```powershell
python -m backend.validate_orientation .work/dra-unet-seed2026.onnx path/to/test_images path/to/test_masks --mask-value 85
```
