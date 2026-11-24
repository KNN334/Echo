import { useEffect, useRef, useState } from 'react'
import { ApiStatus } from '../components/ApiStatus.jsx'
import { SegmentationPlayback } from '../components/SegmentationPlayback.jsx'
import { EmptyState, PageHeading, Panel } from '../components/UI.jsx'
import { apiEnabled, requestApi, useApi } from '../data/api.js'
import styles from '../styles/Pages.module.css'
import ui from '../styles/UI.module.css'

const messages = {
  uploading: '正在上传影像…', queued: '影像已提交，正在等待推理…',
  processing: '正在解码并分割影像…',
}

export default function Segment() {
  const health = useApi('/api/health')
  const [submission, setSubmission] = useState({})
  const controller = useRef(null)
  const config = health.data
  const busy = Boolean(messages[submission.status])

  useEffect(() => () => controller.current?.abort(), [])

  async function segment(data, caseId) {
    controller.current?.abort()
    controller.current = new AbortController()
    const { signal } = controller.current
    const options = { method: 'POST', signal }
    try {
      if (!caseId) {
        setSubmission({ status: 'uploading' })
        const upload = await requestApi('/api/upload?for_inference=true', { ...options, body: data })
        caseId = upload.case_id
      }
      const path = `/api/inference/${caseId}`
      setSubmission({ status: 'queued', caseId })
      let job = await requestApi(path, options)
      while (job.status === 'queued' || job.status === 'processing') {
        setSubmission({ ...job, caseId })
        await new Promise(resolve => setTimeout(resolve, 850))
        job = await requestApi(`${path}/status`, { signal })
      }
      if (job.status !== 'done') throw new Error(job.detail ?? '服务未能完成分割。')
      const result = await requestApi(`${path}/result`, { signal })
      setSubmission({ status: 'done', result })
    } catch (error) {
      if (!signal.aborted) setSubmission({ error: error.message, caseId })
    }
  }

  async function submit(event) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const file = data.get('file')
    if (!file.size || file.size > config.upload_max_bytes) {
      setSubmission({ error: file.size ? '文件超过上传大小限制。' : '请选择非空的影像文件。' })
      return
    }
    await segment(data)
  }

  return <div className={styles.stack}>
    <PageHeading title="影像分割" description="上传心尖二腔心或四腔心灰阶超声影像，由 DRA-UNet 分割左心室。" />
    <Panel title="上传超声心动图">
      {!apiEnabled && <EmptyState title="在线推理服务尚未接入" detail="该功能需要连接服务器上的 DRA-UNet。" />}
      {apiEnabled && !config && <ApiStatus request={health} unavailable="无法连接推理服务" />}
      {config && !config.inference_enabled && <EmptyState title="当前服务器未启用在线推理" detail="连接已启用 DRA-UNet 的服务后即可上传影像。" />}
      {config?.inference_enabled && <form className={styles.uploadForm} onSubmit={submit}>
        <p>{config.inference_formats.join('、')} · 单文件最多 {(config.upload_max_bytes / 1024 / 1024).toLocaleString('zh-CN', { maximumFractionDigits: 2 })} MiB · 视频最多 {config.inference_max_frames} 帧</p>
        <label className={styles.uploadField}>选择影像
          <input type="file" name="file" accept={config.inference_formats.join(',')} required disabled={busy} />
        </label>
        <label className={styles.uploadConsent}>
          <input type="checkbox" name="deidentified" value="true" required disabled={busy} />
          我确认画面、文件名及元数据已去除患者身份信息，同意将影像发送至服务器用于研究分割。
        </label>
        <button className={ui.primaryButton} type="submit" disabled={busy}>上传并分割</button>
        {busy && <div className={styles.segmentProgress} role="status">
          <progress aria-label="分割进度" value={submission.completed_frames ?? undefined} max={submission.total_frames ?? undefined} />
          <span>{messages[submission.status]}{submission.total_frames ? ` ${submission.completed_frames} / ${submission.total_frames} 帧` : ''}</span>
        </div>}
        {submission.error && <p role="alert">{submission.error}</p>}
        {submission.error && submission.caseId && <button className={ui.secondaryButton} type="button"
          onClick={() => segment(null, submission.caseId)}>重试已上传影像</button>}
      </form>}
    </Panel>
    {submission.result && <SegmentationPlayback key={submission.result.case_id} result={submission.result} />}
  </div>
}
