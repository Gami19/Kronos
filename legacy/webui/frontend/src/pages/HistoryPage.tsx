import { useEffect, useMemo, useState } from 'react'
import { getPredictionResultDetail, listPredictionResults, marketHistory } from '../api/endpoints'
import type {
  OhlcRow,
  PredictionDetailRecord,
  PredictionResultListItem,
} from '../api/types'
import AccuracyMetricsPanel from '../components/AccuracyMetricsPanel'
import ComparisonPanel from '../components/ComparisonPanel'
import EChartsCandlestick from '../components/EChartsCandlestick'
import { formatUserFacingError } from '../utils/formatError'
import { mergeOhlcSeries } from '../utils/ohlcMerge'
import { useTicker } from '../context/TickerContext'

const HISTORY_PERIODS = ['5d', '30d', '60d', '1mo'] as const

export default function HistoryPage() {
  const { marketHistoryTickerQuery, yfinanceDisplaySymbol } = useTicker()

  const [list, setList] = useState<PredictionResultListItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<PredictionDetailRecord | null>(null)
  const [listError, setListError] = useState<string | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [loadingList, setLoadingList] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(false)

  const [historyPeriod, setHistoryPeriod] = useState<(typeof HISTORY_PERIODS)[number]>('30d')
  const [marketRows, setMarketRows] = useState<OhlcRow[]>([])
  const [marketError, setMarketError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoadingList(true)
      setListError(null)
      try {
        const res = await listPredictionResults()
        if (!cancelled) setList(res.results ?? [])
      } catch (e) {
        if (!cancelled) setListError(formatUserFacingError(e))
      } finally {
        if (!cancelled) setLoadingList(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!selectedId) {
      setDetail(null)
      return
    }
    let cancelled = false
    ;(async () => {
      setLoadingDetail(true)
      setDetailError(null)
      try {
        const d = await getPredictionResultDetail(selectedId)
        if (!cancelled) setDetail(d)
      } catch (e) {
        if (!cancelled) {
          setDetailError(formatUserFacingError(e))
          setDetail(null)
        }
      } finally {
        if (!cancelled) setLoadingDetail(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [selectedId])

  useEffect(() => {
    if (!detail) {
      setMarketRows([])
      setMarketError(null)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const m = await marketHistory({
          ...(marketHistoryTickerQuery ? { ticker: marketHistoryTickerQuery } : {}),
          interval: '5m',
          period: historyPeriod,
        })
        if (cancelled) return
        if (m.success && m.rows?.length) {
          setMarketRows(m.rows as OhlcRow[])
          setMarketError(null)
        } else {
          setMarketRows([])
          setMarketError(m.error ?? '市場履歴を取得できませんでした')
        }
      } catch (e) {
        if (!cancelled) {
          setMarketRows([])
          setMarketError(formatUserFacingError(e))
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [detail, historyPeriod, marketHistoryTickerQuery])

  const preds = detail?.prediction_results ?? []
  const acts = detail?.actual_data ?? []
  const showComparison = acts.length > 0 && preds.length > 0

  const mergedSeries = useMemo(() => {
    if (!detail) {
      return { history: [], prediction: [], actual: [] }
    }
    return mergeOhlcSeries(
      marketRows,
      detail.prediction_results ?? [],
      detail.actual_data ?? [],
    )
  }, [marketRows, detail])

  const hasChartData =
    mergedSeries.history.length + mergedSeries.prediction.length + mergedSeries.actual.length > 0

  return (
    <div className="history-page">
      <section className="panel history-page__list">
        <h2>過去の予測結果</h2>
        {loadingList && <p className="msg-muted">一覧を読み込み中…</p>}
        {listError && <p className="msg-error">{listError}</p>}
        {!loadingList && !list.length && <p className="msg-muted">保存された結果がありません。</p>}
        <div className="table-wrap">
          <table className="data-table history-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>保存時刻</th>
                <th>種別</th>
                <th>件数</th>
              </tr>
            </thead>
            <tbody>
              {list.map((row) => (
                <tr
                  key={row.id}
                  className={selectedId === row.id ? 'history-table__row--active' : undefined}
                  onClick={() => setSelectedId(row.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      setSelectedId(row.id)
                    }
                  }}
                  role="button"
                  tabIndex={0}
                >
                  <td>{row.id}</td>
                  <td>{row.timestamp ?? '—'}</td>
                  <td className="history-table__type">{row.prediction_type ?? '—'}</td>
                  <td>
                    予測 {row.counts?.prediction_results ?? 0} / 実測 {row.counts?.actual_data ?? 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel history-page__detail">
        <h2>詳細</h2>
        {!selectedId && <p className="msg-muted">テーブルから行を選択してください。</p>}
        {selectedId && loadingDetail && <p className="msg-muted">読み込み中…</p>}
        {detailError && <p className="msg-error">{detailError}</p>}
        {detail && !loadingDetail && (
          <>
            <p className="msg-muted small">{detail.timestamp}</p>
            <p className="msg-muted small">
              履歴は yfinance の <strong>{yfinanceDisplaySymbol}</strong>（5分足）です。保存時の CSV
              と一致しない場合があります。
            </p>
            <div className="form-group chart-period-row">
              <label htmlFor="hist-mh-period">市場履歴の取得期間</label>
              <select
                id="hist-mh-period"
                value={historyPeriod}
                onChange={(e) => setHistoryPeriod(e.target.value as (typeof HISTORY_PERIODS)[number])}
              >
                {HISTORY_PERIODS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            {marketError && (
              <p className="msg-warning small">
                履歴取得: {marketError}（予測・実測のみ表示します）
              </p>
            )}
            {hasChartData ? (
              <EChartsCandlestick
                history={mergedSeries.history}
                prediction={mergedSeries.prediction}
                actual={mergedSeries.actual}
                title="統合ローソク"
                subtitle={`${yfinanceDisplaySymbol} · 5m · ${historyPeriod}`}
                height={520}
                showDataZoom
              />
            ) : (
              <p className="msg-muted">表示できる OHLC データがありません。</p>
            )}
            {showComparison && (
              <>
                <AccuracyMetricsPanel
                  predictionType={detail.prediction_type}
                  predictions={preds}
                  actuals={acts}
                />
                <ComparisonPanel
                  predictionType={detail.prediction_type}
                  predictions={preds}
                  actuals={acts}
                />
              </>
            )}
          </>
        )}
      </section>
    </div>
  )
}
