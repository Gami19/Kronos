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

/** POST /api/load-model */
export interface LoadModelResponse {
  success: boolean
  message?: string
  error?: string
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
