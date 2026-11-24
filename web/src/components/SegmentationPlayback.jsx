import { useEffect, useState } from 'react'
import { Pause, Play } from 'lucide-react'
import { apiUrl } from '../data/api.js'
import { CineImage } from './CineImage.jsx'
import { Panel } from './UI.jsx'
import styles from '../styles/Pages.module.css'
import ui from '../styles/UI.module.css'

export function SegmentationPlayback({ result }) {
  const [frame, setFrame] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [loadedSheet, setLoadedSheet] = useState(null)
  const { atlas, frames, playback_fps: fps } = result
  const perSheet = atlas.rows * atlas.columns
  const sheet = Math.floor(frame / perSheet)

  useEffect(() => {
    if (!playing || sheet !== loadedSheet) return
    const timer = window.setTimeout(() => {
      if (frame + 1 >= frames) setPlaying(false)
      else setFrame(frame + 1)
    }, 1000 / (fps ?? 15))
    return () => window.clearTimeout(timer)
  }, [playing, sheet, loadedSheet, frame, frames, fps])

  const PlayIcon = playing ? Pause : Play
  return <Panel title="左心室分割结果" subtitle={`${result.model} · ${frames} 帧 · 耗时 ${result.elapsed_s.toFixed(1)} 秒`}>
    <div className={styles.segmentPlayback}>
      <div className={styles.segmentFrameLabels}><span>原始灰阶影像</span><span>左心室预测掩膜</span></div>
      <CineImage key={sheet} cine={{ atlas, atlasUrl: apiUrl(result.sheet_urls[sheet]) }} index={frame % perSheet}
        label={`第 ${frame + 1} 帧原始超声与左心室预测掩膜`} onReady={ready => setLoadedSheet(ready ? sheet : null)} />
      {frames > 1 && <div className={styles.segmentControl}>
        <button className={ui.secondaryButton} type="button" onClick={() => {
          if (!playing && frame + 1 >= frames) setFrame(0)
          setPlaying(!playing)
        }}><PlayIcon size={15} />{playing ? '暂停' : '播放'}</button>
        <input type="range" aria-label="分割结果帧" min="0" max={frames - 1} value={frame} onChange={event => {
          setPlaying(false)
          setFrame(Number(event.target.value))
        }} />
        <output>第 {frame + 1} / {frames} 帧</output>
      </div>}
      {result.quality_flags.map(flag => <p className={styles.footnote} key={flag}>{flag}</p>)}
      {Boolean(result.input_rotation_degrees) && <p className={styles.footnote}>已自动校正侧向声束，掩膜已映回原始方向。</p>}
    </div>
  </Panel>
}
