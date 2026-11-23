import { useEffect, useRef } from 'react'
import styles from '../styles/Pages.module.css'

export function ContourExample({ phase, unavailable = false, showReference = true }) {
  const canvas = useRef(null)
  useEffect(() => {
    const ctx = canvas.current.getContext('2d')
    const width = 560
    const height = 300
    const center = width / 2
    const radius = 276
    const ed = phase === 'ED'
    const region = new Path2D()
    region.moveTo(center, 12)
    region.arc(center, 12, radius, Math.PI * 0.23, Math.PI * 0.77)
    region.closePath()
    ctx.fillStyle = '#080f1b'
    ctx.fillRect(0, 0, width, height)
    const image = ctx.createImageData(width, height)
    let seed = ed ? 7 : 21
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const dx = x - center
        const dy = y - 12
        if (dy < Math.abs(dx) * .88 || Math.hypot(dx, dy) > radius) continue
        seed = (1664525 * seed + 1013904223) >>> 0
        const chamber = ((dx + 0.15 * (y - 140)) / (ed ? 63 : 45)) ** 2 + ((y - 151) / (ed ? 90 : 73)) ** 2
        const tissue = 18 + 21 * (Math.sin(dx * .036 + Math.sin(y / 22)) + 1)
          + 13 * Math.cos(y * .094 - dx * .049) + 32 * Math.exp(-((chamber - 1) ** 2) * 15)
        const speckle = 24 * (seed / 4294967296 - .5)
        const tone = Math.round((tissue + speckle) * (chamber < 1 ? .4 : 1))
        const offset = (y * width + x) * 4
        image.data[offset] = tone
        image.data[offset + 1] = tone + 3
        image.data[offset + 2] = tone + 9
        image.data[offset + 3] = 255
      }
    }
    const background = document.createElement('canvas')
    background.width = width
    background.height = height
    background.getContext('2d').putImageData(image, 0, 0)
    ctx.save()
    ctx.clip(region)
    ctx.drawImage(background, 0, 0)
    ctx.restore()
    ctx.strokeStyle = '#526277'
    ctx.lineWidth = 1
    ctx.stroke(region)

    if (!unavailable) {
      const outline = (color, dashed) => {
        ctx.beginPath()
        ctx.ellipse(center + (dashed ? 6 : 0), ed ? 149 : 156,
          (ed ? 55 : 37) + (dashed ? 4 : 0), (ed ? 80 : 63) + (dashed ? 2 : 0),
          0.15, 0, Math.PI * 2)
        ctx.strokeStyle = color
        ctx.lineWidth = 2.7
        ctx.setLineDash(dashed ? [7, 5] : [])
        ctx.stroke()
      }
      if (showReference) outline('#c7d1dc', true)
      outline('#53a4fc', false)
    }
  }, [phase, unavailable, showReference])

  return <figure className={styles.contour}>
    <canvas ref={canvas} width="560" height="300" role="img"
      aria-label={`${phase} 超声轮廓示意${unavailable ? '，相位缺失' : ''}`} />
    <figcaption><strong>{phase} · {phase === 'ED' ? '舒张末期' : '收缩末期'}</strong><span>{unavailable ? '相位缺失' : '合成示例图'}</span></figcaption>
  </figure>
}
