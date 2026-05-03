/** Flask がエラー時に返す JSON の共通形（success はエンドポイントにより省略可） */
export interface ApiErrorBody {
  error?: string
}

/**
 * Plotly Figure を JSON 化したオブジェクト（`POST /api/predict`・保存 JSON の chart）。
 * 完全な Plotly 型は持たず、参照用の最小キーのみ。
 */
export interface PlotlyFigureJSON {
  data?: unknown[]
  layout?: Record<string, unknown>
  frames?: unknown[]
  config?: Record<string, unknown>
}

/** GET /api/model-status */
export interface ModelStatusResponse {
  available: boolean
  loaded: boolean
  message: string
  current_model?: {
    name: string
    device: string
  }
}

/** GET /api/available-models */
export interface AvailableModelsResponse {
  models: Record<
    string,
    {
      name: string
      model_id: string
      tokenizer_id: string
      context_length: number
      params: string
      description: string
    }
  >
  model_available: boolean
}

/** GET /api/tickers の各要素 */
export interface TickerEntry {
  id: string
  label: string
  legacy_root?: boolean
}

/** GET /api/tickers */
export interface TickersResponse {
  success: boolean
  tickers: TickerEntry[]
  default_ticker: string | null
}

/** GET /api/data-files の各要素 */
export interface DataFileMeta {
  name: string
  path: string
  size: string
}

/** GET /api/prediction-results */
export interface PredictionResultListItem {
  id: string
  filename: string
  timestamp?: string
  prediction_type?: string
  file_path?: string
  prediction_params?: Record<string, unknown>
  counts?: {
    prediction_results: number
    actual_data: number
  }
}

export interface PredictionResultsListResponse {
  success: boolean
  results: PredictionResultListItem[]
}

export interface DataInfo {
  rows: number
  columns: string[]
  start_date?: string
  end_date?: string
  price_range?: {
    min: number
    max: number
  }
  prediction_columns?: string[]
  timeframe?: string
}

/** POST /api/load-data */
export interface LoadDataResponse {
  success: boolean
  data_info?: DataInfo
  ohlc_rows?: OhlcRow[]
  message?: string
  error?: string
}

/** POST /api/data/import-market */
export interface ImportMarketResponse {
  success: boolean
  ticker_id?: string
  file_path?: string
  message?: string
  error?: string
}

/** POST /api/data/upload */
export interface UploadDataResponse {
  success: boolean
  ticker_id?: string
  file_path?: string
  filename?: string
  error?: string
}

/** POST /api/data/validate の data_info（サマリのみ） */
export interface ValidateDataInfoSummary {
  rows: number
  columns: string[]
  start_date?: string | null
  end_date?: string | null
}

/** POST /api/data/validate（HTTP 200 + valid で成否） */
export interface ValidateDataResponse {
  valid: boolean
  error?: string
  file_path?: string | null
  message?: string
  data_info?: ValidateDataInfoSummary
}

/** POST /api/train/jobs */
export interface CreateTrainJobRequest {
  data_path: string
  pretrained_tokenizer?: string
  pretrained_predictor?: string
  device?: 'cuda' | 'cpu' | 'mps'
  tokenizer_learning_rate?: number
  predictor_learning_rate?: number
  tokenizer_epochs?: number
  basemodel_epochs?: number
  batch_size?: number
  log_interval?: number
  num_workers?: number
  seed?: number
  lookback_window?: number
  predict_window?: number
  max_context?: number
  clip?: number
  train_ratio?: number
  val_ratio?: number
  test_ratio?: number
  accumulation_steps?: number
  experiment_name?: string
  experiment_description?: string
  skip_existing?: boolean
  skip_tokenizer?: boolean
  skip_basemodel?: boolean
  device_id?: number
}

export interface TrainJobMeta {
  job_id: string
  status?: string
  created_at?: string
  updated_at?: string
  data_path?: string
  train_last_timestamp?: string
  config_path?: string
  exit_code?: number | null
  tokenizer_best_model_path?: string | null
  basemodel_best_model_path?: string | null
  error_message?: string | null
  device?: string
  pid?: number
}

