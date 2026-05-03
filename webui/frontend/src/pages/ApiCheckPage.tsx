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
      <p className="msg-muted small">
        ファインチューン向けデータ API: <code>POST /api/data/import-market</code>、
        <code>POST /api/data/upload</code>（multipart）、<code>POST /api/data/validate</code>（常に HTTP 200 +{' '}
        <code>valid</code>）。
      </p>
      <p className="msg-muted small">
        プレビュー・予測: <code>POST /api/load-data</code>（<code>file_path</code>）、<code>POST /api/predict</code>（
        <code>file_path</code> / lookback / pred_len / temperature / top_p / sample_count、任意 <code>start_date</code>
        ）。
      </p>
      <p className="msg-muted small">
        <strong>API 一覧（ファインチューン UI 想定）</strong>:{' '}
        <code>POST /api/data/import-market</code> · <code>POST /api/data/upload</code> ·{' '}
        <code>POST /api/data/validate</code> · <code>POST /api/load-data</code> · <code>POST /api/load-model</code> ·{' '}
        <code>POST /api/train/jobs</code> · <code>GET /api/train/jobs</code> · <code>GET /api/train/jobs/&lt;id&gt;</code> ·{' '}
        <code>GET /api/train/jobs/&lt;id&gt;/log</code> · <code>POST /api/predict</code> · <code>POST /api/backtest/run</code>
        。
      </p>
      <p className="msg-muted small">
        学習ジョブ API: <code>POST /api/train/jobs</code>（201）、<code>GET /api/train/jobs</code>、{' '}
        <code>{'GET /api/train/jobs/<job_id>'}</code>、<code>{'GET /api/train/jobs/<job_id>/log?tail_lines='}</code>。
      </p>
      <p className="msg-muted small">
        <code>POST /api/load-model</code> は排他: <code>model_key</code>（HF） / <code>train_job_id</code>（meta から
        checkpoint） / <code>local_tokenizer_path</code>＋<code>local_predictor_path</code> のいずれか一組。
      </p>
      <p className="msg-muted small">
        <code>POST /api/backtest/run</code>（同期）: <code>backtest_spec_version: &quot;1.0&quot;</code>、
        <code>data_path</code>、必須 <code>train_last_timestamp</code>、checkpoint は{' '}
        <code>train_job_id</code> または <code>local_*</code> 排他、任意 <code>eval_start</code>/<code>eval_end</code>。
        応答は <code>metrics</code> と <code>series</code>（累積倍率曲線）。
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
