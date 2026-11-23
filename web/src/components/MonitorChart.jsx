import { CartesianGrid, Line, LineChart, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import styles from '../styles/Monitor.module.css'

const axis = { fontSize: 11, fill: '#536783' }

export function MonitorChart({ series, cursor, events, duration, simulation = false }) {
  return <div className={styles.chart} role="group" aria-label={simulation ? '仿真容积曲线' : '逐帧容积曲线'}>
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={series} margin={{ top: 17, right: 17, left: 0, bottom: 1 }}>
        <CartesianGrid stroke="#e5edf7" vertical={false} />
        <XAxis dataKey="time" type="number" domain={[0, duration]} tick={axis}
          tickLine={false} axisLine={false} tickFormatter={value => `${Math.round(value)}`} />
        <YAxis width={37} tick={axis} tickLine={false} axisLine={false} allowDecimals={false}
          domain={[min => Math.max(0, Math.floor((min - 5) / 10) * 10),
            max => Math.ceil((max + 5) / 10) * 10]} />
        <Tooltip labelFormatter={value => `${Number(value).toFixed(1)} ms`}
          formatter={value => [`${value.toFixed(1)} mL`, '左室容积']} />
        <Line dataKey="volume" stroke="#2563eb" strokeWidth={2.5} dot={false} connectNulls={false} isAnimationActive={false} />
        {events.map(({ phase, time, volume }, i) => <ReferenceDot key={`${phase}-${time}`} x={time} y={volume} r={4}
          fill={phase === 'ES' ? '#b6631b' : '#2563eb'} stroke="#fff" strokeWidth={1.7}
          label={{ value: phase, position: i === 0 ? 'right' : time === duration ? 'left' : 'top',
            fontSize: 11, fill: '#344b6a' }} />)}
        {cursor && <ReferenceLine x={cursor.time} stroke="#6786b7" strokeDasharray="3 4" />}
        {cursor?.volume != null && <ReferenceDot x={cursor.time} y={cursor.volume} r={6}
          fill="none" stroke="#244b8c" strokeWidth={1.5} />}
      </LineChart>
    </ResponsiveContainer>
  </div>
}
