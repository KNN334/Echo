# EchoLab 后端

FastAPI 服务提供公开 CAMUS 报表查询和去标识影像存档。报表在启动时加载到内存，替换报表后重启服务。上传与报表查询使用独立存储。**研究基线 · 非临床验证。**

## 本地启动

需要 Python 3.10+。在仓库根目录执行以下命令。Windows 可将 `python` 换成 `.venv/Scripts/python.exe`。

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload --no-access-log
```

打开 [接口文档](http://127.0.0.1:8000/docs) 或 [服务状态](http://127.0.0.1:8000/api/health)。在 `backend/` 下也可使用 `python -m uvicorn app.main:app --reload --no-access-log`。

如需在本机验证上传，在启动后端前运行 `$env:ECHO_UPLOADS_ENABLED = 'true'`，并上传已去标识的影像。网页连接方式见 [前端说明](../web/README.md)。

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
| POST | `/api/upload` | 校验并存档 `file`，表单须提交 `deidentified=true` |
| POST | `/api/inference/{case_id}` | 预留推理请求与响应，返回 `501` |
| GET | `/api/inference/{case_id}/status` | 已存档病例返回 `disabled` |

- 报表和公开病例接口接受 `study=legacy` 或 `study=dra`。默认 `legacy` 读取 `reports/full_baseline/`，对应 DeepLabV3-ResNet50 在 CAMUS 固定测试集的 82 名患者、328 个标注帧，患者测量使用专家标注相位与同几何法双平面参考，训练日志为 mean BCE。
- `study=dra` 的评估读取 `reports/lvseg_ablation/results.json` 内 DTE 的 CAMUS 50 人验证集结果，训练曲线为种子 2026 的真实 BCE + Dice 主分割损失。病例查询读取 `web/src/assets/camus-cases.json`，对应 10 名固定测试集公开 A2C 回放病例。病例叠图来自同目录发布的 WebP，曲线保留所有已发布帧及有效峰谷。历史双平面报表的逐帧曲线、独立轮廓点列及 DRA 平滑曲线目前缺测，接口返回 `null` 与原因。
- EF 数值用 `%`，误差用百分点。HR、CO、独立人工解剖关键点等缺测时返回 `null`，并注明具体原因。容积差值的参考由专家掩膜经同一几何法派生。公开回放遵循 CAMUS 的 CC BY-NC-SA 4.0。 [数据许可与署名](../docs/data_sources/CAMUS_LICENSE_TERMS.md)
- 患者查询支持 `search`、`sort_by`、`order`、`issue_filter`、`page` 与 `page_size`。例如 [按 EF 降序查询历史病例](http://127.0.0.1:8000/api/patients?sort_by=EF&order=desc&page_size=8)。
- 缺少或损坏的报表在 `/api/health` 标为 `missing` 或 `invalid`。评估接口返回降级提示与空结果。病例报表不可用时返回 `503`。

## 环境变量

列表值使用 JSON 数组。默认目录以仓库根目录为基准。

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

存档使用随机 UUID 目录，文件重命名为 `original` 加扩展名，元数据保存存档文件名、大小、时间和校验状态。文件内容保留原件，格式签名校验无法验证画面和元数据是否已去标识。ZIP 作为原件存档。上传文件仅可从服务器存储目录管理。

## 公网部署

在 Python 主机安装依赖并部署仓库中的报表及公开站点素材。使用 Uvicorn 运行服务，通过 HTTPS 反向代理对外提供访问。下例适用于代理和 Uvicorn 在同一主机的情形。

```bash
export ECHO_CORS_ORIGINS='["https://knn334.github.io"]'
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

1. 为 Uvicorn 配置进程托管及 HTTPS 代理，在外部网络验证 `/api/health` 可访问。
2. 在 GitHub 仓库的 **Settings → Secrets and variables → Actions → Variables** 设置 `VITE_API_BASE_URL` 为后端 HTTPS 基础地址，不带 `/api`，然后重新运行 Pages 发布工作流。浏览器跨域来源使用 `https://knn334.github.io`，无需附带 `/Echo/`。
3. 公网无登录的实例保持上传关闭。开启内部上传时，将 `ECHO_UPLOAD_DIR` 指向独立持久化目录，限制磁盘配额、请求体大小和访问范围。反向代理日志也应避免记录提交的文件名或真实身份信息。

## 验证

```powershell
python -m pip install -r backend/requirements-test.txt
python -m pytest -q backend/tests --basetemp=.work/pytest-echo-backend
```
