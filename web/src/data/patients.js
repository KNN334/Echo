const missingHeartRate = '缺少完整心动周期或可靠参考心率'

export const issueLabels = {
  incomplete_cycle: { name: '半周期', description: missingHeartRate, tone: 'muted' },
  low_quality_frame: { name: '图像质量异常', description: '示例序列中标记了质量异常帧。', tone: 'warning' },
  missing_reference: { name: '参考值缺失', description: '此示例未提供配对的轮廓派生容积。', tone: 'warning' },
  missing_phase: { name: '相位缺失', description: '有效帧中无法定位可用的收缩末期。', tone: 'warning' },
}

export const measures = [
  { key: 'EDV', name: '舒张末期容积', unit: 'mL' },
  { key: 'ESV', name: '收缩末期容积', unit: 'mL' },
  { key: 'SV', name: '每搏输出量', unit: 'mL' },
  { key: 'EF', name: '射血分数', unit: '%', errorUnit: '百分点' },
  { key: 'HR', name: '心率', unit: '次/分' },
  { key: 'CO', name: '心输出量', unit: 'L/min' },
]

// Fictional inputs. Volumes and derived values are independent of patient_features.csv.
const examples = [
  [124.6, 49.8, 128.0, 52.1, []],
  [111.2, 43.0, 105.8, 42.7, []],
  [158.9, 77.8, 152.3, 70.1, ['low_quality_frame']],
  [96.4, 39.5, 99.3, 41.9, []],
  [136.7, 62.1, null, null, ['missing_reference']],
  [118.2, 54.5, 122.4, 55.8, []],
  [142.3, null, 139.5, 67.0, ['missing_phase']],
  [92.8, 33.5, 96.1, 35.9, []],
  [167.1, 92.2, 161.1, 86.4, ['low_quality_frame']],
  [106.5, 45.7, 108.2, 46.5, []],
]

function derive(EDV, ESV) {
  const SV = EDV == null || ESV == null ? null : EDV - ESV
  return { EDV, ESV, SV, EF: SV == null || !EDV ? null : SV / EDV * 100, HR: null, CO: null }
}

// The list and detail pages consume these same fields when a data adapter replaces the mock.
export const patients = examples.map(([edv, esv, refEdv, refEsv, issues], index) => {
  const reference = Object.fromEntries(
    Object.entries(derive(refEdv, refEsv)).map(([key, value]) => [`ref_${key}`, value]),
  )
  return {
    patient_id: `DEMO-${String(index + 1).padStart(3, '0')}`,
    ...derive(edv, esv),
    ...reference,
    issues: ['incomplete_cycle', ...issues],
    reference_scope: refEdv == null ? '参考值缺失' : '同几何法轮廓派生参考',
    phase_selection: esv == null ? '仅定位到 ED' : '示例半周期内 ED 峰与 ES 谷',
  }
})

export function missingReason(key, patient) {
  if (key === 'ref_CO') return '缺少独立 CO 参考'
  if (key === 'HR' || key === 'ref_HR' || key === 'CO') return missingHeartRate
  if (key.startsWith('ref_')) return '缺少配对的几何参考值'
  return patient.ESV == null ? '缺少可用的收缩末期' : '缺少可用的测量值'
}

export function exampleVolumeSeries(patient) {
  const gap = patient.issues.includes('low_quality_frame')
  const esv = patient.ESV
  return Array.from({ length: 20 }, (_, frame) => {
    const progress = (1 - Math.cos(Math.PI * frame / 19)) / 2
    const unavailable = (gap && frame >= 8 && frame <= 10) || (esv == null && frame >= 12)
    const smooth = patient.EDV - (patient.EDV - (esv ?? patient.EDV * 0.65)) * progress
    const raw = smooth + Math.sin(frame * 1.8) * Math.sin(Math.PI * frame / 19) * 2.4
    return {
      frame,
      raw: unavailable ? null : Number(raw.toFixed(1)),
      smooth: unavailable ? null : Number(smooth.toFixed(1)),
    }
  })
}
