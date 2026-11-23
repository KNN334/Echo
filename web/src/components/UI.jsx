import { ArrowRight, Database, LoaderCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import styles from '../styles/UI.module.css'

export function Badge({ children, tone = 'muted', icon: Icon, title }) {
  return <span className={`${styles.badge} ${styles[tone]}`} title={title}>
    {Icon && <Icon size={14} strokeWidth={1.85} />}{children}
  </span>
}

export function Panel({ title, subtitle, action, children, className = '' }) {
  return <section className={`${styles.panel} ${className}`}>
    {title && <div className={styles.panelHeader}>
      <div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>
      {action}
    </div>}
    {children}
  </section>
}

export function PageHeading({ title, description, action }) {
  return <div className={styles.pageHeading}>
    <div><h1>{title}</h1><p>{description}</p></div>
    {action}
  </div>
}

export function ActionLink({ children, to, primary = false, arrow = true }) {
  return <Link to={to} className={primary ? styles.primaryButton : styles.secondaryButton}>
    {children}{arrow && <ArrowRight size={16} />}
  </Link>
}

export function TextLink({ children, to }) {
  return <Link to={to} className={styles.textLink}>{children}<ArrowRight size={15} /></Link>
}

export function EmptyState({ title, detail, action, to, onAction, loading = false }) {
  return <div className={styles.empty} role={loading ? 'status' : undefined}>
    <span className={styles.emptyIcon}>{loading ? <LoaderCircle className={styles.spin} size={22} /> : <Database size={22} />}</span>
    <strong>{title}</strong>
    {detail && <p>{detail}</p>}
    {to && <ActionLink to={to}>{action}</ActionLink>}
    {onAction && <button type="button" className={styles.secondaryButton} onClick={onAction}>{action}</button>}
  </div>
}

export function Missing({ reason, showReason = false }) {
  return <span className={styles.missing} title={reason} aria-label={`缺测，${reason}`}>
    <span>—</span>{showReason && <small>{reason}</small>}
  </span>
}

export function DataTable({ columns, children, label }) {
  return <div className={styles.tableScroller}>
    <table className={styles.table} aria-label={label}>
      <thead><tr>{columns.map(({ key, label: text, numeric, sort, direction, unit }) =>
        <th scope="col" key={key} className={numeric ? styles.numeric : undefined} aria-sort={direction}>
          {sort ? <button type="button" className={styles.sortButton} onClick={sort}>{text}</button> : text}
          {unit && <small className={styles.unitHint}> {unit}</small>}
        </th>,
      )}</tr></thead>
      <tbody>{children}</tbody>
    </table>
  </div>
}

export function MetricCard({ item }) {
  const { value, title, unit, description, icon: Icon, tint } = item
  return <div className={styles.metricCard}>
    <div className={styles.metricTop}><span>{title}</span><span className={`${styles.metricIcon} ${styles[tint]}`}><Icon size={18} strokeWidth={1.9} /></span></div>
    <div className={styles.metricValue}>{value}<small>{unit}</small></div>
    <p>{description}</p>
  </div>
}