export interface CreateTrainJobResponse {
  success: boolean
  job_id?: string
  meta?: Partial<TrainJobMeta>
  error?: string
}

export interface TrainJobListItem {
  job_id: string
  status: string
  created_at?: string
  exit_code?: number | null
}

export interface ListTrainJobsResponse {
  success: boolean
  jobs: TrainJobListItem[]
}

export interface GetTrainJobResponse {
  success: boolean
  meta?: TrainJobMeta
  error?: string
}

export interface TrainJobLogResponse {
  success: boolean
  job_id?: string
  log?: string
  error?: string
}

/** GET /api/market-history */
export interface MarketHistoryResponse {
  success: boolean
  ticker?: string
  interval?: string
  period?: string
  rows?: OhlcRow[]
  warnings?: string[]
  error?: string
}

export interface OhlcRow {
  timestamp: string | null
  open: number
  high: number
  low: number
  close: number
  volume?: number | null
  amount?: number | null
}

/** POST /api/load-model（model_key / train_job_id / local_* のいずれか一つ） */
export type LoadModelRequest =
  | {
      device: string
      model_key: string
      train_job_id?: undefined
      local_tokenizer_path?: undefined
      local_predictor_path?: undefined
      max_context?: undefined
    }
  | {
      device: string
      train_job_id: string
      model_key?: undefined
      local_tokenizer_path?: undefined
      local_predictor_path?: undefined
      max_context?: number
    }
  | {
      device: string
      local_tokenizer_path: string
      local_predictor_path: string
      model_key?: undefined
      train_job_id?: undefined
      max_context?: number
    }

/** POST /api/load-model */
export interface LoadModelResponse {
  success: boolean
  message?: string
  error?: string
  load_source?: 'hf' | 'train_job' | 'local'
  train_job_id?: string
  tokenizer_path?: string
  predictor_path?: string
  model_info?: {
    name: string
    params: string
    context_length: number
    description: string
  }
}

/** POST /api/predict */
export interface PredictRequest {
  file_path: string
  lookback: number
  pred_len: number
  temperature: number
  top_p: number
  sample_count: number
  start_date?: string
}

export interface PredictResponse {
  success: boolean
  prediction_type?: string
  chart?: PlotlyFigureJSON
  prediction_results?: OhlcRow[]
  actual_data?: OhlcRow[]
  has_comparison?: boolean
  message?: string
  error?: string
}

/** POST /api/backtest/run（v1.0 同期） */
export interface BacktestRunRequest {
  backtest_spec_version: '1.0'
  data_path: string
  train_last_timestamp: string
  eval_start?: string
  eval_end?: string
  train_job_id?: string
  local_tokenizer_path?: string
  local_predictor_path?: string
  lookback?: number
  pred_len?: number
  T?: number
  top_p?: number
  sample_count?: number
  device?: string
  max_context?: number
}

export interface BacktestMetricsV1 {
  strategy_cumulative_return: number
  bh_cumulative_return: number
  strategy_max_drawdown: number
  bh_max_drawdown: number
  trade_count: number
}

export interface BacktestSeriesV1 {
  timestamps: string[]
  strategy_equity: number[]
  bh_equity: number[]
}

export interface BacktestRunResponse {
  success: boolean
  backtest_spec_version?: string
  metrics?: BacktestMetricsV1
  series?: BacktestSeriesV1
  message?: string
  error?: string
}

/** GET /api/prediction-results/:id の全文 */
export interface PredictionDetailRecord {
  timestamp?: string
  file_path?: string
  prediction_type?: string
  prediction_params?: Record<string, unknown>
  input_data_summary?: Record<string, unknown>
  prediction_results?: OhlcRow[]
  actual_data?: OhlcRow[]
  chart?: PlotlyFigureJSON
  analysis?: Record<string, unknown>
}
