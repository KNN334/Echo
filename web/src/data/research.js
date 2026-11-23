import { Activity, ChartNoAxesCombined, Database, Frame, HeartPulse, ScanLine } from 'lucide-react'

export const modules = [
  { id: 'data', icon: Database, title: '数据准备与划分', summary: '读取影像与标注，按患者划分数据集。', detail: '核查原始文件、像素间距和时间信息，保留 ED/ES 标注与坐标变换。归一化参数仅从训练集计算。', source: 'lvseg/data' },
  { id: 'segmentation', icon: ScanLine, title: '左心室分割', summary: '用 DRA-UNet 逐帧提取左心室掩膜。', detail: '空洞残差编码器提取空间特征，ConvLSTM 在瓶颈融合当前帧及最多两帧历史。Attention Gate 筛选跳连，边缘分支辅助 ED/ES 标注帧监督。现行模型直接接收单通道灰度图像。', source: 'lvseg/models/ablation.py' },
  { id: 'geometry', icon: Frame, title: '几何与容积测量', summary: '从分割轮廓估计主轴与逐帧容积。', detail: '将掩膜还原到原始尺寸，在毫米坐标中用 PCA 估计长轴，再以 20 个圆盘完成单平面 Simpson 容积估计。同步配对并标定后可使用双平面圆盘接口。', source: 'lvseg/metrics/volume.py' },
  { id: 'function', icon: HeartPulse, title: '心功能评估', summary: '由 EDV、ESV 派生 SV 和 EF。', detail: 'SV = EDV − ESV，EF = SV / EDV × 100%。CO 需要可用的 SV 和可靠 HR，并换算到 L/min。', source: 'lvseg/metrics/cycles.py' },
  { id: 'temporal', icon: Activity, title: '时序与质量控制', summary: '检查序列时间、曲线峰谷和测量缺口。', detail: '沿原始帧序处理视频，标记无效几何、缺帧与峰谷不足的情况。心率估计需要可靠时间和完整心动周期。', source: 'lvseg/metrics/cycles.py' },
  { id: 'evaluation', icon: ChartNoAxesCombined, title: '评价与可视化', summary: '汇总边界误差、轮廓和容积曲线。', detail: '按患者汇总有标签帧的 Dice、ASSD 与 HD95。预测和专家掩膜应用相同几何法后可比较容积差值和一致性。', source: 'lvseg/metrics · lvseg/visualization' },
]

export const researchSources = {
  dra: 'https://github.com/KNN334/Echo/blob/main/reports/lvseg_ablation/RESULTS.md',
  legacy: 'https://github.com/KNN334/Echo/blob/main/reports/full_baseline/RESULTS.md',
}
export const evaluations = {
  dra: {
    title: 'DRA-UNet',
    scope: 'CAMUS 验证集 · 50 名患者 · 3 个种子',
    segmentation: [
      ['Dice', '0.933', '患者均值'],
      ['ASSD', '1.44 mm', '对称平均边界距离'],
      ['HD95', '3.88 mm', '双向边界距离的第 95 百分位'],
      ['轮廓派生关键点误差', null, 'DRA-UNet 消融报告未提供此项'],
      ['人工解剖关键点误差', null, '缺少独立人工关键点标注'],
    ],
    functional: [
      ['标注帧容积估算', '7.59', null, null, null, 'mL', '专家轮廓经同一单平面 Simpson 几何法派生'],
      ...['EDV', 'ESV', 'SV', 'EF'].map(metric => [metric, null, null, null, null, metric === 'EF' ? '百分点' : 'mL', 'DRA-UNet 分项结果未发布']),
      ['CO', null, null, null, null, 'L/min', '缺少可靠心率与独立 CO 参考'],
    ],
  },
  legacy: {
    title: '历史基线',
    scope: 'CAMUS 测试集 · 82 名患者 · 328 个标注帧',
    segmentation: [
      ['Dice', '0.9125', '患者均值'],
      ['ASSD', '1.94 mm', '对称平均边界距离'],
      ['HD95', '4.76 mm', '双向边界距离的第 95 百分位'],
      ['轮廓派生关键点误差', '5.39 mm', '由预测与专家轮廓分别派生的几何代理误差'],
      ['人工解剖关键点误差', null, '缺少独立人工关键点标注'],
    ],
    functional: [
      ['EDV', '8.91', '−2.19', '7.71 至 10.22', '−22.72 至 18.34', 'mL'],
      ['ESV', '6.11', '+1.31', '5.08 至 7.17', '−14.14 至 16.76', 'mL'],
      ['SV', '8.05', '−3.50', '6.92 至 9.20', '−21.54 至 14.53', 'mL'],
      ['EF', '9.62', '−5.61', '7.81 至 11.72', '−29.06 至 17.84', '百分点'],
      ['CO', null, null, null, null, 'L/min', '缺少可靠心率与独立 CO 参考'],
    ],
  },
}
