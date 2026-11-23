import { useEffect, useRef } from 'react'
import { reflectors, soundSpeed } from '../data/beamforming.js'
import styles from '../styles/Monitor.module.css'

function grid(context, width, height) {
  context.fillStyle = '#091629'
  context.fillRect(0, 0, width, height)
  context.strokeStyle = '#25405f'
  context.lineWidth = 1
  context.beginPath()
  for (let x = 28; x < width; x += 36) { context.moveTo(x, 23); context.lineTo(x, height - 21) }
  for (let y = 24; y < height - 20; y += 30) { context.moveTo(28, y); context.lineTo(width - 28, y) }
  context.stroke()
}

export function AcquisitionDiagram({ rf, depth, progress }) {
  const canvas = useRef(null)
  useEffect(() => {
    const context = canvas.current.getContext('2d')
    const { width, height } = canvas.current
    grid(context, width, height)
    const xAt = x => width / 2 + x * 8
    const yAt = z => 37 + z * (height - 70) / depth
    const echo = reflectors[0]
    const x = xAt(echo.x)
    const y = yAt(echo.z)
    context.strokeStyle = '#66c8f98a'
    context.beginPath()
    for (const receiver of rf.receivers) {
      context.moveTo(x, y)
      context.lineTo(xAt(receiver), 37)
    }
    context.stroke()
    for (const receiver of rf.receivers) {
      context.fillStyle = '#71b6fe'
      context.fillRect(xAt(receiver) - 2.5, 31, 5, 10)
    }
    for (const point of reflectors.filter(item => item.z <= depth)) {
      context.fillStyle = '#efb06a'
      context.beginPath()
      context.arc(xAt(point.x), yAt(point.z), 4.2, 0, 2 * Math.PI)
      context.fill()
    }
    if (progress != null) {
      const pulse = (progress * 2) % 1
      context.strokeStyle = '#74d9ff'
      context.lineWidth = 2
      if (pulse < 0.5) {
        const wave = yAt(echo.z * pulse * 2)
        context.beginPath()
        context.moveTo(width * 0.23, wave)
        context.lineTo(width * 0.77, wave)
        context.stroke()
      } else {
        const travelled = (pulse - 0.5) * 2
        context.beginPath()
        context.arc(x, y, 4 + travelled * (y - 37), Math.PI, 2 * Math.PI)
        context.stroke()
      }
    }
    context.fillStyle = '#b7cde8'
    context.font = '15px sans-serif'
    context.fillText('贴片接收阵元', 28, 22)
    context.fillText(`${depth} mm`, 29, height - 11)
  }, [rf, depth, progress])
  return <canvas ref={canvas} width={640} height={288} role="img" aria-label="贴片阵元、声波传播和点散射体示意" />
}

export function RFDiagram({ rf, sampleRate, progress }) {
  const canvas = useRef(null)
  useEffect(() => {
    const context = canvas.current.getContext('2d')
    const { width, height } = canvas.current
    grid(context, width, height)
    const indices = [...new Set([0, Math.floor((rf.rows.length - 1) / 2), rf.rows.length - 1])]
    const point = reflectors[0]
    const xAtSample = sample => 64 + sample / (rf.rows[0].length - 1) * (width - 87)
    for (const [position, index] of indices.entries()) {
      const baseline = 53 + position * 74
      context.fillStyle = '#c8dbf3'
      context.font = '14px sans-serif'
      context.fillText(`CH ${index + 1}`, 16, baseline + 4)
      context.strokeStyle = '#75c6ff'
      context.beginPath()
      const trace = rf.rows[index]
      for (let sample = 0; sample < trace.length; sample++) {
        const x = xAtSample(sample)
        const y = baseline - 29 * trace[sample]
        if (sample === 0) context.moveTo(x, y)
        else context.lineTo(x, y)
      }
      context.stroke()
      const delay = (point.z + Math.hypot(point.x - rf.receivers[index], point.z)) / soundSpeed
      context.fillStyle = '#ffc07f'
      context.beginPath()
      context.arc(xAtSample(delay * sampleRate), baseline - 29 * point.strength, 4, 0, 2 * Math.PI)
      context.fill()
    }
    if (progress != null) {
      const x = xAtSample(progress * (rf.rows[0].length - 1))
      context.strokeStyle = '#b4d3fa'
      context.beginPath()
      context.moveTo(x, 21)
      context.lineTo(x, height - 28)
      context.stroke()
    }
    context.fillStyle = '#b7cde8'
    context.fillText('0 μs', 64, height - 11)
    context.textAlign = 'right'
    context.fillText(`${rf.timeLimit.toFixed(1)} μs`, width - 22, height - 11)
    context.textAlign = 'left'
  }, [rf, sampleRate, progress])
  return <canvas ref={canvas} width={640} height={288} role="img" aria-label="按接收通道绘制的模拟 RF 采样波形" />
}

export function DASImage({ image, depth, progress }) {
  const canvas = useRef(null)
  useEffect(() => {
    const surface = canvas.current
    const context = surface.getContext('2d')
    const data = context.createImageData(image.width, image.height)
    for (let index = 0; index < image.values.length; index++) {
      const value = image.values[index]
      data.data.set([value, value, value, 255], index * 4)
    }
    context.putImageData(data, 0, 0)
  }, [image])
  return <div className={styles.dasImage}>
    <canvas ref={canvas} width={image.width} height={image.height} role="img" aria-label="由模拟 RF 经 DAS 重建的灰阶点散射体图像" />
    {progress != null && <span className={styles.scanLine} style={{ top: `${progress * 100}%` }} />}
    <div className={styles.imageScale}><span>60 mm 视野</span><span>深度 {depth} mm</span></div>
  </div>
}
