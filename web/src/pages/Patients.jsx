import { useState } from 'react'
import { ArrowDown, ArrowDownUp, ArrowRight, ArrowUp, ChevronLeft, ChevronRight, Search } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiStatus } from '../components/ApiStatus.jsx'
import { Badge, DataTable, EmptyState, Missing, PageHeading, Panel } from '../components/UI.jsx'
import { apiEnabled, useApi } from '../data/api.js'
import { issueLabels, measures, missingReason, patients } from '../data/patients.js'
import styles from '../styles/Pages.module.css'
import ui from '../styles/UI.module.css'

const pageSize = 8
const fields = [
  { key: 'patient_id', label: '患者 ID' },
  ...measures.map(({ key, unit }) => ({ key, label: key, unit, numeric: true })),
  ...measures.filter(({ key }) => ['EDV', 'ESV', 'EF'].includes(key))
    .map(({ key, unit }) => ({ key: `ref_${key}`, label: `参考 ${key}`, unit, numeric: true })),
]

function isFlagged(patient) {
  return patient.issues.some(key => key !== 'incomplete_cycle')
}

export default function Patients() {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const [sort, setSort] = useState({ key: 'patient_id', direction: 'ascending' })
  const [params, setParams] = useSearchParams()
  const study = apiEnabled && params.get('study') === 'legacy' ? 'legacy' : 'dra'
  const [pagination, setPagination] = useState({ study, page: 1 })
  const page = pagination.study === study ? pagination.page : 1
  const setPage = page => setPagination({ study, page })
  const navigate = useNavigate()
  const remote = useApi(apiEnabled ? `/api/patients?${new URLSearchParams({
    study, search: query, issue_filter: filter, sort_by: sort.key,
    order: sort.direction === 'ascending' ? 'asc' : 'desc', page, page_size: pageSize,
  })}` : null)
  const visible = apiEnabled ? [] : patients.filter(patient =>
    patient.patient_id.toLowerCase().includes(query.trim().toLowerCase()) &&
    (filter === 'all' || (filter === 'review' ? isFlagged(patient) : !isFlagged(patient))),
  ).sort((left, right) => {
    const a = left[sort.key]
    const b = right[sort.key]
    if (a == null || b == null) return Number(a == null) - Number(b == null)
    const order = typeof a === 'string' ? a.localeCompare(b) : a - b
    return sort.direction === 'ascending' ? order : -order
  })
  const total = apiEnabled ? remote.data?.total ?? 0 : visible.length
  const pageCount = remote.data?.page_count ?? Math.max(1, Math.ceil(visible.length / pageSize))
  const offset = (page - 1) * pageSize
  const rows = apiEnabled ? remote.data?.items ?? [] : visible.slice(offset, offset + pageSize)
  const columns = fields.map(field => {
    const direction = sort.key === field.key ? sort.direction : undefined
    const SortIcon = direction === 'ascending' ? ArrowUp : direction === 'descending' ? ArrowDown : ArrowDownUp
    return {
      ...field, direction,
      label: <>{field.label}<SortIcon size={12} /></>,
      sort: () => {
        setSort({ key: field.key, direction: direction === 'ascending' ? 'descending' : 'ascending' })
        setPage(1)
      },
    }
  }).concat({ key: 'issues', label: '问题备注' })

  return <div className={styles.stack}>
    <PageHeading title="患者数据" description="浏览 CAMUS 固定测试集病例、预测值与专家轮廓派生参考值。" action={<Badge tone="blue">CAMUS</Badge>} />
    {apiEnabled && <div className={styles.resultControls}>
      <div className={styles.segmented} aria-label="病例口径">
        {[['dra', 'DRA-UNet · A2C 回放'], ['legacy', '历史基线 · 双平面报表']].map(([key, label]) =>
          <button key={key} type="button" aria-pressed={study === key} onClick={() => {
            setPage(1)
            setParams(key === 'legacy' ? { study: key } : {})
          }}>{label}</button>)}
      </div>
      {remote.data && <Badge tone="blue">{remote.data.scope}</Badge>}
    </div>}
    <Panel>
      <div className={styles.tableToolbar}>
        <div><h2>患者列表</h2><p>{!apiEnabled || remote.data ? `${total} 名匹配的公开病例` : 'CAMUS 研究报表'}</p></div>
        <div className={styles.filters}>
          <label className={styles.search}><Search size={17} />
            <input type="search" placeholder="搜索患者 ID" aria-label="搜索患者 ID" value={query}
              onChange={event => { setQuery(event.target.value); setPage(1) }} />
          </label>
          <select aria-label="按问题状态筛选" className={styles.select} value={filter}
            onChange={event => { setFilter(event.target.value); setPage(1) }}>
            <option value="all">所有状态</option><option value="review">有额外问题</option><option value="routine">仅半周期缺测</option>
            {apiEnabled && <option value="missing_co">心输出量缺测</option>}
          </select>
        </div>
      </div>
      {apiEnabled && !remote.data ? <ApiStatus request={remote} /> : rows.length ? <DataTable columns={columns} label="CAMUS 患者级测量">
        {rows.map(patient => {
          const to = `/patients/${patient.patient_id}${study === 'legacy' ? '?study=legacy' : ''}`
          return <tr key={patient.patient_id} className={ui.clickableRow}
            onClick={event => { if (!event.target.closest('a') && !window.getSelection()?.toString()) navigate(to) }}>
            <th scope="row"><Link className={styles.patientLink} to={to}>{patient.patient_id}<ArrowRight size={13} /></Link></th>
            {fields.slice(1).map(({ key }) =>
              <td key={key} className={ui.numeric}>{patient[key]?.toFixed(1) ?? <Missing reason={missingReason(key, patient)} />}</td>,
            )}
            <td><div className={styles.tags}>{patient.issues.map(key => {
              const issue = issueLabels[key]
              return <Badge key={key} tone={issue?.tone ?? 'warning'} title={issue?.description}>{issue?.name ?? key}</Badge>
            })}</div></td>
          </tr>
        })}
      </DataTable> : <EmptyState title="没有符合条件的患者" detail="尝试更换患者 ID 或问题状态。"
        action="清除筛选" onAction={() => { setQuery(''); setFilter('all'); setPage(1) }} />}
      {(!apiEnabled || remote.data) && <div className={styles.pagination}>
        <span>{total ? `第 ${offset + 1}–${offset + rows.length} 条，共 ${total} 条` : '共 0 条'}</span>
        <div><button type="button" aria-label="上一页" disabled={page === 1} onClick={() => setPage(page - 1)}><ChevronLeft size={17} /></button>
          <span>{page} / {pageCount}</span>
          <button type="button" aria-label="下一页" disabled={page === pageCount} onClick={() => setPage(page + 1)}><ChevronRight size={17} /></button></div>
      </div>}
    </Panel>
  </div>
}
