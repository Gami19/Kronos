import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  getAvailableModels,
  getDataFiles,
  loadData,
  loadModel,
  marketHistory,
  predict,
} from '../api/endpoints'
import type { AvailableModelsResponse, LoadDataResponse, OhlcRow, PredictResponse } from '../api/types'
import ComparisonPanel from '../components/ComparisonPanel'
import EChartsCandlestick from '../components/EChartsCandlestick'
import OhlcCandlestickPreview from '../components/OhlcCandlestickPreview'
import TimeWindowSlider, {
  computePredictStartDateIso,
  LOOKBACK,
  PRED_LEN,
  windowFitsRows,
} from '../components/TimeWindowSlider'
import { formatUserFacingError } from '../utils/formatError'
import { mergeOhlcSeries } from '../utils/ohlcMerge'
import { useTicker } from '../context/TickerContext'

type Banner = { kind: 'success' | 'error' | 'info' | 'warning'; text: string }

const PREVIEW_ROWS = 500
const HISTORY_PERIODS = ['5d', '30d', '60d', '1mo'] as const

export default function WorkspacePage() {
  const {
    tickers,
    selectedTickerId,
    setSelectedTickerId,
    marketHistoryTickerQuery,
    yfinanceDisplaySymbol,
    loading: tickerLoading,
    error: tickerError,
  } = useTicker()

  const [banner, setBanner] = useState<Banner | null>(null)
  const [busy, setBusy] = useState(false)

  const [modelsState, setModelsState] = useState<AvailableModelsResponse | null>(null)
  const [modelKey, setModelKey] = useState('')
  const [device, setDevice] = useState('cpu')
  const [modelLoaded, setModelLoaded] = useState(false)

  const [dataFiles, setDataFiles] = useState<{ name: string; path: string; size: string }[]>([])
  const [filePath, setFilePath] = useState('')
  const [loaded, setLoaded] = useState<LoadDataResponse | null>(null)

  const [startPct, setStartPct] = useState(0.1)

  const [temperature, setTemperature] = useState(1)
  const [topP, setTopP] = useState(0.9)
  const [sampleCount, setSampleCount] = useState(1)

  const [predictResult, setPredictResult] = useState<PredictResponse | null>(null)

  const [historyPeriod, setHistoryPeriod] = useState<(typeof HISTORY_PERIODS)[number]>('30d')
  const [marketRows, setMarketRows] = useState<OhlcRow[]>([])
  const [marketError, setMarketError] = useState<string | null>(null)

  const showBanner = useCallback((b: Banner, ms = 6000) => {
    setBanner(b)
    window.setTimeout(() => setBanner(null), ms)
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const m = await getAvailableModels()
        if (!cancelled) setModelsState(m)
      } catch (e) {
        if (!cancelled) showBanner({ kind: 'error', text: formatUserFacingError(e) })
      }
    })()
    return () => {
      cancelled = true
    }
  }, [showBanner])

  useEffect(() => {
    if (!selectedTickerId || tickerLoading) return
    let cancelled = false
    ;(async () => {
      try {
        const files = await getDataFiles(selectedTickerId)
        if (!cancelled) {
          setDataFiles(files)
          setFilePath('')
          setLoaded(null)
          setPredictResult(null)
        }
      } catch (e) {
        if (!cancelled) showBanner({ kind: 'error', text: formatUserFacingError(e) })
      }
    })()
    return () => {
      cancelled = true
    }
  }, [selectedTickerId, tickerLoading, showBanner])

  useEffect(() => {
    if (loaded?.success && loaded.data_info?.rows) {
      setStartPct(0.1)
      setPredictResult(null)
    }
  }, [loaded?.success, loaded?.data_info?.rows])

  useEffect(() => {
    if (!predictResult?.success) {
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
  }, [predictResult, historyPeriod, marketHistoryTickerQuery])

  const dataInfo = loaded?.data_info

  const handleLoadModel = async () => {
    if (!modelKey) {
      showBanner({ kind: 'warning', text: 'モデルを選択してください' })
      return
    }
    setBusy(true)
    try {
      const res = await loadModel({ model_key: modelKey, device })
      if (res.success) {
        setModelLoaded(true)
        showBanner({ kind: 'success', text: res.message ?? 'モデルを読み込みました' })
      } else {
        showBanner({ kind: 'error', text: res.error ?? '読み込みに失敗しました' })
      }
    } catch (e) {
      showBanner({ kind: 'error', text: formatUserFacingError(e) })
    } finally {
      setBusy(false)
    }
  }

  const handleLoadData = async () => {
    if (!filePath) {
      showBanner({ kind: 'warning', text: 'データファイルを選択してください' })
      return
    }
    setBusy(true)
    try {
      const res = await loadData(filePath)
      setLoaded(res)
      if (res.success) {
        showBanner({ kind: 'success', text: res.message ?? 'データを読み込みました' })
      } else {
        showBanner({ kind: 'error', text: res.error ?? '読み込みに失敗しました' })
      }
    } catch (e) {
      setLoaded(null)
      showBanner({ kind: 'error', text: formatUserFacingError(e) })
    } finally {
      setBusy(false)
    }
  }

  const handlePredict = async () => {
    if (!filePath || !modelLoaded || !dataInfo || !windowFitsRows(dataInfo.rows)) {
      showBanner({ kind: 'warning', text: 'モデル読込・データ読込・時間窓を確認してください' })
      return
    }
    setBusy(true)
    try {
      const start_date = computePredictStartDateIso(dataInfo, startPct)
      const res = await predict({
        file_path: filePath,
        lookback: LOOKBACK,
        pred_len: PRED_LEN,
        temperature,
        top_p: topP,
        sample_count: sampleCount,
        start_date,
      })
      if (res.success) {
        setPredictResult(res)
        showBanner({ kind: 'success', text: res.message ?? '予測が完了しました' })
      } else {
        setPredictResult(null)
        showBanner({ kind: 'error', text: res.error ?? '予測に失敗しました' })
      }
    } catch (e) {
      setPredictResult(null)
      showBanner({ kind: 'error', text: formatUserFacingError(e) })
    } finally {
      setBusy(false)
    }
  }

  const modelEntries = modelsState ? Object.entries(modelsState.models) : []
  const ohlcRows = loaded?.ohlc_rows ?? []
  const previewSlice = ohlcRows.slice(0, PREVIEW_ROWS)

  const mergedSeries = useMemo(() => {
    if (!predictResult?.success) {
      return { history: [], prediction: [], actual: [] }
    }
    return mergeOhlcSeries(
      marketRows,
      predictResult.prediction_results ?? [],
      predictResult.actual_data ?? [],
    )
  }, [marketRows, predictResult])

  const canPredict =
    modelLoaded &&
    !!filePath &&
    !!dataInfo &&
    windowFitsRows(dataInfo.rows) &&
    !busy

  return (
    <div className="workspace">
      <aside className="workspace__aside">
        <p className="msg-muted small workspace__hint">
          初回は <code>npm run build</code> 後、Flask を <code>7070</code> で起動してください。開発時は Vite（5173）＋プロキシでも利用できます。
        </p>

        {banner && <div className={`banner banner--${banner.kind}`}>{banner.text}</div>}

        <section className="panel">
          <h2>モデル</h2>
          {!modelsState?.model_available && (
            <p className="msg-warning">Kronos モデルライブラリが利用できない環境です。</p>
          )}
          <div className="form-group">
            <label htmlFor="model-select">モデル</label>
            <select
              id="model-select"
              value={modelKey}
              onChange={(e) => setModelKey(e.target.value)}
              disabled={!modelsState?.model_available}
            >
              <option value="">選択してください</option>
              {modelEntries.map(([key, m]) => (
                <option key={key} value={key}>
                  {m.name} ({m.params})
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="device-select">デバイス</label>
            <select id="device-select" value={device} onChange={(e) => setDevice(e.target.value)}>
              <option value="cpu">CPU</option>
              <option value="cuda">CUDA</option>
              <option value="mps">MPS（Apple Silicon）</option>
            </select>
          </div>
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={handleLoadModel}>
            モデルを読み込む
          </button>
        </section>

        <section className="panel">
          <h2>データ</h2>
          {tickerError && <p className="msg-error small">{tickerError}</p>}
          <div className="form-group">
            <label htmlFor="ticker-select">銘柄（データフォルダ）</label>
            <select
              id="ticker-select"
              value={selectedTickerId}
              onChange={(e) => setSelectedTickerId(e.target.value)}
              disabled={tickerLoading || !tickers.length}
            >
              {!tickers.length && <option value="">—</option>}
              {tickers.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
            <p className="msg-muted small">
              履歴チャートの yfinance は <strong>{yfinanceDisplaySymbol}</strong>（フォルダ名＝銘柄 ID、
              <code>__flat__</code> 時はサーバ既定 {yfinanceDisplaySymbol}）。
            </p>
          </div>
          <div className="form-group">
            <label htmlFor="data-select">データファイル</label>
            <select id="data-select" value={filePath} onChange={(e) => setFilePath(e.target.value)}>
              <option value="">選択してください</option>
              {dataFiles.map((f) => (
                <option key={f.path} value={f.path}>
                  {f.name} ({f.size})
                </option>
              ))}
            </select>
          </div>
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={handleLoadData}>
            データを読み込む
          </button>

          {dataInfo && (
            <div className="data-info-block">
              <h3>データ情報</h3>
              <ul className="data-info-list">
                <li>行数: {dataInfo.rows}</li>
                <li>列数: {dataInfo.columns?.length ?? '—'}</li>
                <li>
                  期間: {dataInfo.start_date} ～ {dataInfo.end_date}
                </li>
                <li>
                  価格帯:{' '}
                  {dataInfo.price_range
                    ? `${dataInfo.price_range.min.toFixed(4)} – ${dataInfo.price_range.max.toFixed(4)}`
                    : '—'}
                </li>
                <li>時間粒度: {dataInfo.timeframe ?? '—'}</li>
                <li>予測列: {(dataInfo.prediction_columns ?? []).join(', ') || '—'}</li>
              </ul>
            </div>
          )}
        </section>

        <section className="panel">
          <h2>時間窓・パラメータ</h2>
          {dataInfo ? (
            <TimeWindowSlider dataInfo={dataInfo} startPct={startPct} onStartPctChange={setStartPct} />
          ) : (
            <p className="msg-muted">データを読み込むと時間窓スライダーが表示されます。</p>
          )}
          <div className="form-group">
            <label>参照期間（lookback）</label>
            <input type="number" value={LOOKBACK} readOnly />
          </div>
          <div className="form-group">
            <label>予測長（pred_len）</label>
            <input type="number" value={PRED_LEN} readOnly />
          </div>
          <div className="form-group">
            <label htmlFor="temperature">温度 T: {temperature.toFixed(1)}</label>
            <input
              id="temperature"
              type="range"
              min={0.1}
              max={2}
              step={0.1}
              value={temperature}
              onChange={(e) => setTemperature(Number(e.target.value))}
            />
          </div>
          <div className="form-group">
            <label htmlFor="top-p">top_p: {topP.toFixed(1)}</label>
            <input
              id="top-p"
              type="range"
              min={0.1}
              max={1}
              step={0.1}
              value={topP}
              onChange={(e) => setTopP(Number(e.target.value))}
            />
          </div>
          <div className="form-group">
            <label htmlFor="sample-count">サンプル数</label>
            <input
              id="sample-count"
              type="number"
              min={1}
              max={5}
              value={sampleCount}
              onChange={(e) => setSampleCount(Number(e.target.value))}
            />
          </div>
          <button type="button" className="btn btn-primary" disabled={!canPredict} onClick={handlePredict}>
            予測を開始
          </button>
        </section>

        {busy && <p className="msg-muted">処理中…</p>}
      </aside>

      <div className="workspace__main">
        <section className="panel">
          <h2>データプレビュー（先頭 {PREVIEW_ROWS} 行）</h2>
          {!ohlcRows.length ? (
            <p className="msg-muted">データを読み込むと表示されます。</p>
          ) : (
            <>
              <p className="msg-muted small">
                全 {ohlcRows.length} 行中 {previewSlice.length} 行を表示
              </p>
              <div className="table-wrap table-wrap--short">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>時刻</th>
                      <th>O</th>
                      <th>H</th>
                      <th>L</th>
                      <th>C</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewSlice.map((r, i) => (
                      <tr key={`${r.timestamp}-${i}`}>
                        <td>{r.timestamp ?? '—'}</td>
                        <td>{r.open.toFixed(4)}</td>
                        <td>{r.high.toFixed(4)}</td>
                        <td>{r.low.toFixed(4)}</td>
                        <td>{r.close.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <h3>ローソクプレビュー（全件・下スライダーで移動）</h3>
              <OhlcCandlestickPreview rows={ohlcRows} />
            </>
          )}
        </section>

        <section className="panel">
          <h2>予測結果チャート（ECharts）</h2>
          {!predictResult?.success && (
            <p className="msg-muted">予測実行後に、市場履歴・予測・実測を統合したローソクが表示されます。</p>
          )}
          {predictResult?.success && (
            <>
              <p className="msg-muted small">
                履歴は yfinance の <strong>{yfinanceDisplaySymbol}</strong>（5分足）です。予測 CSV
                と銘柄・時刻が一致しない場合、チャート上の位置関係は参考程度になります。
              </p>
              <div className="form-group chart-period-row">
                <label htmlFor="mh-period">市場履歴の取得期間</label>
                <select
                  id="mh-period"
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
              <EChartsCandlestick
                history={mergedSeries.history}
                prediction={mergedSeries.prediction}
                actual={mergedSeries.actual}
                title="統合ローソク"
                subtitle={`${yfinanceDisplaySymbol} · 5m · ${historyPeriod}`}
                height={520}
                showDataZoom
              />
            </>
          )}
          {predictResult?.has_comparison &&
            predictResult.prediction_results &&
            predictResult.actual_data && (
              <ComparisonPanel
                predictionType={predictResult.prediction_type}
                predictions={predictResult.prediction_results}
                actuals={predictResult.actual_data}
              />
            )}
        </section>
      </div>
    </div>
  )
}
