# 超声智能心脏功能评估系统

EchoLab 提供概览、项目介绍、核心能力、结果评估、患者列表和患者详情。页面使用 React、React Router、Vite、CSS Modules 与 Recharts，可作为免登录站点静态托管。

## 本地预览与构建

使用 Node.js 22.12 或更新的 LTS 版本。在仓库根目录运行以下命令。

```powershell
cd web
npm ci
npm run dev
```

`npm run build` 生成 `web/dist/`。在 `web/` 下运行 `npm run preview` 可通过本地 HTTP 检查生产构建。

## 静态托管

1. 在 Vercel 或 Netlify 关联源码仓库，将项目根目录设为 `web`，安装命令设为 `npm ci`。
2. 将构建命令设为 `npm run build`，输出目录设为 `dist`，发布后通过平台分配的网址访问。若使用对象存储静态托管，将 `dist` 中的文件原样上传，并设置 `index.html` 为索引页。
3. 打开部署网址下的 `#/patients/DEMO-001` 并刷新页面，确认详情和图表可用。Vite 使用相对资源路径，HashRouter 将路由保留在网址片段中。

## 数据口径

- 概览与默认结果页引用 DRA-UNet 的 CAMUS 验证集消融结果，覆盖 50 名患者和三个种子。容积 MAE 是标注帧使用相同 Simpson 几何法的差值。EDV、ESV、SV、EF 分项及人工关键点误差缺测，表格列出原因。[DRA-UNet 报告](../reports/lvseg_ablation/RESULTS.md)
- 结果页的“历史基线”显示 82 名测试患者的早期 EchoNet 架构适配结果，包括同几何法参考下的心功能 MAE、偏倚和一致性界限。[历史基线报告](../reports/full_baseline/RESULTS.md)
- `src/data/patients.js` 提供与 `patient_features.csv` 对齐的虚构记录和容积序列。后续接入 API 可在这一层替换数据源。轮廓图为合成示意，训练 BCE 曲线为示例序列。
- 页面统一标明“研究基线 · 非临床验证”。CAMUS 影像数据和 EchoNet 代码遵循各自许可。[CAMUS 数据许可](../docs/data_sources/CAMUS_LICENSE_TERMS.md) · [EchoNet 代码许可](https://github.com/echonet/dynamic/blob/master/LICENSE)
