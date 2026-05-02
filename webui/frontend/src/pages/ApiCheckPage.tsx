import { useEffect, useState } from 'react'
import { getAvailableModels, getModelStatus } from '../api/endpoints'
import { formatUserFacingError } from '../utils/formatError'
import type { AvailableModelsResponse, ModelStatusResponse } from '../api/types'

export default function ApiCheckPage() {
  const [status, setStatus] = useState<ModelStatusResponse | null>(null)
  const [models, setModels] = useState<AvailableModelsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const [s, m] = await Promise.all([getModelStatus(), getAvailableModels()])
        if (!cancelled) {
          setStatus(s)
          setModels(m)
        }
      } catch (e) {
        if (!cancelled) {
          setError(formatUserFacingError(e))
          setStatus(null)
          setModels(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="page-card">
      <h2 style={{ marginTop: 0 }}>API 接続確認</h2>
      <p className="msg-muted">
        <code>GET /api/model-status</code> と <code>GET /api/available-models</code> を呼び出しています。
      </p>
      {loading && <p>読み込み中…</p>}
      {error && <p className="msg-error">{error}</p>}
      {!loading && !error && (
        <>
          <h3>model-status</h3>
          <pre className="api-json">{JSON.stringify(status, null, 2)}</pre>
          <h3>available-models</h3>
          <pre className="api-json">{JSON.stringify(models, null, 2)}</pre>
        </>
      )}
    </div>
  )
}
