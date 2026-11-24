import { useState } from 'react'
import { requestApi, useApi } from '../data/api.js'
import { ApiStatus } from './ApiStatus.jsx'
import { Panel } from './UI.jsx'
import styles from '../styles/Pages.module.css'
import ui from '../styles/UI.module.css'

export function CaseUpload() {
  const health = useApi('/api/health')
  const [submission, setSubmission] = useState({})
  const config = health.data

  async function submit(event) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    if (data.get('file').size > config.upload_max_bytes) {
      setSubmission({ error: '文件超过上传大小限制。' })
      return
    }
    setSubmission({ pending: true })
    try {
      const result = await requestApi('/api/upload', { method: 'POST', body: data })
      form.reset()
      setSubmission({ caseId: result.case_id })
    } catch (error) {
      setSubmission({ error: error.message })
    }
  }

  return <Panel title="上传研究影像" subtitle="上传后进行格式和大小校验，并生成匿名存档编号。推理待第二阶段接入。">
    {!config && <ApiStatus request={health} unavailable="无法读取上传配置" />}
    {config && !config.uploads_enabled && <p className={styles.note}>当前服务未开启上传。</p>}
    {config?.uploads_enabled && <form className={styles.uploadForm} onSubmit={submit}>
      <p>允许 {config.upload_formats.join('、')}，文件上限 {(config.upload_max_bytes / 1024 / 1024).toLocaleString('zh-CN', { maximumFractionDigits: 2 })} MiB。</p>
      <label className={styles.uploadField}>选择影像或压缩包
        <input type="file" name="file" accept={config.upload_formats.join(',')} required disabled={submission.pending} />
      </label>
      <label className={styles.uploadConsent}>
        <input type="checkbox" name="deidentified" value="true" required disabled={submission.pending} />
        我已确认文件名、画面、元数据及压缩包内文件均已去除患者身份信息。
      </label>
      <button className={ui.primaryButton} type="submit" disabled={submission.pending}>{submission.pending ? '正在上传…' : '校验并存档'}</button>
      {submission.error && <p role="alert">{submission.error}</p>}
      {submission.caseId && <p role="status">存档成功，匿名编号 <strong>{submission.caseId}</strong>。</p>}
    </form>}
  </Panel>
}
