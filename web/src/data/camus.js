import cases from '../assets/camus-cases.json'

const atlases = import.meta.glob('../assets/patient*_2CH.webp', {
  eager: true, query: '?url', import: 'default',
})

export const camusCases = cases.map(cine => ({
  ...cine,
  atlasUrl: atlases[`../assets/${cine.atlas_file}`],
}))

export const homeCine = camusCases.find(cine => cine.patient_id === 'patient0015')

export function cineSeries(cine) {
  return cine.frames.map(frame => ({ time: frame.time_s * 1000, volume: frame.volume_ml }))
}

export function cineMarkers(cine, series) {
  return cine.events.flatMap(event => [
    { phase: 'ED', ...series[event.ed_frame] },
    { phase: 'ES', ...series[event.es_frame] },
  ])
}
