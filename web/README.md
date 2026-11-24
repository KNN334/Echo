# 超声智能心脏功能评估系统

EchoLab 提供概览、项目介绍、核心能力、结果评估、患者列表和患者详情。页面使用 React、React Router、Vite、CSS Modules 与 Recharts，支持静态展示及 FastAPI 接入。

## 本地预览与构建

使用 Node.js 22.12 或更新的 LTS 版本。在仓库根目录运行以下命令。

```powershell
cd web
npm.cmd ci
npm.cmd run dev
```

`npm run build` 生成 `web/dist/`。在 `web/` 下运行 `npm run preview` 可通过本地 HTTP 检查生产构建。

## 接入后端

按 [后端启动说明](../backend/README.md) 启动 FastAPI 后，在 `web/` 目录运行以下命令。

```powershell
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
npm.cmd run dev
```

该变量在 Vite 启动或构建时读取，省略时使用打包的公开报表与影像。配置后，概览、评估结果、病例查询与详情从后端读取。患者页可切换 DRA-UNet A2C 回放或历史双平面报表，并在上传启用时存档去标识影像。首页分割回放和贴片超声教学使用已经导出的公开素材。

## 静态托管

Echo 仓库通过 GitHub Actions 将 `main` 分支的 `web/` 构建发布到 GitHub Pages。修改 `web/` 后推送至 `main` 即可触发更新。[公开站点](https://knn334.github.io/Echo/) · [部署记录](https://github.com/KNN334/Echo/actions/workflows/pages.yml)

在其他静态托管平台部署时，按以下步骤配置。

1. 在 Vercel 或 Netlify 关联源码仓库，将项目根目录设为 `web`，安装命令设为 `npm ci`。
2. 将构建命令设为 `npm run build`，输出目录设为 `dist`，发布后通过平台分配的网址访问。若使用对象存储静态托管，将 `dist` 中的文件原样上传，并设置 `index.html` 为索引页。
3. 打开部署网址下的 `#/patients/patient0015` 并刷新页面，确认详情和图表可用。Vite 使用相对资源路径，HashRouter 将路由保留在网址片段中。

## 数据口径

- 概览与默认结果页引用 DRA-UNet 的 CAMUS 验证集消融结果，覆盖 50 名患者和三个种子。容积 MAE 是标注帧使用相同 Simpson 几何法的差值。EDV、ESV、SV、EF 分项及人工关键点误差缺测，表格列出原因。[DRA-UNet 报告](../reports/lvseg_ablation/RESULTS.md)
- 结果页的“历史基线”显示 82 名测试患者的早期 EchoNet 架构适配结果，包括同几何法参考下的心功能 MAE、偏倚和一致性界限。[历史基线报告](../reports/full_baseline/RESULTS.md)
- 首页和患者页显示固定测试集按公开 ID 排序取前十名的 CAMUS A2C 影像。DRA-UNet（种子 2026）在离线阶段逐帧分割，网页按采集顺序回放掩膜及容积。专家轮廓派生参考和预测曲线峰谷使用同一单平面 Simpson 几何法。结果页的损失曲线来自该种子的实际训练日志。可在仓库根目录运行 `python scripts/export_web_cine.py` 重新导出，需先准备公开数据、检查点及其训练日志。
- **贴片超声仿真教学**支持分章节播放、暂停和拖动，也可下载 32 秒带字幕 MP4。硬件参数作用于模拟 RF 和 DAS 计算。模拟采用均匀声速与正入射平面波，重建图展示点散射体。左室分割和指标章节使用已成像的 CAMUS 视频。教案中的 8 阵元和 1.20 mm 中心距对应教学阵列，其余为仿真设定。[采集与 DAS 方法](../docs/patch_acquisition_workflow.md)
- 页面统一标明“研究基线 · 非临床验证”。CAMUS 影像数据和 EchoNet 代码遵循各自许可。[CAMUS 数据许可](../docs/data_sources/CAMUS_LICENSE_TERMS.md) · [EchoNet 代码许可](https://github.com/echonet/dynamic/blob/master/LICENSE)
