// Distances in mm and times in microseconds, so a MHz sampling rate is samples per microsecond.
export const patchDefaults = { channels: 8, pitch: 1.2, frequency: 3.5, sampleRate: 20, depth: 65 }
export const soundSpeed = 1.54
export const reflectors = [
  { x: -9, z: 22, strength: 0.86 },
  { x: 8, z: 35, strength: 1 },
  { x: -4, z: 47, strength: 0.65 },
]

function flightTime(x, z, receiver) {
  return (z + Math.hypot(x - receiver, z)) / soundSpeed
}

export function acquireRF({ channels, pitch, frequency, sampleRate, depth }) {
  const receivers = Array.from({ length: channels }, (_, index) => (index - (channels - 1) / 2) * pitch)
  const timeLimit = 2 * Math.hypot(depth, 30 + Math.abs(receivers[0])) / soundSpeed + 3
  const sampleCount = Math.ceil(timeLimit * sampleRate)
  const rows = receivers.map(receiver => {
    const row = new Float32Array(sampleCount)
    for (const { x, z, strength } of reflectors) {
      const arrival = flightTime(x, z, receiver)
      const halfWidth = 2.6 / frequency
      const first = Math.max(0, Math.floor((arrival - halfWidth) * sampleRate))
      const last = Math.min(sampleCount - 1, Math.ceil((arrival + halfWidth) * sampleRate))
      for (let index = first; index <= last; index++) {
        const phase = (index / sampleRate - arrival) * frequency
        row[index] += strength * Math.exp(-0.8 * phase ** 2) * Math.cos(2 * Math.PI * phase)
      }
    }
    return row
  })
  return { receivers, rows, timeLimit }
}

function interpolate(row, sample) {
  const left = Math.floor(sample)
  if (left < 0 || left + 1 >= row.length) return 0
  return row[left] + (row[left + 1] - row[left]) * (sample - left)
}

export function reconstructDAS(rf, { depth, frequency, sampleRate }) {
  const width = 176
  const height = 160
  const values = new Uint8ClampedArray(width * height)
  const quarterPeriodSamples = sampleRate / (4 * frequency)
  for (let row = 0; row < height; row++) {
    const z = (row + 0.5) * depth / height
    for (let column = 0; column < width; column++) {
      const x = ((column + 0.5) / width - 0.5) * 60
      let real = 0
      let quadrature = 0
      for (let channel = 0; channel < rf.receivers.length; channel++) {
        const sample = flightTime(x, z, rf.receivers[channel]) * sampleRate
        const trace = rf.rows[channel]
        real += interpolate(trace, sample)
        quadrature += (interpolate(trace, sample - quarterPeriodSamples) - interpolate(trace, sample + quarterPeriodSamples)) / 2
      }
      const envelope = Math.hypot(real, quadrature) / rf.rows.length
      const decibels = 20 * Math.log10(Math.max(envelope, 0.0001))
      values[row * width + column] = 255 * (1 + decibels / 38)
    }
  }
  return { values, width, height }
}
