import { CartesianGrid, Legend, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { exampleLosses } from '../data/research.js'
import styles from '../styles/UI.module.css'

const grid = '#e7edf5'
const axis = '#65738b'
const blue = '#2563eb'
const gray = '#8294ad'
const axisStyle = { fontSize: 12, fill: axis }
const tooltip = { border: '1px solid #e0e8f3', borderRadius: '8px' }
const legend = { paddingTop: '8px' }

function PhaseLabel({ viewBox, phase, volume }) {
  if (!viewBox) return null
  const ed = phase === 'ED'
  return <text x={viewBox.x + (ed ? 8 : -8)} y={viewBox.y - 10}
    textAnchor={ed ? 'start' : 'end'} fill={blue} fontSize={12}>
    {`${phase} · ${volume.toFixed(1)} mL`}
  </text>
}

export function LossChart() {
  return <div className={styles.chart} aria-label="示例训练和验证 BCE 损失曲线">
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={exampleLosses} margin={{ top: 16, right: 22, left: 0, bottom: 8 }}>
        <CartesianGrid stroke={grid} vertical={false} />
        <XAxis dataKey="epoch" tick={axisStyle} axisLine={false} tickLine={false} tickMargin={8}
          label={{ value: '训练轮次', position: 'insideBottom', offset: 0, fill: axis, fontSize: 12 }} height={42} />
        <YAxis tick={axisStyle} axisLine={false} tickLine={false} domain={[0, .8]} width={48} />
        <Tooltip labelFormatter={epoch => `第 ${epoch} 轮`} contentStyle={tooltip} />
        <Legend wrapperStyle={legend} />
        <Line type="monotone" dataKey="train" name="训练 BCE" stroke={blue} strokeWidth={2.5} dot={false} isAnimationActive={false} />
        <Line type="monotone" dataKey="validation" name="验证 BCE" stroke={gray} strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  </div>
}

export function VolumeChart({ series, edv, esv }) {
  return <div className={styles.chart} aria-label="左室容积示例曲线，显示 ED 峰与 ES 谷">
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={series} margin={{ top: 30, right: 25, left: 10, bottom: 8 }}>
        <CartesianGrid stroke={grid} vertical={false} />
        <XAxis dataKey="frame" type="number" domain={[0, 19]} ticks={[0, 4, 8, 12, 16, 19]}
          tick={axisStyle} axisLine={false} tickLine={false} tickMargin={8}
          label={{ value: '帧索引', position: 'insideBottom', offset: 0, fill: axis, fontSize: 12 }} height={42} />
        <YAxis tick={axisStyle} axisLine={false} tickLine={false} width={62} allowDecimals={false}
          label={{ value: '容积 (mL)', angle: -90, position: 'insideLeft', fill: axis, fontSize: 12 }}
          domain={['dataMin - 8', 'dataMax + 8']} />
        <Tooltip labelFormatter={frame => `帧 ${frame}`} formatter={value => `${value} mL`} contentStyle={tooltip} />
        <Legend wrapperStyle={legend} />
        <Line dataKey="raw" name="原始容积" stroke={gray} strokeWidth={1.5} dot={false} connectNulls={false} isAnimationActive={false} />
        <Line dataKey="smooth" name="平滑容积" stroke={blue} strokeWidth={2.5} dot={false} connectNulls={false} isAnimationActive={false} />
        <ReferenceDot x={0} y={edv} r={5} fill={blue} stroke="#fff" strokeWidth={2}
          label={<PhaseLabel phase="ED" volume={edv} />} />
        {esv != null && <ReferenceDot x={19} y={esv} r={5} fill={blue} stroke="#fff" strokeWidth={2}
          label={<PhaseLabel phase="ES" volume={esv} />} />}
      </LineChart>
    </ResponsiveContainer>
  </div>
}
