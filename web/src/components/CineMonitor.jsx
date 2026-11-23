import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, Pause, Play, RotateCcw } from 'lucide-react'
import { cineMarkers, cineSeries, homeCine as preview } from '../data/camus.js'
import { CineImage } from './CineImage.jsx'
import { Badge, Missing, Panel } from './UI.jsx'
import { MonitorChart } from './MonitorChart.jsx'
import styles from '../styles/Monitor.module.css'

const series = cineSeries(preview)
const [event] = preview.events
const markers = cineMarkers(preview, series)
const last = series.length - 1
const cycleReason = 'CAMUS 半周期，缺少相邻的 EDV 峰'

function Result({ label, value, unit, digits = 1, reason = cycleReason }) {
  return <div className={styles.result}>
    <dt>{label}</dt>
    <dd>{value == null ? <Missing reason={reason} /> : <>{value.toFixed(digits)} <small>{unit}</small></>}</dd>
  </div>
}

export function CineMonitor() {
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(0.125)
  const [ready, setReady] = useState(false)
  const cursor = series[index]
  const predictionPhase = index === event?.ed_frame ? 'ED 峰' : index === event?.es_frame ? 'ES 谷' : null
  const expertPhase = Object.entries(preview.expert_phases).find(([, frame]) => frame === index)?.[0]

  useEffect(() => {
    if (!playing || !ready) return undefined
    if (index === last) {
      setPlaying(false)
      return undefined
    }
    const delay = (series[index + 1].time - cursor.time) / speed
    const timer = window.setTimeout(() => setIndex(index + 1), delay)
    return () => window.clearTimeout(timer)
  }, [index, cursor.time, ready, playing, speed])

  function seek(frame) {
    setPlaying(false)
    setIndex(Math.max(0, Math.min(last, frame)))
  }

  function togglePlayback() {
    if (playing) {
      setPlaying(false)
      return
    }
    if (index === last) setIndex(0)
    setPlaying(true)
  }

  return <div className={styles.monitorGrid}>
    <Panel title="左心室逐帧分割" subtitle="DRA-UNet · CAMUS A2C · 原始帧序"
      action={<Badge tone="blue">分割回放</Badge>}>
      <div className={styles.cineContent}>
        <CineImage cine={preview} index={index} onReady={setReady}>
          <span className={styles.viewMarker}>A2C · {preview.fps} fps</span>
          <span className={styles.frameTag}>{cursor.time.toFixed(1)} ms</span>
        </CineImage>
        <div className={styles.cineControls}>
          <button type="button" className={styles.primary} disabled={!ready} onClick={togglePlayback}>
            {playing ? <Pause size={16} /> : <Play size={16} />}{playing ? '暂停' : '播放'}
          </button>
          <button type="button" className={styles.iconButton} aria-label="回到首帧" title="回到首帧"
            disabled={!ready} onClick={() => seek(0)}><RotateCcw size={16} /></button>
          <button type="button" className={styles.iconButton} aria-label="上一帧" title="上一帧"
            disabled={!ready || index === 0} onClick={() => seek(index - 1)}><ChevronLeft size={17} /></button>
          <button type="button" className={styles.iconButton} aria-label="下一帧" title="下一帧"
            disabled={!ready || index === last} onClick={() => seek(index + 1)}><ChevronRight size={17} /></button>
          <select className={styles.speed} aria-label="播放速度" value={speed} onChange={e => setSpeed(Number(e.target.value))}>
            <option value={0.125}>⅛×</option><option value={0.25}>¼×</option><option value={0.5}>½×</option><option value={1}>1×</option>
          </select>
        </div>
        <label className={styles.seek}>
          <span>帧索引 <strong>{index} / {last}</strong></span>
          <input type="range" aria-label="帧索引" min="0" max={last} value={index} disabled={!ready}
            onChange={e => seek(Number(e.target.value))} />
        </label>
        <div className={styles.legend}>
          <span><i className={styles.maskKey} />DRA-UNet 掩膜</span>
          <span><i className={styles.expertKey} />专家轮廓{expertPhase ? ` · ${expertPhase}` : ' · 本帧无标注'}</span>
        </div>
        <p className={styles.source}>Leclerc 等，CAMUS · 原预览经裁切与缩放 · <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank" rel="noreferrer">CC BY-NC-SA 4.0</a></p>
      </div>
    </Panel>
    <Panel title="指标计算" subtitle="当前帧容积及预测峰谷派生指标">
      <div className={styles.analysis}>
        <div className={styles.current}>
          <div><span>当前帧容积</span><strong data-testid="current-volume">{cursor.volume?.toFixed(1) ?? '—'} <small>mL</small></strong></div>
          <div><Badge tone="blue">{predictionPhase ?? '单平面 Simpson'}</Badge><small>采集时间 {cursor.time.toFixed(1)} ms</small></div>
        </div>
        <dl className={styles.results}>
          <Result label="EDV · 舒张末期" value={event?.EDV} unit="mL" reason="容积曲线缺少有效 ED 峰" />
          <Result label="ESV · 收缩末期" value={event?.ESV} unit="mL" reason="容积曲线缺少有效 ES 谷" />
          <Result label="SV · 每搏输出量" value={event?.SV} unit="mL" reason="缺少有效 EDV / ESV" />
          <Result label="EF · 射血分数" value={event?.EF_percent} unit="%" reason="缺少有效 EDV / ESV" />
          <Result label="HR · 心率" value={event?.HR_bpm} unit="次/分" />
          <Result label="CO · 心输出量" value={event?.CO_L_per_min} unit="L/min" />
        </dl>
        <div className={styles.chartTitle}><h3>左室容积曲线</h3><span>mL / ms</span></div>
        <MonitorChart series={series} cursor={cursor} events={markers} duration={series[last].time} />
        <p className={styles.source}>ED / ES 标签来自预测容积曲线。{cycleReason}，HR 和 CO 缺测。</p>
      </div>
    </Panel>
  </div>
}
