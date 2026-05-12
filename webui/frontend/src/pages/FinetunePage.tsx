import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  createTrainJob,
  getAvailableModels,
  getTrainJob,
  getTrainJobLog,
  importMarket,
  listTrainJobs,
  loadData,
  loadModel,
  marketHistory,
  predict,
  runBacktest,
  uploadDataFile,
  validateDataFile,
} from '../api/endpoints'
import type {
  AvailableModelsResponse,
  BacktestRunRequest,
  BacktestRunResponse,
  LoadDataResponse,
  LoadModelRequest,
  OhlcRow,
  PredictResponse,
  TrainJobListItem,
  TrainJobMeta,
  ValidateDataResponse,
} from '../api/types'
import BacktestEquityChart from '../components/BacktestEquityChart'
import AccuracyMetricsPanel from '../components/AccuracyMetricsPanel'
import ComparisonPanel from '../components/ComparisonPanel'
import EChartsCandlestick from '../components/EChartsCandlestick'
import OhlcCandlestickPreview from '../components/OhlcCandlestickPreview'
import TimeWindowSlider, {
  computePredictStartDateIso,
  LOOKBACK,
  PRED_LEN,
  windowFitsRows,
} from '../components/TimeWindowSlider'
import { useTicker } from '../context/TickerContext'
import { formatUserFacingError } from '../utils/formatError'
import { canNavigateToFinetuneStep, type FinetuneWizardGuardCtx } from '../utils/finetuneWizardGuards'
import { mergeOhlcSeries } from '../utils/ohlcMerge'
import {
  DEFAULT_TEST_RATIO,
  DEFAULT_TRAIN_RATIO,
  DEFAULT_VAL_RATIO,
  trainWindowClientMessage,
} from '../utils/trainWindowGuards'

type Banner = { kind: 'success' | 'error' | 'info' | 'warning'; text: string }

const WIZARD_STEPS = ['データ', 'モデル', '学習', '推論パラメータ', '予測', 'バックテスト'] as const

/** ステッパーで切替可能なステップ */
const WIZARD_CLICKABLE: ReadonlySet<number> = new Set([0, 1, 2, 3, 4, 5])

const HISTORY_PERIODS = ['5d', '30d', '60d', '1mo'] as const

const IMPORT_INTERVALS = [
  '1m',
  '2m',
  '5m',
  '15m',
  '30m',
  '60m',
  '90m',
  '1h',
  '1d',
  '5d',
  '1wk',
  '1mo',
  '3mo',
] as const

const IMPORT_PERIODS = [
  '1d',
  '5d',
  '30d',
  '60d',
  '1mo',
  '3mo',
  '6mo',
  '1y',
  '2y',
  '5y',
  '10y',
  'ytd',
  'max',
] as const

const PREVIEW_ROWS = 500

