import { ArrowLeft, CircleAlert, Info } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { ApiStatus } from '../components/ApiStatus.jsx'
import { CineImage } from '../components/CineImage.jsx'
import { MonitorChart } from '../components/MonitorChart.jsx'
import { Badge, DataTable, EmptyState, Missing, PageHeading, Panel } from '../components/UI.jsx'
import { issueLabels, measures, missingReason, patients } from '../data/patients.js'
import { cineMarkers, cineSeries } from '../data/camus.js'
import { apiEnabled, apiUrl, useApi } from '../data/api.js'
import styles from '../styles/Pages.module.css'
import ui from '../styles/UI.module.css'

const columns = [
  { key: 'metric', label: '指标' }, { key: 'prediction', label: '预测值', numeric: true },
  { key: 'reference', label: '参考值', numeric: true }, { key: 'absolute', label: '绝对误差', numeric: true },
  { key: 'signed', label: '差值（预测 − 参考）', numeric: true },
]

export default function PatientDetail() {
  const { id } = useParams()
  const [params] = useSearchParams()
  const study = apiEnabled && params.get('study') === 'legacy' ? 'legacy' : 'dra'
  const listUrl = `/patients${study === 'legacy' ? '?study=legacy' : ''}`
  const remote = useApi(`/api/patients/${encodeURIComponent(id)}?study=${study}`)
  const detail = remote.data
  const patient = apiEnabled ? detail?.patient : patients.find(item => item.patient_id === id)
  if (apiEnabled && !detail && remote.error?.status !== 404) {
    return <ApiStatus request={remote} unavailable="无法读取该 CAMUS 病例" />
  }
  if (!patient) return <EmptyState title="找不到该 CAMUS 病例" detail="可从患者列表选择一条公开病例。" to={listUrl} action="返回患者列表" />
  const contours = detail?.contours
  const cine = detail && contours.atlas_url ? {
    patient_id: patient.patient_id, atlas: contours.atlas, atlasUrl: apiUrl(contours.atlas_url),
    expert_phases: Object.fromEntries(Object.entries(contours.frames).map(([phase, frame]) => [phase, frame.frame])),
  } : patient.cine
  const curve = detail?.volume_curve
  const series = detail ? curve.raw?.map(frame => ({ index: frame.index, time: frame.time_s * 1000, volume: frame.volume_ml })) : cineSeries(cine)
  const events = detail ? curve.events.map(event => ({ phase: event.phase, ...series?.find(frame => frame.index === event.frame) })) : cineMarkers(cine, series)

  return <div className={styles.stack}>
    <Link to={listUrl} className={ui.textLink}><ArrowLeft size={16} /> 返回患者列表</Link>
    <PageHeading title={patient.patient_id} description={detail ? `${detail.model} · ${detail.scope}` : 'CAMUS 固定测试集 · A2C 切面'} action={<Badge tone="blue">CAMUS</Badge>} />
    <Panel title="预测与参考对照" subtitle={study === 'dra' ? '预测取容积曲线峰谷，参考取专家标注帧，EF 误差采用百分点' : '预测和参考均取专家标注相位，EF 误差采用百分点'} action={<Badge>{patient.reference_scope}</Badge>}>
      <DataTable columns={columns} label="预测与参考测量">
        {measures.map(({ key, name, unit, errorUnit = unit }) => {
          const referenceKey = `ref_${key}`
          const predicted = patient[key]
          const expected = patient[referenceKey]
          const delta = detail ? detail.signed_error[key] : predicted == null || expected == null ? null : predicted - expected
          const absolute = detail ? detail.absolute_error[key] : delta == null ? null : Math.abs(delta)
          return <tr key={key}>
            <th scope="row">{key} <small className={ui.unitHint}>{name}</small></th>
            <td className={ui.numeric}>{predicted == null ? <Missing reason={missingReason(key, patient)} showReason /> : `${predicted.toFixed(1)} ${unit}`}</td>
            <td className={ui.numeric}>{expected == null ? <Missing reason={missingReason(referenceKey, patient)} showReason /> : `${expected.toFixed(1)} ${unit}`}</td>
            <td className={ui.numeric}>{absolute == null ? <Missing reason="无配对测量" /> : `${absolute.toFixed(1)} ${errorUnit}`}</td>
            <td className={ui.numeric}>{delta == null ? <Missing reason="无配对测量" /> : `${delta > 0 ? '+' : ''}${delta.toFixed(1)} ${errorUnit}`}</td>
          </tr>
        })}
      </DataTable>
    </Panel>
    <Panel title="左心室轮廓叠图" subtitle={cine ? 'CAMUS A2C · 专家 ED / ES 标注帧' : undefined}>
      {cine ? <><div className={styles.contours}>
        {Object.entries(cine.expert_phases).map(([phase, index]) => <figure className={styles.contour} key={phase}>
          <CineImage key={cine.patient_id} cine={cine} index={index} />
          <figcaption><strong>{phase} · {phase === 'ED' ? '舒张末期' : '收缩末期'}</strong><span>帧 {index}</span></figcaption>
        </figure>)}
      </div>
      <p className={styles.footnote} style={{ padding: '0 20px 16px' }}>绿色为 DRA-UNet 掩膜，琥珀色为专家轮廓。Leclerc 等，CAMUS · <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank" rel="noreferrer">CC BY-NC-SA 4.0</a></p></>
        : <EmptyState title="暂无轮廓叠图" detail={contours?.reason} />}
    </Panel>
    <Panel title="左室容积时序" subtitle="原始采集时间（ms）与逐帧容积（mL），标记预测 ED 峰和 ES 谷">
      {series?.length ? <MonitorChart series={series} events={events} duration={series.at(-1).time} />
        : <EmptyState title="暂无逐帧容积曲线" detail={curve?.reason} />}
    </Panel>
    <Panel title="质量与备注">
      <div className={styles.quality}>
        {patient.issues.map(key => {
          const issue = issueLabels[key]
          return <div key={key}><Badge tone={issue?.tone ?? 'warning'} icon={issue?.tone === 'muted' ? Info : CircleAlert}>{issue?.name ?? key}</Badge><span>{issue?.description}</span></div>
        })}
        <dl><dt>参考口径</dt><dd>{patient.reference_scope}</dd><dt>相位选择</dt><dd>{patient.phase_selection}</dd></dl>
      </div>
    </Panel>
  </div>
}
