import { useEffect, useState } from 'react'

const base = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/+$/, '').replace(/\/api$/, '')

export const apiEnabled = Boolean(base)
export const apiUrl = path => `${base}${path}`

export async function requestApi(path, options) {
  let response
  try {
    response = await fetch(apiUrl(path), options)
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error('无法连接后端服务，请稍后重试。')
  }
  const body = await response.json().catch(() => null)
  if (!response.ok || body == null) {
    const error = new Error(body?.detail ?? `后端响应异常（HTTP ${response.status}）`)
    error.status = response.status
    throw error
  }
  return body
}

export function useApi(path) {
  const [result, setResult] = useState(null)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    if (!apiEnabled || !path) return
    const controller = new AbortController()
    requestApi(path, { signal: controller.signal }).then(data => {
      if (!controller.signal.aborted) setResult({ path, attempt, data })
    }).catch(error => {
      if (!controller.signal.aborted) setResult({ path, attempt, error })
    })
    return () => controller.abort()
  }, [path, attempt])

  const current = result?.path === path && result.attempt === attempt && result
  return {
    data: current?.data, error: current?.error, loading: apiEnabled && Boolean(path) && !current,
    retry: () => setAttempt(value => value + 1),
  }
}
