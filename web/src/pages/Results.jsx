import { useState } from 'react'
import { ExternalLink, Info } from 'lucide-react'
import { ApiStatus } from '../components/ApiStatus.jsx'
import { Badge, DataTable, Missing, PageHeading, Panel } from '../components/UI.jsx'
import { LossChart } from '../components/Charts.jsx'
import { evaluations, researchSources } from '../data/research.js'
import { apiEnabled, useApi } from '../data/api.js'
import styles from '../styles/Pages.module.css'
import ui from '../styles/UI.module.css'

const segmentationColumns = [
  { key: 'metric', label: '指标' }, { key: 'value', label: '结果', numeric: true },
  { key: 'scope', label: '口径说明' },
]
const functionalColumns = [
  { key: 'metric', label: '指标' }, { key: 'mae', label: 'MAE', numeric: true },
  { key: 'bias', label: '偏倚', numeric: true }, { key: 'ci', label: 'MAE 95% 置信区间', numeric: true },
  { key: 'loa', label: '95% 一致性界限', numeric: true },
  ...(apiEnabled ? [{ key: 'n', label: '有效患者', numeric: true }, { key: 'coverage', label: '覆盖率', numeric: true }] : []),
  { key: 'scope', label: '单位 / 口径' },
]

const interval = range => range?.map(value => value.toFixed(2)).join(' 至 ')

export default function Results() {
  const [selected, setSelected] = useState('dra')
  const study = evaluations[selected]
  const segmentation = useApi(`/api/results/segmentation?study=${selected}`)
  const functional = useApi(`/api/results/function?study=${selected}`)
  const training = useApi(`/api/results/training-history?study=${selected}`)
  const segmentationRows = apiEnabled ? segmentation.data?.metrics.map(item => [
    item.metric, item.value == null ? null : item.value.toFixed(item.unit === '1' ? 4 : 2) + (item.unit === '1' ? '' : ` ${item.unit}`),
    item.scope, item.reason,
  ]) : study.segmentation
  const functionRows = apiEnabled ? functional.data?.metrics.map(item => [
    item.metric, item.mae?.toFixed(2), item.bias?.toFixed(2), interval(item.mae_ci95), interval(item.limits_of_agreement),
    item.unit, item.reason, item.n_patients, item.coverage == null ? null : `${(100 * item.coverage).toFixed(1)}%`,
  ]) : study.functional
  const loss = training.data?.loss
  const epochs = training.data?.epochs.map(row => ({
    epoch: row.epoch, train: row.train_bce ?? row.train_loss, validation: row.val_bce ?? row.val_loss,
  }))
  return <div className={styles.stack}>
    <PageHeading title="结果评估" description="查看分割精度、容积误差和心功能一致性。" />
    <div className={styles.resultControls}>
      <div className={styles.segmented} aria-label="实验">
        {Object.entries(evaluations).map(([key, item]) =>
          <button key={key} type="button" aria-pressed={selected === key} onClick={() => setSelected(key)}>{item.title}</button>,
        )}
      </div>
      {(!apiEnabled || segmentation.data) && <Badge tone="blue">{segmentation.data?.scope ?? study.scope}</Badge>}
    </div>
    <Panel title="分割与轮廓评估" subtitle={segmentation.data?.model ?? study.title}
      action={<a className={ui.textLink} href={researchSources[selected]} target="_blank" rel="noreferrer">实验报告 <ExternalLink size={15} /></a>}>
      {segmentationRows?.length ? <DataTable columns={segmentationColumns} label="分割指标">
        {segmentationRows.map(([metric, value, description, reason]) => <tr key={metric}>
          <th scope="row">{metric}</th>
          <td className={ui.numeric}>{value ?? <Missing reason={reason ?? description} />}</td>
          <td className={ui.mutedText}>{description}</td>
        </tr>)}
      </DataTable> : <ApiStatus request={segmentation} />}
    </Panel>
    <Panel title="心功能与容积评估" subtitle={functional.data?.reference_scope ?? (selected === 'dra' ? '原始 ED/ES 标注帧 · 单平面 Simpson 圆盘法' : '历史基线 · 20 圆盘双平面几何法')}>
      {functionRows?.length ? <DataTable columns={functionalColumns} label="心功能指标与一致性评估">
        {functionRows.map(([metric, mae, bias, ci, loa, unit, reason, n, coverage]) => <tr key={metric}>
          <th scope="row">{metric}</th>
          {[mae, bias, ci, loa, ...(apiEnabled ? [n, coverage] : [])].map((value, index) =>
            <td className={ui.numeric} key={index}>{value ?? <Missing reason={reason ?? '报告未提供'} />}</td>,
          )}
          <td className={ui.mutedText}>{unit}{reason && <small className={ui.reasonText}>{reason}</small>}</td>
        </tr>)}
      </DataTable> : <ApiStatus request={functional} />}
      <div className={styles.note}><Info size={17} /><span>参考容积由专家轮廓经同一几何方法派生。偏倚按预测值减去参考值计算。</span></div>
    </Panel>
    {apiEnabled ? <Panel title={`${study.title} 训练曲线`}
      subtitle={loss && `${training.data.seed == null ? '' : `种子 ${training.data.seed} · `}训练与验证损失（${loss}）`}>
      {epochs?.length ? <LossChart data={epochs} loss={loss} /> : <ApiStatus request={training} />}
    </Panel> : selected === 'dra' && <Panel title="DRA-UNet 训练曲线" subtitle="种子 2026 · 训练与验证的主分割损失（BCE + Dice）">
      <LossChart />
    </Panel>}
  </div>
}
