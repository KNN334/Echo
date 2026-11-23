import { ArrowLeft, CircleAlert, Info } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { ContourExample } from '../components/ContourExample.jsx'
import { VolumeChart } from '../components/Charts.jsx'
import { Badge, DataTable, EmptyState, Missing, PageHeading, Panel } from '../components/UI.jsx'
import { exampleVolumeSeries, issueLabels, measures, missingReason, patients } from '../data/patients.js'
import styles from '../styles/Pages.module.css'
import ui from '../styles/UI.module.css'

const columns = [
  { key: 'metric', label: '指标' }, { key: 'prediction', label: '预测值', numeric: true },
  { key: 'reference', label: '参考值', numeric: true }, { key: 'absolute', label: '绝对误差', numeric: true },
  { key: 'signed', label: '差值（预测 − 参考）', numeric: true },
]

export default function PatientDetail() {
  const { id } = useParams()
  const patient = patients.find(item => item.patient_id === id)
  if (!patient) return <EmptyState title="找不到该患者示例" detail="可从患者列表选择演示记录。" to="/patients" action="返回患者列表" />
  const series = exampleVolumeSeries(patient)
  const hasReference = patient.ref_EDV != null

  return <div className={styles.stack}>
    <Link to="/patients" className={ui.textLink}><ArrowLeft size={16} /> 返回患者列表</Link>
    <PageHeading title={patient.patient_id} description="患者级心功能对照" action={<Badge tone="blue">虚构示例</Badge>} />
    <Panel title="预测与参考对照" subtitle="EF 误差采用百分点" action={<Badge>{patient.reference_scope}</Badge>}>
      <DataTable columns={columns} label="预测与参考测量">
        {measures.map(({ key, name, unit, errorUnit = unit }) => {
          const referenceKey = `ref_${key}`
          const predicted = patient[key]
          const expected = patient[referenceKey]
          const delta = predicted == null || expected == null ? null : predicted - expected
          return <tr key={key}>
            <th scope="row">{key} <small className={ui.unitHint}>{name}</small></th>
            <td className={ui.numeric}>{predicted == null ? <Missing reason={missingReason(key, patient)} showReason /> : `${predicted.toFixed(1)} ${unit}`}</td>
            <td className={ui.numeric}>{expected == null ? <Missing reason={missingReason(referenceKey, patient)} showReason /> : `${expected.toFixed(1)} ${unit}`}</td>
            <td className={ui.numeric}>{delta == null ? <Missing reason="无配对测量" /> : `${Math.abs(delta).toFixed(1)} ${errorUnit}`}</td>
            <td className={ui.numeric}>{delta == null ? <Missing reason="无配对测量" /> : `${delta > 0 ? '+' : ''}${delta.toFixed(1)} ${errorUnit}`}</td>
          </tr>
        })}
      </DataTable>
    </Panel>
    <Panel title="左心室轮廓叠图" subtitle="示例图 · A2C 切面"
      action={<div className={styles.contourLegend}><span>预测</span><span>参考</span></div>}>
      <div className={styles.contours}>
        <ContourExample phase="ED" showReference={hasReference} />
        <ContourExample phase="ES" showReference={hasReference} unavailable={patient.ESV == null} />
      </div>
    </Panel>
    <Panel title="左室容积时序" subtitle="按帧索引展示半周期，曲线在缺测处断开" action={<Badge tone="blue">示例数据</Badge>}>
      <VolumeChart series={series} edv={patient.EDV} esv={patient.ESV} />
    </Panel>
    <Panel title="质量与备注">
      <div className={styles.quality}>
        {patient.issues.map(key => {
          const issue = issueLabels[key]
          return <div key={key}><Badge tone={issue.tone} icon={issue.tone === 'warning' ? CircleAlert : Info}>{issue.name}</Badge><span>{issue.description}</span></div>
        })}
        <dl><dt>参考口径</dt><dd>{patient.reference_scope}</dd><dt>相位选择</dt><dd>{patient.phase_selection}</dd></dl>
      </div>
    </Panel>
  </div>
}