export default function FinetunePage() {
  const {
    tickers,
    selectedTickerId,
    setSelectedTickerId,
    marketHistoryTickerQuery,
    yfinanceDisplaySymbol,
  } = useTicker()

  const [activeWizardStep, setActiveWizardStep] = useState(0)

  const [banner, setBanner] = useState<Banner | null>(null)
  const [busy, setBusy] = useState(false)

  const [importTicker, setImportTicker] = useState('8058.T')
  const [importInterval, setImportInterval] = useState<(typeof IMPORT_INTERVALS)[number]>('5m')
  const [importPeriod, setImportPeriod] = useState<(typeof IMPORT_PERIODS)[number]>('30d')

  const [uploadTicker, setUploadTicker] = useState('8058.T')
  const [uploadFile, setUploadFile] = useState<File | null>(null)

  const [filePath, setFilePath] = useState('')
  const [validateResult, setValidateResult] = useState<ValidateDataResponse | null>(null)
  const [loaded, setLoaded] = useState<LoadDataResponse | null>(null)

  const [dataPathTrain, setDataPathTrain] = useState('')
  const [pretrainedTokenizer, setPretrainedTokenizer] = useState('')
  const [pretrainedPredictor, setPretrainedPredictor] = useState('')
  const [tokenizerLr, setTokenizerLr] = useState(0.0002)
  const [predictorLr, setPredictorLr] = useState(0.000001)
  const [tokenizerEpochs, setTokenizerEpochs] = useState(30)
  const [basemodelEpochs, setBasemodelEpochs] = useState(20)
  const [batchSize, setBatchSize] = useState(32)
  const [lookbackWindow, setLookbackWindow] = useState(512)
  const [predictWindow, setPredictWindow] = useState(48)
  const [trainDevice, setTrainDevice] = useState<'cuda' | 'cpu' | 'mps'>('cpu')
  const [skipExisting, setSkipExisting] = useState(false)
  const [skipTokenizer, setSkipTokenizer] = useState(false)
  const [skipBasemodel, setSkipBasemodel] = useState(false)

  const [jobId, setJobId] = useState<string | null>(null)
  const [jobMeta, setJobMeta] = useState<TrainJobMeta | null>(null)
  const [trainLog, setTrainLog] = useState('')

  const [modelLoadMode, setModelLoadMode] = useState<'hf' | 'job' | 'local'>('hf')
  const [modelsState, setModelsState] = useState<AvailableModelsResponse | null>(null)
  const [modelKey, setModelKey] = useState('')
  const [modelDevice, setModelDevice] = useState('cpu')
  const [trainJobsList, setTrainJobsList] = useState<TrainJobListItem[]>([])
  const [selectedTrainJobId, setSelectedTrainJobId] = useState('')
  const [localTokPath, setLocalTokPath] = useState('')
  const [localPredPath, setLocalPredPath] = useState('')
  const [modelMaxContext, setModelMaxContext] = useState('')

  const [btDataPath, setBtDataPath] = useState('')
  const [btEvalStart, setBtEvalStart] = useState('')
  const [btEvalEnd, setBtEvalEnd] = useState('')
  const [btTrainLast, setBtTrainLast] = useState('')
  const [btCkptMode, setBtCkptMode] = useState<'job' | 'local'>('job')
  const [btTrainJobId, setBtTrainJobId] = useState('')
  const [btLocalTok, setBtLocalTok] = useState('')
  const [btLocalPred, setBtLocalPred] = useState('')
  const [btLookback, setBtLookback] = useState(400)
  const [btPredLen, setBtPredLen] = useState(1)
  const [btT, setBtT] = useState(1.0)
  const [btTopP, setBtTopP] = useState(0.9)
  const [btSampleCount, setBtSampleCount] = useState(1)
  const [btDevice, setBtDevice] = useState('cpu')
  const [btMaxContext, setBtMaxContext] = useState('')
  const [btResult, setBtResult] = useState<BacktestRunResponse | null>(null)

  const [modelLoaded, setModelLoaded] = useState(false)
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

  const wizardGuardCtx: FinetuneWizardGuardCtx = useMemo(
    () => ({
      filePath,
      modelLoaded,
      loadedSuccess: !!loaded?.success,
      dataInfoRows: loaded?.data_info?.rows,
    }),
    [filePath, modelLoaded, loaded?.success, loaded?.data_info?.rows],
  )

  const goWizardStep = useCallback(
    (i: number) => {
      if (!WIZARD_CLICKABLE.has(i)) return
      const gate = canNavigateToFinetuneStep(i, wizardGuardCtx)
      if (!gate.ok) {
        showBanner({ kind: 'warning', text: gate.reason ?? 'このステップにはまだ進めません' })
        return
      }
      setActiveWizardStep(i)
      if (i === 2) {
        setDataPathTrain((p) => p || filePath)
      }
      if (i === 1 && jobId && jobMeta?.status === 'succeeded') {
        setSelectedTrainJobId(jobId)
      }
      if (i === 3) {
        setStartPct(0.1)
      }
      if (i === 5) {
        setBtDataPath((p) => p || filePath)
        if (jobMeta?.train_last_timestamp) {
          setBtTrainLast(jobMeta.train_last_timestamp)
        }
        if (jobId && jobMeta?.status === 'succeeded') {
          setBtTrainJobId(jobId)
        }
      }
    },
    [filePath, jobId, jobMeta?.status, jobMeta?.train_last_timestamp, showBanner, wizardGuardCtx],
  )

  const handleImport = async () => {
    if (!importTicker.trim()) {
      showBanner({ kind: 'warning', text: '銘柄 ID（ticker_id）を入力してください' })
      return
    }
    setBusy(true)
    setValidateResult(null)
    setLoaded(null)
    try {
      const res = await importMarket({
        ticker_id: importTicker.trim(),
        interval: importInterval,
        period: importPeriod,
      })
      if (res.success && res.file_path) {
        setFilePath(res.file_path)
        showBanner({ kind: 'success', text: res.message ?? '市場データを保存しました' })
      } else {
        showBanner({ kind: 'error', text: res.error ?? '取り込みに失敗しました' })
      }
    } catch (e) {
      showBanner({ kind: 'error', text: formatUserFacingError(e) })
    } finally {
      setBusy(false)
    }
  }

  const handleUpload = async () => {
    if (!uploadTicker.trim()) {
      showBanner({ kind: 'warning', text: 'アップロード先の銘柄 ID を入力してください' })
      return
    }
    if (!uploadFile) {
      showBanner({ kind: 'warning', text: 'ファイルを選択してください' })
      return
    }
    setBusy(true)
    setValidateResult(null)
    setLoaded(null)
    try {
      const res = await uploadDataFile(uploadTicker.trim(), uploadFile)
      if (res.success && res.file_path) {
        setFilePath(res.file_path)
        showBanner({ kind: 'success', text: `アップロードしました: ${res.filename ?? ''}` })
      } else {
        showBanner({ kind: 'error', text: res.error ?? 'アップロードに失敗しました' })
      }
    } catch (e) {
      showBanner({ kind: 'error', text: formatUserFacingError(e) })
    } finally {
      setBusy(false)
    }
  }

  const handleValidate = async () => {
    if (!filePath.trim()) {
      showBanner({ kind: 'warning', text: 'file_path を入力するか、取り込み／アップロードしてください' })
      return
    }
    setBusy(true)
    try {
      const res = await validateDataFile(filePath.trim())
      setValidateResult(res)
      if (res.valid) {
        showBanner({ kind: 'success', text: res.message ?? '検証に成功しました' })
      } else {
        showBanner({ kind: 'error', text: res.error ?? '検証に失敗しました' })
      }
    } catch (e) {
      setValidateResult(null)
      showBanner({ kind: 'error', text: formatUserFacingError(e) })
    } finally {
      setBusy(false)
    }
  }

  const handleLoadPreview = async () => {
    if (!filePath.trim()) {
      showBanner({ kind: 'warning', text: 'file_path を指定してください' })
      return
    }
    setBusy(true)
    try {
      const res = await loadData(filePath.trim())
      setLoaded(res)
      if (res.success) {
        showBanner({ kind: 'success', text: res.message ?? 'プレビューを読み込みました' })
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

  const refreshTrainLog = useCallback(async (id: string) => {
    try {
      const logR = await getTrainJobLog(id, 300)
      if (logR.success && logR.log != null) setTrainLog(logR.log)
    } catch {
      /* ignore */
    }
  }, [])

  const handleSubmitTrainJob = async () => {
    if (!dataPathTrain.trim()) {
      showBanner({ kind: 'warning', text: '学習用 data_path を入力してください' })
      return
    }
    const trainPath = dataPathTrain.trim()
    let rowHint: number | undefined
    if (loaded?.success && loaded.data_info?.rows != null && filePath.trim() === trainPath) {
      rowHint = loaded.data_info.rows
    } else if (
      validateResult?.valid &&
      validateResult.data_info?.rows != null &&
      (validateResult.file_path?.trim() === trainPath || validateResult.file_path === trainPath)
    ) {
      rowHint = validateResult.data_info.rows
    }
    if (rowHint != null) {
      const msg = trainWindowClientMessage(
        rowHint,
        lookbackWindow,
        predictWindow,
        DEFAULT_TRAIN_RATIO,
        DEFAULT_VAL_RATIO,
        DEFAULT_TEST_RATIO,
      )
      if (msg) {
        showBanner({ kind: 'warning', text: msg })
        return
      }
    }
    setBusy(true)
    try {
      const res = await createTrainJob({
        data_path: trainPath,
        pretrained_tokenizer: pretrainedTokenizer.trim() || undefined,
        pretrained_predictor: pretrainedPredictor.trim() || undefined,
        device: trainDevice,
        tokenizer_learning_rate: tokenizerLr,
        predictor_learning_rate: predictorLr,
        tokenizer_epochs: tokenizerEpochs,
        basemodel_epochs: basemodelEpochs,
        batch_size: batchSize,
        lookback_window: lookbackWindow,
        predict_window: predictWindow,
        train_ratio: DEFAULT_TRAIN_RATIO,
        val_ratio: DEFAULT_VAL_RATIO,
        test_ratio: DEFAULT_TEST_RATIO,
        skip_existing: skipExisting,
        skip_tokenizer: skipTokenizer,
        skip_basemodel: skipBasemodel,
      })
      if (res.success && res.job_id) {
        setJobId(res.job_id)
        setJobMeta((res.meta as TrainJobMeta) ?? { job_id: res.job_id, status: 'queued' })
        setTrainLog('')
        showBanner({ kind: 'success', text: `ジョブを投入しました: ${res.job_id}` })
        void refreshTrainLog(res.job_id)
      } else {
        showBanner({ kind: 'error', text: res.error ?? 'ジョブ投入に失敗しました' })
      }
    } catch (e) {
      showBanner({ kind: 'error', text: formatUserFacingError(e) })
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (!jobId) return
    let cancelled = false
    const poll = async () => {
      try {
        const r = await getTrainJob(jobId)
        if (cancelled || !r.success || !r.meta) return
        setJobMeta(r.meta)
        await refreshTrainLog(jobId)
      } catch {
        /* ignore */
      }
    }
    poll()
    const id = window.setInterval(poll, 2500)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [jobId, refreshTrainLog])

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

  useEffect(() => {
    if (activeWizardStep !== 1) return
    let cancelled = false
    ;(async () => {
      try {
        const [m, j] = await Promise.all([getAvailableModels(), listTrainJobs()])
        if (cancelled) return
        setModelsState(m)
        if (j.success && j.jobs) {
          setTrainJobsList(j.jobs)
        } else {
          setTrainJobsList([])
        }
        if (m?.models) {
          const keys = Object.keys(m.models)
          if (keys.length) {
            setModelKey((prev) => prev || keys[0])
          }
        }
      } catch (e) {
        if (!cancelled) showBanner({ kind: 'error', text: formatUserFacingError(e) })
      }
    })()
    return () => {
      cancelled = true
    }
  }, [activeWizardStep, showBanner])

  const handleLoadModel = async () => {
    setBusy(true)
    try {
      if (modelLoadMode === 'hf') {
        if (!modelKey) {
          showBanner({ kind: 'warning', text: 'モデル（model_key）を選択してください' })
          return
        }
        const res = await loadModel({ device: modelDevice, model_key: modelKey })
        if (res.success) {
          setModelLoaded(true)
          showBanner({ kind: 'success', text: res.message ?? 'モデルを読み込みました' })
        } else {
          setModelLoaded(false)
          showBanner({ kind: 'error', text: res.error ?? '読み込みに失敗しました' })
        }
        return
      }
      if (modelLoadMode === 'job') {
        if (!selectedTrainJobId.trim()) {
          showBanner({ kind: 'warning', text: '学習ジョブを選択してください' })
          return
        }
        const mcStr = modelMaxContext.trim()
        let payload: LoadModelRequest
        if (mcStr) {
          const mc = parseInt(mcStr, 10)
          if (Number.isNaN(mc) || mc < 32) {
            showBanner({ kind: 'warning', text: 'max_context は 32 以上の整数で指定してください' })
            return
          }
          payload = { device: modelDevice, train_job_id: selectedTrainJobId.trim(), max_context: mc }
        } else {
          payload = { device: modelDevice, train_job_id: selectedTrainJobId.trim() }
        }
        const res = await loadModel(payload)
        if (res.success) {
          setModelLoaded(true)
          showBanner({ kind: 'success', text: res.message ?? 'モデルを読み込みました' })
        } else {
          setModelLoaded(false)
          showBanner({ kind: 'error', text: res.error ?? '読み込みに失敗しました' })
        }
        return
      }
      if (!localTokPath.trim() || !localPredPath.trim()) {
        showBanner({ kind: 'warning', text: 'tokenizer / predictor のローカルパスを両方入力してください' })
        return
      }
      const mcStr = modelMaxContext.trim()
      let payload: LoadModelRequest
      if (mcStr) {
        const mc = parseInt(mcStr, 10)
        if (Number.isNaN(mc) || mc < 32) {
          showBanner({ kind: 'warning', text: 'max_context は 32 以上の整数で指定してください' })
          return
        }
        payload = {
          device: modelDevice,
          local_tokenizer_path: localTokPath.trim(),
          local_predictor_path: localPredPath.trim(),
          max_context: mc,
        }
      } else {
        payload = {
          device: modelDevice,
          local_tokenizer_path: localTokPath.trim(),
          local_predictor_path: localPredPath.trim(),
        }
      }
      const res = await loadModel(payload)
      if (res.success) {
        setModelLoaded(true)
        showBanner({ kind: 'success', text: res.message ?? 'モデルを読み込みました' })
      } else {
        setModelLoaded(false)
        showBanner({ kind: 'error', text: res.error ?? '読み込みに失敗しました' })
      }
    } catch (e) {
      setModelLoaded(false)
      showBanner({ kind: 'error', text: formatUserFacingError(e) })
    } finally {
      setBusy(false)
    }
  }

  const handlePredict = async () => {
    const di = loaded?.data_info
    if (!filePath || !modelLoaded || !di || !windowFitsRows(di.rows)) {
      showBanner({ kind: 'warning', text: 'モデル読込・データプレビュー・時間窓を確認してください' })
      return
    }
    setBusy(true)
    try {
      const start_date = computePredictStartDateIso(di, startPct)
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

  const handleRunBacktest = async () => {
    if (!btDataPath.trim()) {
      showBanner({ kind: 'warning', text: 'data_path を入力してください' })
      return
    }
    if (!btTrainLast.trim()) {
      showBanner({ kind: 'warning', text: 'train_last_timestamp を入力してください' })
      return
    }
    setBusy(true)
    setBtResult(null)
    try {
      const body: BacktestRunRequest = {
        backtest_spec_version: '1.0',
        data_path: btDataPath.trim(),
        train_last_timestamp: btTrainLast.trim(),
        lookback: btLookback,
        pred_len: btPredLen,
        T: btT,
        top_p: btTopP,
        sample_count: btSampleCount,
        device: btDevice,
      }
      if (btEvalStart.trim()) body.eval_start = btEvalStart.trim()
      if (btEvalEnd.trim()) body.eval_end = btEvalEnd.trim()
      if (btCkptMode === 'job') {
        if (!btTrainJobId.trim()) {
          showBanner({ kind: 'warning', text: 'train_job_id を入力するか、学習完了ジョブを選んでください' })
          setBusy(false)
          return
        }
        body.train_job_id = btTrainJobId.trim()
      } else {
        if (!btLocalTok.trim() || !btLocalPred.trim()) {
          showBanner({ kind: 'warning', text: 'ローカル tokenizer / predictor パスを両方入力してください' })
          setBusy(false)
          return
        }
        body.local_tokenizer_path = btLocalTok.trim()
        body.local_predictor_path = btLocalPred.trim()
      }
      const mc = btMaxContext.trim()
      if (mc) {
        const n = parseInt(mc, 10)
        if (!Number.isNaN(n) && n >= 32) {
          body.max_context = n
        }
      }
      const res = await runBacktest(body)
      if (res.success && res.metrics && res.series) {
        setBtResult(res)
        showBanner({ kind: 'success', text: res.message ?? 'バックテストが完了しました' })
      } else {
        showBanner({ kind: 'error', text: res.error ?? 'バックテストに失敗しました' })
      }
    } catch (e) {
      showBanner({ kind: 'error', text: formatUserFacingError(e) })
    } finally {
      setBusy(false)
    }
  }

  const dataInfo = loaded?.data_info
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
    <div className="finetune">
      <div className="finetune-stepper" aria-label="ウィザードのステップ">
        {WIZARD_STEPS.map((label, i) => {
          const clickable = WIZARD_CLICKABLE.has(i)
          const active = i === activeWizardStep
          const nav = canNavigateToFinetuneStep(i, wizardGuardCtx)
          const stepDisabled = !nav.ok && i !== activeWizardStep
          const cls = [
            'finetune-step',
            active ? 'finetune-step--active' : 'finetune-step--pending',
            clickable ? 'finetune-step--clickable' : '',
          ]
            .filter(Boolean)
            .join(' ')
          if (clickable) {
            return (
              <button
                key={label}
                type="button"
                className={cls}
                disabled={stepDisabled}
                title={!nav.ok ? nav.reason : undefined}
                onClick={() => goWizardStep(i)}
              >
                {i + 1}. {label}
              </button>
            )
          }
          return (
            <span key={label} className={cls}>
              {i + 1}. {label}
            </span>
          )
        })}
      </div>

      {banner && <div className={`banner banner--${banner.kind}`}>{banner.text}</div>}

      {activeWizardStep === 1 && (
        <div className="finetune-grid finetune-grid--model">
          <section className="panel">
            <h2>ステップ2 — モデル読込</h2>
            <p className="msg-muted small">
              Hugging Face の事前学習モデル、学習ジョブ成果物（succeeded）、またはリポジトリ内の checkpoint ディレクトリから読み込みます。モードは排他です。
            </p>

            <div className="finetune-model-modes" role="radiogroup" aria-label="読込モード">
              <label>
                <input
                  type="radio"
                  name="ft-model-mode"
                  checked={modelLoadMode === 'hf'}
                  onChange={() => setModelLoadMode('hf')}
                />{' '}
                HF（model_key）
              </label>
              <label>
                <input
                  type="radio"
                  name="ft-model-mode"
                  checked={modelLoadMode === 'job'}
                  onChange={() => setModelLoadMode('job')}
                />{' '}
                学習ジョブ
              </label>
              <label>
                <input
                  type="radio"
                  name="ft-model-mode"
                  checked={modelLoadMode === 'local'}
                  onChange={() => setModelLoadMode('local')}
                />{' '}
                ローカルパス
              </label>
            </div>

            <div className="form-group">
              <label htmlFor="ft-model-device">device（推論・サーバ側）</label>
              <select
                id="ft-model-device"
                value={modelDevice}
                onChange={(e) => setModelDevice(e.target.value)}
              >
                <option value="cpu">cpu</option>
                <option value="mps">mps</option>
                <option value="cuda">cuda</option>
              </select>
            </div>

            {modelLoadMode === 'hf' && (
              <>
                {!modelsState?.model_available && (
                  <p className="msg-warning small">Kronos モデルライブラリが利用できない環境です。</p>
                )}
                <div className="form-group">
                  <label htmlFor="ft-model-key">model_key</label>
                  <select
                    id="ft-model-key"
                    value={modelKey}
                    onChange={(e) => setModelKey(e.target.value)}
                    disabled={!modelsState?.model_available}
                  >
                    {modelsState?.models &&
                      Object.entries(modelsState.models).map(([key, info]) => (
                        <option key={key} value={key}>
                          {info.name} ({info.params})
                        </option>
                      ))}
                  </select>
                </div>
              </>
            )}

            {modelLoadMode === 'job' && (
              <>
                <div className="form-group">
                  <label htmlFor="ft-train-job-pick">succeeded ジョブ</label>
                  <select
                    id="ft-train-job-pick"
                    value={selectedTrainJobId}
                    onChange={(e) => setSelectedTrainJobId(e.target.value)}
                  >
                    <option value="">選択してください</option>
                    {trainJobsList
                      .filter((j) => j.status === 'succeeded')
                      .map((j) => (
                        <option key={j.job_id} value={j.job_id}>
                          {j.job_id.slice(0, 12)}… · {j.created_at ?? ''}
                        </option>
                      ))}
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="ft-model-mc-job">max_context（任意・空ならジョブ config）</label>
                  <input
                    id="ft-model-mc-job"
                    type="number"
                    min={32}
                    placeholder="例: 512"
                    value={modelMaxContext}
                    onChange={(e) => setModelMaxContext(e.target.value)}
                  />
                </div>
              </>
            )}

            {modelLoadMode === 'local' && (
              <>
                <div className="form-group">
                  <label htmlFor="ft-local-tok">local_tokenizer_path</label>
                  <input
                    id="ft-local-tok"
                    type="text"
                    value={localTokPath}
                    onChange={(e) => setLocalTokPath(e.target.value)}
                    spellCheck={false}
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="ft-local-pred">local_predictor_path</label>
                  <input
                    id="ft-local-pred"
                    type="text"
                    value={localPredPath}
                    onChange={(e) => setLocalPredPath(e.target.value)}
                    spellCheck={false}
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="ft-model-mc-local">max_context（任意・既定 512）</label>
                  <input
                    id="ft-model-mc-local"
                    type="number"
                    min={32}
                    placeholder="512"
                    value={modelMaxContext}
                    onChange={(e) => setModelMaxContext(e.target.value)}
                  />
                </div>
              </>
            )}

            <button type="button" className="btn btn-primary" disabled={busy} onClick={handleLoadModel}>
              モデルを読み込む
            </button>
          </section>

          <section className="panel">
            <h2>ヒント</h2>
            <ul className="data-info-list">
              <li>ワークスペースの予測は、このサーバに読み込んだモデルを使用します。</li>
              <li>学習ジョブは一覧 API のうち status が succeeded のもののみ選択できます。</li>
              <li>ローカルパスはプロジェクトルート配下のディレクトリに限ります。</li>
            </ul>
          </section>
        </div>
      )}

      {activeWizardStep === 0 && (
        <div className="finetune-grid">
          <section className="panel">
            <h2>ステップ1 — データ</h2>
            <p className="msg-muted small">
              市場から yfinance で取り込むか、CSV / Feather をアップロードし、検証のあとプレビュー読込まで行います。
            </p>

            <h3>市場から取り込み</h3>
            <div className="form-group">
              <label htmlFor="ft-import-ticker">銘柄 ID（data フォルダ名＝yfinance シンボル）</label>
              <input
                id="ft-import-ticker"
                type="text"
                value={importTicker}
                onChange={(e) => setImportTicker(e.target.value)}
                autoComplete="off"
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-import-interval">interval</label>
              <select
                id="ft-import-interval"
                value={importInterval}
                onChange={(e) => setImportInterval(e.target.value as (typeof IMPORT_INTERVALS)[number])}
              >
                {IMPORT_INTERVALS.map((iv) => (
                  <option key={iv} value={iv}>
                    {iv}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="ft-import-period">period</label>
              <select
                id="ft-import-period"
                value={importPeriod}
                onChange={(e) => setImportPeriod(e.target.value as (typeof IMPORT_PERIODS)[number])}
              >
                {IMPORT_PERIODS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={handleImport}>
              市場から取り込む
            </button>

            <h3>ファイルをアップロード</h3>
            <div className="form-group">
              <label htmlFor="ft-upload-ticker">保存先銘柄 ID</label>
              <input
                id="ft-upload-ticker"
                type="text"
                value={uploadTicker}
                onChange={(e) => setUploadTicker(e.target.value)}
                autoComplete="off"
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-upload-file">ファイル（.csv / .feather）</label>
              <input
                id="ft-upload-file"
                type="file"
                accept=".csv,.feather"
                onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
              />
            </div>
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={handleUpload}>
              アップロード
            </button>

            <h3>パス・検証・プレビュー</h3>
            <div className="form-group">
              <label htmlFor="ft-file-path">file_path（取り込み／アップロードで自動入力）</label>
              <input
                id="ft-file-path"
                type="text"
                value={filePath}
                onChange={(e) => setFilePath(e.target.value)}
                spellCheck={false}
              />
            </div>
            <div className="finetune-actions-row">
              <button type="button" className="btn btn-secondary" disabled={busy} onClick={handleValidate}>
                パスを検証
              </button>
              <button type="button" className="btn btn-primary" disabled={busy} onClick={handleLoadPreview}>
                プレビュー読込
              </button>
            </div>

            {validateResult && (
              <div className="data-info-block">
                <h3>検証結果</h3>
                <p className="small">{validateResult.valid ? '有効' : `無効: ${validateResult.error ?? ''}`}</p>
                {validateResult.valid && validateResult.data_info && (
                  <ul className="data-info-list">
                    <li>行数: {validateResult.data_info.rows}</li>
                    <li>列: {(validateResult.data_info.columns ?? []).join(', ')}</li>
                    <li>
                      期間: {validateResult.data_info.start_date ?? '—'} ～{' '}
                      {validateResult.data_info.end_date ?? '—'}
                    </li>
                  </ul>
                )}
              </div>
            )}

            {dataInfo && (
              <div className="data-info-block">
                <h3>データ情報（load-data）</h3>
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
            <h2>データプレビュー（先頭 {PREVIEW_ROWS} 行）</h2>
            {!ohlcRows.length ? (
              <p className="msg-muted">プレビュー読込後に表示されます。</p>
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
            {busy && <p className="msg-muted">処理中…</p>}
          </section>
        </div>
      )}

      {activeWizardStep === 2 && (
        <div className="finetune-grid finetune-grid--train">
          <section className="panel">
            <h2>ステップ3 — 学習</h2>
            <p className="msg-muted small">
              データパスはステップ1の file_path をデフォルトにしています。事前学習はリポジトリ内のディレクトリパス（または環境変数
              KRONOS_PRETRAINED_*）が必要です。
            </p>

            <div className="form-group">
              <label htmlFor="ft-train-data-path">data_path</label>
              <input
                id="ft-train-data-path"
                type="text"
                value={dataPathTrain}
                onChange={(e) => setDataPathTrain(e.target.value)}
                spellCheck={false}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-ptok">pretrained_tokenizer（省略時は環境変数）</label>
              <input
                id="ft-ptok"
                type="text"
                value={pretrainedTokenizer}
                onChange={(e) => setPretrainedTokenizer(e.target.value)}
                placeholder="/path/to/repo/pretrained/..."
                spellCheck={false}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-ppred">pretrained_predictor（省略時は環境変数）</label>
              <input
                id="ft-ppred"
                type="text"
                value={pretrainedPredictor}
                onChange={(e) => setPretrainedPredictor(e.target.value)}
                placeholder="/path/to/repo/pretrained/..."
                spellCheck={false}
              />
            </div>

            <div className="form-group">
              <label htmlFor="ft-tok-lr">tokenizer_learning_rate</label>
              <input
                id="ft-tok-lr"
                type="number"
                step="any"
                value={tokenizerLr}
                onChange={(e) => setTokenizerLr(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-pred-lr">predictor_learning_rate</label>
              <input
                id="ft-pred-lr"
                type="number"
                step="any"
                value={predictorLr}
                onChange={(e) => setPredictorLr(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-tok-ep">tokenizer_epochs</label>
              <input
                id="ft-tok-ep"
                type="number"
                min={1}
                value={tokenizerEpochs}
                onChange={(e) => setTokenizerEpochs(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-base-ep">basemodel_epochs</label>
              <input
                id="ft-base-ep"
                type="number"
                min={1}
                value={basemodelEpochs}
                onChange={(e) => setBasemodelEpochs(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-bs">batch_size</label>
              <input
                id="ft-bs"
                type="number"
                min={1}
                value={batchSize}
                onChange={(e) => setBatchSize(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-lb">lookback_window</label>
              <input
                id="ft-lb"
                type="number"
                min={1}
                value={lookbackWindow}
                onChange={(e) => setLookbackWindow(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-pw">predict_window</label>
              <input
                id="ft-pw"
                type="number"
                min={1}
                value={predictWindow}
                onChange={(e) => setPredictWindow(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-dev">device</label>
              <select
                id="ft-dev"
                value={trainDevice}
                onChange={(e) => setTrainDevice(e.target.value as 'cuda' | 'cpu' | 'mps')}
              >
                <option value="cpu">cpu</option>
                <option value="mps">mps（Apple Silicon）</option>
                <option value="cuda">cuda</option>
              </select>
            </div>

            <div className="form-group finetune-check-row">
              <label>
                <input
                  type="checkbox"
                  checked={skipExisting}
                  onChange={(e) => setSkipExisting(e.target.checked)}
                />{' '}
                skip_existing（--skip-existing）
              </label>
            </div>
            <div className="form-group finetune-check-row">
              <label>
                <input
                  type="checkbox"
                  checked={skipTokenizer}
                  onChange={(e) => setSkipTokenizer(e.target.checked)}
                />{' '}
                skip_tokenizer（--skip-tokenizer）
              </label>
            </div>
            <div className="form-group finetune-check-row">
              <label>
                <input
                  type="checkbox"
                  checked={skipBasemodel}
                  onChange={(e) => setSkipBasemodel(e.target.checked)}
                />{' '}
                skip_basemodel（--skip-basemodel）
              </label>
            </div>

            <button type="button" className="btn btn-primary" disabled={busy} onClick={handleSubmitTrainJob}>
              ジョブ投入
            </button>

            {jobId && (
              <div className="data-info-block">
                <h3>ジョブ状態</h3>
                <p className="small">
                  <code>{jobId}</code>
                </p>
                {jobMeta && (
                  <ul className="data-info-list">
                    <li>status: {jobMeta.status ?? '—'}</li>
                    <li>exit_code: {jobMeta.exit_code ?? '—'}</li>
                    <li>train_last_timestamp: {jobMeta.train_last_timestamp ?? '—'}</li>
                    <li>tokenizer: {jobMeta.tokenizer_best_model_path ?? '—'}</li>
                    <li>basemodel: {jobMeta.basemodel_best_model_path ?? '—'}</li>
                  </ul>
                )}
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={!jobId}
                  onClick={() => jobId && void refreshTrainLog(jobId)}
                >
                  ログを手動更新
                </button>
              </div>
            )}
          </section>

          <section className="panel">
            <h2>train.log 末尾</h2>
            <p className="msg-muted small">約 2.5 秒ごとにジョブ状態とログをポーリングします。</p>
            <pre className="finetune-log-pre">{trainLog || '（ログなし）'}</pre>
            {jobMeta?.error_message && (
              <div className="data-info-block">
                <h3>エラー抜粋</h3>
                <pre className="finetune-log-pre">{jobMeta.error_message}</pre>
              </div>
            )}
          </section>
        </div>
      )}

      {activeWizardStep === 3 && (
        <div className="finetune-grid finetune-grid--infer-params">
          <section className="panel">
            <h2>ステップ4 — 推論パラメータ</h2>
            <p className="msg-muted small">
              ステップ1でプレビュー読込に成功すると <code>data_info</code> に基づき時間窓を選べます。参照本数・予測本数は
              Workspace と同じ固定値です。
            </p>
            {dataInfo ? (
              <TimeWindowSlider dataInfo={dataInfo} startPct={startPct} onStartPctChange={setStartPct} />
            ) : (
              <p className="msg-muted">ステップ1で「プレビュー読込」を成功させてください。</p>
            )}
            <div className="form-group">
              <label htmlFor="ft-infer-lb">参照期間（lookback）</label>
              <input id="ft-infer-lb" type="number" value={LOOKBACK} readOnly />
            </div>
            <div className="form-group">
              <label htmlFor="ft-infer-pl">予測長（pred_len）</label>
              <input id="ft-infer-pl" type="number" value={PRED_LEN} readOnly />
            </div>
            <div className="form-group">
              <label htmlFor="ft-infer-temp">温度 T: {temperature.toFixed(1)}</label>
              <input
                id="ft-infer-temp"
                type="range"
                min={0.1}
                max={2}
                step={0.1}
                value={temperature}
                onChange={(e) => setTemperature(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-infer-topp">top_p: {topP.toFixed(1)}</label>
              <input
                id="ft-infer-topp"
                type="range"
                min={0.1}
                max={1}
                step={0.1}
                value={topP}
                onChange={(e) => setTopP(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-infer-sc">サンプル数</label>
              <input
                id="ft-infer-sc"
                type="number"
                min={1}
                max={5}
                value={sampleCount}
                onChange={(e) => setSampleCount(Number(e.target.value))}
              />
            </div>
            {modelLoaded ? (
              <p className="msg-muted small">モデルは読み込み済みです。ステップ5で予測を実行できます。</p>
            ) : (
              <p className="msg-warning small">ステップ2でモデルを読み込んでからステップ5へ進んでください。</p>
            )}
          </section>
        </div>
      )}

      {activeWizardStep === 4 && (
        <div className="finetune-grid finetune-grid--predict">
          <section className="panel">
            <h2>ステップ5 — 予測</h2>
            <p className="msg-muted small">
              <code>POST /api/predict</code> を呼び出します。チャート用の市場履歴は yfinance（5
              分足）です。銘柄はヘッダコンテキストの選択に追従します。
            </p>
            <div className="form-group">
              <label htmlFor="ft-pred-ticker">市場履歴用銘柄 ID</label>
              <select
                id="ft-pred-ticker"
                value={selectedTickerId}
                onChange={(e) => setSelectedTickerId(e.target.value)}
              >
                {tickers.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
              <p className="msg-muted small">
                yfinance シンボル表示: <strong>{yfinanceDisplaySymbol}</strong>
              </p>
            </div>
            <div className="form-group chart-period-row">
              <label htmlFor="ft-mh-period">市場履歴の取得期間</label>
              <select
                id="ft-mh-period"
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
            <button type="button" className="btn btn-primary" disabled={!canPredict} onClick={() => void handlePredict()}>
              予測を開始
            </button>
            {busy && <p className="msg-muted small">処理中…</p>}
          </section>

          <section className="panel">
            <h2>予測結果チャート（ECharts）</h2>
            {!predictResult?.success && (
              <p className="msg-muted">予測実行後に、市場履歴・予測・実測を統合したローソクが表示されます。</p>
            )}
            {predictResult?.success && (
              <>
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
                <>
                  <AccuracyMetricsPanel
                    predictionType={predictResult.prediction_type}
                    predictions={predictResult.prediction_results}
                    actuals={predictResult.actual_data}
                  />
                  <ComparisonPanel
                    predictionType={predictResult.prediction_type}
                    predictions={predictResult.prediction_results}
                    actuals={predictResult.actual_data}
                  />
                </>
              )}
          </section>
        </div>
      )}

      {activeWizardStep === 5 && (
        <div className="finetune-grid finetune-grid--backtest">
          <section className="panel">
            <h2>ステップ6 — バックテスト（v1.0）</h2>
            <p className="msg-muted small">
              <code>POST /api/backtest/run</code> を呼び出します。評価窓の全バーは{' '}
              <code>train_last_timestamp</code> より後である必要があります（リーク防止）。
            </p>

            <div className="form-group">
              <label htmlFor="ft-bt-data">data_path</label>
              <input
                id="ft-bt-data"
                type="text"
                value={btDataPath}
                onChange={(e) => setBtDataPath(e.target.value)}
                spellCheck={false}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-bt-ev-s">eval_start（任意・ISO）</label>
              <input
                id="ft-bt-ev-s"
                type="text"
                value={btEvalStart}
                onChange={(e) => setBtEvalStart(e.target.value)}
                placeholder="例: 2024-06-01"
                spellCheck={false}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-bt-ev-e">eval_end（任意・ISO）</label>
              <input
                id="ft-bt-ev-e"
                type="text"
                value={btEvalEnd}
                onChange={(e) => setBtEvalEnd(e.target.value)}
                spellCheck={false}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-bt-tls">train_last_timestamp（必須）</label>
              <input
                id="ft-bt-tls"
                type="text"
                value={btTrainLast}
                onChange={(e) => setBtTrainLast(e.target.value)}
                spellCheck={false}
              />
            </div>

            <div className="finetune-model-modes" role="radiogroup" aria-label="バックテスト checkpoint">
              <label>
                <input
                  type="radio"
                  name="ft-bt-ckpt"
                  checked={btCkptMode === 'job'}
                  onChange={() => setBtCkptMode('job')}
                />{' '}
                train_job_id
              </label>
              <label>
                <input
                  type="radio"
                  name="ft-bt-ckpt"
                  checked={btCkptMode === 'local'}
                  onChange={() => setBtCkptMode('local')}
                />{' '}
                ローカル checkpoint
              </label>
            </div>

            {btCkptMode === 'job' ? (
              <div className="form-group">
                <label htmlFor="ft-bt-job">train_job_id</label>
                <input
                  id="ft-bt-job"
                  type="text"
                  value={btTrainJobId}
                  onChange={(e) => setBtTrainJobId(e.target.value)}
                  spellCheck={false}
                />
              </div>
            ) : (
              <>
                <div className="form-group">
                  <label htmlFor="ft-bt-ltok">local_tokenizer_path</label>
                  <input
                    id="ft-bt-ltok"
                    type="text"
                    value={btLocalTok}
                    onChange={(e) => setBtLocalTok(e.target.value)}
                    spellCheck={false}
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="ft-bt-lpred">local_predictor_path</label>
                  <input
                    id="ft-bt-lpred"
                    type="text"
                    value={btLocalPred}
                    onChange={(e) => setBtLocalPred(e.target.value)}
                    spellCheck={false}
                  />
                </div>
              </>
            )}

            <div className="form-group">
              <label htmlFor="ft-bt-lb">lookback</label>
              <input
                id="ft-bt-lb"
                type="number"
                min={2}
                value={btLookback}
                onChange={(e) => setBtLookback(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-bt-pl">pred_len（API 検証用・推論は 1 本先のみ使用）</label>
              <input
                id="ft-bt-pl"
                type="number"
                min={1}
                value={btPredLen}
                onChange={(e) => setBtPredLen(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-bt-t">T（temperature）</label>
              <input
                id="ft-bt-t"
                type="number"
                step="any"
                value={btT}
                onChange={(e) => setBtT(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-bt-topp">top_p</label>
              <input
                id="ft-bt-topp"
                type="number"
                step="any"
                value={btTopP}
                onChange={(e) => setBtTopP(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-bt-sc">sample_count</label>
              <input
                id="ft-bt-sc"
                type="number"
                min={1}
                value={btSampleCount}
                onChange={(e) => setBtSampleCount(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ft-bt-dev">device</label>
              <select
                id="ft-bt-dev"
                value={btDevice}
                onChange={(e) => setBtDevice(e.target.value)}
              >
                <option value="cpu">cpu</option>
                <option value="mps">mps</option>
                <option value="cuda">cuda</option>
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="ft-bt-mc">max_context（任意・ジョブ時は省略で config 値）</label>
              <input
                id="ft-bt-mc"
                type="text"
                value={btMaxContext}
                onChange={(e) => setBtMaxContext(e.target.value)}
                placeholder="空欄で既定"
                spellCheck={false}
              />
            </div>

            <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void handleRunBacktest()}>
              バックテスト実行
            </button>
            {busy && <p className="msg-muted">処理中…（モデル読込とバーごとの推論に時間がかかります）</p>}
          </section>

          <section className="panel">
            <h2>結果</h2>
            {!btResult?.metrics && <p className="msg-muted">未実行です。</p>}
            {btResult?.metrics && (
              <>
                <table className="data-table">
                  <tbody>
                    <tr>
                      <th>戦略 累積リターン</th>
                      <td>{(btResult.metrics.strategy_cumulative_return * 100).toFixed(4)} %</td>
                    </tr>
                    <tr>
                      <th>B&amp;H 累積リターン</th>
                      <td>{(btResult.metrics.bh_cumulative_return * 100).toFixed(4)} %</td>
                    </tr>
                    <tr>
                      <th>戦略 最大DD</th>
                      <td>{(btResult.metrics.strategy_max_drawdown * 100).toFixed(4)} %</td>
                    </tr>
                    <tr>
                      <th>B&amp;H 最大DD</th>
                      <td>{(btResult.metrics.bh_max_drawdown * 100).toFixed(4)} %</td>
                    </tr>
                    <tr>
                      <th>取引回数（ポジション変化）</th>
                      <td>{btResult.metrics.trade_count}</td>
                    </tr>
                  </tbody>
                </table>
                {btResult.series &&
                  btResult.series.timestamps.length > 0 &&
                  btResult.series.strategy_equity.length > 0 && (
                    <>
                      <h3 style={{ marginTop: '1rem' }}>累積倍率（戦略 vs B&amp;H）</h3>
                      <BacktestEquityChart
                        timestamps={btResult.series.timestamps}
                        strategyEquity={btResult.series.strategy_equity}
                        bhEquity={btResult.series.bh_equity}
                        height={360}
                      />
                    </>
                  )}
              </>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
