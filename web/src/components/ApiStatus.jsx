import { Loading } from './Loading.jsx'
import { EmptyState } from './UI.jsx'

export function ApiStatus({ request, unavailable = '数据暂不可用' }) {
  if (request.loading) return <Loading label="正在读取研究报表…" />
  if (request.error) return <EmptyState title={unavailable} detail={request.error.message}
    action="重试" onAction={request.retry} />
  const warning = request.data?.warnings?.[0]
  return warning ? <EmptyState title={warning} detail="检查报表文件并重启后端以重新加载。" /> : null
}
