import { camusCases } from './camus.js'

const missingHeartRate = '缺少完整心动周期或可靠参考心率'

export const issueLabels = {
  incomplete_cycle: { name: '半周期', description: missingHeartRate, tone: 'muted' },
  missing_reference: { name: '参考值缺失', description: '缺少一组有效的专家轮廓派生容积。', tone: 'warning' },
  missing_phase: { name: '相位缺失', description: '预测容积曲线缺少有效的 ED 峰与 ES 谷配对。', tone: 'warning' },
  invalid_geometry: { name: '容积缺帧', description: '至少一帧无法用预测轮廓估算容积。', tone: 'warning' },
}

export const measures = [
  { key: 'EDV', name: '舒张末期容积', unit: 'mL' },
  { key: 'ESV', name: '收缩末期容积', unit: 'mL' },
  { key: 'SV', name: '每搏输出量', unit: 'mL' },
  { key: 'EF', name: '射血分数', unit: '%', errorUnit: '百分点' },
  { key: 'HR', name: '心率', unit: '次/分' },
  { key: 'CO', name: '心输出量', unit: 'L/min' },
]

function derive(EDV, ESV) {
  const SV = EDV == null || ESV == null || ESV >= EDV ? null : EDV - ESV
  return { EDV, ESV, SV, EF: SV == null || !EDV ? null : SV / EDV * 100, HR: null, CO: null }
}

export const patients = camusCases.map(cine => {
  const { ED: refEdv = null, ES: refEsv = null } = cine.expert_volumes_ml
  const [event] = cine.events
  const issues = ['incomplete_cycle']
  if (!event) issues.push('missing_phase')
  if (refEdv == null || refEsv == null) issues.push('missing_reference')
  if (cine.frames.some(frame => frame.volume_ml == null)) issues.push('invalid_geometry')
  const reference = Object.fromEntries(
    Object.entries(derive(refEdv, refEsv)).map(([key, value]) => [`ref_${key}`, value]),
  )
  return {
    patient_id: cine.patient_id,
    cine,
    ...derive(event?.EDV ?? null, event?.ESV ?? null),
    ...reference,
    issues,
    reference_scope: '专家轮廓派生 · 单平面 Simpson',
    phase_selection: event ? `预测 ED 峰在帧 ${event.ed_frame}，ES 谷在帧 ${event.es_frame}` : '缺少有效预测峰谷',
  }
})

export function missingReason(key, patient) {
  if (key === 'ref_CO') return '缺少独立 CO 参考'
  if (key === 'HR' || key === 'ref_HR' || key === 'CO') return missingHeartRate
  if (key.startsWith('ref_')) return '缺少配对的几何参考值'
  return patient.ESV == null ? '缺少有效预测峰谷配对' : '缺少可用的测量值'
}
