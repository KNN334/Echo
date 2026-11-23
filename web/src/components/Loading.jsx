import { Activity } from 'lucide-react'
import styles from '../styles/Monitor.module.css'

export function Loading({ label = '正在加载页面…' }) {
  return <div className={styles.loading} role="status">
    <span className={styles.loadingMark}><Activity size={25} strokeWidth={1.85} /></span>
    <span>{label}</span>
  </div>
}
