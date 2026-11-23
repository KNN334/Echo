import { useEffect, useRef, useState } from 'react'
import {
  Activity, ChartNoAxesCombined, ChevronRight, CircleHelp, Database,
  LayoutGrid, Network, PanelLeftClose, PanelLeftOpen, ShieldCheck, Telescope, X,
} from 'lucide-react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { Badge } from './UI.jsx'
import styles from '../styles/Layout.module.css'

const links = [
  { path: '/', icon: LayoutGrid, label: '概览', title: '研究概览' },
  { path: '/about', icon: Telescope, label: '项目介绍' },
  { path: '/features', icon: Network, label: '核心能力' },
  { path: '/results', icon: ChartNoAxesCombined, label: '结果评估' },
  { path: '/patients', icon: Database, label: '患者数据' },
]

export function Layout({ children }) {
  const [collapsed, setCollapsed] = useState(false)
  const contact = useRef(null)
  const { pathname, hash } = useLocation()
  const section = links.find(({ path }) => path === '/' ? pathname === '/' : pathname.startsWith(path))
  const detail = pathname.startsWith('/patients/')
  const title = detail ? '患者详情' : section?.title ?? section?.label ?? '页面未找到'
  const CollapseIcon = collapsed ? PanelLeftOpen : PanelLeftClose

  useEffect(() => {
    document.title = `${title} · 超声智能心脏功能评估系统`
    if (!hash) window.scrollTo({ top: 0, behavior: 'instant' })
  }, [title, pathname, hash])

  return (
    <div className={`${styles.shell} ${collapsed ? styles.collapsed : ''}`}>
      <a className={styles.skip} href="#main" onClick={event => {
        event.preventDefault()
        document.getElementById('main').focus()
      }}>跳转至内容</a>
      <aside className={styles.sidebar} aria-label="应用侧边栏">
        <Link to="/" className={styles.brand} aria-label="EchoLab 概览">
          <span className={styles.logo}><Activity size={24} strokeWidth={2.3} /></span>
          <span className={styles.brandText}><strong>EchoLab</strong><small>心脏超声评估</small></span>
        </Link>
        <div className={styles.navigation}>
          <div className={styles.navLabel}>研究工作台</div>
          <nav aria-label="主导航">
            {links.map(({ path, label, icon: Icon }) => (
              <NavLink key={path} to={path} end={path === '/'} title={label} aria-label={label}
                className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}>
                <Icon size={19} strokeWidth={1.8} />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>
        <div className={styles.sidebarFooter}>
          <div className={styles.workspace}><span className={styles.workspaceIcon}><ShieldCheck size={17} /></span><span><strong>研究工作区</strong><small>CAMUS · DRA-UNet</small></span></div>
          <button type="button" className={styles.collapse} onClick={() => setCollapsed(!collapsed)}
            aria-expanded={!collapsed} aria-label={collapsed ? '展开侧边栏' : '折叠侧边栏'} title="切换侧边栏">
            <CollapseIcon size={18} /><span>{collapsed ? '展开侧边栏' : '折叠侧边栏'}</span>
          </button>
        </div>
      </aside>
      <div className={styles.workspaceBody}>
        <header className={styles.topbar}>
          <div className={styles.breadcrumb}>
            <Link to="/">研究工作台</Link><ChevronRight size={14} />
            {detail && <><Link to="/patients">患者数据</Link><ChevronRight size={14} /></>}
            <strong>{title}</strong>
          </div>
          <div className={styles.headerActions}>
            <Badge tone="blue" icon={ShieldCheck}>研究基线 · 非临床验证</Badge>
            <button type="button" className={styles.contact} onClick={() => contact.current.showModal()}>
              <CircleHelp size={17} /> <span>项目联系</span>
            </button>
          </div>
        </header>
        <main id="main" className={styles.content} tabIndex={-1}>{children}</main>
        <footer className={styles.footer}><span>EchoLab · 超声智能心脏功能评估系统</span><span>研究工程基线</span></footer>
      </div>
      <dialog ref={contact} className={styles.dialog} aria-labelledby="contact-title">
        <form method="dialog"><button className={styles.close} aria-label="关闭"><X size={19} /></button></form>
        <h2 id="contact-title">项目联系</h2>
        <p>当前展示页未配置内部联系方式。</p>
        <a href="https://github.com/KNN334/Echo" target="_blank" rel="noreferrer">查看 Echo 项目仓库</a>
      </dialog>
    </div>
  )
}
