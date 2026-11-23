import { useEffect, useMemo, useState } from 'react'
import { ArrowUpRight, AudioLines, Cpu, Download, HeartPulse, Pause, Play, RotateCcw, ScanLine, Signal } from 'lucide-react'
import lessonVideo from '../assets/patch-ultrasound-lesson.mp4?url'
import { acquireRF, patchDefaults, reconstructDAS } from '../data/beamforming.js'
import { cineMarkers, cineSeries, homeCine } from '../data/camus.js'
import { AcquisitionDiagram, DASImage, RFDiagram } from './BeamformingVisual.jsx'
import { CineImage } from './CineImage.jsx'
import { MonitorChart } from './MonitorChart.jsx'
import { Badge, Panel } from './UI.jsx'
import styles from '../styles/Monitor.module.css'

const chapters = [
  { title: '贴片采集', icon: Cpu, source: '贴片阵列仿真', duration: 6, caption: '平面脉冲扫过组织。反射回波沿不同路径返回阵元，形成独立的接收通道。' },
  { title: 'RF 回波', icon: AudioLines, source: '模拟通道数据', duration: 6, caption: '以固定采样率记录各通道电信号。琥珀色标记对应同一散射点在各通道的到达时刻。' },
  { title: 'DAS 成像', icon: Signal, source: '浏览器重建', duration: 7, caption: '延时 τ =（发射路径 + 接收路径）/ 声速。按各通道的 τ 插值取样并求和，经近似包络检测与对数压缩生成灰阶图。' },
  { title: '左室分割', icon: ScanLine, source: 'CAMUS A2C', duration: 6, caption: '切换至 CAMUS 公开 B 超影像。DRA-UNet 对全部帧生成左心室掩膜，绿色显示预测区域。' },
  { title: '指标计算', icon: HeartPulse, source: 'CAMUS A2C', duration: 7, caption: '对每帧的预测掩膜计算单平面 Simpson 容积，由 ED 峰和 ES 谷得到 SV、EF。该片段为半周期，HR 与 CO 缺测。' },
]
let totalDuration = 0
const timeline = chapters.map(chapter => {
  const start = totalDuration
  totalDuration += chapter.duration
  return { ...chapter, start }
})
const series = cineSeries(homeCine)
const markers = cineMarkers(homeCine, series)
const [event] = homeCine.events

const controls = [
  { key: 'channels', title: '接收阵元数', unit: '个', min: 4, max: 24, step: 1 },
  { key: 'pitch', title: '阵元中心距', unit: 'mm', min: 0.4, max: 1.4, step: 0.1 },
  { key: 'frequency', title: '中心频率', unit: 'MHz', min: 2, max: 5, step: 0.1 },
  { key: 'sampleRate', title: 'RF 采样率', unit: 'MHz', min: 12, max: 40, step: 1 },
  { key: 'depth', title: '成像深度', unit: 'mm', min: 30, max: 90, step: 1 },
]

