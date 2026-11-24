import { useEffect, useRef } from 'react'
import { Activity, ArrowRight, Focus, HeartPulse, Layers3, Ruler, ShieldCheck } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { CineMonitor } from '../components/CineMonitor.jsx'
import { ApiStatus } from '../components/ApiStatus.jsx'
import { PatchLesson } from '../components/PatchLesson.jsx'
import { ActionLink, Badge, MetricCard, Panel, TextLink } from '../components/UI.jsx'
import { modules, researchSources } from '../data/research.js'
import { apiEnabled, useApi } from '../data/api.js'
import styles from '../styles/Pages.module.css'

const metrics = [
  { key: 'Dice', title: 'Dice 相似度', value: '0.933', description: '左心室掩膜 · 患者均值', icon: Layers3, tint: 'blue' },
  { key: 'ASSD', title: 'ASSD 边界距离', value: '1.44', unit: 'mm', description: '对称平均表面距离', icon: Ruler, tint: 'cyan' },
  { key: 'HD95', title: 'HD95 边界距离', value: '3.88', unit: 'mm', description: '双向边界距离第 95 百分位', icon: Focus, tint: 'violet' },
  { key: '标注帧容积估算', title: '容积估算 MAE', value: '7.59', unit: 'mL', description: 'ED / ES · 同几何法参考', icon: HeartPulse, tint: 'indigo' },
]

const workflow = [
  [modules[0], '数据准备', 'CAMUS · 患者级划分'],
  [modules[1], '左心室分割', 'DRA-UNet · 逐帧推理'],
  [modules[2], '几何与容积', 'PCA · Simpson 圆盘'],
  [modules[3], '心功能评估', 'EDV / ESV / SV / EF'],
  [modules[5], '评价与可视化', '掩膜对比 · 容积曲线'],
]

function PulseGraphic() {
  const canvas = useRef(null)
  useEffect(() => {
    const context = canvas.current.getContext('2d')
    const points = [[0, 0], [.14, 0], [.21, -7], [.27, 0], [.34, 0], [.38, 12],
      [.42, -73], [.47, 40], [.53, 0], [.62, 0], [.69, -12], [.75, -15], [.83, 0], [1, 0]]
    const gradient = context.createLinearGradient(0, 0, 960, 0)
    gradient.addColorStop(0, '#6fb9ff00')
    gradient.addColorStop(.26, '#80c7ff')
    gradient.addColorStop(.72, '#9be5ff')
    gradient.addColorStop(1, '#6fb9ff10')
    context.lineWidth = 2.5
    context.lineJoin = 'round'
    context.lineCap = 'round'
    context.strokeStyle = gradient
    context.shadowColor = '#3dc6ff'
    context.shadowBlur = 18
    context.beginPath()
    context.moveTo(0, 163)
    for (let beat = 0; beat < 3; beat++) {
      for (const [time, amplitude] of points) {
        context.lineTo(beat * 340 + time * 340, 163 + amplitude * (beat === 1 ? 2.1 : .75))
      }
    }
    context.stroke()
  }, [])
  return <div className={styles.heroGraphic} aria-hidden="true">
    <div className={styles.heroRings} />
    <canvas ref={canvas} width="960" height="316" />
    <div className={styles.signalMarker}><Activity size={15} /> DRA-UNet</div>
  </div>
}

export default function Overview() {
  const { hash } = useLocation()
  const report = useApi('/api/overview?study=dra')
  const available = !apiEnabled || (report.data && !report.data.warnings.length)
  const cards = metrics.map(item => {
    if (!apiEnabled) return item
    const value = report.data?.segmentation.find(row => row.metric === item.key)?.value
      ?? report.data?.function_mae.find(row => row.metric === item.key)?.mae
    return { ...item, value: value?.toFixed(item.key === 'Dice' ? 3 : 2) ?? '—' }
  })
  useEffect(() => {
    if (hash === '#simulation') document.getElementById('simulation')?.scrollIntoView()
  }, [hash])

  return <div className={styles.stack}>
    <section className={styles.hero} aria-labelledby="system-title">
      <PulseGraphic />
      <div className={styles.heroContent}>
        <div className={styles.heroLabel}><ShieldCheck size={15} /> 研究基线 · 非临床验证</div>
        <h1 id="system-title">超声智能心脏功能评估系统</h1>
        <p>基于超声心动图的左心室分割、容积测量与心功能分析。</p>
        <div className={styles.heroActions}>
          <ActionLink to="/segment" primary>上传影像并分割</ActionLink>
          <ActionLink to="/#simulation" arrow={false}>观看贴片超声教学</ActionLink>
          <ActionLink to="/results" arrow={false}>查看评估结果</ActionLink>
        </div>
      </div>
    </section>
    <CineMonitor />
    <div className={styles.anchor} id="simulation"><PatchLesson /></div>
    <section aria-labelledby="overview-eval">
      <div className={styles.sectionHeading}>
        <div><h2 id="overview-eval">模型评估概览</h2>
          {available && <p>{apiEnabled ? `${report.data.model} · ${report.data.scope} · ${report.data.patients} 名患者` : 'DRA-UNet · CAMUS 验证集 · 50 名患者 · 3 个种子均值'}</p>}
        </div>
        <Badge tone="blue">验证集</Badge>
      </div>
      {available ? <div className={styles.metrics}>{cards.map(item => <MetricCard key={item.title} item={item} />)}</div>
        : <ApiStatus request={report} />}
    </section>
    <Panel title="评估工作流" subtitle="从超声影像到患者级评估">
      <div className={styles.workflow}>{workflow.map(([mod, title, caption]) => (
        <Link key={mod.id} to={`/features#${mod.id}`} className={styles.step}>
          <span className={styles.stepIcon}><mod.icon size={20} strokeWidth={1.8} /></span>
          <span className={styles.stepCopy}><strong>{title}</strong><small>{caption}</small></span>
          <ArrowRight className={styles.stepArrow} size={15} />
        </Link>
      ))}</div>
    </Panel>
    <section aria-labelledby="overview-features">
      <div className={styles.sectionHeading}>
        <div><h2 id="overview-features">核心能力</h2><p>查看各环节的方法与源码</p></div>
        <TextLink to="/features">浏览全部</TextLink>
      </div>
      <div className={styles.featureGrid}>{modules.map(({ id, icon: Icon, title, summary }) => (
        <Link key={id} to={`/features#${id}`} className={styles.featureLink}>
          <span className={styles.stepIcon}><Icon size={19} strokeWidth={1.8} /></span>
          <span className={styles.stepCopy}><strong>{title}</strong><small>{summary}</small></span>
          <ArrowRight size={15} className={styles.featureArrow} />
        </Link>
      ))}</div>
    </section>
    <p className={styles.footnote}>指标来自三种子消融报告。EF 和各相位容积的分项 MAE 详见结果评估。 <a href={researchSources.dra} target="_blank" rel="noreferrer">查看实验报告</a></p>
  </div>
}
