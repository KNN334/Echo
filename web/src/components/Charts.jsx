import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import losses from '../assets/dra-training-loss.json'
import styles from '../styles/UI.module.css'

const axis = { fontSize: 12, fill: '#65738b' }

export function LossChart() {
  return <div className={styles.chart} aria-label="DRA-UNet 训练和验证主分割损失曲线">
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={losses} margin={{ top: 16, right: 22, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="#e7edf5" vertical={false} />
        <XAxis dataKey="epoch" tick={axis} axisLine={false} tickLine={false} tickMargin={8}
          label={{ value: '训练轮次', position: 'insideBottom', offset: 0, fill: '#65738b', fontSize: 12 }} height={42} />
        <YAxis tick={axis} axisLine={false} tickLine={false} width={48} />
        <Tooltip labelFormatter={epoch => '第 ' + epoch + ' 轮'} formatter={value => value.toFixed(4)} />
        <Legend wrapperStyle={{ paddingTop: '8px' }} />
        <Line dataKey="train" name="训练 BCE + Dice" stroke="#2563eb" strokeWidth={2.5} dot={false} isAnimationActive={false} />
        <Line dataKey="validation" name="验证 BCE + Dice" stroke="#8294ad" strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  </div>
}
