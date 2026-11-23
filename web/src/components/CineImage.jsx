import { useState } from 'react'
import { Loading } from './Loading.jsx'
import styles from '../styles/Monitor.module.css'

export function CineImage({ cine, index, children, onReady }) {
  const [status, setStatus] = useState('loading')
  const [attempt, setAttempt] = useState(0)
  const tile = cine.atlas

  return <div className={styles.viewer} role="img" aria-label={`CAMUS A2C 左心室分割 · 帧 ${index}`}
    aria-busy={status === 'loading'} style={{ aspectRatio: `${tile.width} / ${tile.height}` }}>
    <img key={attempt} className={styles.atlas} src={cine.atlasUrl} alt=""
      onLoad={() => { setStatus('ready'); onReady?.(true) }}
      onError={() => { setStatus('error'); onReady?.(false) }}
      style={{ width: `${tile.columns * 100}%`, height: `${tile.rows * 100}%`,
        left: `${-(index % tile.columns) * 100}%`, top: `${-Math.floor(index / tile.columns) * 100}%`,
        visibility: status === 'ready' ? 'visible' : 'hidden' }} />
    {status === 'loading' && <Loading label="正在加载分割影像…" />}
    {status === 'error' && <div className={styles.mediaError}>
      <p role="alert">分割影像加载失败</p>
      <button type="button" className={styles.button} onClick={() => {
        setStatus('loading')
        setAttempt(attempt + 1)
      }}>重试</button>
    </div>}
    {status === 'ready' && children}
  </div>
}