export function PatchLesson() {
  const [params, setParams] = useState(patchDefaults)
  const [time, setTime] = useState(0)
  const [playing, setPlaying] = useState(false)
  const active = timeline.findLastIndex(chapter => chapter.start <= time)
  const current = timeline[active]
  const progress = Math.min(1, (time - current.start) / current.duration)
  const rf = useMemo(() => acquireRF(params), [params])
  const image = useMemo(() => active === 2 ? reconstructDAS(rf, params) : null, [active, rf, params])
  const frame = Math.min(series.length - 1, Math.floor(progress * series.length))

  useEffect(() => {
    if (!playing) return undefined
    let previous = performance.now()
    const clock = window.setInterval(() => {
      const now = performance.now()
      const delta = (now - previous) / 1000
      previous = now
      setTime(value => Math.min(totalDuration, value + delta))
    }, 50)
    return () => window.clearInterval(clock)
  }, [playing])

  useEffect(() => {
    if (time >= totalDuration) setPlaying(false)
  }, [time])

  function seek(value) {
    setPlaying(false)
    setTime(value)
  }

  return <Panel title="贴片超声仿真教学" subtitle="从阵元采集到左心室分割与心功能指标"
    action={<a className={styles.download} href={lessonVideo} download="patch-ultrasound-lesson.mp4"><Download size={15} /> 下载教学视频</a>}>
    <div className={styles.lessonGrid}>
      <div className={styles.lesson}>
        <div className={styles.chapters} aria-label="教学章节">
          {timeline.map(({ title, icon: Icon, start }, index) => <button key={title} type="button"
            aria-pressed={index === active} onClick={() => seek(start)}><Icon size={15} />{title}</button>)}
        </div>
        <div className={styles.lessonStage} id="lesson-stage">
          <div className={styles.stageHeader}><h3>{current.title}</h3><Badge tone="blue">{current.source}</Badge></div>
          <div className={styles.stageVisual}>
            {active === 0 && <AcquisitionDiagram rf={rf} depth={params.depth} progress={progress} />}
            {active === 1 && <RFDiagram rf={rf} sampleRate={params.sampleRate} progress={progress} />}
            {active === 2 && <DASImage image={image} depth={params.depth} progress={progress} />}
            {active === 3 && <div className={styles.lessonCine}><CineImage cine={homeCine} index={frame} /></div>}
            {active === 4 && <div className={styles.lessonMetrics}>
              <MonitorChart series={series} cursor={series[frame]} events={markers} duration={series.at(-1).time} />
              {event && <p>EDV {event.EDV.toFixed(1)} mL · ESV {event.ESV.toFixed(1)} mL · SV {event.SV.toFixed(1)} mL · EF {event.EF_percent.toFixed(1)}%</p>}
            </div>}
          </div>
          <p className={styles.caption}>{current.caption}</p>
          {active >= 3 && <p className={styles.source}>CAMUS · Leclerc 等，IEEE TMI 2019 · CC BY-NC-SA 4.0</p>}
        </div>
        <div className={styles.cineControls}>
          <button type="button" className={styles.primary} onClick={() => {
            if (time >= totalDuration) setTime(0)
            setPlaying(!playing)
          }}>{playing ? <Pause size={16} /> : <Play size={16} />}{playing ? '暂停教学' : '播放教学'}</button>
          <label className={styles.lessonSeek}>
            <input type="range" aria-label="教学视频进度" min="0" max={totalDuration} step="0.05" value={time}
              onChange={e => seek(Number(e.target.value))} />
            <span>{Math.floor(time)} / {totalDuration} s</span>
          </label>
        </div>
      </div>
      <aside className={styles.hardware} aria-labelledby="patch-params">
        <div className={styles.hardwareHeader}>
          <h3 id="patch-params">贴片硬件参数</h3>
          <button type="button" className={styles.iconButton} aria-label="重置硬件参数" title="重置硬件参数"
            onClick={() => setParams(patchDefaults)}><RotateCcw size={16} /></button>
        </div>
        <p>调整参数，观察 RF 回波和 DAS 图像随之变化。</p>
        {controls.map(({ key, title, unit, min, max, step }) => <label className={styles.parameter} key={key}>
          <span>{title} <output>{params[key].toFixed(step < 1 ? 1 : 0)} {unit}</output></span>
          <input type="range" aria-label={title} min={min} max={max} step={step} value={params[key]}
            onChange={e => {
              const value = Number(e.target.value)
              setParams(values => ({ ...values, [key]: value }))
            }} />
        </label>)}
        <p><strong>仿真假设</strong> 正入射平面波，均匀声速 1540 m/s。8 阵元、1.20 mm 中心距取自教学阵列设计，频率、采样率及深度为仿真设定。</p>
        <a href="https://github.com/KNN334/Echo/blob/main/docs/patch_acquisition_workflow.md" target="_blank" rel="noreferrer">采集与 DAS 方法 <ArrowUpRight size={13} /></a>
      </aside>
    </div>
  </Panel>
}
