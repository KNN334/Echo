import { useEffect } from 'react'
import { CodeXml } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { PageHeading, Panel } from '../components/UI.jsx'
import { modules } from '../data/research.js'
import styles from '../styles/Pages.module.css'

export default function Features() {
  const { hash } = useLocation()
  const selected = hash.slice(1)
  useEffect(() => {
    if (selected) document.getElementById(selected)?.scrollIntoView({ block: 'start' })
  }, [selected])
  return <div className={styles.stack}>
    <PageHeading title="核心能力" description="左心室分割、时序容积与评价的六个模块。" />
    <nav className={styles.jumpLinks} aria-label="能力目录">
      {modules.map(({ id, title }) => <a key={id} className={selected === id ? styles.jumpActive : undefined} href={`#/features#${id}`}>{title}</a>)}
    </nav>
    <div className={styles.twoCol}>
      {modules.map(({ id, icon: Icon, title, detail, source }) => (
        <div id={id} key={id} className={styles.anchor}>
          <Panel className={`${styles.moduleCard} ${selected === id ? styles.moduleActive : ''}`}>
            <span className={styles.stepIcon}><Icon size={22} strokeWidth={1.8} /></span>
            <h2>{title}</h2><p>{detail}</p>
            <span className={styles.sourceCode}><CodeXml size={15} /><code>{source}</code></span>
          </Panel>
        </div>
      ))}
    </div>
  </div>
}
